from typing import Optional, Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool


def before_tool_callback(
    tool: BaseTool,
    input: dict,
    callback_context: CallbackContext,
) -> Optional[Any]:
    """
    Executes before a tool runs to sanitize and validate input arguments.

    CXAS/ADK signature:
        tool             — the BaseTool instance about to be called
        input            — dict of arguments the LLM is passing to the tool
        callback_context — CallbackContext; use callback_context.variables for session vars

    Returns:
        None      → proceed normally with the (possibly mutated) input args.
        Any dict  → skip the tool call and use this as the tool response instead.

    ⚠️  Parameter names MUST match what the CXAS runtime injects by keyword:
        'input' (not 'args') and 'callback_context' (not 'tool_context').
    """
    tool_name = getattr(tool, "name", str(tool)) if tool else ""
    session_vars = callback_context.variables

    # Inject session_id from session variables if the tool needs it
    if "session_id" not in input and session_vars.get("session_id"):
        input["session_id"] = session_vars.get("session_id")

    # Sanitize price_max for catalog search — must be a positive float
    if tool_name == "search_catalog":
        if input.get("price_max") is not None:
            try:
                input["price_max"] = abs(float(input["price_max"]))
            except (ValueError, TypeError):
                input["price_max"] = None

    # Returning None lets the tool execute with the (possibly mutated) input
    return None
