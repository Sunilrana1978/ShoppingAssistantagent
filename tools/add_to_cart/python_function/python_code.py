import os
import json
import tempfile
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

_FALLBACK_CARTS: Dict[str, Dict[str, Any]] = {}

CATALOG_PRICES = {
    "sku_1029": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
    "trailblaze": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
    "sku_1030": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
    "apex": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
    "sku_1031": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
    "stormflex": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
    "sku_1032": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
    "procourt": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
    "sku_1033": {"name": "UltraGrip Gym Gloves", "price": 29.99},
    "ultragrip": {"name": "UltraGrip Gym Gloves", "price": 29.99}
}


def _resolve_product_info(sku: str) -> Dict[str, Any]:
    clean = str(sku).lower().replace("-", "_").strip()
    for key, val in CATALOG_PRICES.items():
        if key in clean or clean in key:
            return val
    pretty_name = clean.replace("sku_", "").replace("_", " ").title()
    return {"name": pretty_name, "price": 99.99}


def add_to_cart(
    session_id: str = "",
    sku: str = "",
    qty: int = 1,
    size: str = "",
    discount_pct: float = 0.0,
    user_id: str = "",
    current_cart: Optional[Dict[str, Any]] = None
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

            # Merge cart state from current_cart, memory, and disk fallback
            candidate_carts = []
            if current_cart and isinstance(current_cart, dict) and isinstance(current_cart.get("items"), list):
                candidate_carts.append(current_cart)
            if sid in _FALLBACK_CARTS:
                candidate_carts.append(_FALLBACK_CARTS[sid])
            if sid in tmp_carts:
                candidate_carts.append(tmp_carts[sid])
            if uid and f"user_{uid}" in _FALLBACK_CARTS:
                candidate_carts.append(_FALLBACK_CARTS[f"user_{uid}"])
            if uid and f"user_{uid}" in tmp_carts:
                candidate_carts.append(tmp_carts[f"user_{uid}"])

            merged_items: Dict[str, Dict[str, Any]] = {}
            base_disc_pct = float(discount_pct or 0.0)

            # Consolidate existing items across candidate cart snapshots
            for c in candidate_carts:
                if c.get("discount_pct"):
                    base_disc_pct = max(base_disc_pct, float(c["discount_pct"]))
                for item in c.get("items", []):
                    item_key = f"{str(item.get('sku')).lower()}_{str(item.get('size')).lower()}"
                    if item_key not in merged_items:
                        merged_items[item_key] = dict(item)
                    else:
                        merged_items[item_key]["qty"] = max(merged_items[item_key]["qty"], item["qty"])

            info = _resolve_product_info(sku)
            clean_sku = str(sku).lower().strip()
            item_key = f"{clean_sku}_{str(size or 'Default').lower()}"

            if item_key in merged_items:
                merged_items[item_key]["qty"] += qty
            else:
                merged_items[item_key] = {
                    "sku": sku,
                    "name": info["name"],
                    "unit_price": info["price"],
                    "qty": qty,
                    "size": size or "Default"
                }

            items_list = list(merged_items.values())
            subtotal = round(sum(float(i.get("unit_price", 0.0)) * int(i.get("qty", 1)) for i in items_list), 2)
            disc_amt = round(subtotal * (base_disc_pct / 100.0), 2)

            cart = {
                "session_id": sid,
                "user_id": uid,
                "items": items_list,
                "subtotal": subtotal,
                "discount_pct": base_disc_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2)
            }

            _FALLBACK_CARTS[sid] = cart
            if uid:
                _FALLBACK_CARTS[f"user_{uid}"] = cart
            tmp_carts[sid] = cart
            if uid:
                tmp_carts[f"user_{uid}"] = cart
            _save_tmp_carts(tmp_carts)

        return {
            "status": "success",
            "added_item": {
                "sku": sku,
                "qty": qty,
                "size": size
            },
            "cart": cart,
            "x-ces-session-context": {
                "variables": {
                    "cart": cart
                }
            }
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
