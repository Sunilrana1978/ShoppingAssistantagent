from typing import Dict, Any
from services.cart_service import cart_service

def after_tool_callback(tool_name: str, tool_output: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hook executed after a tool call finishes.
    Recomputes cart pricing server-side when cart tools complete and tracks feedback state.
    """
    state = context.get("state", {})
    session_id = state.get("session_id", "sess_default")
    discount_pct = float(state.get("discount_pct", 0))

    if tool_name in ["add_to_cart", "get_cart", "remove_from_cart"]:
        updated_cart = cart_service.update_cart_pricing(session_id, discount_pct)
        state["cart"] = updated_cart
        if isinstance(tool_output, dict):
            tool_output["cart"] = updated_cart

    elif tool_name == "get_discount":
        if isinstance(tool_output, dict) and "discount_pct" in tool_output:
            state["discount_pct"] = tool_output["discount_pct"]
            updated_cart = cart_service.update_cart_pricing(session_id, tool_output["discount_pct"])
            state["cart"] = updated_cart

    elif tool_name == "get_user_profile":
        if isinstance(tool_output, dict):
            name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
            state["user_name"] = name
            state["membership_tier"] = tool_output.get("membership_tier", "none")

    elif tool_name == "search_catalog":
        if isinstance(tool_output, dict) and "products" in tool_output:
            state["search_results"] = tool_output["products"]

    elif tool_name == "submit_feedback":
        if isinstance(tool_output, dict) and tool_output.get("status") == "success":
            state["feedback_submitted"] = True
            state["last_feedback_id"] = tool_output.get("feedback_id")

    return tool_output
