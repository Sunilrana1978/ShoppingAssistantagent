from typing import Dict, Any
from services.catalog_service import catalog_service

def search_catalog(
    query: str = "",
    category: str = "",
    sport: str = "",
    brand: str = "",
    size: str = "",
    price_max: float = 0.0
) -> Dict[str, Any]:
    """
    Search catalog with query and optional filters.

    Returns dict with matches or agent_action on error.
    """
    try:
        p_max = price_max if price_max > 0 else None
        q = query if query else None
        cat = category if category else None
        sp = sport if sport else None
        br = brand if brand else None
        sz = size if size else None

        results = catalog_service.search_products(
            query=q,
            category=cat,
            sport=sp,
            brand=br,
            size=sz,
            price_max=p_max
        )
        return {
            "status": "success",
            "results_count": len(results),
            "products": results
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Failed searching catalog: " + str(e)
        }
