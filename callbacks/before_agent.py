from typing import Any

try:
    from services.user_service import user_service
except ImportError:
    user_service = None

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before agent invocation.
    If user_id is present in context, fetches user profile and populates
    user_name and membership_tier into context state.
    Does NOT overwrite state if user_id is absent.
    """
    # 1. Extract user_id dynamically from context
    user_id = None
    if hasattr(context, "get_variable"):
        user_id = context.get_variable("user_id")

    if not user_id and hasattr(context, "state") and isinstance(context.state, dict):
        user_id = context.state.get("user_id")

    if not user_id and hasattr(context, "variables") and isinstance(context.variables, dict):
        user_id = context.variables.get("user_id")

    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    # 2. Only populate state if user_id is provided
    if not user_id or user_id.lower() == "guest":
        return None

    # 3. Fetch user profile based on user_id
    if user_service:
        profile = user_service.get_user_profile(user_id)
    else:
        mock_users = {
            "u_1029": {"name": "Alex", "membership_tier": "gold"},
            "u_1030": {"name": "Jordan", "membership_tier": "silver"},
            "u_1031": {"name": "Taylor", "membership_tier": "bronze"}
        }
        profile = mock_users.get(user_id, {"name": user_id.capitalize(), "membership_tier": "none"})

    name = profile.get("user_name") or profile.get("name", "Shopper")
    tier = profile.get("membership_tier", "none")

    # 4. Populate context state dynamically
    if hasattr(context, "state") and isinstance(context.state, dict):
        context.state["user_id"] = user_id
        context.state["user_name"] = name
        context.state["membership_tier"] = tier
    elif hasattr(context, "set_variable"):
        context.set_variable("user_id", user_id)
        context.set_variable("user_name", name)
        context.set_variable("membership_tier", tier)
    elif isinstance(context, dict):
        if "state" not in context:
            context["state"] = {}
        context["state"]["user_id"] = user_id
        context["state"]["user_name"] = name
        context["state"]["membership_tier"] = tier

    return None
