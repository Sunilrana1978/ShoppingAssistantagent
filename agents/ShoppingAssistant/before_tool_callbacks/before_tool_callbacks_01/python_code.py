from typing import Any, Optional, Dict, List

Tool = Any
CallbackContext = Any


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
        session_vars = callback_context.variables

        if "session_id" not in input and session_vars.get("session_id"):
            input["session_id"] = session_vars.get("session_id")

        if tool_name == "search_catalog":
            if input.get("price_max") is not None:
                try:
                    input["price_max"] = abs(float(input["price_max"]))
                except (ValueError, TypeError):
                    input["price_max"] = None

    except Exception:
        pass

    return None
