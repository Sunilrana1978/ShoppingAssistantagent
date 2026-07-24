from services.interfaces import IUserService, IDiscountService, ICatalogService, ICartService, IFeedbackService
from services.user_service import user_service
from services.discount_service import discount_service
from services.catalog_service import catalog_service
from services.cart_service import cart_service
from services.feedback_service import feedback_service

__all__ = [
    "IUserService",
    "IDiscountService",
    "ICatalogService",
    "ICartService",
    "IFeedbackService",
    "user_service",
    "discount_service",
    "catalog_service",
    "cart_service",
    "feedback_service"
]
