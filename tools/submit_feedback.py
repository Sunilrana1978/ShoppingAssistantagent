from typing import Dict, Any, Optional
from services.feedback_service import feedback_service

def submit_feedback(
    user_id: str,
    rating: int,
    comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit customer rating (1-5 stars) and optional feedback comments.

    Args:
        user_id: Customer user ID.
        rating: Rating value between 1 and 5.
        comments: Optional feedback text or comments.

    Returns:
        Dict containing status, feedback_id, and confirmation message.
    """
    res = feedback_service.submit_feedback(user_id=user_id, rating=rating, comments=comments)
    return res
