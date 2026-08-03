import logging
from typing import Any, Optional

CallbackContext = Any
Content = Any

logger = logging.getLogger(__name__)


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

    if hasattr(callback_context, "session"):
        session = getattr(callback_context, "session")
        _set_on_target(session)
        for attr in ("state", "variables", "session_variables", "parameters"):
            if hasattr(session, attr):
                _set_on_target(session, attr)


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    """
    Executes at the beginning of each agent turn (RootAgent).
    Ensures user_id and default variables are initialized cleanly.
    """
    try:
        state = get_state(callback_context)

        user_id = state.get("user_id")
        if not user_id and hasattr(callback_context, "session") and hasattr(callback_context.session, "get_parameter"):
            user_id = callback_context.session.get_parameter("user_id", "")

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id:
            user_id = "guest"
            set_state_var(callback_context, "user_id", "guest")

        if not state.get("user_name"):
            set_state_var(callback_context, "user_name", "Shopper")

    except Exception as e:
        logger.error(f"Error in RootAgent before_agent_callback: {e}")

    return None
