from typing import Any

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before the agent invocation.
    Extracts user_id from channel payload, preserves pre-existing state user_id, or defaults to guest.
    Compatible with both CX Agent Studio CallbackContext objects and Python dict contexts.
    """
    # Extract state safely
    if hasattr(context, "state") and context.state is not None:
        state = context.state
    elif isinstance(context, dict):
        if "state" not in context or not isinstance(context["state"], dict):
            context["state"] = {}
        state = context["state"]
    else:
        state = {}

    # Extract channel_payload safely
    if hasattr(context, "channel_payload"):
        channel_payload = context.channel_payload
    elif isinstance(context, dict):
        channel_payload = context.get("channel_payload", {})
    else:
        channel_payload = {}

    if isinstance(channel_payload, str):
        try:
            import json
            channel_payload = json.loads(channel_payload)
        except Exception:
            channel_payload = {}

    if not isinstance(channel_payload, dict):
        channel_payload = {}

    user_id = channel_payload.get("user_id")

    if not user_id and isinstance(state, dict):
        user_id = state.get("user_id")

    if not user_id:
        user_id = "guest"

    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    if isinstance(state, dict):
        state["user_id"] = user_id

        if "session_id" not in state:
            sess_id = getattr(context, "session_id", None) if hasattr(context, "session_id") else (context.get("session_id") if isinstance(context, dict) else None)
            state["session_id"] = sess_id or "sess_default"

    return context
