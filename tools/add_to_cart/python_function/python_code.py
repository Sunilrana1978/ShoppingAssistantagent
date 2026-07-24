from typing import Dict, Any

SESSION_CARTS = {}

def add_to_cart(session_id: str, sku: str, qty: int = 1, size: str = "") -> Dict[str, Any]:
    """
    Add item to session cart.
    """
    try:
        if session_id not in SESSION_CARTS:
            SESSION_CARTS[session_id] = {
                "session_id": session_id,
                "items": [],
                "subtotal": 0.0,
                "discount_amount": 0.0,
                "total": 0.0
            }
        
        cart = SESSION_CARTS[session_id]
        
        # Prices lookup
        item_prices = {
            "sku_1029": {"name": "AeroSwift Trail Running Shoes", "price": 129.99},
            "sku_2041": {"name": "ProFlex Basketball Shoes", "price": 149.99},
            "sku_3012": {"name": "DryFit Performance Training Shirt", "price": 39.99},
            "sku_4055": {"name": "Carbon Strike Tennis Racket", "price": 199.99}
        }
        
        info = item_prices.get(sku, {"name": f"Product ({sku})", "price": 99.99})
        unit_price = info["price"]
        
        # Check existing line item
        existing = next((i for i in cart["items"] if i["sku"] == sku), None)
        if existing:
            existing["qty"] += qty
        else:
            cart["items"].append({
                "sku": sku,
                "name": info["name"],
                "unit_price": unit_price,
                "qty": qty,
                "size": size or "Default"
            })
            
        # Recalculate subtotal
        cart["subtotal"] = round(sum(i["unit_price"] * i["qty"] for i in cart["items"]), 2)
        cart["total"] = cart["subtotal"]
        
        return {
            "status": "success",
            "cart": cart
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Could not add SKU " + str(sku) + " to cart: " + str(e)
        }
