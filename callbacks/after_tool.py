from typing import Dict, Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

def after_tool_callback(tool: Any, tool_input: Any = None, callback_context: Any = None, tool_response: Any = None) -> Any:
    """
    Hook executed after a tool call finishes.
    Signature expected by CX Agent Studio:
    (tool: Tool, tool_input: dict[str, Any], callback_context: CallbackContext, tool_response: dict[str, Any]) -> dict
    """
    # Support 3-arg call fallback for local tests: (tool_name, tool_output, context)
    if tool_response is None and isinstance(tool_input, dict) and isinstance(callback_context, dict):
        tool_name = str(tool)
        tool_output = tool_input
        ctx = callback_context
    else:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        ctx = callback_context
        tool_output = tool_response if tool_response is not None else (tool_input if isinstance(tool_input, dict) else {})

    if hasattr(ctx, "state") and ctx.state is not None:
        state = ctx.state
    elif isinstance(ctx, dict):
        if "state" not in ctx or not isinstance(ctx["state"], dict):
            ctx["state"] = {}
        state = ctx["state"]
    else:
        state = {}

    session_id = state.get("session_id", "sess_default") if isinstance(state, dict) else "sess_default"
    discount_pct = float(state.get("discount_pct", 0)) if isinstance(state, dict) else 0.0

    if tool_name in ["add_to_cart", "get_cart", "remove_from_cart"]:
        if isinstance(tool_output, dict) and tool_output.get("status") == "success":
            if cart_service:
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
                elif "cart" in tool_output and not tool_output["cart"].get("items") == [] and tool_name not in ["add_to_cart", "remove_from_cart"]:
                    sc = cart_service.get_cart(session_id)
                    sc["items"] = tool_output["cart"].get("items", [])
                
                updated_cart = cart_service.update_cart_pricing(session_id, discount_pct)
                if isinstance(state, dict):
                    state["cart"] = updated_cart
                tool_output["cart"] = updated_cart
            else:
                cart = state.get("cart", {"items": [], "subtotal": 0.0, "discount_pct": discount_pct, "discount_amount": 0.0, "total": 0.0}) if isinstance(state, dict) else {"items": [], "subtotal": 0.0, "discount_pct": discount_pct, "discount_amount": 0.0, "total": 0.0}
                if isinstance(tool_output, dict) and "cart" in tool_output:
                    cart = tool_output["cart"]
                subtotal = sum(float(item.get("price", 0.0)) * int(item.get("qty", 1)) for item in cart.get("items", []))
                disc_amt = round(subtotal * (discount_pct / 100.0), 2)
                total = round(subtotal - disc_amt, 2)
                cart["subtotal"] = subtotal
                cart["discount_pct"] = discount_pct
                cart["discount_amount"] = disc_amt
                cart["total"] = total
                if isinstance(state, dict):
                    state["cart"] = cart
                tool_output["cart"] = cart

    elif tool_name == "get_discount":
        if isinstance(tool_output, dict) and "discount_pct" in tool_output:
            if isinstance(state, dict):
                state["discount_pct"] = tool_output["discount_pct"]
            if cart_service:
                updated_cart = cart_service.update_cart_pricing(session_id, tool_output["discount_pct"])
                if isinstance(state, dict):
                    state["cart"] = updated_cart
            elif isinstance(state, dict) and "cart" in state and isinstance(state["cart"], dict):
                cart = state["cart"]
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (tool_output["discount_pct"] / 100.0), 2)
                cart["discount_pct"] = tool_output["discount_pct"]
                cart["discount_amount"] = disc_amt
                cart["total"] = round(subtotal - disc_amt, 2)

    elif tool_name == "get_user_profile":
        if isinstance(tool_output, dict) and isinstance(state, dict):
            name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
            state["user_name"] = name
            state["membership_tier"] = tool_output.get("membership_tier", "none")

    elif tool_name == "search_catalog":
        if isinstance(tool_output, dict) and "products" in tool_output and isinstance(state, dict):
            state["search_results"] = tool_output["products"]

    elif tool_name == "submit_feedback":
        if isinstance(tool_output, dict) and tool_output.get("status") == "success" and isinstance(state, dict):
            state["feedback_submitted"] = True
            state["last_feedback_id"] = tool_output.get("feedback_id")

    return tool_output
