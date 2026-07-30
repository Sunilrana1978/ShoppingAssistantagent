from typing import Any, Optional

try:
    from services.user_service import user_service
except ImportError:
    user_service = None


def before_agent_callback(callback_context: Any) -> Optional[Any]:
    """
    Executes at the beginning of each agent turn.
    Reads user_id from session state, looks up profile, and populates
    user_name and membership_tier.
    """
    try:
        if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
            state = callback_context.state
        elif hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
            state = callback_context.variables
        elif isinstance(callback_context, dict):
            if "state" in callback_context and isinstance(callback_context["state"], dict):
                state = callback_context["state"]
            elif "variables" in callback_context and isinstance(callback_context["variables"], dict):
                state = callback_context["variables"]
            else:
                state = callback_context
        else:
            state = {}

        def set_var(k: str, v: Any):
            state[k] = v
            if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
                callback_context.state[k] = v
            if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
                callback_context.variables[k] = v
            if isinstance(callback_context, dict):
                if "state" in callback_context and isinstance(callback_context["state"], dict):
                    callback_context["state"][k] = v
                if "variables" in callback_context and isinstance(callback_context["variables"], dict):
                    callback_context["variables"][k] = v
                callback_context[k] = v

        user_id = state.get("user_id", None)
        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id or user_id.lower() == "guest":
            if not state.get("user_name"):
                set_var("user_name", "Shopper")
            return None

        if user_service:
            profile = user_service.get_user_profile(user_id)
        else:
            mock_users = {
                "u_1029": {"name": "Alex", "membership_tier": "gold"},
                "u_1030": {"name": "Jordan", "membership_tier": "silver"},
                "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
            }
            profile = mock_users.get(
                user_id,
                {"name": user_id.capitalize(), "membership_tier": "none"},
            )

        name = profile.get("user_name") or profile.get("name", "Shopper")
        tier = profile.get("membership_tier", "none")

        set_var("user_id", user_id)
        set_var("user_name", name)
        set_var("membership_tier", tier)

    except Exception:
        pass

    return None
