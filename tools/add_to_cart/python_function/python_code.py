import os
import json
import tempfile
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

_FALLBACK_CARTS: Dict[str, Dict[str, Any]] = {}

def add_to_cart(
    session_id: str = "",
    sku: str = "",
    qty: int = 1,
    size: str = "",
    discount_pct: float = 0.0,
    user_id: str = "",
    current_cart: Optional[Dict[str, Any]] = {}
) -> Dict[str, Any]:
    """
    Add item SKU and quantity to active session shopping cart and compute discounted total.
    Persists cart state across turns and sessions via cart_service, callback context state, or disk fallback.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if cart_service:
            cart = cart_service.add_item(session_id=sid, sku=sku, qty=qty, size=size, user_id=uid)
            if discount_pct > 0:
                cart = cart_service.update_cart_pricing(sid, discount_pct)
        else:
            tmp_carts = _load_tmp_carts()

            base_cart = None
            if current_cart and isinstance(current_cart, dict) and current_cart.get("items") is not None:
                base_cart = current_cart
            elif sid in _FALLBACK_CARTS:
                base_cart = _FALLBACK_CARTS[sid]
            elif sid in tmp_carts:
                base_cart = tmp_carts[sid]

            if base_cart:
                cart = json.loads(json.dumps(base_cart))
                cart["session_id"] = sid
                if uid:
                    cart["user_id"] = uid
            else:
                cart = {
                    "session_id": sid,
                    "user_id": uid,
                    "items": [],
                    "subtotal": 0.0,
                    "discount_pct": float(discount_pct or 0.0),
                    "discount_amount": 0.0,
                    "total": 0.0
                }

            item_prices = {
                "sku_1029": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
                "sku_trailblaze": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
                "sku_1030": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
                "sku_apex_aero": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
                "sku_1031": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
                "sku_stormflex_jacket": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
                "sku_1032": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
                "sku_procourt_racket": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
                "sku_1033": {"name": "UltraGrip Gym Gloves", "price": 29.99},
                "sku_ultragrip_gloves": {"name": "UltraGrip Gym Gloves", "price": 29.99}
            }

            clean_sku = str(sku).lower().strip()
            info = None
            for key, val in item_prices.items():
                if key.lower() == clean_sku or key.lower() in clean_sku or clean_sku in key.lower():
                    info = val
                    break
            if not info:
                pretty_name = clean_sku.replace("sku_", "").replace("_", " ").title()
                info = {"name": pretty_name, "price": 99.99}

            existing = next((i for i in cart.get("items", []) if str(i.get("sku")).lower() == clean_sku), None)
            if existing:
                existing["qty"] += qty
                if size:
                    existing["size"] = size
            else:
                if "items" not in cart:
                    cart["items"] = []
                cart["items"].append({
                    "sku": sku,
                    "name": info["name"],
                    "unit_price": info["price"],
                    "qty": qty,
                    "size": size or "Default"
                })

            subtotal = round(sum(float(i.get("unit_price", 0.0)) * int(i.get("qty", 1)) for i in cart["items"]), 2)
            disc_pct = float(discount_pct or cart.get("discount_pct", 0.0))
            disc_amt = round(subtotal * (disc_pct / 100.0), 2)
            cart.update({
                "subtotal": subtotal,
                "discount_pct": disc_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2)
            })

            _FALLBACK_CARTS[sid] = cart
            tmp_carts[sid] = cart
            _save_tmp_carts(tmp_carts)

        return {
            "status": "success",
            "added_item": {
                "sku": sku,
                "qty": qty,
                "size": size
            },
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": f"Could not add SKU {sku} to cart: {str(e)}"
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

def _save_tmp_carts(carts: Dict[str, Dict[str, Any]]) -> None:
    path = _get_tmp_storage_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(carts, f, indent=2)
    except Exception:
        pass
