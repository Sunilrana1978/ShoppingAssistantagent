from typing import Any, Optional
import json

CallbackContext = Any
Content = Any

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
    from google.cloud.aiplatform_v1beta1 import MemoryBankServiceClient  # type: ignore
    _MEMORY_BANK_AVAILABLE = True
except ImportError:
    try:
        from google.cloud.aiplatform.memory import MemoryBankServiceClient  # type: ignore
        _MEMORY_BANK_AVAILABLE = True
    except ImportError:
        _MEMORY_BANK_AVAILABLE = False


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if not callback_context:
        return {}
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            return callback_context["state"]
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            return callback_context["variables"]
        return callback_context

    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        return callback_context.state
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        return callback_context.variables
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "state") and isinstance(getattr(session, "state"), dict):
            return session.state
        if hasattr(session, "variables") and isinstance(getattr(session, "variables"), dict):
            return session.variables
        if hasattr(session, "parameters") and isinstance(getattr(session, "parameters"), dict):
            return session.parameters
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across all Python object/dict types in CXAS Agent Engine."""
    if not callback_context:
        return

    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            callback_context["state"][key] = value
        elif "variables" in callback_context and isinstance(callback_context["variables"], dict):
            callback_context["variables"][key] = value
        else:
            callback_context[key] = value

    def _apply(target: Any):
        if target is None or isinstance(target, dict):
            return
        try:
            target[key] = value
        except Exception:
            pass
        try:
            setattr(target, key, value)
        except Exception:
            pass
        if hasattr(target, "set_parameter"):
            try:
                target.set_parameter(key, value)
            except Exception:
                pass

    _apply(callback_context)
    if hasattr(callback_context, "state"):
        _apply(getattr(callback_context, "state"))
    if hasattr(callback_context, "variables"):
        _apply(getattr(callback_context, "variables"))
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        _apply(session)
        if hasattr(session, "state"):
            _apply(getattr(session, "state"))
        if hasattr(session, "variables"):
            _apply(getattr(session, "variables"))
        if hasattr(session, "set_parameter"):
            try:
                session.set_parameter(key, value)
            except Exception:
                pass


import os

def _retrieve_memories(user_id: str, project_id: str = "ecom-cx-agent", location: str = "us-central1") -> list:
    """
    Retrieve up to 5 long-term memory facts from Vertex AI Memory Bank
    for the given user_id.
    """
    if not _MEMORY_BANK_AVAILABLE or not user_id:
        return []

    try:
        endpoint = f"{location}-aiplatform.googleapis.com"
        client = MemoryBankServiceClient(client_options={"api_endpoint": endpoint})
        engine_id = os.getenv("REASONING_ENGINE_ID", "432575911913586688")
        parent = f"projects/{project_id}/locations/{location}/reasoningEngines/{engine_id}"
        response = client.retrieve_memories(
            parent=parent,
            user_id=user_id,
            max_results=5,
        )
        memories = []
        if hasattr(response, "memories") and response.memories:
            for m in response.memories:
                fact = getattr(m, "fact", None) or getattr(m, "text", None) or str(m)
                if fact:
                    memories.append(fact)
        return memories
    except Exception:
        # Fall back gracefully to local profile memories if GCP Memory Bank is unconfigured
        return []


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
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
        
        # Check active cart from cart_service
        if cart_service:
            restored_cart = cart_service.get_cart(session_id, user_id=user_id)
            if restored_cart and restored_cart.get("items"):
                cart = restored_cart
                set_state_var(callback_context, "cart", cart)

        # Include previous session cart in long-term memory facts (without polluting active cart)
        if previous_cart and previous_cart.get("items"):
            prev_items = [f"{i.get('name')} (size {i.get('size')}, qty {i.get('qty')})" for i in previous_cart["items"]]
            memory_fact = f"User previously had items in cart in past chat: {', '.join(prev_items)} with Total ${previous_cart.get('total')}."
            if memory_fact not in memories:
                memories.append(memory_fact)

        set_state_var(callback_context, "long_term_memories", json.dumps(memories))

    except Exception:
        pass

    return None
