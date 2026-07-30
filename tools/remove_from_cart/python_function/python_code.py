from typing import Dict, Any

SESSION_CARTS = {}

def remove_from_cart(session_id: str, sku: str) -> Dict[str, Any]:
    """
    Remove item SKU from active session cart.
    """
    try:
        cart = SESSION_CARTS.get(session_id, {
            "session_id": session_id,
            "items": [],
            "subtotal": 0.0,
            "discount_pct": 0.0,
            "discount_amount": 0.0,
            "total": 0.0
        })
        cart["items"] = [i for i in cart["items"] if i["sku"] != sku]
        
        subtotal = round(sum(i["unit_price"] * i["qty"] for i in cart["items"]), 2)
        disc_pct = float(cart.get("discount_pct", 0.0))
        disc_amt = round(subtotal * (disc_pct / 100.0), 2)
        total = round(subtotal - disc_amt, 2)
        
        cart["subtotal"] = subtotal
        cart["discount_pct"] = disc_pct
        cart["discount_amount"] = disc_amt
        cart["total"] = total
        
        return {
            "status": "success",
            "removed_sku": sku,
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not remove SKU " + str(sku) + " from cart: " + str(e)
        }
