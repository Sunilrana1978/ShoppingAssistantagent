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
        if isinstance(tool_output, dict) and tool_output.get("status") == "success":
            if tool_name == "add_to_cart" and "added_item" in tool_output:
                added = tool_output["added_item"]
                cart_service.add_item(
                    session_id=session_id,
                    sku=added.get("sku"),
                    qty=int(added.get("qty", 1)),
                    size=added.get("size")
                )
            elif tool_name == "remove_from_cart" and "removed_sku" in tool_output:
                cart_service.remove_item(session_id=session_id, sku=tool_output["removed_sku"])
            elif "cart" in tool_output and not tool_output["cart"].get("items") == [] and not tool_name in ["add_to_cart", "remove_from_cart"]:
                sc = cart_service.get_cart(session_id)
                sc["items"] = tool_output["cart"].get("items", [])

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
