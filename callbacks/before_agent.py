from typing import Any

def find_key_in_obj(obj: Any, key_name: str, max_depth: int = 3) -> Any:
    """Recursively search for a key in nested dicts or Pydantic/object properties."""
    if max_depth <= 0 or obj is None:
        return None
    if isinstance(obj, dict):
        if key_name in obj and obj[key_name]:
            return obj[key_name]
        for k, v in obj.items():
            if isinstance(v, (dict, list, object)):
                res = find_key_in_obj(v, key_name, max_depth - 1)
                if res:
                    return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_key_in_obj(item, key_name, max_depth - 1)
            if res:
                return res
    elif hasattr(obj, "__dict__"):
        d = getattr(obj, "__dict__", {})
        if isinstance(d, dict) and key_name in d and d[key_name]:
            return d[key_name]
        for k, v in d.items():
            if not k.startswith("_"):
                res = find_key_in_obj(v, key_name, max_depth - 1)
                if res:
                    return res
    return None

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

    # Deep search for user_id across all context properties
    user_id = state.get("user_id")

    if not user_id:
        user_id = find_key_in_obj(context, "user_id")

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
