import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from services.interfaces import IFeedbackService

class MockFeedbackService(IFeedbackService):
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "mock_feedback.json"
        self.data_path = Path(data_path)
        self._load_data()

    def _load_data(self):
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.feedback_entries = json.load(f)
        else:
            self.feedback_entries = []

    def submit_feedback(
        self,
        user_id: str,
        rating: int,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        rating = max(1, min(5, int(rating)))
        fb_id = f"fb_{len(self.feedback_entries) + 1001}"
        entry = {
            "feedback_id": fb_id,
            "user_id": user_id,
            "rating": rating,
            "comments": comments or "",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.feedback_entries.append(entry)
        return {
            "status": "success",
            "feedback_id": fb_id,
            "rating": rating,
            "message": "Thank you for your feedback!"
        }

    def get_user_feedback(self, user_id: str) -> List[Dict[str, Any]]:
        return [f for f in self.feedback_entries if f.get("user_id") == user_id]

feedback_service = MockFeedbackService()
