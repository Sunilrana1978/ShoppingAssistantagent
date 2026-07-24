from typing import Dict, Any
import datetime

FEEDBACK_ENTRIES = []

def submit_feedback(user_id: str, rating: int, comments: str = "") -> Dict[str, Any]:
    """
    Submit customer rating (1-5 stars) and optional feedback comments.
    """
    try:
        r = max(1, min(5, int(rating)))
        fb_id = f"fb_{len(FEEDBACK_ENTRIES) + 1001}"
        entry = {
            "feedback_id": fb_id,
            "user_id": user_id,
            "rating": r,
            "comments": comments or "",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        FEEDBACK_ENTRIES.append(entry)
        return {
            "status": "success",
            "feedback_id": fb_id,
            "user_id": user_id,
            "rating": r,
            "comments": comments,
            "message": "Thank you for your feedback!"
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Failed to submit feedback: " + str(e)
        }
