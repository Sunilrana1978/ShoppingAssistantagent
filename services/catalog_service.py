import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from services.interfaces import ICatalogService

class MockCatalogService(ICatalogService):
    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = Path(__file__).parent.parent / "data" / "mock_catalog.json"
        self.data_path = Path(data_path)
        self._load_data()

    def _load_data(self):
        if self.data_path.exists():
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {}

    def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        return self.catalog.get(sku)

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        sport: Optional[str] = None,
        brand: Optional[str] = None,
        size: Optional[Any] = None,
        price_max: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        results = []
        q_tokens = query.lower().split() if query else []

        for sku, prod in self.catalog.items():
            # Category filter
            if category and prod.get("category", "").lower() != category.lower():
                continue
            # Sport filter
            if sport and prod.get("sport", "").lower() != sport.lower():
                continue
            # Brand filter
            if brand and prod.get("brand", "").lower() != brand.lower():
                continue
            # Price filter
            if price_max is not None and prod.get("price", 0.0) > float(price_max):
                continue
            # Size filter
            if size is not None:
                sizes = prod.get("sizes", [])
                if size not in sizes and str(size) not in [str(s) for s in sizes]:
                    continue

            # Free-text relevance scoring
            if q_tokens:
                text_corpus = f"{prod.get('name', '')} {prod.get('description', '')} {prod.get('sport', '')} {prod.get('category', '')} {prod.get('brand', '')}".lower()
                matches = sum(1 for token in q_tokens if token in text_corpus)
                if matches == 0:
                    continue

            results.append(prod)

        return results

catalog_service = MockCatalogService()
