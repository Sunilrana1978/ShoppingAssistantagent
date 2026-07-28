from typing import Any

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before the agent invocation.
    Extracts user_id from all possible CX Agent Studio context properties (state, variables, session, channel_payload).
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

    if not isinstance(channel_payload, dict):
        channel_payload = {}

    # Exhaustive search for user_id across all CX Agent Studio context attributes
    user_id = None

    # 1. Check state dict/object
    if isinstance(state, dict) and state.get("user_id"):
        user_id = state["user_id"]
    elif hasattr(state, "user_id") and getattr(state, "user_id", None):
        user_id = getattr(state, "user_id")

    # 2. Check context.variables (dict or object)
    if not user_id and hasattr(context, "variables") and getattr(context, "variables", None):
        vars_obj = getattr(context, "variables")
        if isinstance(vars_obj, dict):
            user_id = vars_obj.get("user_id")
        elif hasattr(vars_obj, "user_id"):
            user_id = getattr(vars_obj, "user_id")

    # 3. Check direct user_id attribute on context
    if not user_id and hasattr(context, "user_id") and getattr(context, "user_id", None):
        user_id = getattr(context, "user_id")

    # 4. Check context.session or context.session_variables
    if not user_id and hasattr(context, "session") and getattr(context, "session", None):
        sess_obj = getattr(context, "session")
        if isinstance(sess_obj, dict):
            user_id = sess_obj.get("user_id")
        elif hasattr(sess_obj, "user_id"):
            user_id = getattr(sess_obj, "user_id")

    # 5. Check channel_payload
    if not user_id and channel_payload.get("user_id"):
        user_id = channel_payload["user_id"]

    # 6. Check context dict if context is a dict
    if not user_id and isinstance(context, dict):
        user_id = context.get("user_id")

    # Clean user_id string if present
    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    # Default to guest only if no user_id found anywhere
    if not user_id:
        user_id = "guest"

    mock_users = {
        "u_1029": {"name": "Alex", "membership_tier": "gold"},
        "u_1030": {"name": "Jordan", "membership_tier": "silver"},
        "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
        "guest": {"name": "Valued Shopper", "membership_tier": "none"}
    }

    # Match user info from mock_users
    info = mock_users.get(user_id)
    if not info:
        # Fallback partial matching (e.g. "1029", "alex")
        for key, val in mock_users.items():
            if key in str(user_id).lower() or val["name"].lower() in str(user_id).lower():
                info = val
                break
    if not info:
        info = {"name": str(user_id).capitalize(), "membership_tier": "guest"}

    if isinstance(state, dict):
        state["user_id"] = user_id
        state["user_name"] = info["name"]
        state["membership_tier"] = info["membership_tier"]

        if "session_id" not in state or not state["session_id"]:
            sess_id = getattr(context, "session_id", None) if hasattr(context, "session_id") else (context.get("session_id") if isinstance(context, dict) else None)
            state["session_id"] = sess_id or "sess_default"

    return None
