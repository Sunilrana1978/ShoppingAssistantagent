from typing import Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

try:
    from google.cloud.aiplatform.memory import MemoryBankServiceClient  # type: ignore
    _MEMORY_BANK_AVAILABLE = True
except ImportError:
    _MEMORY_BANK_AVAILABLE = False

MEMORY_BANK_RESOURCE_NAME = "projects/ecom-cx-agent/locations/us-central1/memoryBanks/shopping-assistant-user-memory-bank"


def _save_live_memory(user_id: str, fact_text: str) -> None:
    """Save a long-term fact to live Vertex AI Memory Bank if available."""
    if not _MEMORY_BANK_AVAILABLE or not user_id or user_id.lower() in ("guest", "u_guest"):
        return
    try:
        client = MemoryBankServiceClient()
        client.generate_and_save_memory(
            parent=MEMORY_BANK_RESOURCE_NAME,
            user_id=user_id,
            text=fact_text,
        )
    except Exception:
        pass


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


def after_tool_callback(
    tool: Any,
    input: Any = None,
    callback_context: Any = None,
    tool_response: Any = None,
) -> Optional[Any]:
    """
    Executes after a tool call finishes to update session variables
    and recompute cart pricing.
    """
    if tool_response is None and callback_context is not None:
        tool_name = str(tool)
        tool_output = input if isinstance(input, dict) else {}
        context_obj = callback_context
    else:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        tool_output = tool_response if isinstance(tool_response, dict) else (input if isinstance(input, dict) else {})
        context_obj = callback_context if callback_context is not None else input

    state = get_state(context_obj)
    session_id = state.get("session_id", "sess_default")
    user_id = state.get("user_id", "")
    discount_pct = float(state.get("discount_pct", 0))

    if tool_name in ("add_to_cart", "remove_from_cart", "get_cart"):
        cart = tool_output.get("cart") or state.get("cart")
        if cart and isinstance(cart, dict):
            subtotal = float(cart.get("subtotal", 0.0))
            disc_amt = round(subtotal * (discount_pct / 100.0), 2)
            cart.update({
                "discount_pct": discount_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2),
            })
            set_state_var(context_obj, "cart", cart)
            tool_output["cart"] = cart

            # Save live memory fact to Vertex AI Memory Bank
            if user_id and tool_name == "add_to_cart" and cart.get("items"):
                item_summaries = [f"{i.get('name')} (size {i.get('size')})" for i in cart["items"]]
                fact = f"User added {', '.join(item_summaries)} to cart for ${cart.get('total')}."
                _save_live_memory(user_id, fact)

    elif tool_name == "get_discount":
        if "discount_pct" in tool_output:
            new_pct = tool_output["discount_pct"]
            set_state_var(context_obj, "discount_pct", new_pct)
            if cart_service:
                updated_cart = cart_service.update_cart_pricing(session_id, new_pct)
                set_state_var(context_obj, "cart", updated_cart)
            elif state.get("cart"):
                cart = dict(state["cart"])
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (new_pct / 100.0), 2)
                cart.update({
                    "discount_pct": new_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                set_state_var(context_obj, "cart", cart)

    elif tool_name == "get_user_profile":
        name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
        set_state_var(context_obj, "user_name", name)
        set_state_var(context_obj, "membership_tier", tool_output.get("membership_tier", "none"))

    elif tool_name == "search_catalog":
        if "products" in tool_output:
            set_state_var(context_obj, "search_results", tool_output["products"])

    elif tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            set_state_var(context_obj, "feedback_submitted", True)
            set_state_var(context_obj, "last_feedback_id", tool_output.get("feedback_id"))
            if user_id:
                _save_live_memory(user_id, f"User submitted rating {tool_output.get('rating')} star feedback.")

    return tool_output
