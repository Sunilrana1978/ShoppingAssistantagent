from typing import Optional, Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool


def before_tool_callback(
    tool: BaseTool,
    args: dict,
    tool_context: CallbackContext,
) -> Optional[Any]:
    """
    Executes before a tool runs to sanitize and validate input arguments.

    ADK signature:
        tool         — the BaseTool instance about to be called
        args         — dict of arguments the LLM is passing to the tool
        tool_context — CallbackContext; use tool_context.variables for session vars

    Returns:
        None      → proceed normally with the (possibly mutated) args.
        Any dict  → skip the tool call and use this as the tool response instead.
    """
    tool_name = getattr(tool, "name", str(tool)) if tool else ""
    session_vars = tool_context.variables

    # Inject session_id from session variables if the tool needs it
    if "session_id" not in args and session_vars.get("session_id"):
        args["session_id"] = session_vars.get("session_id")

    # Sanitize price_max for catalog search — must be a positive float
    if tool_name == "search_catalog":
        if args.get("price_max") is not None:
            try:
                args["price_max"] = abs(float(args["price_max"]))
            except (ValueError, TypeError):
                args["price_max"] = None

    # Returning None lets the tool execute with the (possibly mutated) args
    return None
