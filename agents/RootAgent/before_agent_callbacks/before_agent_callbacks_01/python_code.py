from typing import Optional, Any

try:
    from google.adk.agents.callback_context import CallbackContext
except ImportError:
    CallbackContext = Any

try:
    from google.genai import types
except ImportError:
    types = Any

try:
    from services.user_service import user_service
except ImportError:
    user_service = None


def before_agent_callback(callback_context: Any) -> Optional[Any]:
    """
    Executes at the beginning of each agent turn.

    Reads user_id from session variables, looks up the user profile,
    and injects user_name and membership_tier back into session variables
    so that {user_name} and {membership_tier} placeholders resolve
    correctly in the instruction template before the LLM call.
    """
    try:
        session_vars = callback_context.variables

        # --- Short-circuit override (maintenance / kill-switch) -----------
        if session_vars.get("skip_llm_agent") is True:
            if types and hasattr(types, "Content") and hasattr(types, "Part"):
                return types.Content(
                    parts=[types.Part.from_text(
                        text="The system is undergoing routine maintenance. "
                             "Please try again later."
                    )]
                )
            return {"parts": [{"text": "The system is undergoing routine maintenance. Please try again later."}]}

        # --- Extract user_id from session variables -----------------------
        user_id = session_vars.get("user_id", None)

        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()

        if not user_id or user_id.lower() == "guest":
            if not session_vars.get("user_name"):
                callback_context.variables["user_name"] = "Shopper"
            return None

        # --- Fetch user profile -------------------------------------------
        if user_service:
            profile = user_service.get_user_profile(user_id)
        else:
            mock_users = {
                "u_1029": {"name": "Alex",   "membership_tier": "gold"},
                "u_1030": {"name": "Jordan", "membership_tier": "silver"},
                "u_1031": {"name": "Taylor", "membership_tier": "bronze"},
            }
            profile = mock_users.get(
                user_id,
                {"name": user_id.capitalize(), "membership_tier": "none"},
            )

        name = profile.get("user_name") or profile.get("name", "Shopper")
        tier = profile.get("membership_tier", "none")

        # --- Write back into session variables ----------------------------
        callback_context.variables["user_id"] = user_id
        callback_context.variables["user_name"] = name
        callback_context.variables["membership_tier"] = tier

    except Exception:
        pass

    return None
