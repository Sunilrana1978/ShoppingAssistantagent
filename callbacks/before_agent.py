from typing import Any

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before the agent invocation.
    Extracts user_id from pre-existing state/variables, channel payload, or defaults to guest.
    Pre-populates user_name and membership_tier into session state so agents can greet by name.
    Compatible with both CX Agent Studio CallbackContext objects and Python dict contexts.
    Modifies context state in place and returns None (no overridden content payload).
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

    # Extract pre-existing user_id from state, variables, or channel_payload
    user_id = None
    if isinstance(state, dict) and state.get("user_id"):
        user_id = state["user_id"]

    if not user_id and hasattr(context, "variables") and isinstance(context.variables, dict):
        user_id = context.variables.get("user_id")

    if not user_id and hasattr(context, "user_id"):
        user_id = getattr(context, "user_id", None)

    if not user_id:
        user_id = channel_payload.get("user_id")

    if not user_id:
        user_id = "guest"

    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    if isinstance(state, dict):
        state["user_id"] = user_id

        if "session_id" not in state or not state["session_id"]:
            sess_id = getattr(context, "session_id", None) if hasattr(context, "session_id") else (context.get("session_id") if isinstance(context, dict) else None)
            state["session_id"] = sess_id or "sess_default"

        # Pre-populate user profile attributes if missing
        if "user_name" not in state or not state["user_name"]:
            mock_users = {
                "u_1029": {"name": "Alex", "membership_tier": "gold"},
                "u_1030": {"name": "Jordan", "membership_tier": "silver"},
                "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
                "guest": {"name": "Shopper", "membership_tier": "none"}
            }
            info = mock_users.get(user_id, {"name": "Shopper", "membership_tier": "none"})
            state["user_name"] = info["name"]
            state["membership_tier"] = info["membership_tier"]

    return None
