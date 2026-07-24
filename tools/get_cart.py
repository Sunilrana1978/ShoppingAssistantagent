from typing import Dict, Any
from services.cart_service import cart_service

def get_cart(session_id: str) -> Dict[str, Any]:
    """
    Retrieve active shopping cart for the session.

    Args:
        session_id: Unique session identifier.

    Returns:
        Dict containing full cart details with items and running totals.
    """
    cart = cart_service.get_cart(session_id)
    return {
        "status": "success",
        "cart": cart
    }
