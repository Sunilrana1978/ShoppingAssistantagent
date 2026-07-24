from typing import Dict, Any
from services.feedback_service import feedback_service

def submit_feedback(user_id: str, rating: int, comments: str = "") -> Dict[str, Any]:
    """
    Submit feedback rating and comments.

    Returns dict with submission status or agent_action on error.
    """
    try:
        result = feedback_service.submit_feedback(user_id=user_id, rating=rating, comments=comments)
        return {
            "status": "success",
            "feedback_id": result.get("feedback_id"),
            "user_id": user_id,
            "rating": result.get("rating", rating),
            "comments": comments,
            "message": result.get("message", "Thank you for your feedback!")
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Failed to submit feedback: " + str(e)
        }
