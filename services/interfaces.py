from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class IUserService(ABC):
    @abstractmethod
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile including name and membership tier."""
        pass

class IDiscountService(ABC):
    @abstractmethod
    def get_discount_percentage(self, tier: str) -> int:
        """Fetch discount percentage for a given membership tier."""
        pass

class ICatalogService(ABC):
    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        sport: Optional[str] = None,
        brand: Optional[str] = None,
        size: Optional[Any] = None,
        price_max: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search products with free-text and structured filters."""
        pass

    @abstractmethod
    def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get product details by SKU."""
        pass

class ICartService(ABC):
    @abstractmethod
    def get_cart(self, session_id: str) -> Dict[str, Any]:
        """Retrieve current session cart."""
        pass

    @abstractmethod
    def add_item(
        self,
        session_id: str,
        sku: str,
        qty: int = 1,
        size: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Add item SKU to session cart."""
        pass

    @abstractmethod
    def remove_item(self, session_id: str, sku: str) -> Dict[str, Any]:
        """Remove item SKU from session cart."""
        pass

    @abstractmethod
    def update_cart_pricing(self, session_id: str, discount_pct: float) -> Dict[str, Any]:
        """Recompute cart subtotal, discount, and total server-side."""
        pass

class IFeedbackService(ABC):
    @abstractmethod
    def submit_feedback(
        self,
        user_id: str,
        rating: int,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit customer feedback and rating."""
        pass

    @abstractmethod
    def get_user_feedback(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch past feedback submitted by a user."""
        pass
