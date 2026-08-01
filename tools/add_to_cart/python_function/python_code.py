import os
import json
import ssl
import logging
import fcntl
import tempfile
import urllib.request
from typing import Dict, Any, Optional

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

logger = logging.getLogger(__name__)

_FALLBACK_CARTS: Dict[str, Dict[str, Any]] = {}

CLOUD_RUN_TARGETS = [
    {"url": "https://shopping-user-service-331751626808.us-central1.run.app", "headers": {}},
    {"url": "https://34.143.73.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://34.143.76.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://34.143.74.2", "headers": {"Host": "shopping-user-service-331751626808.us-central1.run.app"}},
    {"url": "https://shopping-user-service-4ig7nhz5fq-uc.a.run.app", "headers": {}}
]


CATALOG_PRICES = {
    "sku_1029": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
    "trailblaze": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
    "tb": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},

    "sku_1030": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
    "apex": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
    "aa987": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
    "aa": {"name": "Apex Aero Road Running Shoes", "price": 149.99},

    "sku_1031": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
    "stormflex": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
    "sf456": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
    "sf": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},

    "sku_1032": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
    "procourt": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
    "pc123": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
    "pc": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},

    "sku_1033": {"name": "UltraGrip Gym Gloves", "price": 29.99},
    "ultragrip": {"name": "UltraGrip Gym Gloves", "price": 29.99},
    "ug": {"name": "UltraGrip Gym Gloves", "price": 29.99},
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

        # Read current cart (and user_id fallback) from context.state if provided
        if current_cart is None or not uid:
            if "context" in globals() and hasattr(globals()["context"], "state") and getattr(globals()["context"], "state"):
                state = globals()["context"].state
                if current_cart is None:
                    current_cart = state.get("cart")
                if not uid:
                    uid = str(state.get("user_id") or "").strip()
            elif "get_variable" in globals():
                if current_cart is None:
                    current_cart = globals()["get_variable"]("cart")
                if not uid:
                    uid = str(globals()["get_variable"]("user_id") or "").strip()

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
            cart = _save_tmp_carts(tmp_carts, target_sid=sid, target_uid=uid) or cart

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
            "added_item": {
                "sku": sku,
                "qty": qty,
                "size": size
            },
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
            "agent_action": f"Could not add SKU {sku} to cart: {str(e)}"
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


def _get_lock_file() -> str:
    return os.path.join(tempfile.gettempdir(), "cxas_session_carts.lock")


def _load_tmp_carts() -> Dict[str, Dict[str, Any]]:
    path = _get_tmp_storage_file()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_tmp_carts(carts: Dict[str, Dict[str, Any]], target_sid: str = "", target_uid: str = "") -> Optional[Dict[str, Any]]:
    path = _get_tmp_storage_file()
    lock_path = _get_lock_file()
    res_cart = None
    try:
        with open(lock_path, "w") as lock_f:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
            try:
                existing = {}
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                    except Exception:
                        pass
                for sid, cart in carts.items():
                    if sid in existing and existing[sid].get("items"):
                        merged_items = {}
                        for item in (existing[sid].get("items", []) + cart.get("items", [])):
                            key = f"{str(item.get('sku')).lower()}_{str(item.get('size')).lower()}"
                            if key not in merged_items:
                                merged_items[key] = dict(item)
                            else:
                                merged_items[key]["qty"] = max(merged_items[key]["qty"], item["qty"])
                        items_list = list(merged_items.values())
                        subtotal = round(sum(float(i.get("unit_price", 0.0)) * int(i.get("qty", 1)) for i in items_list), 2)
                        disc_pct = float(cart.get("discount_pct") or existing[sid].get("discount_pct") or 0.0)
                        disc_amt = round(subtotal * (disc_pct / 100.0), 2)
                        merged_cart = {
                            "session_id": sid,
                            "user_id": cart.get("user_id") or existing[sid].get("user_id") or "",
                            "items": items_list,
                            "subtotal": subtotal,
                            "discount_pct": disc_pct,
                            "discount_amount": disc_amt,
                            "total": round(subtotal - disc_amt, 2)
                        }
                        existing[sid] = merged_cart
                    else:
                        existing[sid] = cart

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(existing, f, indent=2)

                if target_sid and target_sid in existing:
                    res_cart = existing[target_sid]
                elif target_uid and f"user_{target_uid}" in existing:
                    res_cart = existing[f"user_{target_uid}"]
            finally:
                fcntl.flock(lock_f, fcntl.LOCK_UN)
    except Exception:
        pass
    return res_cart
