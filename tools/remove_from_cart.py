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
            "discount_amount": 0.0,
            "total": 0.0
        })
        cart["items"] = [i for i in cart["items"] if i["sku"] != sku]
        cart["subtotal"] = round(sum(i["unit_price"] * i["qty"] for i in cart["items"]), 2)
        cart["total"] = cart["subtotal"]
        
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
