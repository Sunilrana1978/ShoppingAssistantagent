from typing import Dict, Any

MOCK_USERS = {
    "u_1029": {
        "user_id": "u_1029",
        "name": "Alex",
        "membership_tier": "gold"
    },
    "u_1030": {
        "user_id": "u_1030",
        "name": "Jordan",
        "membership_tier": "silver"
    },
    "u_1031": {
        "user_id": "u_1031",
        "name": "Taylor",
        "membership_tier": "bronze"
    },
    "guest": {
        "user_id": "guest",
        "name": "Guest Customer",
        "membership_tier": "none"
    }
}

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Look up user profile by user_id.

    Returns dict containing user_id, user_name, and membership_tier.
    """
    try:
        if isinstance(user_id, str):
            user_id = user_id.strip('"').strip("'").strip()
        profile = MOCK_USERS.get(user_id, MOCK_USERS["guest"])

        # Direct CXAS runtime state mutation
        if "context" in globals() and hasattr(globals()["context"], "state"):
            globals()["context"].state["user_id"] = profile["user_id"]
            globals()["context"].state["user_name"] = profile["name"]
            globals()["context"].state["membership_tier"] = profile["membership_tier"]
        if "set_variable" in globals():
            globals()["set_variable"]("user_id", profile["user_id"])
            globals()["set_variable"]("user_name", profile["name"])
            globals()["set_variable"]("membership_tier", profile["membership_tier"])

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
