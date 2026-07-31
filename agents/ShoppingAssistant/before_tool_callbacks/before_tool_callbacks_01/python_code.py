from typing import Any, Optional

Tool = Any
CallbackContext = Any


def get_session_id(callback_context: Any) -> str:
    """Helper to extract active session ID from Agent Engine callback context."""
    if not callback_context:
        return ""
    if hasattr(callback_context, "session_id") and getattr(callback_context, "session_id"):
        return str(getattr(callback_context, "session_id"))
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "id") and getattr(session, "id"):
            return str(getattr(session, "id"))
        if hasattr(session, "session_id") and getattr(session, "session_id"):
            return str(getattr(session, "session_id"))
        if isinstance(session, dict):
            return str(session.get("id") or session.get("session_id") or "")
    if isinstance(callback_context, dict):
        return str(callback_context.get("session_id") or callback_context.get("state", {}).get("session_id") or "")
    return ""


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


def before_tool_callback(
    tool: Tool,
    input: dict[str, Any],
    callback_context: CallbackContext,
) -> Optional[dict[str, Any]]:
    """
    Executes before a tool runs to sanitize and validate input arguments,
    injecting active session_id, user_id, and cart state.
    """
    try:
        tool_name = getattr(tool, "name", str(tool)) if tool else ""
        state = get_state(callback_context)
        sid = get_session_id(callback_context) or state.get("session_id")

        if sid and ("session_id" not in input or not input.get("session_id") or input.get("session_id") == "sess_default"):
            input["session_id"] = sid

        if state.get("user_id") and ("user_id" not in input or not input.get("user_id")):
            input["user_id"] = state.get("user_id")

        if tool_name in ("add_to_cart", "remove_from_cart", "get_cart"):
            if "current_cart" not in input or not input.get("current_cart"):
                if state.get("cart"):
                    input["current_cart"] = state.get("cart")
            if ("discount_pct" not in input or not input.get("discount_pct") or input.get("discount_pct") == 0) and state.get("discount_pct"):
                try:
                    input["discount_pct"] = float(state.get("discount_pct"))
                except (ValueError, TypeError):
                    pass

        if tool_name == "search_catalog":
            if input.get("price_max") is not None:
                try:
                    input["price_max"] = abs(float(input["price_max"]))
                except (ValueError, TypeError):
                    input["price_max"] = None

    except Exception:
        pass

    return None
