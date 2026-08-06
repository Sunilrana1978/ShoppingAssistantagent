from typing import Any, Optional

CallbackContext = Any
Content = Any

try:
    from services.user_service import user_service
except ImportError:
    user_service = None


def get_state(callback_context: Any) -> dict:
    """Helper to retrieve state dict following CXAS Scrapi Design Guide standards."""
    if not callback_context:
        return {}
    if isinstance(callback_context, dict):
        if "state" in callback_context and callback_context["state"] is not None:
            return callback_context["state"]
        if "variables" in callback_context and callback_context["variables"] is not None:
            return callback_context["variables"]
        return callback_context

    if hasattr(callback_context, "state") and getattr(callback_context, "state") is not None:
        return getattr(callback_context, "state")
    if hasattr(callback_context, "variables") and getattr(callback_context, "variables") is not None:
        return getattr(callback_context, "variables")
    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        if hasattr(session, "state") and getattr(session, "state") is not None:
            return getattr(session, "state")
        if hasattr(session, "variables") and getattr(session, "variables") is not None:
            return getattr(session, "variables")
        if hasattr(session, "parameters") and getattr(session, "parameters") is not None:
            return getattr(session, "parameters")
    return {}


def set_state_var(callback_context: Any, key: str, value: Any) -> None:
    """Helper to write state variable across all Python object/dict types in CXAS Agent Engine."""
    if not callback_context:
        return

    def _set_on_target(target: Any):
        if target is None:
            return
        if isinstance(target, dict):
            target[key] = value
            return
        try:
            target[key] = value
        except Exception:
            pass
        try:
            setattr(target, key, value)
        except Exception:
            pass
        for method in ("set_variable", "set_session_variable", "set_parameter", "update_variable", "add_variable"):
            if hasattr(target, method):
                try:
                    getattr(target, method)(key, value)
                except Exception:
                    pass

    _set_on_target(callback_context)

    state = get_state(callback_context)
    if state is not None and state is not callback_context:
        _set_on_target(state)

    for attr in ("state", "variables", "session_variables", "parameters"):
        if hasattr(callback_context, attr):
            _set_on_target(getattr(callback_context, attr))


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    """
    Executes at the beginning of each agent turn.
    Reads user_id from session state (or session parameter), looks up profile,
    and populates user_name and membership_tier into session state.
    """
    try:
        state = get_state(callback_context)

        # RootAgent re-evaluates intent on every turn using {active_intent} as
        # context, but nothing ever set it -- it was always blank, which likely
        # contributed to terse cart follow-ups ("Add sku_1029 quantity 1 to
        # cart") getting misclassified as ambiguous on turns after the first.
        # Mark the session as an active shopping flow as soon as
        # ShoppingAssistant is engaged, so RootAgent has a real signal.
        set_state_var(callback_context, "active_intent", "shopping")

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
