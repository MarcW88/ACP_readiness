import xml.etree.ElementTree as ET
import json
import csv
import io
from typing import Dict, List, Any, Optional
from .models import ParseResult


class FeedParser:
    """Parse various feed formats into a unified product list"""

    def parse(self, content: str, format: str = "auto") -> ParseResult:
        """Parse feed content with auto-detection"""
        if not content or not content.strip():
            return ParseResult(products=[], format="unknown")

        if format == "auto":
            format = self.detect_format(content)

        if format == "gmc_xml":
            products = self.parse_gmc_xml(content)
            metadata = {"source": "Google Merchant Center", "original_format": "XML"}
        elif format == "shopify_json":
            products = self.parse_shopify_json(content)
            metadata = {"source": "Shopify", "original_format": "JSON"}
        elif format == "acp_json":
            products = self.parse_acp_json(content)
            metadata = {"source": "ACP Feed API", "original_format": "JSON"}
        elif format == "csv":
            products = self.parse_csv(content)
            metadata = {"source": "CSV Export", "original_format": "CSV"}
        else:
            return ParseResult(products=[], format="unknown")

        available_fields = self._compute_field_coverage(products)

        return ParseResult(
            products=products,
            format=format,
            available_fields=available_fields,
            metadata=metadata
        )

    def detect_format(self, content: str) -> str:
        """Auto-detect feed format from content"""
        content = content.strip()

        if content.startswith("<"):
            if "<g:" in content or "base.google.com" in content or "<item>" in content:
                return "gmc_xml"
            return "gmc_xml"

        if content.startswith("{") or content.startswith("["):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    if "products" in data and isinstance(data["products"], list):
                        first = data["products"][0] if data["products"] else {}
                        if "variants" in first and "body_html" not in first:
                            return "acp_json"
                        if "body_html" in first or "vendor" in first:
                            return "shopify_json"
                        return "acp_json"
                    if "product" in data:
                        return "shopify_json"
                elif isinstance(data, list):
                    first = data[0] if data else {}
                    if "body_html" in first or "vendor" in first:
                        return "shopify_json"
                    return "acp_json"
            except json.JSONDecodeError:
                pass
            return "acp_json"

        if "," in content.split("\n")[0] or "\t" in content.split("\n")[0]:
            return "csv"

        return "unknown"

    def parse_gmc_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse Google Merchant Center XML feed"""
        products = []
        try:
            root = ET.fromstring(xml_content)
            ns = "http://base.google.com/ns/1.0"

            for item in root.findall('.//{http://www.w3.org/2005/Atom}entry') or root.findall('.//item'):
                product = self._extract_gmc_product(item, ns)
                if product and product.get("id"):
                    products.append(product)

            if not products:
                for item in root.findall('.//item'):
                    product = self._extract_gmc_product(item, ns)
                    if product and product.get("id"):
                        products.append(product)

        except ET.ParseError:
            pass
        return products

    def _extract_gmc_product(self, item, ns: str) -> Dict[str, Any]:
        """Extract product data from a GMC XML item"""
        def get_text(tag):
            elem = item.find(f'.//{{{ns}}}{tag}')
            if elem is not None and elem.text:
                return elem.text.strip()
            elem = item.find(f'.//{tag}')
            if elem is not None and elem.text:
                return elem.text.strip()
            return None

        product = {
            "id": get_text("id"),
            "title": get_text("title"),
            "description": get_text("description"),
            "link": get_text("link"),
            "image_link": get_text("image_link"),
            "additional_image_link": get_text("additional_image_link"),
            "price": get_text("price"),
            "sale_price": get_text("sale_price"),
            "availability": get_text("availability"),
            "brand": get_text("brand"),
            "gtin": get_text("gtin"),
            "mpn": get_text("mpn"),
            "condition": get_text("condition"),
            "product_category": get_text("google_product_category") or get_text("product_type"),
            "color": get_text("color"),
            "size": get_text("size"),
            "material": get_text("material"),
            "gender": get_text("gender"),
            "age_group": get_text("age_group"),
            "item_group_id": get_text("item_group_id"),
            "shipping_weight": get_text("shipping_weight"),
            "custom_label_0": get_text("custom_label_0"),
            "custom_label_1": get_text("custom_label_1"),
        }

        # Clean None values
        return {k: v for k, v in product.items() if v is not None}

    def parse_shopify_json(self, json_content: str) -> List[Dict[str, Any]]:
        """Parse Shopify product JSON export"""
        products = []
        try:
            data = json.loads(json_content)
            if isinstance(data, dict) and "products" in data:
                raw_products = data["products"]
            elif isinstance(data, dict) and "product" in data:
                raw_products = [data["product"]]
            elif isinstance(data, list):
                raw_products = data
            else:
                return []

            for p in raw_products:
                base = {
                    "id": str(p.get("id", "")),
                    "title": p.get("title", ""),
                    "description": p.get("body_html", ""),
                    "link": p.get("handle", ""),
                    "brand": p.get("vendor", ""),
                    "product_category": p.get("product_type", ""),
                    "image_link": p.get("images", [{}])[0].get("src", "") if p.get("images") else "",
                    "tags": p.get("tags", []),
                }
                variants = p.get("variants", [])
                if variants:
                    for v in variants:
                        product = {
                            **base,
                            "variant_id": str(v.get("id", "")),
                            "price": str(v.get("price", "")),
                            "availability": "in stock" if v.get("available", True) else "out of stock",
                            "gtin": v.get("barcode", ""),
                            "sku": v.get("sku", ""),
                            "size": v.get("option1", ""),
                            "color": v.get("option2", ""),
                            "item_group_id": str(p.get("id", "")),
                        }
                        products.append({k: v for k, v in product.items() if v})
                else:
                    products.append({k: v for k, v in base.items() if v})

        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return products

    def parse_acp_json(self, json_content: str) -> List[Dict[str, Any]]:
        """Parse ACP Feed API JSON (already in target format)"""
        products = []
        try:
            data = json.loads(json_content)
            if isinstance(data, list):
                raw = data
            elif isinstance(data, dict) and "products" in data:
                raw = data["products"]
            elif isinstance(data, dict):
                raw = [data]
            else:
                return []

            for p in raw:
                base = {k: v for k, v in p.items() if k != "variants"}
                variants = p.get("variants", [])
                if variants:
                    for v in variants:
                        merged = {**base, **v, "variant_id": v.get("id"), "is_variant": True}
                        products.append(merged)
                else:
                    products.append({**base, "is_variant": False})

        except json.JSONDecodeError:
            pass
        return products

    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV/TSV feed export"""
        products = []
        try:
            dialect = csv.Sniffer().sniff(csv_content[:2048])
            reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)
            for row in reader:
                product = {k.strip().lower().replace(" ", "_"): v.strip()
                           for k, v in row.items() if v and v.strip()}
                if product.get("id") or product.get("product_id"):
                    if "product_id" in product and "id" not in product:
                        product["id"] = product["product_id"]
                    products.append(product)
        except (csv.Error, Exception):
            pass
        return products

    def _compute_field_coverage(self, products: List[Dict]) -> Dict[str, float]:
        """Compute field fill rate across all products"""
        if not products:
            return {}

        all_fields = set()
        for p in products:
            all_fields.update(p.keys())

        coverage = {}
        total = len(products)
        for field_name in sorted(all_fields):
            count = sum(1 for p in products if p.get(field_name))
            coverage[field_name] = round(count / total, 3)

        return coverage

    def get_field_samples(self, products: List[Dict], field: str, n: int = 3) -> List[str]:
        """Get sample values for a field"""
        samples = []
        for p in products:
            val = p.get(field)
            if val and str(val) not in samples:
                samples.append(str(val)[:100])
            if len(samples) >= n:
                break
        return samples
