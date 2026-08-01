import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if google-cloud-firestore client is installed
try:
    from google.cloud import firestore
    _FIRESTORE_AVAILABLE = True
except ImportError:
    _FIRESTORE_AVAILABLE = False


DEFAULT_MOCK_USERS = {
    "u_1029": {
        "user_id": "u_1029",
        "name": "Alex",
        "user_name": "Alex",
        "membership_tier": "gold",
        "memories": [],
        "previous_cart": {}
    },
    "u_1030": {
        "user_id": "u_1030",
        "name": "Jordan",
        "user_name": "Jordan",
        "membership_tier": "silver",
        "memories": [],
        "previous_cart": {}
    },
    "u_1031": {
        "user_id": "u_1031",
        "name": "Taylor",
        "user_name": "Taylor",
        "membership_tier": "bronze",
        "memories": [],
        "previous_cart": {}
    },
    "guest": {
        "user_id": "guest",
        "name": "Guest Customer",
        "user_name": "Guest Customer",
        "membership_tier": "none",
        "memories": [],
        "previous_cart": {}
    }
}


class FirestoreService:
    """Service layer managing user profile and long-term memory operations in Firestore."""

    def __init__(self, project_id: Optional[str] = None, collection_name: str = "user_profiles"):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "ecom-cx-agent")
        self.collection_name = collection_name
        self.db = None
        self._local_cache: Dict[str, Dict[str, Any]] = dict(DEFAULT_MOCK_USERS)

        if _FIRESTORE_AVAILABLE:
            try:
                self.db = firestore.Client(project=self.project_id)
                logger.info(f"Firestore Client initialized for project: {self.project_id}")
            except Exception as e:
                logger.warning(f"Firestore Client init error: {e}. Falling back to in-memory store.")
                self.db = None
        else:
            logger.warning("google-cloud-firestore package not available. Using in-memory store.")

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile metadata, long-term memory facts, and previous cart from Firestore."""
        if not user_id:
            user_id = "guest"

        user_id = user_id.strip('"').strip("'").strip()

        if self.db:
            try:
                doc_ref = self.db.collection(self.collection_name).document(user_id)
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict() or {}
                    return {
                        "user_id": user_id,
                        "name": data.get("name") or data.get("user_name", "Shopper"),
                        "user_name": data.get("user_name") or data.get("name", "Shopper"),
                        "membership_tier": data.get("membership_tier", "none"),
                        "memories": data.get("memories", []),
                        "previous_cart": data.get("previous_cart", {}),
                        "preferences": data.get("preferences", {})
                    }
                else:
                    # Initialize default profile in Firestore if document doesn't exist yet
                    default_profile = DEFAULT_MOCK_USERS.get(user_id, DEFAULT_MOCK_USERS["guest"])
                    self.save_user_profile(user_id, default_profile)
                    return default_profile
            except Exception as e:
                logger.error(f"Firestore read error for user {user_id}: {e}")

        # Fallback to local cache
        return self._local_cache.get(user_id, DEFAULT_MOCK_USERS["guest"])

    def save_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Save or merge user profile in Firestore."""
        if not user_id:
            return False

        user_id = user_id.strip('"').strip("'").strip()
        profile_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._local_cache[user_id] = profile_data

        if self.db:
            try:
                doc_ref = self.db.collection(self.collection_name).document(user_id)
                doc_ref.set(profile_data, merge=True)
                return True
            except Exception as e:
                logger.error(f"Firestore write error for user {user_id}: {e}")
                return False

        return True

    def add_user_memory(self, user_id: str, memory_fact: str) -> bool:
        """Append a long-term memory fact to user profile in Firestore."""
        if not user_id or not memory_fact:
            return False

        user_id = user_id.strip('"').strip("'").strip()
        profile = self.get_user_profile(user_id)
        memories: List[str] = profile.get("memories", [])

        if memory_fact not in memories:
            memories.append(memory_fact)
            profile["memories"] = memories
            return self.save_user_profile(user_id, profile)

        return True

    def save_user_cart(self, user_id: str, cart_data: Dict[str, Any]) -> bool:
        """Save cross-session cart snapshot to user profile in Firestore."""
        if not user_id:
            return False

        user_id = user_id.strip('"').strip("'").strip()
        profile = self.get_user_profile(user_id)
        profile["previous_cart"] = cart_data
        return self.save_user_profile(user_id, profile)


firestore_service = FirestoreService()
