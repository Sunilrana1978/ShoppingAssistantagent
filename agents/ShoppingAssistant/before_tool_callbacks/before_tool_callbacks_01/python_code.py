from typing import Any, Optional


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
    tool: Any,
    input: dict,
    callback_context: Any,
) -> Optional[Any]:
    """
    Executes before a tool runs to sanitize and validate input arguments.
    """
    try:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        state = get_state(callback_context)

        if "session_id" not in input and state.get("session_id"):
            input["session_id"] = state.get("session_id")

        if tool_name == "search_catalog":
            if input.get("price_max") is not None:
                try:
                    input["price_max"] = abs(float(input["price_max"]))
                except (ValueError, TypeError):
                    input["price_max"] = None

    except Exception:
        pass

    return None
