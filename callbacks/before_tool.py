from typing import Any

def before_tool_callback(tool: Any = None, tool_input: Any = None, callback_context: Any = None) -> Any:
    """
    Hook executed before a tool runs to sanitize and validate input arguments.
    Supports (tool, tool_input, callback_context) signature expected by CX Agent Studio.
    """
    tool_name = getattr(tool, "name", str(tool)) if tool else ""
    tool_args = tool_input if isinstance(tool_input, dict) else (tool if isinstance(tool, dict) else {})
    context = callback_context if callback_context is not None else (tool_input if hasattr(tool_input, "state") else None)

    if hasattr(context, "state") and context.state is not None:
        state = context.state
    elif isinstance(context, dict):
        state = context.get("state", {})
    else:
        state = {}

    if isinstance(tool_args, dict) and isinstance(state, dict):
        if "session_id" not in tool_args and "session_id" in state:
            tool_args["session_id"] = state["session_id"]

        if tool_name == "search_catalog":
            if "price_max" in tool_args and tool_args["price_max"] is not None:
                try:
                    tool_args["price_max"] = abs(float(tool_args["price_max"]))
                except (ValueError, TypeError):
                    tool_args["price_max"] = None

    return tool_args
