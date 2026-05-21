import json
from typing import Dict, List, Any, Optional
from .models import ACPProduct, ACPVariant


class ACPFeedGenerator:
    """Generate ACP Feed API 2026-04-17 JSON output"""

    def generate(self, products: List[ACPProduct], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate complete ACP Feed API structure"""
        feed = {
            "products": [p.to_dict() for p in products]
        }
        if metadata:
            if metadata.get("feed_id"):
                feed["id"] = metadata["feed_id"]
            if metadata.get("target_country"):
                feed["target_country"] = metadata["target_country"]
        return feed

    def to_json(self, feed: Dict[str, Any], pretty: bool = True) -> str:
        """Convert feed to JSON string"""
        if pretty:
            return json.dumps(feed, indent=2, ensure_ascii=False)
        return json.dumps(feed, ensure_ascii=False)

    def generate_sample(self, products: List[ACPProduct], n: int = 5) -> str:
        """Generate a sample JSON with first N products"""
        sample = products[:n]
        feed = self.generate(sample)
        return self.to_json(feed)

    def generate_single_product(self, product: ACPProduct) -> str:
        """Generate JSON for a single product"""
        return json.dumps(product.to_dict(), indent=2, ensure_ascii=False)

    def get_stats(self, products: List[ACPProduct]) -> Dict[str, Any]:
        """Get statistics about the generated feed"""
        total_products = len(products)
        total_variants = sum(len(p.variants) for p in products)
        products_with_media = sum(1 for p in products if p.media)
        products_with_desc = sum(1 for p in products if p.description)
        products_with_url = sum(1 for p in products if p.url)

        variants_with_price = 0
        variants_with_availability = 0
        variants_with_categories = 0
        variants_with_seller = 0
        variants_with_options = 0

        for p in products:
            for v in p.variants:
                if v.price:
                    variants_with_price += 1
                if v.availability:
                    variants_with_availability += 1
                if v.categories:
                    variants_with_categories += 1
                if v.seller:
                    variants_with_seller += 1
                if v.variant_options:
                    variants_with_options += 1

        return {
            "total_products": total_products,
            "total_variants": total_variants,
            "product_fields": {
                "id": total_products,
                "title": total_products,
                "description": products_with_desc,
                "url": products_with_url,
                "media": products_with_media,
            },
            "variant_fields": {
                "id": total_variants,
                "price": variants_with_price,
                "availability": variants_with_availability,
                "categories": variants_with_categories,
                "seller": variants_with_seller,
                "variant_options": variants_with_options,
            },
            "completeness": {
                "product_required": 1.0,  # id and title always present after mapping
                "product_recommended": round(
                    (products_with_desc + products_with_url + products_with_media) / (total_products * 3)
                    if total_products > 0 else 0, 3),
                "variant_required": round(
                    (variants_with_price + variants_with_availability) / (total_variants * 2)
                    if total_variants > 0 else 0, 3),
                "variant_recommended": round(
                    (variants_with_categories + variants_with_seller + variants_with_options) / (total_variants * 3)
                    if total_variants > 0 else 0, 3),
            }
        }
