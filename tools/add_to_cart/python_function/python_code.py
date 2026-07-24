from typing import Dict, Any
from services.cart_service import cart_service

def add_to_cart(session_id: str, sku: str, qty: int = 1, size: str = "") -> Dict[str, Any]:
    """
    Add item to session cart.

    Returns dict with cart update or agent_action on error.
    """
    try:
        sz = size if size else None
        cart = cart_service.add_item(session_id=session_id, sku=sku, qty=qty, size=sz)
        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not add SKU " + str(sku) + " to cart: " + str(e)
        }
