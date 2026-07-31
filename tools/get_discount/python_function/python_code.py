from typing import Dict, Any

MEMBERSHIP_DISCOUNTS = {
    "gold": 15,
    "silver": 10,
    "bronze": 5,
    "none": 0,
    "guest": 0
}

def get_discount(membership_tier: str) -> Dict[str, Any]:
    """
    Look up discount percentage for a membership tier.

    Returns dict containing membership_tier and discount_pct.
    """
    try:
        tier_key = str(membership_tier).lower().strip()
        pct = MEMBERSHIP_DISCOUNTS.get(tier_key, 0)
        return {
            "status": "success",
            "membership_tier": tier_key,
            "discount_pct": pct,
            "x-ces-session-context": {
                "variables": {
                    "discount_pct": pct
                }
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Unable to fetch discount for tier " + str(membership_tier) + ": " + str(e)
        }
