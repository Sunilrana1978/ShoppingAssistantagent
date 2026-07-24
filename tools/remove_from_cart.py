from typing import Dict, Any
from services.cart_service import cart_service

def remove_from_cart(session_id: str, sku: str) -> Dict[str, Any]:
    """
    Remove an item from the session cart.

    Args:
        session_id: Unique session identifier.
        sku: Product SKU or name to remove.

    Returns:
        Dict containing status and updated cart object.
    """
    cart = cart_service.remove_item(session_id, sku)
    return {
        "status": "success",
        "cart": cart
    }
