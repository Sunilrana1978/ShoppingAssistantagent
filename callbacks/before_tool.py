from typing import Dict, Any

def before_tool_callback(tool_name: str, tool_args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hook executed before a tool runs to sanitize and validate input arguments.
    """
    state = context.get("state", {})
    
    if "session_id" not in tool_args and "session_id" in state:
        tool_args["session_id"] = state["session_id"]

    if tool_name == "search_catalog":
        # Ensure max price is positive
        if "price_max" in tool_args and tool_args["price_max"] is not None:
            try:
                tool_args["price_max"] = abs(float(tool_args["price_max"]))
            except (ValueError, TypeError):
                tool_args["price_max"] = None

    return tool_args
