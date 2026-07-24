from typing import Dict, Any
from services.cart_service import cart_service

def remove_from_cart(session_id: str, sku: str) -> Dict[str, Any]:
    """
    Remove item from session cart.

    Returns dict with updated cart or agent_action on error.
    """
    try:
        cart = cart_service.remove_item(session_id=session_id, sku=sku)
        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not remove SKU " + str(sku) + " from cart: " + str(e)
        }
