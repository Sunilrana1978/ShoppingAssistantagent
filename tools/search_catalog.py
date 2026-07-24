from typing import Dict, Any, Optional
from services.catalog_service import catalog_service

def search_catalog(
    query: Optional[str] = None,
    category: Optional[str] = None,
    sport: Optional[str] = None,
    brand: Optional[str] = None,
    size: Optional[Any] = None,
    price_max: Optional[float] = None
) -> Dict[str, Any]:
    """
    Search product catalog by free-text and extracted attributes.

    Args:
        query: Natural language product description (e.g. "trail running shoes").
        category: Product category ("shoes", "apparel", "equipment").
        sport: Sport activity ("running", "tennis", "fitness").
        brand: Brand name ("Northline", "Velocity", "AceCraft").
        size: Size filter (numeric or string size).
        price_max: Maximum price cap.

    Returns:
        Dict containing search results list and total count.
    """
    products = catalog_service.search(
        query=query,
        category=category,
        sport=sport,
        brand=brand,
        size=size,
        price_max=price_max
    )
    return {
        "status": "success",
        "count": len(products),
        "products": products
    }
