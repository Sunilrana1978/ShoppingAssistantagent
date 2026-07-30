from typing import Dict, Any

SESSION_CARTS = {}
USER_CARTS = {}

def add_to_cart(
    session_id: str,
    sku: str,
    qty: int = 1,
    size: str = "",
    discount_pct: float = 0.0,
    user_id: str = ""
) -> Dict[str, Any]:
    """
    Add item SKU and quantity to active session shopping cart and compute discounted total.
    Persists cart state per user_id across separate chat sessions.
    """
    try:
        # Determine lookup key (user_id preferred for cross-session persistence)
        uid = str(user_id or "").strip()
        sid = str(session_id or "sess_default").strip()

        # Retrieve existing cart or create new
        cart = None
        if sid in SESSION_CARTS:
            cart = SESSION_CARTS[sid]
        elif uid and uid in USER_CARTS:
            cart = USER_CARTS[uid]
            cart["session_id"] = sid

        if not cart:
            cart = {
                "session_id": sid,
                "user_id": uid,
                "items": [],
                "subtotal": 0.0,
                "discount_pct": float(discount_pct or 0.0),
                "discount_amount": 0.0,
                "total": 0.0
            }

        # Update discount_pct if passed explicitly
        if discount_pct > 0:
            cart["discount_pct"] = float(discount_pct)

        # Comprehensive Product Prices lookup matching data/mock_catalog.json
        item_prices = {
            "sku_1029": {"name": "TrailBlaze Pro Trail Runner", "price": 129.99},
            "sku_1030": {"name": "Apex Aero Road Running Shoes", "price": 149.99},
            "sku_1031": {"name": "StormFlex Waterproof Trail Jacket", "price": 89.99},
            "sku_1032": {"name": "ProCourt Precision Tennis Racket", "price": 199.99},
            "sku_1033": {"name": "UltraGrip Gym Gloves", "price": 29.99}
        }

        info = item_prices.get(sku, {"name": f"Product ({sku})", "price": 99.99})
        unit_price = info["price"]

        # Check existing line item
        existing = next((i for i in cart["items"] if i["sku"] == sku), None)
        if existing:
            existing["qty"] += qty
            if size:
                existing["size"] = size
        else:
            cart["items"].append({
                "sku": sku,
                "name": info["name"],
                "unit_price": unit_price,
                "qty": qty,
                "size": size or "Default"
            })

        # Compute subtotal, discount_amount, and total
        subtotal = round(sum(i["unit_price"] * i["qty"] for i in cart["items"]), 2)
        disc_pct = float(cart.get("discount_pct", discount_pct or 0.0))
        disc_amt = round(subtotal * (disc_pct / 100.0), 2)
        total = round(subtotal - disc_amt, 2)

        cart["subtotal"] = subtotal
        cart["discount_pct"] = disc_pct
        cart["discount_amount"] = disc_amt
        cart["total"] = total

        # Store in session and user persistent maps
        SESSION_CARTS[sid] = cart
        if uid:
            USER_CARTS[uid] = cart

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
            "agent_action": "Could not add SKU " + str(sku) + " to cart: " + str(e)
        }
