from typing import Any, Optional

try:
    from services.user_service import user_service
except ImportError:
    user_service = None


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        return callback_context.state
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        return callback_context.variables
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            return callback_context["state"]
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            return callback_context["variables"]
        return callback_context
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across CXAS runtime and local test harnesses."""
    state = get_state(callback_context)
    state[key] = value
    if hasattr(callback_context, "state") and isinstance(getattr(callback_context, "state"), dict):
        callback_context.state[key] = value
    if hasattr(callback_context, "variables") and isinstance(getattr(callback_context, "variables"), dict):
        callback_context.variables[key] = value
    if isinstance(callback_context, dict):
        if "state" in callback_context and isinstance(callback_context["state"], dict):
            callback_context["state"][key] = value
        if "variables" in callback_context and isinstance(callback_context["variables"], dict):
            callback_context["variables"][key] = value
        callback_context[key] = value


def before_agent_callback(callback_context: Any) -> Optional[Any]:
    """
    Executes at the beginning of each agent turn.
    Reads user_id from session state (or session parameter), looks up profile,
    and populates user_name and membership_tier into session state.
    """
    try:
        state = get_state(callback_context)

        # Retrieve user_id from state or session parameter fallback
        user_id = state.get("user_id")
        if not user_id and hasattr(callback_context, "session") and hasattr(callback_context.session, "get_parameter"):
            user_id = callback_context.session.get_parameter("user_id", "")

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id or user_id.lower() == "guest":
            if not state.get("user_name"):
                set_state_var(callback_context, "user_name", "Shopper")
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

        set_state_var(callback_context, "user_id", user_id)
        set_state_var(callback_context, "user_name", name)
        set_state_var(callback_context, "membership_tier", tier)

    except Exception:
        pass

    return None
