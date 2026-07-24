import json
from pathlib import Path
from typing import Dict, Optional
from services.interfaces import IDiscountService

class MockDiscountService(IDiscountService):
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "membership_discounts.json"
        self.data_path = Path(data_path)
        self._load_data()

    def _load_data(self):
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.discounts = json.load(f)
        else:
            self.discounts = {"none": 0, "bronze": 5, "silver": 10, "gold": 15}

    def get_discount_percentage(self, tier: str) -> int:
        tier_key = (tier or "none").lower()
        return self.discounts.get(tier_key, 0)

discount_service = MockDiscountService()
