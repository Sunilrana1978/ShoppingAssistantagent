from typing import Dict, Any, Optional
from services.cart_service import cart_service

def add_to_cart(
    session_id: str,
    sku: str,
    qty: int = 1,
    size: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Add a confirmed item SKU to the session cart.

    Args:
        session_id: Unique session identifier.
        sku: Product SKU code or product identifier.
        qty: Quantity to add (default: 1).
        size: Selected size (optional).

    Returns:
        Dict containing status and updated cart object.
    """
    cart = cart_service.add_item(session_id=session_id, sku=sku, qty=qty, size=size)
    return {
        "status": "success",
        "cart": cart
    }
