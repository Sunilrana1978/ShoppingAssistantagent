from typing import Dict, Any
from services.user_service import user_service

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Look up user profile by user_id.

    Args:
        user_id: Unique identifier for the customer.

    Returns:
        Dict containing user_id, name, and membership_tier.
    """
    profile = user_service.get_user_profile(user_id)
    return {
        "status": "success",
        "user_id": profile["user_id"],
        "user_name": profile["name"],
        "membership_tier": profile["membership_tier"]
    }
