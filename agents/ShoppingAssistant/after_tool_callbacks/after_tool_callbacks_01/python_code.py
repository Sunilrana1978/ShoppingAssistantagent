import logging
from typing import Any, Optional

Tool = Any
CallbackContext = Any

logger = logging.getLogger(__name__)


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if not callback_context:
        return {}
    if isinstance(callback_context, dict):
        if "state" in callback_context and callback_context["state"] is not None:
            return callback_context["state"]
        if "variables" in callback_context and callback_context["variables"] is not None:
            return callback_context["variables"]
        return callback_context

    if hasattr(callback_context, "state") and getattr(callback_context, "state") is not None:
        return getattr(callback_context, "state")
    if hasattr(callback_context, "variables") and getattr(callback_context, "variables") is not None:
        return getattr(callback_context, "variables")
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "state") and getattr(session, "state") is not None:
            return getattr(session, "state")
        if hasattr(session, "variables") and getattr(session, "variables") is not None:
            return getattr(session, "variables")
        if hasattr(session, "parameters") and getattr(session, "parameters") is not None:
            return getattr(session, "parameters")
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across all Python object/dict types in CXAS Agent Engine."""
    if not callback_context:
        return

    def _set_on_target(target: Any):
        if target is None:
            return
        if isinstance(target, dict):
            target[key] = value
            return
        try:
            target[key] = value
        except Exception:
            pass
        try:
            setattr(target, key, value)
        except Exception:
            pass
        for method in ("set_variable", "set_session_variable", "set_parameter", "update_variable", "add_variable"):
            if hasattr(target, method):
                try:
                    getattr(target, method)(key, value)
                except Exception:
                    pass

    _set_on_target(callback_context)

    state = get_state(callback_context)
    if state is not None and state is not callback_context:
        _set_on_target(state)

    for attr in ("state", "variables", "session_variables", "parameters"):
        if hasattr(callback_context, attr):
            _set_on_target(getattr(callback_context, attr))

    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        _set_on_target(session)
        for attr in ("state", "variables", "session_variables", "parameters"):
            if hasattr(session, attr):
                _set_on_target(session, attr)


def after_tool_callback(
    tool: Tool,
    input: dict[str, Any],
    callback_context: CallbackContext,
    tool_response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Executes after a tool call finishes.
    Updates cart math and session variables dynamically.
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
    discount_pct = float(state.get("discount_pct") or (tool_output.get("cart", {}).get("discount_pct") if isinstance(tool_output.get("cart"), dict) else 0) or 0)

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

    elif tool_name == "search_catalog":
        products = tool_output.get("products")
        if isinstance(products, list):
            set_state_var(context_obj, "search_results", products)

    elif tool_name == "get_discount":
        if "discount_pct" in tool_output:
            new_pct = tool_output["discount_pct"]
            set_state_var(context_obj, "discount_pct", new_pct)
            if state.get("cart"):
                cart = dict(state["cart"])
                subtotal = float(cart.get("subtotal", 0.0))
                disc_amt = round(subtotal * (new_pct / 100.0), 2)
                cart.update({
                    "discount_pct": new_pct,
                    "discount_amount": disc_amt,
                    "total": round(subtotal - disc_amt, 2),
                })
                set_state_var(context_obj, "cart", cart)

    elif tool_name in ("get_user_profile", "fetch_user_profile", "fetch_user_profile_fetch_user_profile"):
        name = tool_output.get("user_name") or tool_output.get("name") or "Shopper"
        set_state_var(context_obj, "user_name", name)
        set_state_var(context_obj, "membership_tier", tool_output.get("membership_tier", "none"))
        set_state_var(context_obj, "long_term_memories", tool_output.get("memories", []))
        set_state_var(context_obj, "preferences", tool_output.get("preferences", {}))

    elif tool_name in ("add_user_memory", "add_user_memory_add_user_memory"):
        if tool_output.get("status") == "success" and "fact" in tool_output:
            existing = state.get("long_term_memories") or []
            if isinstance(existing, list) and tool_output["fact"] not in existing:
                set_state_var(context_obj, "long_term_memories", existing + [tool_output["fact"]])

    elif tool_name in ("update_user_preferences", "update_user_preferences_update_user_preferences"):
        if tool_output.get("status") == "success" and "preferences" in tool_output:
            set_state_var(context_obj, "preferences", tool_output["preferences"])

    return tool_output
