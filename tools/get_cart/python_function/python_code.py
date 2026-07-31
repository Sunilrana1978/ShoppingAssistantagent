from typing import Dict, Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

def get_cart(session_id: str = "", user_id: str = "") -> Dict[str, Any]:
    """
    Get active cart details for a session or user via cart_service.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if cart_service:
            cart = cart_service.get_cart(session_id=sid, user_id=uid)
        else:
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
            "agent_action": f"Could not retrieve cart for session {session_id}: {str(e)}"
        }

