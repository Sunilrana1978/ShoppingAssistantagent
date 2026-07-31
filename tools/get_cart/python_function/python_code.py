import os
import json
import tempfile
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

def get_cart(session_id: str = "", user_id: str = "", current_cart: Optional[Dict[str, Any]] = {}) -> Dict[str, Any]:
    """
    Get active cart details for a session or user via cart_service or fallback state.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if cart_service:
            cart = cart_service.get_cart(session_id=sid, user_id=uid)
        elif current_cart and isinstance(current_cart, dict) and current_cart.get("items") is not None:
            cart = current_cart
        else:
            path = _get_tmp_storage_file()
            cart = None
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        carts = json.load(f)
                        cart = carts.get(sid)
                except Exception:
                    pass
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
            "agent_action": f"Could not retrieve cart for session {session_id}: {str(e)}"
        }

def _get_tmp_storage_file() -> str:
    return os.path.join(tempfile.gettempdir(), "cxas_session_carts.json")
