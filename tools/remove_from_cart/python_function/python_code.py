from typing import Dict, Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

def remove_from_cart(session_id: str, sku: str) -> Dict[str, Any]:
    """
    Remove item SKU from active session cart via cart_service.
    """
    try:
        sid = str(session_id or "sess_default").strip()

        if cart_service:
            cart = cart_service.remove_item(session_id=sid, sku=sku)
        else:
            cart = {
                "session_id": sid,
                "items": [],
                "subtotal": 0.0,
                "discount_pct": 0.0,
                "discount_amount": 0.0,
                "total": 0.0
            }

        return {
            "status": "success",
            "removed_sku": sku,
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": f"Could not remove SKU {sku} from cart: {str(e)}"
        }

