from typing import Optional, Any, Dict, List

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None


def after_tool_callback(
    tool: BaseTool,
    input: dict,
    callback_context: CallbackContext,
    tool_response: Any,
) -> Optional[Any]:
    """
    Executes after a tool call finishes to update session variables
    and recompute cart pricing.

    CXAS/ADK signature:
        tool             — the BaseTool instance that was called
        input            — the arguments that were passed to the tool
        callback_context — CallbackContext; use callback_context.variables for session vars
        tool_response    — the raw dict returned by the tool function

    Returns:
        None      → the original tool_response is passed back to the LLM as-is.
        Any dict  → this value is passed to the LLM instead of tool_response.

    ⚠️  Parameter names MUST match what the CXAS runtime injects by keyword:
        'input' (not 'args') and 'callback_context' (not 'tool_context').
    """
    tool_name = getattr(tool, "name", str(tool)) if tool else ""
    session_vars = callback_context.variables
    tool_output = tool_response if isinstance(tool_response, dict) else {}

    session_id = session_vars.get("session_id", "sess_default")
    discount_pct = float(session_vars.get("discount_pct", 0))

    # ------------------------------------------------------------------
    # Cart operations: add_to_cart, get_cart, remove_from_cart
    # ------------------------------------------------------------------
    if tool_name in ["add_to_cart", "get_cart", "remove_from_cart"]:
        if tool_output.get("status") == "success":
            if cart_service:
                if tool_name == "add_to_cart" and "added_item" in tool_output:
                    added = tool_output["added_item"]
                    cart_service.add_item(
                        session_id=session_id,
                        sku=added.get("sku"),
                        qty=int(added.get("qty", 1)),
                        size=added.get("size"),
                    )
                elif tool_name == "remove_from_cart" and "removed_sku" in tool_output:
                    cart_service.remove_item(
                        session_id=session_id,
                        sku=tool_output["removed_sku"],
                    )

                updated_cart = cart_service.update_cart_pricing(session_id, discount_pct)
                callback_context.variables["cart"] = updated_cart
                tool_output["cart"] = updated_cart
            else:
                # Fallback: recompute cart pricing without cart_service
                cart = session_vars.get(
                    "cart",
                    {"items": [], "subtotal": 0.0, "discount_pct": discount_pct,
                     "discount_amount": 0.0, "total": 0.0},
                )
                if "cart" in tool_output:
                    cart = tool_output["cart"]
                subtotal = sum(
                    float(item.get("price", 0.0)) * int(item.get("qty", 1))
                    for item in cart.get("items", [])
                )
                disc_amt = round(subtotal * (discount_pct / 100.0), 2)
                cart.update({
                    "subtotal": subtotal,
                    "discount_pct": discount_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                callback_context.variables["cart"] = cart
                tool_output["cart"] = cart

    # ------------------------------------------------------------------
    # get_discount: persist discount_pct and recompute cart
    # ------------------------------------------------------------------
    elif tool_name == "get_discount":
        if "discount_pct" in tool_output:
            new_pct = tool_output["discount_pct"]
            callback_context.variables["discount_pct"] = new_pct
            if cart_service:
                updated_cart = cart_service.update_cart_pricing(session_id, new_pct)
                callback_context.variables["cart"] = updated_cart
            elif session_vars.get("cart"):
                cart = dict(session_vars["cart"])
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (new_pct / 100.0), 2)
                cart.update({
                    "discount_pct": new_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                callback_context.variables["cart"] = cart

    # ------------------------------------------------------------------
    # get_user_profile: persist user_name and membership_tier
    # ------------------------------------------------------------------
    elif tool_name == "get_user_profile":
        name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
        callback_context.variables["user_name"] = name
        callback_context.variables["membership_tier"] = tool_output.get("membership_tier", "none")

    # ------------------------------------------------------------------
    # search_catalog: cache results for after_model rich cards
    # ------------------------------------------------------------------
    elif tool_name == "search_catalog":
        if "products" in tool_output:
            callback_context.variables["search_results"] = tool_output["products"]

    # ------------------------------------------------------------------
    # submit_feedback: mark submission complete
    # ------------------------------------------------------------------
    elif tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            callback_context.variables["feedback_submitted"] = True
            callback_context.variables["last_feedback_id"] = tool_output.get("feedback_id")

    return tool_output
