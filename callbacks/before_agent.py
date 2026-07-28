from typing import Any

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before the agent invocation.
    Populates user_name and membership_tier into session state based on user_id if present.
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

    if not isinstance(state, dict):
        return None

    # Extract channel_payload safely if present
    channel_payload = {}
    if hasattr(context, "channel_payload"):
        channel_payload = context.channel_payload
    elif isinstance(context, dict):
        channel_payload = context.get("channel_payload", {})

    if isinstance(channel_payload, str):
        try:
            import json
            channel_payload = json.loads(channel_payload)
        except Exception:
            channel_payload = {}

    # Read user_id if already present in state or context properties
    user_id = state.get("user_id")

    if not user_id and hasattr(context, "variables") and isinstance(context.variables, dict):
        user_id = context.variables.get("user_id")

    if not user_id and hasattr(context, "user_id") and getattr(context, "user_id", None):
        user_id = getattr(context, "user_id")

    if not user_id and isinstance(channel_payload, dict):
        user_id = channel_payload.get("user_id")

    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    # Look up user profile from mock database if user_id is provided
    mock_users = {
        "u_1029": {"name": "Alex", "membership_tier": "gold"},
        "u_1030": {"name": "Jordan", "membership_tier": "silver"},
        "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
        "guest": {"name": "Shopper", "membership_tier": "none"}
    }

    if user_id:
        state["user_id"] = user_id
        info = mock_users.get(user_id)
        if not info:
            for key, val in mock_users.items():
                if key in str(user_id).lower() or val["name"].lower() in str(user_id).lower():
                    info = val
                    break
        if not info:
            info = {"name": str(user_id).capitalize(), "membership_tier": "none"}

        state["user_name"] = info["name"]
        state["membership_tier"] = info["membership_tier"]
    else:
        if "user_name" not in state or not state["user_name"]:
            state["user_name"] = "Shopper"
        if "membership_tier" not in state or not state["membership_tier"]:
            state["membership_tier"] = "none"

    if "session_id" not in state or not state["session_id"]:
        sess_id = getattr(context, "session_id", None) if hasattr(context, "session_id") else (context.get("session_id") if isinstance(context, dict) else None)
        state["session_id"] = sess_id or "sess_default"

    return None
