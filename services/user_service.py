import json
from pathlib import Path
from typing import Dict, Any, Optional
from services.interfaces import IUserService

class MockUserService(IUserService):
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "mock_users.json"
        self.data_path = Path(data_path)
        self._load_data()

    def _load_data(self):
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.users = json.load(f)
        else:
            self.users = {}

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        user = self.users.get(user_id)
        if not user:
            return {
                "user_id": user_id,
                "name": "Shopper",
                "user_name": "Shopper",
                "membership_tier": "none",
                "memories": [],
                "previous_cart": {}
            }
        return {
            "user_id": user_id,
            "name": user.get("name", "Shopper"),
            "user_name": user.get("name", "Shopper"),
            "membership_tier": user.get("membership_tier", "none"),
            "memories": user.get("memories", []),
            "previous_cart": user.get("previous_cart", {})
        }

user_service = MockUserService()
