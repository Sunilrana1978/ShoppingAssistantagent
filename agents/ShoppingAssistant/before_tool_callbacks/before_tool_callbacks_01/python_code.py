from typing import Optional, Any

try:
    from google.adk.agents.callback_context import CallbackContext
except ImportError:
    CallbackContext = Any

try:
    from google.adk.tools import BaseTool
except ImportError:
    BaseTool = Any


def before_tool_callback(
    tool: BaseTool,
    input: dict,
    callback_context: CallbackContext,
) -> Optional[Any]:
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
