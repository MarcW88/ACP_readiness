import json
import os
import re
from typing import Dict, List, Any, Optional
from .models import MappingRule, ACPProduct, ACPVariant


# Known field aliases for fuzzy matching
FIELD_ALIASES = {
    "product.id": ["id", "product_id", "sku", "item_id"],
    "product.title": ["title", "name", "product_name", "product_title"],
    "product.description": ["description", "body_html", "short_description", "long_description"],
    "product.url": ["link", "url", "product_url", "canonical_url", "handle"],
    "product.media": ["image_link", "image_url", "images", "main_image", "image_src"],
    "variant.id": ["variant_id", "sku", "id", "item_id"],
    "variant.price": ["price", "sale_price", "current_price", "unit_price"],
    "variant.availability": ["availability", "stock_status", "in_stock", "available"],
    "variant.title": ["title", "variant_title", "name"],
    "variant.description": ["description", "variant_description"],
    "variant.url": ["link", "url", "variant_url"],
    "variant.media": ["image_link", "variant_image", "image_url"],
    "variant.list_price": ["sale_price", "compare_at_price", "list_price", "original_price", "price"],
    "variant.categories": ["product_category", "google_product_category", "product_type", "category", "categories"],
    "variant.condition": ["condition", "item_condition"],
    "variant.variant_options": ["color", "size", "material", "option1", "option2", "option3"],
    "variant.seller": ["brand", "vendor", "seller_name", "merchant"],
}


