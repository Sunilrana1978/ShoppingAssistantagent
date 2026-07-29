from typing import Any

def before_agent_callback(context: Any) -> Any:
    """
    Hook executed before agent invocation.
    Dynamically looks up user profile (name, tier) from backend user database using user_id
    and sets session state variables (user_name, membership_tier).
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

    # 2. Database / Mock User Service Lookup
    mock_users = {
        "u_1029": {"name": "Alex", "membership_tier": "gold"},
        "u_1030": {"name": "Jordan", "membership_tier": "silver"},
        "u_1031": {"name": "Taylor", "membership_tier": "bronze"}
    }

    if user_id in mock_users:
        profile = mock_users[user_id]
    else:
        profile = {"name": "Shopper", "membership_tier": "none"}

    # 3. Set variables in context state dynamically
    if hasattr(context, "set_variable"):
        context.set_variable("user_id", user_id or "guest")
        context.set_variable("user_name", profile["name"])
        context.set_variable("membership_tier", profile["membership_tier"])
    elif hasattr(context, "state") and isinstance(context.state, dict):
        context.state["user_id"] = user_id or "guest"
        context.state["user_name"] = profile["name"]
        context.state["membership_tier"] = profile["membership_tier"]
    elif isinstance(context, dict):
        if "state" not in context:
            context["state"] = {}
        context["state"]["user_id"] = user_id or "guest"
        context["state"]["user_name"] = profile["name"]
        context["state"]["membership_tier"] = profile["membership_tier"]

    return None
