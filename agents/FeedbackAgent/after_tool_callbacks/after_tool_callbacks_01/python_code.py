from typing import Any, Optional, Dict, List

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
    tool: Tool,
    input: dict[str, Any],
    callback_context: CallbackContext,
    tool_response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Executes after a tool call finishes to update session variables.
    """
    if tool_response is None and callback_context is not None:
        tool_name = str(tool)
        tool_output = input if isinstance(input, dict) else {}
        context_obj = callback_context
    else:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        tool_output = tool_response if isinstance(tool_response, dict) else (input if isinstance(input, dict) else {})
        context_obj = callback_context if callback_context is not None else input

    if tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            set_state_var(context_obj, "feedback_submitted", True)
            set_state_var(context_obj, "last_feedback_id", tool_output.get("feedback_id"))

    return tool_output