class FieldMapper:
    """Maps source feed fields to ACP Feed API fields"""

    def __init__(self, preset: str = "gmc_to_acp"):
        self.rules: List[MappingRule] = []
        self.preset_name = preset
        self.load_preset(preset)

    def load_preset(self, name: str):
        """Load mapping rules from a preset JSON file"""
        preset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "presets")
        preset_path = os.path.join(preset_dir, f"{name}.json")

        if os.path.exists(preset_path):
            with open(preset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules = [
                    MappingRule(
                        acp_field=r["acp_field"],
                        source_field=r.get("source_field"),
                        transform=r.get("transform", "direct"),
                        params=r.get("params")
                    )
                    for r in data.get("rules", [])
                ]
        else:
            self.rules = self._get_default_rules()

    def _get_default_rules(self) -> List[MappingRule]:
        """Default GMC → ACP mapping rules"""
        return [
            MappingRule("product.id", "id", "direct"),
            MappingRule("product.title", "title", "direct"),
            MappingRule("product.description", "description", "direct"),
            MappingRule("product.url", "link", "direct"),
            MappingRule("product.media", "image_link", "to_array"),
            MappingRule("variant.id", "id", "prefix", {"prefix": "var_"}),
            MappingRule("variant.price", "price", "direct"),
            MappingRule("variant.availability", "availability", "map_values",
                        {"in stock": "in_stock", "out of stock": "out_of_stock",
                         "preorder": "preorder", "backorder": "backorder"}),
            MappingRule("variant.categories", "product_category", "split", {"separator": " > "}),
            MappingRule("variant.condition", "condition", "direct"),
            MappingRule("variant.list_price", "sale_price", "direct"),
            MappingRule("variant.seller", "brand", "to_seller"),
        ]

    def auto_map(self, source_fields: List[str]) -> List[MappingRule]:
        """Automatically map source fields to ACP fields using fuzzy matching"""
        rules = []
        source_lower = {f.lower(): f for f in source_fields}

        for acp_field, aliases in FIELD_ALIASES.items():
            matched_source = None
            for alias in aliases:
                if alias.lower() in source_lower:
                    matched_source = source_lower[alias.lower()]
                    break

            if matched_source:
                transform = self._suggest_transform(acp_field, matched_source)
                rules.append(MappingRule(
                    acp_field=acp_field,
                    source_field=matched_source,
                    transform=transform
                ))
            else:
                rules.append(MappingRule(
                    acp_field=acp_field,
                    source_field=None,
                    transform="none"
                ))

        self.rules = rules
        return rules

    def _suggest_transform(self, acp_field: str, source_field: str) -> str:
        """Suggest the best transform based on field types"""
        if acp_field.endswith(".media"):
            return "to_array"
        if acp_field == "variant.availability":
            return "map_values"
        if acp_field == "variant.categories":
            return "split"
        if acp_field == "variant.seller":
            return "to_seller"
        if acp_field == "variant.variant_options":
            return "to_options"
        return "direct"

    def apply_mapping(self, product: Dict[str, Any]) -> ACPProduct:
        """Apply mapping rules to convert a source product to ACPProduct"""
        product_fields = {}
        variant_fields = {}

        for rule in self.rules:
            if not rule.source_field or rule.transform == "none":
                continue

            raw_value = product.get(rule.source_field)
            if raw_value is None:
                continue

            transformed = self._apply_transform(raw_value, rule.transform, rule.params, product)

            if rule.acp_field.startswith("product."):
                field_name = rule.acp_field.replace("product.", "")
                product_fields[field_name] = transformed
            elif rule.acp_field.startswith("variant."):
                field_name = rule.acp_field.replace("variant.", "")
                variant_fields[field_name] = transformed

        # Build ACPProduct
        acp_product = ACPProduct(
            id=product_fields.get("id", product.get("id", "")),
            title=product_fields.get("title", product.get("title", "")),
            description=product_fields.get("description"),
            url=product_fields.get("url"),
            media=product_fields.get("media"),
        )

        # Build variant
        variant = ACPVariant(
            id=variant_fields.get("id", f"var_{product.get('id', '')}"),
            price=variant_fields.get("price", product.get("price", "")),
            availability=variant_fields.get("availability", "in_stock"),
            title=variant_fields.get("title"),
            description=variant_fields.get("description"),
            url=variant_fields.get("url"),
            media=variant_fields.get("media"),
            list_price=variant_fields.get("list_price"),
            categories=variant_fields.get("categories"),
            condition=variant_fields.get("condition"),
            variant_options=variant_fields.get("variant_options"),
            seller=variant_fields.get("seller"),
        )

        acp_product.variants = [variant]
        return acp_product

    def _apply_transform(self, value: Any, transform: str, params: Optional[Dict], product: Dict = None) -> Any:
        """Apply a transformation to a value"""
        if value is None:
            return None

        if transform == "direct":
            return str(value)

        elif transform == "to_array":
            if isinstance(value, list):
                return value
            return [str(value)]

        elif transform == "split":
            separator = (params or {}).get("separator", " > ")
            return [s.strip() for s in str(value).split(separator) if s.strip()]

        elif transform == "prefix":
            prefix = (params or {}).get("prefix", "")
            return f"{prefix}{value}"

        elif transform == "map_values":
            mapping = params or {}
            str_val = str(value).lower().strip()
            return mapping.get(str_val, str_val)

        elif transform == "to_seller":
            return {"name": str(value), "url": ""}

        elif transform == "to_options":
            options = {}
            if product:
                for opt_field in ["color", "size", "material", "option1", "option2", "option3"]:
                    opt_val = product.get(opt_field)
                    if opt_val:
                        options[opt_field] = str(opt_val)
            if not options and value:
                options["value"] = str(value)
            return options if options else None

        elif transform == "constant":
            return (params or {}).get("value")

        elif transform == "template":
            template = (params or {}).get("template", "{value}")
            try:
                if product:
                    return template.format(value=value, **product)
                return template.format(value=value)
            except (KeyError, IndexError):
                return str(value)

        elif transform == "format_price":
            price_str = str(value).strip()
            match = re.match(r'([\d.,]+)\s*(\w{3})?', price_str)
            if match:
                amount = match.group(1)
                currency = match.group(2) or (params or {}).get("currency", "USD")
                return f"{amount} {currency}"
            return price_str

        return str(value)

    def get_unmapped_fields(self) -> List[str]:
        """Get ACP fields that have no source mapping"""
        return [r.acp_field for r in self.rules if not r.source_field or r.transform == "none"]

    def get_mapped_fields(self) -> List[str]:
        """Get ACP fields that have a source mapping"""
        return [r.acp_field for r in self.rules if r.source_field and r.transform != "none"]

    def update_rule(self, acp_field: str, source_field: Optional[str], transform: str = "direct", params: Optional[Dict] = None):
        """Update a specific mapping rule"""
        for i, rule in enumerate(self.rules):
            if rule.acp_field == acp_field:
                self.rules[i] = MappingRule(acp_field, source_field, transform, params)
                return
        self.rules.append(MappingRule(acp_field, source_field, transform, params))

    def export_rules(self) -> List[Dict]:
        """Export current rules as dict list"""
        return [r.to_dict() for r in self.rules]
