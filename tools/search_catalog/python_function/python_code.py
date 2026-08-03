from typing import Dict, Any, List

MOCK_CATALOG = [
    {
        "sku": "sku_1029",
        "name": "TrailBlaze Pro Trail Runner",
        "category": "shoes",
        "sport": "running",
        "brand": "Northline",
        "price": 129.99,
        "available_sizes": ["8", "9", "10", "11"],
        "sizes": [8, 9, 10, 11],
        "description": "Trail running shoe with grippy outsole and rock plate protection.",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff"
    },
    {
        "sku": "sku_1030",
        "name": "Apex Aero Road Running Shoes",
        "category": "shoes",
        "sport": "running",
        "brand": "Velocity",
        "price": 149.99,
        "available_sizes": ["9", "10", "11", "12"],
        "sizes": [9, 10, 11, 12],
        "description": "Lightweight breathable road shoes with carbon plate technology.",
        "image_url": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a"
    },
    {
        "sku": "sku_1031",
        "name": "StormFlex Waterproof Trail Jacket",
        "category": "apparel",
        "sport": "running",
        "brand": "Northline",
        "price": 89.99,
        "available_sizes": ["S", "M", "L", "XL"],
        "sizes": ["S", "M", "L", "XL"],
        "description": "Windproof and waterproof trail jacket with reflective accents.",
        "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5"
    },
    {
        "sku": "sku_1032",
        "name": "ProCourt Precision Tennis Racket",
        "category": "equipment",
        "sport": "tennis",
        "brand": "AceCraft",
        "price": 199.99,
        "available_sizes": ["4 1/4", "4 3/8"],
        "sizes": ["4 1/4", "4 3/8"],
        "description": "High control graphite frame tennis racket built for speed.",
        "image_url": "https://images.unsplash.com/photo-1617083934555-563200253457"
    },
    {
        "sku": "sku_1033",
        "name": "UltraGrip Gym Gloves",
        "category": "equipment",
        "sport": "fitness",
        "brand": "IronFit",
        "price": 29.99,
        "available_sizes": ["M", "L"],
        "sizes": ["M", "L"],
        "description": "Padded weightlifting gloves with wrist support strap.",
        "image_url": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd"
    },
    {
        "sku": "sku_1034",
        "name": "CourtKing Official Basketball",
        "category": "equipment",
        "sport": "basketball",
        "brand": "CourtKing",
        "price": 34.99,
        "available_sizes": ["Size 6", "Size 7"],
        "sizes": ["Size 6", "Size 7"],
        "description": "Official size composite leather basketball with deep channel design for consistent grip.",
        "image_url": "https://images.unsplash.com/photo-1627627256672-027a4613d028"
    },
    {
        "sku": "sku_1035",
        "name": "TrailForge Summit Hiking Boots",
        "category": "shoes",
        "sport": "hiking",
        "brand": "TrailForge",
        "price": 159.99,
        "available_sizes": ["8", "9", "10", "11", "12"],
        "sizes": [8, 9, 10, 11, 12],
        "description": "Waterproof leather hiking boots with ankle support and rugged traction sole.",
        "image_url": "https://images.unsplash.com/photo-1645259041347-bde12b3c24d9"
    },
    {
        "sku": "sku_1036",
        "name": "Velocity AeroShield Cycling Helmet",
        "category": "equipment",
        "sport": "cycling",
        "brand": "Velocity",
        "price": 79.99,
        "available_sizes": ["S/M", "L/XL"],
        "sizes": ["S/M", "L/XL"],
        "description": "Lightweight aero road cycling helmet with MIPS protection and 18 vents.",
        "image_url": "https://images.unsplash.com/photo-1554237160-bab09733f443"
    },
    {
        "sku": "sku_1037",
        "name": "ZenFlex Pro Yoga Mat",
        "category": "equipment",
        "sport": "yoga",
        "brand": "ZenFlex",
        "price": 39.99,
        "available_sizes": ["4mm", "6mm"],
        "sizes": ["4mm", "6mm"],
        "description": "Non-slip extra-cushioned yoga mat with alignment guide lines.",
        "image_url": "https://images.unsplash.com/photo-1646239646963-b0b9be56d6b5"
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
            # Filter category
            if category and str(category).lower() not in prod["category"].lower():
                continue
            # Filter sport
            if sport and str(sport).lower() not in prod["sport"].lower():
                continue
            # Filter brand
            if brand and str(brand).lower() not in prod["brand"].lower():
                continue
            # Filter price_max
            if price_max > 0 and prod["price"] > price_max:
                continue
            # Filter size flexibly
            if size:
                sz_str = str(size).lower().strip()
                prod_sizes = [str(s).lower() for s in prod.get("available_sizes", prod.get("sizes", []))]
                if sz_str not in prod_sizes:
                    continue

            # Query tokenized matching
            if query:
                q_raw = str(query).lower().strip()
                text = (
                    prod["name"] + " " +
                    prod["description"] + " " +
                    prod["category"] + " " +
                    prod["sport"] + " " +
                    prod["brand"]
                ).lower()
                
                # Check exact phrase or keyword token matches
                if q_raw not in text:
                    tokens = [t for t in q_raw.split() if len(t) > 2]
                    # Exclude stop words if necessary
                    stop_words = {"for", "the", "and", "with", "in", "size", "with"}
                    significant_tokens = [t for t in tokens if t not in stop_words]
                    
                    if significant_tokens:
                        matched_any = any(t in text for t in significant_tokens)
                        # Special handling for "training shoes" or "trail running" matching shoes category
                        if not matched_any:
                            if "shoe" in q_raw and prod["category"] == "shoes":
                                matched_any = True
                        if not matched_any:
                            continue

            matches.append(prod)

        # Fallback: if specific size filter produced 0 matches but category/query matched shoes, return catalog shoes
        if not matches and (category == "shoes" or "shoe" in str(query).lower()):
            matches = [p for p in MOCK_CATALOG if p["category"] == "shoes"]

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
