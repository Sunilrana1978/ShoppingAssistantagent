from typing import Dict, List, Any, Optional
from services.interfaces import ICartService
from services.catalog_service import catalog_service

class MockCartService(ICartService):
    def __init__(self):
        # Session storage mapping: session_id -> cart dict
        self._carts: Dict[str, Dict[str, Any]] = {}
        # User storage mapping: user_id -> cart dict
        self._user_carts: Dict[str, Dict[str, Any]] = {}

    def get_cart(self, session_id: str, user_id: str = "") -> Dict[str, Any]:
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if sid in self._carts:
            return self._carts[sid]
        
        if uid and uid in self._user_carts:
            cart = self._user_carts[uid]
            cart["session_id"] = sid
            self._carts[sid] = cart
            return cart

        cart = {
            "session_id": sid,
            "user_id": uid,
            "items": [],
            "subtotal": 0.0,
            "discount_pct": 0,
            "discount_amount": 0.0,
            "total": 0.0
        }
        self._carts[sid] = cart
        if uid:
            self._user_carts[uid] = cart
        return cart

    def add_item(
        self,
        session_id: str,
        sku: str,
        qty: int = 1,
        size: Optional[Any] = None,
        user_id: str = ""
    ) -> Dict[str, Any]:
        cart = self.get_cart(session_id, user_id=user_id)
        product = catalog_service.get_product(sku)
        if not product:
            # Fallback lookup by partial name if model passed name instead of sku
            results = catalog_service.search(query=sku)
            if results:
                product = results[0]

        if not product:
            raise ValueError(f"Product SKU or item '{sku}' not found in catalog.")

        # Check existing line items
        existing = False
        for item in cart["items"]:
            if item["sku"] == product["sku"] and item.get("size") == size:
                item["qty"] += qty
                existing = True
                break

        if not existing:
            cart["items"].append({
                "sku": product["sku"],
                "name": product["name"],
                "qty": qty,
                "size": size or (product["sizes"][0] if product.get("sizes") else None),
                "unit_price": float(product["price"]),
                "image_url": product.get("image_url", "")
            })

        # Recompute subtotal
        subtotal = sum(i["unit_price"] * i["qty"] for i in cart["items"])
        cart["subtotal"] = round(subtotal, 2)
        
        # Apply existing discount
        discount_pct = cart.get("discount_pct", 0)
        disc_amount = cart["subtotal"] * (discount_pct / 100.0)
        cart["discount_amount"] = round(disc_amount, 2)
        cart["total"] = round(cart["subtotal"] - cart["discount_amount"], 2)

        uid = cart.get("user_id") or user_id
        if uid:
            self._user_carts[uid] = cart

        return cart

    def remove_item(self, session_id: str, sku: str) -> Dict[str, Any]:
        cart = self.get_cart(session_id)
        cart["items"] = [i for i in cart["items"] if i["sku"] != sku and i["name"] != sku]
        
        subtotal = sum(i["unit_price"] * i["qty"] for i in cart["items"])
        cart["subtotal"] = round(subtotal, 2)
        
        discount_pct = cart.get("discount_pct", 0)
        disc_amount = cart["subtotal"] * (discount_pct / 100.0)
        cart["discount_amount"] = round(disc_amount, 2)
        cart["total"] = round(cart["subtotal"] - cart["discount_amount"], 2)

        return cart

    def update_cart_pricing(self, session_id: str, discount_pct: float) -> Dict[str, Any]:
        cart = self.get_cart(session_id)
        cart["discount_pct"] = discount_pct
        subtotal = sum(i["unit_price"] * i["qty"] for i in cart["items"])
        cart["subtotal"] = round(subtotal, 2)
        disc_amount = cart["subtotal"] * (discount_pct / 100.0)
        cart["discount_amount"] = round(disc_amount, 2)
        cart["total"] = round(cart["subtotal"] - cart["discount_amount"], 2)
        return cart

cart_service = MockCartService()
