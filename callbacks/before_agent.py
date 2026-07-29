from typing import Any

try:
    from services.user_service import user_service
except ImportError:
    user_service = None

def extract_user_id_from_context(context: Any) -> Any:
    """Extracts user_id from context state, variables, model_dump, or pydantic extra fields."""
    if context is None:
        return None

    # 1. Check direct variable helpers
    if hasattr(context, "get_variable"):
        val = context.get_variable("user_id")
        if val:
            return val

    if hasattr(context, "state") and isinstance(context.state, dict):
        val = context.state.get("user_id")
        if val:
            return val

    if hasattr(context, "variables") and isinstance(context.variables, dict):
        val = context.variables.get("user_id")
        if val:
            return val

    # 2. Dump Pydantic model or dict to inspect raw JSON payload for updatedVariables
    raw_data = None
    if hasattr(context, "model_dump"):
        try:
            raw_data = context.model_dump(by_alias=True)
        except Exception:
            pass

    if not raw_data and hasattr(context, "__dict__"):
        raw_data = getattr(context, "__dict__", {})

    if not raw_data and isinstance(context, dict):
        raw_data = context

    def deep_search(data: Any, key: str, depth: int = 5) -> Any:
        if depth <= 0 or not data:
            return None
        if isinstance(data, dict):
            if key in data and data[key]:
                return data[key]
            for k, v in data.items():
                res = deep_search(v, key, depth - 1)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = deep_search(item, key, depth - 1)
                if res:
                    return res
        return None

    return deep_search(raw_data, "user_id")

def before_agent_callback(callback_context: Any) -> Any:
    """
    Hook executed before agent invocation.
    Extracts user_id from context (including state, updatedVariables, or message chunks),
    queries backend user_service/database, and updates context state with user_name and membership_tier.
    Must return None to satisfy CXAS _CallbackResult Optional[Content] contract.
    """
    context = callback_context

    user_id = extract_user_id_from_context(context)

    if isinstance(user_id, str):
        user_id = user_id.strip('"').strip("'").strip()

    if not user_id or user_id.lower() == "guest":
        return None

    # Fetch user profile based on user_id
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

    # Update state on context dynamically
    if hasattr(context, "set_variable"):
        context.set_variable("user_id", user_id)
        context.set_variable("user_name", name)
        context.set_variable("membership_tier", tier)

    if hasattr(context, "state") and isinstance(context.state, dict):
        context.state["user_id"] = user_id
        context.state["user_name"] = name
        context.state["membership_tier"] = tier
    elif isinstance(context, dict):
        if "state" not in context:
            context["state"] = {}
        context["state"]["user_id"] = user_id
        context["state"]["user_name"] = name
        context["state"]["membership_tier"] = tier

    # MUST return None to pass CXAS _CallbackResult Optional[Content] validation
    return None
