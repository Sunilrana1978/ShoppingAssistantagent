from typing import Dict, Any

MOCK_USERS = {
    "u_1029": {
        "user_id": "u_1029",
        "name": "Alex",
        "membership_tier": "gold",
        "memories": [
            "User Alex previously added TrailBlaze Pro Trail Runner (size 10, qty 1) to cart for $110.49."
        ],
        "previous_cart": {
          "session_id": "sess_previous",
          "user_id": "u_1029",
          "items": [
            {
              "sku": "sku_1029",
              "name": "TrailBlaze Pro Trail Runner",
              "qty": 1,
              "size": "10",
              "unit_price": 129.99
            }
          ],
          "subtotal": 129.99,
          "discount_pct": 15.0,
          "discount_amount": 19.50,
          "total": 110.49
        }
    },
    "u_1030": {
        "user_id": "u_1030",
        "name": "Jordan",
        "membership_tier": "silver",
        "memories": [
            "User Jordan previously added Apex Aero Road Running Shoes (size 10, qty 1) to cart for $134.99."
        ],
        "previous_cart": {
          "session_id": "sess_previous",
          "user_id": "u_1030",
          "items": [
            {
              "sku": "sku_1030",
              "name": "Apex Aero Road Running Shoes",
              "qty": 1,
              "size": "10",
              "unit_price": 149.99
            }
          ],
          "subtotal": 149.99,
          "discount_pct": 10.0,
          "discount_amount": 15.00,
          "total": 134.99
        }
    },
    "u_1031": {
        "user_id": "u_1031",
        "name": "Taylor",
        "membership_tier": "bronze",
        "memories": [],
        "previous_cart": {}
    },
    "guest": {
        "user_id": "guest",
        "name": "Guest Customer",
        "membership_tier": "none",
        "memories": [],
        "previous_cart": {}
    }
}

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Look up user profile by user_id.

    Returns dict containing user_id, user_name, membership_tier, memories, and previous_cart.
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
            "membership_tier": profile["membership_tier"],
            "memories": profile.get("memories", []),
            "previous_cart": profile.get("previous_cart", {})
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Unable to fetch user profile for " + str(user_id) + ": " + str(e)
        }
