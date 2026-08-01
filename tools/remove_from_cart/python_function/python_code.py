import os
import json
import ssl
import logging
import tempfile
import urllib.request
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

logger = logging.getLogger(__name__)

CLOUD_RUN_TARGETS = [
    {"url": "https://shopping-user-service-331751626808.us-central1.run.app", "headers": {}},
    {"url": "https://34.143.73.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://34.143.76.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://34.143.74.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://shopping-user-service-4ig7nhz5fq-uc.a.run.app", "headers": {}}
]


def remove_from_cart(session_id: str = "", sku: str = "", discount_pct: float = 0.0, user_id: str = "", current_cart: Optional[Dict[str, Any]] = {}) -> Dict[str, Any]:
    """
    Remove item SKU from active session cart via cart_service or fallback state.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        clean_sku = str(sku).lower().strip()
        uid = str(user_id or "").strip()

        if not uid:
            if "context" in globals() and hasattr(globals()["context"], "state") and getattr(globals()["context"], "state"):
                uid = str(globals()["context"].state.get("user_id") or "").strip()
            elif "get_variable" in globals():
                uid = str(globals()["get_variable"]("user_id") or "").strip()

        if cart_service:
            cart = cart_service.remove_item(session_id=sid, sku=sku)
        else:
            base_cart = None
            if current_cart and isinstance(current_cart, dict) and current_cart.get("items") is not None:
                base_cart = current_cart
            else:
                path = _get_tmp_storage_file()
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            carts = json.load(f)
                            base_cart = carts.get(sid)
                    except Exception:
                        pass

            if base_cart:
                cart = json.loads(json.dumps(base_cart))
            else:
                cart = {
                    "session_id": sid,
                    "items": [],
                    "subtotal": 0.0,
                    "discount_pct": float(discount_pct or 0.0),
                    "discount_amount": 0.0,
                    "total": 0.0
                }

            cart["items"] = [
                i for i in cart.get("items", [])
                if str(i.get("sku", "")).lower() != clean_sku and str(i.get("name", "")).lower() != clean_sku
            ]
            subtotal = round(sum(float(i.get("unit_price", 0.0)) * int(i.get("qty", 1)) for i in cart["items"]), 2)
            disc_pct = float(discount_pct or cart.get("discount_pct", 0.0))
            disc_amt = round(subtotal * (disc_pct / 100.0), 2)
            cart.update({
                "subtotal": subtotal,
                "discount_pct": disc_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2)
            })

            path = _get_tmp_storage_file()
            try:
                carts = {}
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        carts = json.load(f)
                carts[sid] = cart
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(carts, f, indent=2)
            except Exception:
                pass

        try:
            _save_cart_snapshot(uid, cart)
        except Exception as err:
            logger.debug(f"Cart snapshot persist skipped: {err}")

        # Direct CXAS runtime state mutation
        if "context" in globals() and hasattr(globals()["context"], "state"):
            globals()["context"].state["cart"] = cart
        if "set_variable" in globals():
            globals()["set_variable"]("cart", cart)

        return {
            "status": "success",
            "removed_sku": sku,
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
            "agent_action": f"Could not remove SKU {sku} from cart: {str(e)}"
        }

def _save_cart_snapshot(user_id: str, cart: Dict[str, Any], timeout: int = 5) -> None:
    """
    Best-effort persist of the cart snapshot to Firestore via the user-profile microservice,
    so it can be recalled as previous_cart by fetch_user_profile in a future session.
    Never raises - a failed/slow save must not break the tool's primary response.
    """
    if not user_id:
        return

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    body = json.dumps({"cart": cart}).encode("utf-8")

    for target in CLOUD_RUN_TARGETS:
        url = f"{target['url'].rstrip('/')}/api/v1/users/{user_id}/cart"
        headers = dict(target["headers"])
        headers["Content-Type"] = "application/json"
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                if resp.status == 200:
                    return
        except Exception as err:
            logger.debug(f"Cart snapshot POST {url} failed: {err}")


def _get_tmp_storage_file() -> str:
    return os.path.join(tempfile.gettempdir(), "cxas_session_carts.json")
