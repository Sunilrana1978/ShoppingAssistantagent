import os
import json
import tempfile
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None


def get_cart(session_id: str = "", user_id: str = "", current_cart: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get active cart details for a session or user via cart_service or fallback state.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        cart = None
        if cart_service:
            cart = cart_service.get_cart(session_id=sid, user_id=uid)

        if not cart or not cart.get("items"):
            if current_cart and isinstance(current_cart, dict) and current_cart.get("items"):
                cart = current_cart
            else:
                tmp_carts = _load_tmp_carts()
                if sid in tmp_carts and tmp_carts[sid].get("items"):
                    cart = tmp_carts[sid]
                elif uid and f"user_{uid}" in tmp_carts and tmp_carts[f"user_{uid}"].get("items"):
                    cart = tmp_carts[f"user_{uid}"]

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
            "cart": cart,
            "updatedVariables": {
                "cart": cart
            },
            "updated_variables": {
                "cart": cart
            },
            "variables": {
                "cart": cart
            },
            "x-ces-session-context": {
                "variables": {
                    "cart": cart
                }
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": f"Could not retrieve cart for session {session_id}: {str(e)}"
        }


def _get_tmp_storage_file() -> str:
    return os.path.join(tempfile.gettempdir(), "cxas_session_carts.json")


def _load_tmp_carts() -> Dict[str, Dict[str, Any]]:
    path = _get_tmp_storage_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
