from typing import Dict, Any

try:
    from services.cart_service import cart_service
except ImportError:
    cart_service = None

# Fallback isolated store if cart_service is missing
_FALLBACK_CARTS: Dict[str, Dict[str, Any]] = {}

def add_to_cart(
    session_id: str = "",
    sku: str = "",
    qty: int = 1,
    size: str = "",
    discount_pct: float = 0.0,
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Add item SKU and quantity to active session shopping cart and compute discounted total.
    Persists cart state across turns and sessions via cart_service.
    """
    try:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if cart_service:
            cart = cart_service.add_item(session_id=sid, sku=sku, qty=qty, size=size, user_id=uid)
            if discount_pct > 0:
                cart = cart_service.update_cart_pricing(sid, discount_pct)
        else:
            cart = _FALLBACK_CARTS.get(sid, {
                "session_id": sid,
                "user_id": uid,
                "items": [],
                "subtotal": 0.0,
                "discount_pct": float(discount_pct or 0.0),
                "discount_amount": 0.0,
                "total": 0.0
            })
            item_prices = {
                "sku_1029": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
                "sku_1030": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
                "sku_1031": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
                "sku_1032": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
                "sku_1033": {"name": "UltraGrip Gym Gloves", "price": 29.99}
            }
            info = item_prices.get(sku, {"name": f"Product ({sku})", "price": 99.99})
            existing = next((i for i in cart["items"] if i["sku"] == sku), None)
            if existing:
                existing["qty"] += qty
                if size:
                    existing["size"] = size
            else:
                cart["items"].append({
                    "sku": sku,
                    "name": info["name"],
                    "unit_price": info["price"],
                    "qty": qty,
                    "size": size or "Default"
                })
            subtotal = round(sum(i["unit_price"] * i["qty"] for i in cart["items"]), 2)
            disc_pct = float(cart.get("discount_pct", discount_pct or 0.0))
            disc_amt = round(subtotal * (disc_pct / 100.0), 2)
            cart.update({
                "subtotal": subtotal,
                "discount_pct": disc_pct,
                "discount_amount": disc_amt,
                "total": round(subtotal - disc_amt, 2)
            })
            _FALLBACK_CARTS[sid] = cart

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

