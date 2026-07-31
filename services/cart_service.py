import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from services.interfaces import ICartService
from services.catalog_service import catalog_service

def _get_storage_file() -> Path:
    base_dir = Path(__file__).parent.parent / "data"
    if not base_dir.exists():
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            base_dir = Path(tempfile.gettempdir())
    return base_dir / "session_carts.json"

class MockCartService(ICartService):
    def __init__(self):
        self.file_path = _get_storage_file()
        self._load_from_disk()

    def _load_from_disk(self):
        self._carts: Dict[str, Dict[str, Any]] = {}
        self._user_carts: Dict[str, Dict[str, Any]] = {}
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._carts = data.get("carts", {})
                    self._user_carts = data.get("user_carts", {})
            except Exception:
                pass

    def _save_to_disk(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({"carts": self._carts, "user_carts": self._user_carts}, f, indent=2)
        except Exception:
            pass

    def get_cart(self, session_id: str = "", user_id: str = "") -> Dict[str, Any]:
        self._load_from_disk()
        sid = str(session_id or "sess_default").strip()
        uid = str(user_id or "").strip()

        if sid in self._carts:
            return self._carts[sid]
        
        if uid and uid in self._user_carts:
            cart = self._user_carts[uid]
            cart["session_id"] = sid
            self._carts[sid] = cart
            self._save_to_disk()
            return cart

        # Fallback to latest active cart in memory/disk if sid is default/empty
        if (not session_id or session_id == "sess_default") and self._carts:
            latest_cart = list(self._carts.values())[-1]
            return latest_cart

        cart = {
            "session_id": sid,
            "user_id": uid,
            "items": [],
            "subtotal": 0.0,
            "discount_pct": 0.0,
            "discount_amount": 0.0,
            "total": 0.0
        }
        self._carts[sid] = cart
        if uid:
            self._user_carts[uid] = cart
        self._save_to_disk()
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
            clean_q = str(sku).replace("_", " ").replace("-", " ").strip()
            results = catalog_service.search(query=clean_q)
            if results:
                product = results[0]

        if not product:
            pretty_name = str(sku).replace("sku_", "").replace("_", " ").title()
            product = {
                "sku": sku,
                "name": pretty_name,
                "price": 99.99,
                "sizes": [size] if size else ["Default"],
                "image_url": ""
            }

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

        sid = cart.get("session_id") or session_id or "sess_default"
        uid = cart.get("user_id") or user_id
        self._carts[sid] = cart
        if uid:
            self._user_carts[uid] = cart
        self._save_to_disk()

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

        sid = cart.get("session_id") or session_id or "sess_default"
        self._carts[sid] = cart
        self._save_to_disk()

        return cart

    def update_cart_pricing(self, session_id: str, discount_pct: float) -> Dict[str, Any]:
        cart = self.get_cart(session_id)
        cart["discount_pct"] = discount_pct
        subtotal = sum(i["unit_price"] * i["qty"] for i in cart["items"])
        cart["subtotal"] = round(subtotal, 2)
        disc_amount = cart["subtotal"] * (discount_pct / 100.0)
        cart["discount_amount"] = round(disc_amount, 2)
        cart["total"] = round(cart["subtotal"] - cart["discount_amount"], 2)

        sid = cart.get("session_id") or session_id or "sess_default"
        self._carts[sid] = cart
        self._save_to_disk()

        return cart

cart_service = MockCartService()

