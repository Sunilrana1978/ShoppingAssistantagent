from typing import Any

def before_tool_callback(tool: Any, tool_args: Any, context: Any) -> Any:
    """
    Hook executed before a tool runs to sanitize and validate input arguments.
    Compatible with CX Agent Studio CallbackContext object and dict context.
    """
    tool_name = getattr(tool, "name", str(tool)) if tool else ""

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
