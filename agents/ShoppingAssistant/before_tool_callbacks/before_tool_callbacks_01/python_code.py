from typing import Any, Optional

Tool = Any
CallbackContext = Any


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


def before_tool_callback(
    tool: Tool,
    input: dict[str, Any],
    callback_context: CallbackContext,
) -> Optional[dict[str, Any]]:
    """
    Executes before a tool runs to sanitize and validate input arguments.
    """
    try:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        state = get_state(callback_context)

        if "session_id" not in input and state.get("session_id"):
            input["session_id"] = state.get("session_id")

        if tool_name in ("add_to_cart", "remove_from_cart", "get_cart"):
            if "current_cart" not in input and state.get("cart"):
                input["current_cart"] = state.get("cart")
            if ("discount_pct" not in input or not input.get("discount_pct")) and state.get("discount_pct"):
                try:
                    input["discount_pct"] = float(state.get("discount_pct"))
                except (ValueError, TypeError):
                    pass

        if tool_name == "search_catalog":
            if input.get("price_max") is not None:
                try:
                    input["price_max"] = abs(float(input["price_max"]))
                except (ValueError, TypeError):
                    input["price_max"] = None

    except Exception:
        pass

    return None
