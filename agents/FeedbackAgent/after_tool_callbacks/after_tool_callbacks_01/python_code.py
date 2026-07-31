from typing import Any, Optional, Dict, List

Tool = Any
CallbackContext = Any


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if not callback_context:
        return {}
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            return callback_context["state"]
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            return callback_context["variables"]
        return callback_context

    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        return callback_context.state
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        return callback_context.variables
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "state") and isinstance(getattr(session, "state"), dict):
            return session.state
        if hasattr(session, "variables") and isinstance(getattr(session, "variables"), dict):
            return session.variables
        if hasattr(session, "parameters") and isinstance(getattr(session, "parameters"), dict):
            return session.parameters
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across all Python object/dict types in CXAS Agent Engine."""
    if not callback_context:
        return

    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            callback_context["state"][key] = value
        elif "variables" in callback_context and isinstance(callback_context["variables"], dict):
            callback_context["variables"][key] = value
        else:
            callback_context[key] = value

    def _apply(target: Any):
        if target is None or isinstance(target, dict):
            return
        try:
            target[key] = value
        except Exception:
            pass
        try:
            setattr(target, key, value)
        except Exception:
            pass
        if hasattr(target, "set_parameter"):
            try:
                target.set_parameter(key, value)
            except Exception:
                pass

    _apply(callback_context)
    if hasattr(callback_context, "state"):
        _apply(getattr(callback_context, "state"))
    if hasattr(callback_context, "variables"):
        _apply(getattr(callback_context, "variables"))
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        _apply(session)
        if hasattr(session, "state"):
            _apply(getattr(session, "state"))
        if hasattr(session, "variables"):
            _apply(getattr(session, "variables"))
        if hasattr(session, "set_parameter"):
            try:
                session.set_parameter(key, value)
            except Exception:
                pass


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
