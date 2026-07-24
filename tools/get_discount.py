from typing import Dict, Any
from services.discount_service import discount_service

def get_discount(membership_tier: str) -> Dict[str, Any]:
    """
    Look up membership discount percentage by tier.

    Args:
        membership_tier: The user's membership tier ("none", "bronze", "silver", "gold").

    Returns:
        Dict containing membership_tier and discount_pct.
    """
    pct = discount_service.get_discount_percentage(membership_tier)
    return {
        "status": "success",
        "membership_tier": membership_tier,
        "discount_pct": pct
    }
