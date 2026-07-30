from typing import Optional, Any, Dict, List

try:
    from google.adk.agents.callback_context import CallbackContext
except ImportError:
    CallbackContext = Any

try:
    from google.adk.tools import BaseTool
except ImportError:
    BaseTool = Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None


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

    if hasattr(context_obj, "variables") and isinstance(getattr(context_obj, "variables"), dict):
        session_vars = context_obj.variables
    elif isinstance(context_obj, dict):
        if "variables" in context_obj and isinstance(context_obj["variables"], dict):
            session_vars = context_obj["variables"]
        elif "state" in context_obj and isinstance(context_obj["state"], dict):
            session_vars = context_obj["state"]
        else:
            session_vars = context_obj
    else:
        session_vars = {}

    def set_var(key: str, val: Any):
        session_vars[key] = val
        if hasattr(context_obj, "variables") and isinstance(getattr(context_obj, "variables"), dict):
            context_obj.variables[key] = val
        elif isinstance(context_obj, dict):
            if "variables" in context_obj and isinstance(context_obj["variables"], dict):
                context_obj["variables"][key] = val
            elif "state" in context_obj and isinstance(context_obj["state"], dict):
                context_obj["state"][key] = val
            else:
                context_obj[key] = val

    session_id = session_vars.get("session_id", "sess_default")
    discount_pct = float(session_vars.get("discount_pct", 0))

    if tool_name in ("add_to_cart", "remove_from_cart", "get_cart"):
        cart = tool_output.get("cart") or session_vars.get("cart")
        if cart and isinstance(cart, dict):
            subtotal = float(cart.get("subtotal", 0.0))
            disc_amt = round(subtotal * (discount_pct / 100.0), 2)
            cart.update({
                "discount_pct": discount_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2),
            })
            set_var("cart", cart)
            tool_output["cart"] = cart

    elif tool_name == "get_discount":
        if "discount_pct" in tool_output:
            new_pct = tool_output["discount_pct"]
            set_var("discount_pct", new_pct)
            if cart_service:
                updated_cart = cart_service.update_cart_pricing(session_id, new_pct)
                set_var("cart", updated_cart)
            elif session_vars.get("cart"):
                cart = dict(session_vars["cart"])
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (new_pct / 100.0), 2)
                cart.update({
                    "discount_pct": new_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                set_var("cart", cart)

    elif tool_name == "get_user_profile":
        name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
        set_var("user_name", name)
        set_var("membership_tier", tool_output.get("membership_tier", "none"))

    elif tool_name == "search_catalog":
        if "products" in tool_output:
            set_var("search_results", tool_output["products"])

    elif tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            set_var("feedback_submitted", True)
            set_var("last_feedback_id", tool_output.get("feedback_id"))

    return tool_output
