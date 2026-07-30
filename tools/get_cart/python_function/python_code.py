from typing import Dict, Any

SESSION_CARTS = {}
USER_CARTS = {}

def get_cart(session_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Get active cart details for a session or user.
    Retrieves previous session cart if user_id matches across separate chat sessions.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        cart = SESSION_CARTS.get(sid)
        if not cart and uid and uid in USER_CARTS:
            cart = USER_CARTS[uid]
            cart["session_id"] = sid

        if not cart:
            cart = {
                "session_id": sid,
                "user_id": uid,
                "items": [],
                "subtotal": 0.0,
                "discount_pct": 0.0,
                "discount_amount": 0.0,
                "total": 0.0
            }

        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not retrieve cart for session " + str(session_id) + ": " + str(e)
        }
