from typing import Any, Optional
import json

try:
    from services.user_service import user_service
except ImportError:
    user_service = None

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

# ---------------------------------------------------------------------------
# Long-Term Memory Bank integration (Vertex AI Memory Bank)
# ---------------------------------------------------------------------------
try:
    from google.cloud.aiplatform.memory import MemoryBankServiceClient  # type: ignore
    _MEMORY_BANK_AVAILABLE = True
except ImportError:
    _MEMORY_BANK_AVAILABLE = False


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        return callback_context.state
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        return callback_context.variables
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            return callback_context["state"]
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            return callback_context["variables"]
        return callback_context
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across CXAS runtime and local test harnesses."""
    state = get_state(callback_context)
    state[key] = value
    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        callback_context.state[key] = value
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        callback_context.variables[key] = value
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            callback_context["state"][key] = value
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            callback_context["variables"][key] = value
        callback_context[key] = value


def _retrieve_memories(user_id: str) -> list:
    """
    Retrieve up to 5 long-term memory facts from Vertex AI Memory Bank
    for the given user_id.
    """
    if not _MEMORY_BANK_AVAILABLE:
        return []

    try:
        client = MemoryBankServiceClient()
        response = client.retrieve_memories(
            user_id=user_id,
            max_results=5,
        )
        return [m.fact for m in response.memories if hasattr(m, "fact")]
    except Exception:
        return []


def before_agent_callback(callback_context: Any) -> Optional[Any]:
    """
    Executes at the beginning of each agent turn (RootAgent).

    Responsibilities:
    1. Reads user_id from session state or session parameter.
    2. Looks up user profile (name, membership_tier, memories, previous_cart).
    3. Retrieves long-term memories from Vertex AI Memory Bank and
       restores cross-session cart state for the user.
    4. Populates user_name, membership_tier, cart, and long_term_memories
       into session state for downstream agents.
    """
    try:
        state = get_state(callback_context)

        # ----------------------------------------------------------------
        # 1. Resolve user_id
        # ----------------------------------------------------------------
        user_id = state.get("user_id")
        if not user_id and hasattr(callback_context, "session") and hasattr(callback_context.session, "get_parameter"):
            user_id = callback_context.session.get_parameter("user_id", "")

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id or user_id.lower() in ("guest", "u_guest"):
            if not state.get("user_name"):
                set_state_var(callback_context, "user_name", "Shopper")
            set_state_var(callback_context, "long_term_memories", "[]")
            return None

        # ----------------------------------------------------------------
        # 2. Load user profile & long-term memories
        # ----------------------------------------------------------------
        if user_service:
            profile = user_service.get_user_profile(user_id)
        else:
            mock_users = {
                "u_1029": {
                    "name": "Alex",
                    "membership_tier": "gold",
                    "memories": ["User Alex previously added TrailBlaze Pro Trail Runner (size 10, qty 1) to cart for $110.49."],
                    "previous_cart": {
                        "session_id": "sess_previous",
                        "user_id": "u_1029",
                        "items": [{"sku": "sku_1029", "name": "TrailBlaze Pro Trail Runner", "qty": 1, "size": "10", "unit_price": 129.99}],
                        "subtotal": 129.99,
                        "discount_pct": 15.0,
                        "discount_amount": 19.50,
                        "total": 110.49
                    }
                },
                "u_1030": {
                    "name": "Jordan",
                    "membership_tier": "silver",
                    "memories": ["User Jordan previously added Apex Aero Road Running Shoes (size 10, qty 1) to cart for $134.99."],
                    "previous_cart": {
                        "session_id": "sess_previous",
                        "user_id": "u_1030",
                        "items": [{"sku": "sku_1030", "name": "Apex Aero Road Running Shoes", "qty": 1, "size": "10", "unit_price": 149.99}],
                        "subtotal": 149.99,
                        "discount_pct": 10.0,
                        "discount_amount": 15.00,
                        "total": 134.99
                    }
                },
                "u_1031": {"name": "Taylor", "membership_tier": "bronze", "memories": [], "previous_cart": {}},
            }
            profile = mock_users.get(
                user_id,
                {"name": user_id.capitalize(), "membership_tier": "none", "memories": [], "previous_cart": {}},
            )

        name = profile.get("user_name") or profile.get("name", "Shopper")
        tier = profile.get("membership_tier", "none")
        profile_memories = profile.get("memories", [])
        previous_cart = profile.get("previous_cart", {})

        set_state_var(callback_context, "user_id", user_id)
        set_state_var(callback_context, "user_name", name)
        set_state_var(callback_context, "membership_tier", tier)

        # ----------------------------------------------------------------
        # 3. Retrieve Vertex AI Memory Bank + Profile Memories
        # ----------------------------------------------------------------
        memories = _retrieve_memories(user_id)
        for m in profile_memories:
            if m not in memories:
                memories.append(m)

        # ----------------------------------------------------------------
        # 4. Cross-Session Cart Persistence & Memory Synthesis
        # ----------------------------------------------------------------
        session_id = state.get("session_id", "sess_default")
        cart = state.get("cart")
        
        # If cart in current session is empty, attempt lookup from previous_cart or cart_service
        if not cart or not cart.get("items"):
            if previous_cart and previous_cart.get("items"):
                cart = dict(previous_cart)
                cart["session_id"] = session_id
                set_state_var(callback_context, "cart", cart)
            elif cart_service:
                restored_cart = cart_service.get_cart(session_id, user_id=user_id)
                if restored_cart and restored_cart.get("items"):
                    cart = restored_cart
                    set_state_var(callback_context, "cart", cart)

        if cart and isinstance(cart, dict) and cart.get("items"):
            item_summaries = [f"{i.get('name')} (size {i.get('size')}, qty {i.get('qty')})" for i in cart["items"]]
            memory_fact = f"User has items in cart from previous chat: {', '.join(item_summaries)} with Total ${cart.get('total')}."
            if memory_fact not in memories:
                memories.append(memory_fact)

        set_state_var(callback_context, "long_term_memories", json.dumps(memories))

    except Exception:
        pass

    return None
