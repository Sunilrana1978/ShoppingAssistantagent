from typing import Dict, Any

SESSION_CARTS = {}

def get_cart(session_id: str) -> Dict[str, Any]:
    """
    Get active cart details for a session.
    """
    try:
        cart = SESSION_CARTS.get(session_id, {
            "session_id": session_id,
            "items": [],
            "subtotal": 0.0,
            "discount_amount": 0.0,
            "total": 0.0
        })
        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not retrieve cart for session " + str(session_id) + ": " + str(e)
        }
