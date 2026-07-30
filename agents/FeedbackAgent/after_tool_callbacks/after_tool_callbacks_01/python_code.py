from typing import Any, Optional, Dict, List

Tool = Any
CallbackContext = Any


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

    if tool_name == "submit_feedback":
        if tool_output.get("status") == "success":
            set_var("feedback_submitted", True)
            set_var("last_feedback_id", tool_output.get("feedback_id"))

    return tool_output
