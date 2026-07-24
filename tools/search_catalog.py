from typing import Dict, Any, List

MOCK_CATALOG = [
    {
        "sku": "sku_1029",
        "name": "AeroSwift Trail Running Shoes",
        "category": "shoes",
        "sport": "running",
        "brand": "AeroSport",
        "price": 129.99,
        "available_sizes": ["8", "9", "10", "11"],
        "description": "Lightweight water-resistant trail running shoes with grip tread.",
        "image_url": "https://storage.googleapis.com/cxas-demo-assets/shoes_trail.jpg"
    },
    {
        "sku": "sku_2041",
        "name": "ProFlex Basketball Shoes",
        "category": "shoes",
        "sport": "basketball",
        "brand": "CourtPro",
        "price": 149.99,
        "available_sizes": ["9", "10", "11", "12"],
        "description": "High-top basketball shoes with maximum ankle support and cushion.",
        "image_url": "https://storage.googleapis.com/cxas-demo-assets/shoes_bball.jpg"
    },
    {
        "sku": "sku_3012",
        "name": "DryFit Performance Training Shirt",
        "category": "apparel",
        "sport": "fitness",
        "brand": "AeroSport",
        "price": 39.99,
        "available_sizes": ["S", "M", "L", "XL"],
        "description": "Moisture-wicking athletic t-shirt for intense training sessions.",
        "image_url": "https://storage.googleapis.com/cxas-demo-assets/shirt_dryfit.jpg"
    },
    {
        "sku": "sku_4055",
        "name": "Carbon Strike Tennis Racket",
        "category": "equipment",
        "sport": "tennis",
        "brand": "RacquetTech",
        "price": 199.99,
        "available_sizes": ["Standard"],
        "description": "Lightweight carbon fiber tennis racket with optimized string tension.",
        "image_url": "https://storage.googleapis.com/cxas-demo-assets/tennis_racket.jpg"
    }
]

def search_catalog(
    query: str = "",
    category: str = "",
    sport: str = "",
    brand: str = "",
    size: str = "",
    price_max: float = 0.0
) -> Dict[str, Any]:
    """
    Search product catalog by query, category, sport, brand, size, or price limit.
    """
    try:
        matches = []
        for prod in MOCK_CATALOG:
            if category and str(category).lower() not in prod["category"].lower():
                continue
            if sport and str(sport).lower() not in prod["sport"].lower():
                continue
            if brand and str(brand).lower() not in prod["brand"].lower():
                continue
            if price_max > 0 and prod["price"] > price_max:
                continue
            if size and str(size) not in prod["available_sizes"]:
                continue
            if query:
                q = str(query).lower()
                text = (prod["name"] + " " + prod["description"] + " " + prod["category"]).lower()
                if q not in text:
                    continue
            matches.append(prod)

        return {
            "status": "success",
            "results_count": len(matches),
            "products": matches
        }
    except Exception as e:
        return {
            "status": "error",
            "agent_action": "Failed searching catalog: " + str(e)
        }
