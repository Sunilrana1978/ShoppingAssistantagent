from typing import Dict, Any
from services.user_service import user_service

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Look up user profile by user_id.

    Returns dict with status, user details, or agent_action on error.
    """
    try:
        profile = user_service.get_user_profile(user_id)
        return {
            "status": "success",
            "user_id": profile["user_id"],
            "user_name": profile["name"],
            "membership_tier": profile["membership_tier"]
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Unable to fetch user profile for " + str(user_id) + ": " + str(e)
        }
