from typing import Dict, Any
from services.cart_service import cart_service

def get_cart(session_id: str) -> Dict[str, Any]:
    """
    Get session cart contents.

    Returns dict with cart details or agent_action on error.
    """
    try:
        cart = cart_service.get_cart(session_id)
        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not retrieve cart for session " + str(session_id) + ": " + str(e)
        }
