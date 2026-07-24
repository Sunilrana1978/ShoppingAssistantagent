from typing import Dict, Any
from services.discount_service import discount_service

def get_discount(membership_tier: str) -> Dict[str, Any]:
    """
    Look up discount percentage for a membership tier.

    Returns dict with status, discount details, or agent_action on error.
    """
    try:
        discount_info = discount_service.get_discount_by_tier(membership_tier)
        return {
            "status": "success",
            "membership_tier": discount_info["tier"],
            "discount_pct": discount_info["discount_pct"]
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Unable to fetch discount for tier " + str(membership_tier) + ": " + str(e)
        }
