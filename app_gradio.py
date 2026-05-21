import gradio as gr
import xml.etree.ElementTree as ET
import json
import re
from collections import defaultdict, Counter
from typing import Dict, List, Any
import base64
from datetime import datetime
import tempfile

class CommerceReadinessChecker:
    def __init__(self):
        self.required_fields = [
            "enable_search", "enable_checkout", "id", "title", "description", 
            "link", "image_link", "price", "currency", "availability", "brand",
            "gtin_or_mpn", "material", "weight", "inventory_quantity",
            "seller_name", "seller_url", "return_policy", "return_window"
        ]
        
        self.recommended_fields = [
            "additional_image_link", "product_category", "color", "size"
        ]

    def parse_xml_feed(self, xml_content: str) -> List[Dict]:
        """Parse Google Merchant XML feed"""
        try:
            if not xml_content or not xml_content.strip():
                return []
                
            root = ET.fromstring(xml_content)
            products = []
            
            for item in root.findall('.//item'):
                product = self._extract_product_data(item)
                if product:  # Only add valid products
                    products.append(product)
                
            return products
        except Exception as e:
            raise ValueError(f"Erreur parsing XML: {str(e)}")

    def _extract_product_data(self, item) -> Dict:
        """Extract and normalize product data from XML item"""
        def get_text(tag):
            # Try with Google namespace first
            ns = "http://base.google.com/ns/1.0"
            elem = item.find(f'.//{{{ns}}}{tag}')
            if elem is not None:
                return elem.text
            # Fallback without namespace
            elem = item.find(f'.//{tag}')
            return elem.text if elem is not None else None

        def get_direct_text(tag):
            # For non-namespaced tags like title, description, link
            elem = item.find(f'./{tag}')
            return elem.text if elem is not None else None

        # Parse price
        price_str = get_text('price') or ""
        price_match = re.match(r'([\d.,]+)\s*(\w+)', price_str)
        price = float(price_match.group(1).replace(',', '.')) if price_match else None
        currency = price_match.group(2) if price_match else None

        # Handle multiple additional_image_link elements
        additional_images = []
        for img_elem in item.findall('.//{http://base.google.com/ns/1.0}additional_image_link'):
            if img_elem.text:
                additional_images.append(img_elem.text)
        
        return {
            "id": get_text('id'),
            "title": get_direct_text('title'),
            "description": get_direct_text('description'), 
            "link": get_direct_text('link'),
            "image_link": get_text('image_link'),
            "additional_image_link": additional_images[0] if additional_images else None,
            "additional_images": additional_images,
            "price": price,
            "currency": currency,
            "availability": get_text('availability'),
            "brand": get_text('brand'),
            "gtin": get_text('gtin'),
            "mpn": get_text('mpn'),
            "product_category": get_text('product_type') or get_text('google_product_category'),
            "color": get_text('color'),
            "size": get_text('size'),
            "gender": get_text('gender'),
            "age_group": get_text('age_group'),
            "condition": get_text('condition'),
            "item_group_id": get_text('item_group_id'),
            "sale_price": get_text('sale_price'),
            # ACP specific fields (always None in GMC feeds)
            "enable_search": None,
            "enable_checkout": None,
            "material": None,
            "weight": None,
            "inventory_quantity": None,
            "seller_name": None,
            "seller_url": None,
            "seller_privacy_policy": None,
            "seller_tos": None,
            "return_policy": None,
            "return_window": None,
        }

    def _get_namespace(self):
        return "http://base.google.com/ns/1.0"
    
    def _analyze_fields_detailed(self, products: List[Dict]) -> Dict:
        """Analyze field coverage in detail with visual status"""
        total_products = len(products)
        if total_products == 0:
            return {}
        
        field_categories = {
            "OPENAI FLAGS": {
                "enable_search": {"required": True, "description": "Required field 'enable_search' is missing"},
                "enable_checkout": {"required": True, "description": "Required field 'enable_checkout' is missing"}
            },
            "BASIC PRODUCT DATA": {
                "id": {"required": True, "description": "Required field 'id' is missing"},
                "title": {"required": True, "description": "Required field 'title' is missing"},
                "description": {"required": True, "description": "Required field 'description' is missing"},
                "link": {"required": True, "description": "Required field 'link' is missing"},
                "image_link": {"required": True, "description": "Required field 'image_link' is missing"},
                "additional_image_link": {"required": False, "description": "Not set"}
            },
            "PRICING & AVAILABILITY": {
                "price": {"required": True, "description": "Required field 'price' is missing"},
                "currency": {"required": True, "description": "Required field 'currency' is missing"},
                "availability": {"required": True, "description": "Required field 'availability' is missing"},
                "inventory_quantity": {"required": True, "description": "Required field 'inventory_quantity' is missing"}
            },
            "ITEM INFORMATION": {
                "brand": {"required": True, "description": "Required for all products except movies, books, and musical recordings"},
                "gtin": {"required": False, "description": "Not set"},
                "mpn": {"required": False, "description": "Manufacturer part number (required if no GTIN)"},
                "product_category": {"required": True, "description": "Required field 'product_category' is missing"},
                "material": {"required": True, "description": "Required field 'material' is missing"},
                "weight": {"required": True, "description": "Required field 'weight' is missing"},
                "color": {"required": False, "description": "Not set"},
                "size": {"required": False, "description": "Not set"}
            },
            "MERCHANT INFO": {
                "seller_name": {"required": True, "description": "Required field 'seller_name' is missing"},
                "seller_url": {"required": True, "description": "Required field 'seller_url' is missing"},
                "return_policy": {"required": True, "description": "Required field 'return_policy' is missing"},
                "return_window": {"required": True, "description": "Required field 'return_window' is missing"}
            }
        }
        
        analysis = {}
        
        for category_name, fields in field_categories.items():
            category_analysis = []
            
            for field_name, field_info in fields.items():
                count_with_field = 0
                for product in products:
                    value = product.get(field_name)
                    if value is not None and value != "" and value != 0:
                        count_with_field += 1
                
                coverage = count_with_field / total_products
                coverage_pct = coverage * 100
                
                if field_info["required"]:
                    if coverage >= 0.95:
                        status = "✅ Pass"
                        status_class = "pass"
                    elif coverage >= 0.5:
                        status = "⚠️ Warning"
                        status_class = "warning"
                    else:
                        status = "❌ Fail"
                        status_class = "fail"
                else:
                    if coverage >= 0.8:
                        status = "✅ Pass"
                        status_class = "pass"
                    elif coverage >= 0.3:
                        status = "⚠️ Warning"
                        status_class = "warning"
                    else:
                        status = "— Not Set"
                        status_class = "not_set"
                
                if field_name in ["gtin", "mpn"]:
                    gtin_count = sum(1 for p in products if p.get("gtin"))
                    mpn_count = sum(1 for p in products if p.get("mpn"))
                    combined_coverage = (gtin_count + mpn_count) / total_products
                    
                    if field_name == "gtin" and combined_coverage >= 0.95:
                        status = "✅ Pass"
                        status_class = "pass"
                
                category_analysis.append({
                    "field": field_name.replace("_", " ").title(),
                    "status": status,
                    "status_class": status_class,
                    "coverage": round(coverage_pct, 1),
                    "count": count_with_field,
                    "description": field_info["description"],
                    "required": field_info["required"]
                })
            
            analysis[category_name] = category_analysis
        
        return analysis

    def check_acp_compliance(self, product: Dict) -> Dict:
        """Check ACP compliance for a single product"""
        if not product:
            return {
                "id": "unknown",
                "title": "",
                "missing_required": self.required_fields.copy(),
                "missing_recommended": self.recommended_fields.copy(),
                "score": 0.0,
                "product_category": "Unknown"
            }
            
        missing_required = []
        missing_recommended = []

        for field in ["enable_search", "enable_checkout", "material", "weight", 
                     "inventory_quantity", "seller_name", "seller_url", 
                     "return_policy", "return_window"]:
            if not product.get(field):
                missing_required.append(field)

        for field in ["id", "title", "description", "link", "image_link", 
                     "price", "currency", "availability", "brand"]:
            if not product.get(field):
                missing_required.append(field)

        if not product.get("gtin") and not product.get("mpn"):
            missing_required.append("gtin_or_mpn")

        if not product.get("additional_image_link"):
            missing_recommended.append("additional_image_link")
        if not product.get("product_category"):
            missing_recommended.append("product_category")

        category = (product.get("product_category") or "").lower()
        if any(x in category for x in ["chaussures", "apparel", "shoes", "clothing"]):
            if not product.get("color"):
                missing_recommended.append("color")
            if not product.get("size"):
                missing_recommended.append("size")

        total_required = len(self.required_fields)
        missing_count = len(set(missing_required))
        score = max(0, 100 * (total_required - missing_count) / total_required)

        return {
            "id": product["id"],
            "title": product.get("title", "")[:50] + "..." if product.get("title", "") else "",
            "missing_required": list(set(missing_required)),
            "missing_recommended": list(set(missing_recommended)),
            "score": round(score, 1),
            "product_category": product.get("product_category", "Unknown")
        }

    def check_google_ai_product(self, product: Dict) -> Dict:
        """Check Google AI Shopping readiness for a single product"""
        if not product:
            return {
                "id": "unknown",
                "title": "",
                "score_google_ai": 0.0,
                "missing_core": [],
                "missing_enriched": [],
                "missing_agentic": [],
                "product_category": "Unknown"
            }
        
        core_fields = ["title", "description", "image_link", "price", "currency",
                       "availability", "brand", "link", "product_category"]
        missing_core = []
        for field in core_fields:
            if not product.get(field):
                missing_core.append(field)
        
        if not product.get("gtin") and not product.get("mpn"):
            missing_core.append("gtin_or_mpn")
        
        enriched_fields = ["additional_image_link", "color", "size", "gender", 
                          "age_group", "material", "weight"]
        missing_enriched = []
        for field in enriched_fields:
            if not product.get(field):
                missing_enriched.append(field)
        
        agentic_fields = ["inventory_quantity", "item_group_id"]
        missing_agentic = []
        for field in agentic_fields:
            if not product.get(field):
                missing_agentic.append(field)
        
        core_total = len(core_fields) + 1
        score_core = 100 * (core_total - len(missing_core)) / core_total if core_total > 0 else 0
        
        enriched_total = len(enriched_fields)
        score_enriched = 100 * (enriched_total - len(missing_enriched)) / enriched_total if enriched_total > 0 else 0
        
        agentic_total = len(agentic_fields)
        score_agentic = 100 * (agentic_total - len(missing_agentic)) / agentic_total if agentic_total > 0 else 0
        
        score_global = 0.6 * score_core + 0.3 * score_enriched + 0.1 * score_agentic
        
        return {
            "id": product.get("id", ""),
            "title": product.get("title", ""),
            "score_google_ai": round(score_global, 1),
            "missing_core": sorted(set(missing_core)),
            "missing_enriched": sorted(set(missing_enriched)),
            "missing_agentic": sorted(set(missing_agentic)),
            "product_category": product.get("product_category", "Unknown")
        }

    def _analyze_single_product(self, product: Dict) -> Dict:
        """Analyze a single product for AI Shopping readiness"""
        if not product:
            return {
                "score": 0,
                "errors": [],
                "warnings": [],
                "passed": [],
                "analysis": "Produit invalide ou données manquantes."
            }

        errors = []
        warnings = []
        passed = []
        
        field_checks = {
            "SEO & Page Optimization": {
                "title": {"value": product.get("title"), "required": True, "message": "Product title is missing"},
                "description": {"value": product.get("description"), "required": True, "message": "Product description is missing"},
                "link": {"value": product.get("link"), "required": True, "message": "Product URL is missing"},
                "image_link": {"value": product.get("image_link"), "required": True, "message": "Main product image is missing"}
            },
            "OpenAI Flags": {
                "enable_search": {"value": product.get("enable_search"), "required": True, "message": "Required field 'enable_search' is missing"},
                "enable_checkout": {"value": product.get("enable_checkout"), "required": True, "message": "Required field 'enable_checkout' is missing"}
            },
            "Basic Product Data": {
                "id": {"value": product.get("id"), "required": True, "message": "Product ID is missing"},
                "brand": {"value": product.get("brand"), "required": True, "message": "Brand information is missing"},
                "gtin": {"value": product.get("gtin"), "required": False, "message": "GTIN is not provided"},
                "mpn": {"value": product.get("mpn"), "required": False, "message": "MPN is not provided"},
                "price": {"value": product.get("price"), "required": True, "message": "Product price is missing"},
                "availability": {"value": product.get("availability"), "required": True, "message": "Availability status is missing"}
            },
            "Product Content": {
                "material": {"value": product.get("material"), "required": True, "message": "Material information is missing"},
                "weight": {"value": product.get("weight"), "required": True, "message": "Product weight is missing"},
                "color": {"value": product.get("color"), "required": False, "message": "Color information is not set"},
                "size": {"value": product.get("size"), "required": False, "message": "Size information is not set"}
            },
            "Merchant Info": {
                "seller_name": {"value": product.get("seller_name"), "required": True, "message": "Seller name is missing"},
                "seller_url": {"value": product.get("seller_url"), "required": True, "message": "Seller URL is missing"},
                "return_policy": {"value": product.get("return_policy"), "required": True, "message": "Return policy is missing"},
                "return_window": {"value": product.get("return_window"), "required": True, "message": "Return window is missing"}
            }
        }
        
        for category, fields in field_checks.items():
            for field_name, check in fields.items():
                value = check["value"]
                is_required = check["required"]
                message = check["message"]
                
                if value is None or value == "" or value == 0:
                    if is_required:
                        errors.append({
                            "category": category,
                            "field": field_name,
                            "message": message,
                            "status": "Fail"
                        })
                    else:
                        warnings.append({
                            "category": category,
                            "field": field_name,
                            "message": message,
                            "status": "Not set"
                        })
                else:
                    passed.append({
                        "category": category,
                        "field": field_name,
                        "message": f"{field_name.replace('_', ' ').title()} is properly set",
                        "status": "Pass"
                    })
        
        total_fields = len(errors) + len(warnings) + len(passed)
        score = round((len(passed) / total_fields) * 100, 1) if total_fields > 0 else 0
        
        analysis_text = self._generate_ai_analysis_text(product, errors, warnings, passed, score)
        
        return {
            "score": score,
            "errors": errors,
            "warnings": warnings,
            "passed": passed,
            "analysis": analysis_text,
            "field_checks": field_checks
        }

    def _generate_ai_analysis_text(self, product, errors, warnings, passed, score):
        """Generate AI-style analysis text"""
        product_name = product.get("title", "Ce produit")
        
        if score >= 80:
            return f"{product_name} présente une excellente compatibilité avec l'AI Shopping. La plupart des champs requis sont présents et correctement renseignés."
        elif score >= 50:
            return f"{product_name} nécessite des améliorations modérées pour optimiser sa compatibilité AI Shopping. Les données de base sont présentes mais plusieurs champs critiques manquent."
        else:
            critical_missing = [e["field"] for e in errors[:3]]
            return f"{product_name} présente des lacunes importantes pour l'AI Shopping. Les champs critiques manquants incluent {', '.join(critical_missing)}."

    def _generate_feed_hero_html(self, first_product, full_analysis):
        """Generate HTML for feed hero section"""
        score = full_analysis["global_score"]
        total_products = full_analysis["total_products"]
        
        field_analysis = full_analysis.get("field_analysis", {})
        total_errors = 0
        total_warnings = 0
        total_passed = 0
        
        for category, fields in field_analysis.items():
            for field in fields:
                if field["status_class"] == "fail":
                    total_errors += 1
                elif field["status_class"] == "warning":
                    total_warnings += 1
                elif field["status_class"] == "pass":
                    total_passed += 1
        
        if score >= 80:
            score_color = "#43A047"
            score_label = "Excellent"
        elif score >= 50:
            score_color = "#FB8C00"
            score_label = "Needs improvement"
        else:
            score_color = "#E53935"
            score_label = "Critical issues"
        
        context_parts = [f"Analysé sur {total_products:,} produits du feed"]
        context = " • ".join(context_parts)
        
        return f"""
        <div class="product-hero">
            <div class="product-image">
                <div style="width: 120px; height: 120px; background: linear-gradient(135deg, #0079B2, #00A3E0); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">
                    ACP
                </div>
            </div>
            <div class="product-info">
                <h2 class="product-name">Analyse du Feed Produit</h2>
                <p class="product-context">{context}</p>
            </div>
            <div class="product-scores">
                <div class="main-score">
                    <div class="score-number" style="color: {score_color};">{score}%</div>
                    <div class="score-label">{score_label}</div>
                </div>
                <div class="status-badges">
                    <div class="status-badge badge-error">{total_errors} Champs Manquants</div>
                    <div class="status-badge badge-warning">{total_warnings} Avertissements</div>
                    <div class="status-badge badge-passed">{total_passed} Conformes</div>
                </div>
            </div>
        </div>
        """

    def _generate_feed_ai_analysis_html(self, full_analysis):
        """Generate HTML for AI analysis section"""
        score = full_analysis["global_score"]
        total_products = full_analysis["total_products"]
        top_missing = full_analysis.get("top_missing_fields", [])[:3]
        
        if score >= 80:
            analysis_text = f"Votre feed de {total_products:,} produits présente une excellente compatibilité avec l'AI Shopping."
        elif score >= 50:
            missing_fields = ", ".join([f["field"] for f in top_missing])
            analysis_text = f"Votre feed de {total_products:,} produits nécessite des améliorations modérées. Champs critiques: {missing_fields}."
        else:
            missing_fields = ", ".join([f["field"] for f in top_missing])
            analysis_text = f"Votre feed de {total_products:,} produits présente des lacunes importantes. Champs critiques: {missing_fields}."
        
        return f"""
        <div class="ai-analysis">
            <h2 class="section-title">AI Analysis</h2>
            <p class="analysis-text">{analysis_text}</p>
        </div>
        """

    def _generate_feed_category_section_html(self, category_name, full_analysis):
        """Generate HTML for category sections"""
        field_analysis = full_analysis.get("field_analysis", {})
        
        category_mapping = {
            "SEO & Page Optimization": "BASIC PRODUCT DATA",
            "OpenAI Flags": "OPENAI FLAGS", 
            "Basic Product Data": "BASIC PRODUCT DATA",
            "Product Content": "ITEM INFORMATION",
            "Merchant Info": "MERCHANT INFO"
        }
        
        analysis_category = category_mapping.get(category_name, category_name.upper())
        fields = field_analysis.get(analysis_category, [])
        
        if not fields:
            return ""
        
        errors = sum(1 for f in fields if f["status_class"] == "fail")
        warnings = sum(1 for f in fields if f["status_class"] == "warning") 
        passed = sum(1 for f in fields if f["status_class"] == "pass")
        
        table_rows = ""
        for field in fields:
            status_class = f"status-{field['status_class']}"
            status_text = field['status']
            
            coverage = field.get("coverage", 0)
            count = field.get("count", 0)
            total = full_analysis["total_products"]
            
            table_rows += f"""
            <tr>
                <td class="field-name">{field['field']}</td>
                <td class="field-message">{coverage}% coverage ({count:,}/{total:,} products)</td>
                <td><span class="field-status {status_class}">{status_text}</span></td>
            </tr>
            """
        
        return f"""
        <div class="category-card">
            <div class="category-header">
                <h2 class="category-title">{category_name}</h2>
                <div class="category-stats">
                    <span>Missing: {errors}</span>
                    <span>Warnings: {warnings}</span>
                    <span>Complete: {passed}</span>
                </div>
            </div>
            <table class="fields-table">
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Coverage</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

    def _generate_product_details_html(self, full_analysis):
        """Generate detailed product analysis"""
        products = self.parse_xml_feed(full_analysis.get("xml_content", ""))
        if not products:
            return "<p>Aucun détail produit disponible</p>"
        
        total_products = len(products)
        sample_count = min(len(products), 10)
        sample_products = products[:sample_count]
        
        details_html = f"""
        <div style="margin-bottom: 20px; padding: 16px; background: #F4F3EC; border-radius: 8px;">
            <strong>Analyse détaillée de {sample_count} produits sur {total_products} total</strong>
        </div>
        """
        
        for i, product in enumerate(sample_products):
            product_analysis = self._analyze_single_product(product)
            
            product_title = product.get("title", f"Produit {i+1}")
            product_id = product.get("id", "")
            
            name_parts = [product_title[:40]]
            if product_id:
                name_parts.append(f"ID: {product_id}")
            
            product_name = " • ".join(name_parts)
            if len(product_name) > 80:
                product_name = product_name[:80] + "..."
            
            field_details = ""
            for category, checks in product_analysis["field_checks"].items():
                field_details += f"<h4 style='color: #141414; margin: 16px 0 8px 0;'>{category}</h4>"
                for field_name, check in checks.items():
                    value = check["value"]
                    required = check["required"]
                    
                    if value:
                        status_class = "status-pass"
                        status_text = "PASS"
                        detail = f"Valeur: '{value}'"
                    else:
                        status_class = "status-fail" if required else "status-not-set"
                        status_text = "FAIL" if required else "NOT SET"
                        detail = "Champ manquant" if required else "Optionnel"
                    
                    field_details += f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #E6E2D5;">
                        <div>
                            <strong>{field_name.replace('_', ' ').title()}</strong>
                            <div style="color: #777777; font-size: 13px;">{detail}</div>
                        </div>
                        <span class="field-status {status_class}">{status_text}</span>
                    </div>
                    """
            
            details_html += f"""
            <div class="category-card" style="margin-bottom: 24px;">
                <div class="category-header">
                    <h3 class="category-title">{product_name}</h3>
                    <div class="category-stats">
                        <span style="color: #0079B2;">Score: {product_analysis['score']}%</span>
                    </div>
                </div>
                <div style="max-height: 300px; overflow-y: auto;">
                    {field_details}
                </div>
            </div>
            """
        
        return f"""
        <div class="category-card">
            <div class="category-header">
                <h2 class="category-title">Détail par Produit ({sample_count}/{total_products})</h2>
            </div>
            <div style="max-height: 600px; overflow-y: auto;">
                {details_html}
            </div>
        </div>
        """

    def _generate_google_ai_hero_html(self, google_ai_analysis):
        """Generate HTML for Google AI Shopping hero section"""
        score = google_ai_analysis["global_score"]
        total_products = google_ai_analysis["total_products"]
        
        if score >= 80:
            score_color = "#43A047"
            score_label = "Excellent pour AI Shopping"
        elif score >= 60:
            score_color = "#0079B2"
            score_label = "Bon pour AI Shopping"
        elif score >= 40:
            score_color = "#FB8C00"
            score_label = "Améliorations nécessaires"
        else:
            score_color = "#E53935"
            score_label = "Optimisation critique requise"
        
        core_missing = len([f for f in google_ai_analysis["field_coverage"] if f["impact"] == "Core" and f["coverage"] < 0.5])
        enriched_missing = len([f for f in google_ai_analysis["field_coverage"] if f["impact"] == "Enriched" and f["coverage"] < 0.5])
        agentic_missing = len([f for f in google_ai_analysis["field_coverage"] if f["impact"] == "Agentic" and f["coverage"] < 0.5])
        
        return f"""
        <div class="product-hero">
            <div class="product-image">
                <div style="width: 120px; height: 120px; background: linear-gradient(135deg, #4285f4, #34a853); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">
                    Google AI
                </div>
            </div>
            <div class="product-info">
                <h2 class="product-name">Google AI Shopping Readiness</h2>
                <p class="product-context">Analysé sur {total_products:,} produits • AI Mode + Gemini + Shopping Graph</p>
            </div>
            <div class="product-scores">
                <div class="main-score">
                    <div class="score-number" style="color: {score_color};">{score}%</div>
                    <div class="score-label">{score_label}</div>
                </div>
                <div class="status-badges">
                    <div class="status-badge badge-error">{core_missing} Core Manquants</div>
                    <div class="status-badge badge-warning">{enriched_missing} Enriched Manquants</div>
                    <div class="status-badge badge-passed">{agentic_missing} Agentic Manquants</div>
                </div>
            </div>
        </div>
        """

    def _generate_google_ai_analysis_html(self, google_ai_analysis):
        """Generate HTML for Google AI analysis section"""
        score = google_ai_analysis["global_score"]
        total_products = google_ai_analysis["total_products"]
        
        top_missing = sorted(google_ai_analysis["field_coverage"], key=lambda x: x["coverage"])[:3]
        
        if score >= 70:
            analysis_text = f"Votre feed présente une excellente compatibilité avec Google AI Shopping."
        elif score >= 50:
            analysis_text = f"Votre feed nécessite des améliorations modérées pour optimiser sa visibilité dans Google AI Shopping."
        else:
            missing_fields = [f["field"] for f in top_missing]
            analysis_text = f"Votre feed présente des lacunes importantes. Champs critiques: {', '.join(missing_fields[:2])}."
        
        recommendations_html = ""
        for field_info in top_missing:
            field = field_info["field"]
            coverage = field_info["coverage"]
            impact = field_info["impact"]
            
            if coverage < 0.5:
                impact_color = "#E53935" if impact == "Core" else "#FB8C00" if impact == "Enriched" else "#777777"
                recommendations_html += f"""
                <div style="padding: 12px; margin: 8px 0; background: #f9f9f9; border-left: 4px solid {impact_color}; border-radius: 4px;">
                    <strong>{field.replace('_', ' ').title()}</strong> ({impact})
                    <div style="color: #666; font-size: 14px;">Couverture: {coverage*100:.1f}%</div>
                </div>
                """
        
        return f"""
        <div class="category-card">
            <div class="category-header">
                <h2 class="category-title">Analyse Google AI Shopping</h2>
                <div class="category-stats">
                    <span>Score global: {score}%</span>
                </div>
            </div>
            <div class="analysis-content">
                <p class="analysis-text">{analysis_text}</p>
                <h3 class="section-title">Priorités d'amélioration</h3>
                {recommendations_html if recommendations_html else '<p style="color: #43A047;">✅ Aucune amélioration critique nécessaire</p>'}
            </div>
        </div>
        """

    def _generate_google_ai_category_section_html(self, google_ai_analysis):
        """Generate HTML for Google AI field coverage by impact"""
        field_coverage = google_ai_analysis["field_coverage"]
        
        by_impact = {"Core": [], "Enriched": [], "Agentic": []}
        for field_info in field_coverage:
            impact = field_info["impact"]
            if impact in by_impact:
                by_impact[impact].append(field_info)
        
        sections_html = ""
        
        for impact, fields in by_impact.items():
            if not fields:
                continue
                
            good = sum(1 for f in fields if f["coverage"] >= 0.8)
            warning = sum(1 for f in fields if 0.5 <= f["coverage"] < 0.8)
            missing = sum(1 for f in fields if f["coverage"] < 0.5)
            
            table_rows = ""
            for field_info in sorted(fields, key=lambda x: x["coverage"]):
                field = field_info["field"]
                coverage = field_info["coverage"]
                
                if coverage >= 0.8:
                    status_class = "status-pass"
                    status_text = "Excellent"
                elif coverage >= 0.5:
                    status_class = "status-warning"
                    status_text = "Partiel"
                else:
                    status_class = "status-fail"
                    status_text = "Manquant"
                
                table_rows += f"""
                <tr>
                    <td class="field-name">{field.replace('_', ' ').title()}</td>
                    <td class="field-message">{coverage*100:.1f}% de couverture</td>
                    <td><span class="field-status {status_class}">{status_text}</span></td>
                </tr>
                """
            
            impact_colors = {
                "Core": "#E53935",
                "Enriched": "#FB8C00", 
                "Agentic": "#0079B2"
            }
            
            sections_html += f"""
            <div class="category-card">
                <div class="category-header">
                    <h2 class="category-title" style="color: {impact_colors.get(impact, '#141414')};">{impact} Fields</h2>
                    <div class="category-stats">
                        <span>Excellent: {good}</span>
                        <span>Partiel: {warning}</span>
                        <span>Manquant: {missing}</span>
                    </div>
                </div>
                <table class="fields-table">
                    <thead>
                        <tr>
                            <th>Field</th>
                            <th>Coverage</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
            """
        
        return sections_html

    def _generate_complete_pdf_report(self, full_analysis, hero_html, ai_html, category_sections):
        """Generate complete PDF report as HTML"""
        current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        all_sections = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #F4F3EC; padding: 20px;">
            <div style="max-width: 1200px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 40px; background: white; padding: 40px; border-radius: 16px;">
                    <h1 style="color: #141414; font-size: 36px; margin: 0 0 16px 0;">AI Shopping Readiness Report</h1>
                    <p style="color: #777777; font-size: 18px;">Généré le {current_date}</p>
                </div>
                
                {hero_html}
                {ai_html}
                {category_sections}
                
                <div style="margin-top: 40px; padding: 20px; background: white; border-radius: 16px; text-align: center; color: #777777;">
                    <p>Rapport généré par AI Shopping Readiness Checker</p>
                </div>
            </div>
        </div>
        """
        
        report_encoded = base64.b64encode(all_sections.encode('utf-8')).decode('utf-8')
        return f"data:text/html;base64,{report_encoded}"

    def _generate_documentation_html(self):
        """Generate documentation HTML"""
        return """
        <div class="category-card" style="margin: 24px;">
            <div class="category-header">
                <h2 class="category-title">📘 Documentation ACP (OpenAI)</h2>
            </div>
            <div style="padding: 20px;">
                <h3 style="color: #0079B2;">Champs Requis pour ACP</h3>
                <ul style="line-height: 1.8;">
                    <li><strong>enable_search</strong>: Permet aux agents IA de rechercher le produit</li>
                    <li><strong>enable_checkout</strong>: Permet aux agents IA d'effectuer l'achat</li>
                    <li><strong>inventory_quantity</strong>: Quantité en stock</li>
                    <li><strong>seller_name, seller_url</strong>: Informations sur le vendeur</li>
                    <li><strong>return_policy, return_window</strong>: Politique de retour</li>
                </ul>
            </div>
        </div>
        <div class="category-card" style="margin: 24px;">
            <div class="category-header">
                <h2 class="category-title">📗 Documentation Google AI Shopping</h2>
            </div>
            <div style="padding: 20px;">
                <h3 style="color: #34a853;">Core Fields (60% du score)</h3>
                <ul style="line-height: 1.8;">
                    <li>title, description, image_link, price, currency</li>
                    <li>availability, brand, link, product_category</li>
                    <li>gtin ou mpn (au moins un requis)</li>
                </ul>
                <h3 style="color: #FB8C00;">Enriched Fields (30% du score)</h3>
                <ul style="line-height: 1.8;">
                    <li>additional_image_link, color, size, gender</li>
                    <li>age_group, material, weight</li>
                </ul>
                <h3 style="color: #0079B2;">Agentic Fields (10% du score)</h3>
                <ul style="line-height: 1.8;">
                    <li>inventory_quantity, item_group_id</li>
                </ul>
            </div>
        </div>
        """

    def analyze_feed(self, xml_content: str) -> Dict:
        """Analyze entire feed for both ACP and Google AI Shopping readiness"""
        products = self.parse_xml_feed(xml_content)
        
        if not products:
            return {
                "global_score": 0,
                "total_products": 0,
                "top_missing_fields": [],
                "by_category": [],
                "sample_products": [],
                "field_analysis": {},
                "acp": {"global_score": 0, "total_products": 0, "top_missing_fields": [], "field_analysis": {}},
                "google_ai": {"global_score": 0, "total_products": 0, "field_coverage": []}
            }
        
        # ACP Analysis
        acp_results = [self.check_acp_compliance(p) for p in products]
        total_products = len(acp_results)
        acp_global_score = sum(r["score"] for r in acp_results) / total_products if total_products > 0 else 0
        
        all_missing_acp = []
        for r in acp_results:
            all_missing_acp.extend(r["missing_required"])
        
        acp_counter = Counter(all_missing_acp)
        top_missing_acp = [
            {"field": field, "coverage": 1 - (count / total_products), "missing_count": count}
            for field, count in acp_counter.most_common()
        ]
        
        # Google AI Analysis
        google_ai_results = [self.check_google_ai_product(p) for p in products]
        google_ai_global_score = sum(r["score_google_ai"] for r in google_ai_results) / total_products if total_products > 0 else 0
        
        # Field coverage analysis for Google AI
        all_core_missing = []
        all_enriched_missing = []
        all_agentic_missing = []
        
        for r in google_ai_results:
            all_core_missing.extend(r["missing_core"])
            all_enriched_missing.extend(r["missing_enriched"])
            all_agentic_missing.extend(r["missing_agentic"])
        
        field_coverage = []
        
        core_counter = Counter(all_core_missing)
        for field, missing_count in core_counter.most_common():
            coverage = 1 - (missing_count / total_products)
            field_coverage.append({
                "field": field,
                "coverage": round(coverage, 3),
                "impact": "Core",
                "missing_count": missing_count
            })
        
        enriched_counter = Counter(all_enriched_missing)
        for field, missing_count in enriched_counter.most_common():
            coverage = 1 - (missing_count / total_products)
            field_coverage.append({
                "field": field,
                "coverage": round(coverage, 3),
                "impact": "Enriched",
                "missing_count": missing_count
            })
        
        agentic_counter = Counter(all_agentic_missing)
        for field, missing_count in agentic_counter.most_common():
            coverage = 1 - (missing_count / total_products)
            field_coverage.append({
                "field": field,
                "coverage": round(coverage, 3),
                "impact": "Agentic",
                "missing_count": missing_count
            })
        
        # Detailed field analysis
        field_analysis = self._analyze_fields_detailed(products)
        
        # Category analysis
        by_category = defaultdict(list)
        for r in acp_results:
            by_category[r["product_category"]].append(r)
        
        category_stats = []
        for category, cat_results in by_category.items():
            if len(cat_results) >= 5:
                avg_score = sum(r["score"] for r in cat_results) / len(cat_results)
                
                cat_missing = []
                for r in cat_results:
                    cat_missing.extend(r["missing_required"])
                
                cat_counter = Counter(cat_missing)
                
                category_stats.append({
                    "category": category,
                    "products": len(cat_results),
                    "avg_score": round(avg_score, 1),
                    "top_missing": [
                        {"field": field, "coverage": 1 - (count / len(cat_results))}
                        for field, count in cat_counter.most_common(3)
                    ]
                })
        
        category_stats.sort(key=lambda x: x["products"], reverse=True)
        
        return {
            "global_score": round(acp_global_score, 1),
            "total_products": total_products,
            "top_missing_fields": top_missing_acp,
            "by_category": category_stats[:10],
            "sample_products": acp_results[:20],
            "field_analysis": field_analysis,
            "acp": {
                "global_score": round(acp_global_score, 1),
                "total_products": total_products,
                "top_missing_fields": top_missing_acp,
                "field_analysis": field_analysis
            },
            "google_ai": {
                "global_score": round(google_ai_global_score, 1),
                "total_products": total_products,
                "field_coverage": sorted(field_coverage, key=lambda x: x["coverage"]),
                "by_category": category_stats[:10],
                "sample_products": google_ai_results[:20]
            }
        }

def create_interface():
    checker = CommerceReadinessChecker()
    
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    body {
        background-color: #F4F3EC !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .gradio-container {
        max-width: none !important;
        margin: 0 !important;
        padding: 0 !important;
        background-color: #F4F3EC !important;
    }
    
    .app-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 64px;
        background: white;
        border-bottom: 1px solid #E6E2D5;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        display: flex;
        align-items: center;
        padding: 0 24px;
    }
    
    .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .app-title {
        font-size: 18px;
        font-weight: 600;
        color: #141414;
        margin: 0;
    }
    
    .main-container {
        margin-top: 64px;
        max-width: 1200px;
        margin-left: auto;
        margin-right: auto;
        padding: 24px;
    }
    
    .hero-section {
        text-align: center;
        padding: 80px 24px;
        background: white;
        border-radius: 16px;
        margin-bottom: 32px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .hero-title {
        font-size: 48px;
        font-weight: 700;
        color: #141414;
        margin: 0 0 16px 0;
        line-height: 1.2;
    }
    
    .hero-subtitle {
        font-size: 20px;
        color: #777777;
        margin: 0 0 48px 0;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .product-hero {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 24px;
    }
    
    .product-image {
        width: 120px;
        height: 120px;
        border-radius: 8px;
        object-fit: cover;
        background: #f3f4f6;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #9ca3af;
        font-size: 14px;
    }
    
    .product-info {
        flex: 1;
    }
    
    .product-name {
        font-size: 20px;
        font-weight: 600;
        color: #111827;
        margin: 0 0 8px 0;
    }
    
    .product-context {
        font-size: 14px;
        color: #6b7280;
        margin: 0;
    }
    
    .product-scores {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 16px;
    }
    
    .main-score {
        text-align: center;
    }
    
    .score-number {
        font-size: 32px;
        font-weight: 700;
        color: #0079B2;
        margin: 0;
    }
    
    .score-label {
        font-size: 13px;
        color: #6b7280;
        margin: 4px 0 0 0;
    }
    
    .status-badges {
        display: flex;
        gap: 12px;
    }
    
    .status-badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .badge-error {
        background: #E53935;
        color: white;
        border: none;
    }
    
    .badge-warning {
        background: #FB8C00;
        color: white;
        border: none;
    }
    
    .badge-passed {
        background: #43A047;
        color: white;
        border: none;
    }
    
    .ai-analysis {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 24px;
    }
    
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #141414;
        margin: 0 0 16px 0;
    }
    
    .analysis-text {
        font-size: 15px;
        line-height: 1.6;
        color: #777777;
        margin: 0;
    }
    
    .category-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        margin-bottom: 24px;
    }
    
    .category-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    
    .category-title {
        font-size: 18px;
        font-weight: 600;
        color: #141414;
        margin: 0;
    }
    
    .category-stats {
        display: flex;
        gap: 16px;
        font-size: 13px;
        color: #777777;
    }
    
    .fields-table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .fields-table th {
        text-align: left;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 600;
        color: #777777;
        border-bottom: 1px solid #E6E2D5;
        background: #f9fafb;
    }
    
    .fields-table td {
        padding: 16px;
        border-bottom: 1px solid #E6E2D5;
        font-size: 14px;
    }
    
    .field-name {
        font-weight: 500;
        color: #141414;
    }
    
    .field-message {
        color: #777777;
    }
    
    .field-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
    }
    
    .status-pass {
        background: #43A047;
        color: white;
        border: none;
    }
    
    .status-fail {
        background: #E53935;
        color: white;
        border: none;
    }
    
    .status-warning {
        background: #FB8C00;
        color: white;
        border: none;
    }
    
    .status-not-set {
        background: #f9fafb;
        color: #B0B0B0;
        border: 1px solid #E6E2D5;
    }
    
    .doc-btn {
        background: none !important;
        border: none !important;
        color: #0079B2 !important;
        cursor: pointer !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        transition: background-color 0.2s !important;
    }
    
    .doc-btn:hover {
        background: #f0f9ff !important;
    }
    
    .doc-modal {
        display: none;
        position: fixed;
        z-index: 10000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        justify-content: center;
        align-items: center;
        padding: 20px;
        box-sizing: border-box;
    }
    
    .doc-modal-content {
        background: white;
        border-radius: 12px;
        width: 90%;
        max-width: 1000px;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    .doc-modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 24px;
        border-bottom: 1px solid #E6E2D5;
        background: #F4F3EC;
        border-radius: 12px 12px 0 0;
    }
    
    .doc-modal-header h2 {
        margin: 0;
        color: #141414;
        font-size: 24px;
        font-weight: 600;
    }
    
    .doc-close {
        background: none;
        border: none;
        font-size: 28px;
        cursor: pointer;
        color: #777777;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        transition: background-color 0.2s;
    }
    
    .doc-close:hover {
        background: #E6E2D5;
        color: #141414;
    }
    
    .doc-modal-body {
        padding: 0;
        overflow-y: auto;
        flex: 1;
        border-radius: 0 0 12px 12px;
    }
    
    .run-analysis-btn {
        background: #0079B2;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .run-analysis-btn:hover {
        background: #006699;
    }
    """
    
    with gr.Blocks(title="AI Shopping Readiness Checker", css=custom_css) as interface:
        gr.HTML("""
        <div class="app-header">
            <div class="header-left">
                <h1 class="app-title">AI Commerce Readiness Checker</h1>
            </div>
            <div class="header-right">
                <button onclick="toggleDocumentation()" class="doc-btn">📚 Documentation</button>
            </div>
        </div>
        
        <div id="doc-modal" class="doc-modal" style="display: none;">
            <div class="doc-modal-content">
                <div class="doc-modal-header">
                    <h2>📚 Documentation Complète</h2>
                    <button onclick="toggleDocumentation()" class="doc-close">&times;</button>
                </div>
                <div class="doc-modal-body">
                    """ + checker._generate_documentation_html() + """
                </div>
            </div>
        </div>
        
        <script>
        function toggleDocumentation() {
            const modal = document.getElementById('doc-modal');
            if (modal.style.display === 'none' || modal.style.display === '') {
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            } else {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('doc-modal');
            if (event.target === modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }
        </script>
        """)
        
        with gr.Column(elem_classes=["main-container"]):
            with gr.Column(visible=True) as hero_section:
                gr.HTML("""
                <div class="hero-section">
                    <h1 class="hero-title">AI Shopping Readiness Checker</h1>
                    <p class="hero-subtitle">Analysez votre feed Google Merchant Center pour optimiser votre visibilité dans l'AI Shopping</p>
                </div>
                """)
                
                with gr.Row():
                    with gr.Column(scale=4):
                        file_input = gr.File(
                            label="📁 Sélectionnez votre fichier XML",
                            file_types=[".xml"],
                            type="binary"
                        )
                    with gr.Column(scale=1):
                        analyze_btn = gr.Button(
                            "🚀 Analyser le Feed",
                            variant="primary",
                            elem_classes=["run-analysis-btn"]
                        )
            
            loading_section = gr.HTML(visible=False)
            nav_section = gr.HTML(visible=False)
            results_container = gr.Column(visible=False)
            
            with results_container:
                with gr.Tabs():
                    with gr.TabItem("📊 Résumé Global"):
                        global_summary = gr.HTML()
                        priorities_section = gr.HTML()
                    
                    with gr.TabItem("🔵 ACP (OpenAI)"):
                        acp_hero = gr.HTML()
                        acp_ai_analysis = gr.HTML()
                        acp_seo_section = gr.HTML()
                        acp_openai_section = gr.HTML()
                        acp_basic_data_section = gr.HTML()
                        acp_product_content_section = gr.HTML()
                        acp_merchant_info_section = gr.HTML()
                    
                    with gr.TabItem("🟢 Google AI Shopping"):
                        google_hero = gr.HTML()
                        google_ai_analysis = gr.HTML()
                        google_sections = gr.HTML()
                    
                    with gr.TabItem("🔍 Détail par Produit"):
                        product_details_section = gr.HTML()
                    
                    with gr.TabItem("📄 Export JSON"):
                        json_export = gr.File(label="Télécharger le rapport JSON complet")
                        json_content = gr.JSON(label="Aperçu des données")
        
        def analyze_feed_new(file):
            if file is None:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False),
                    "", "", "", "", "", "", "", "", "", "", "", "", "", "", None, {}
                )
            
            loading_html = """
            <div style="text-align: center; padding: 60px; background: white; border-radius: 16px; margin: 32px 0;">
                <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                <h2 style="color: #141414; margin-bottom: 8px;">Analyse en cours...</h2>
                <p style="color: #777777;">Traitement de votre feed produit, veuillez patienter</p>
            </div>
            """
            
            yield (
                gr.update(visible=False),
                gr.update(visible=True, value=loading_html),
                gr.update(visible=False, value=""),
                gr.update(visible=False),
                "", "", "", "", "", "", "", "", "", "", "", "", "", "", None, {}
            )
            
            try:
                xml_content = file.decode('utf-8') if isinstance(file, bytes) else file
                
                full_analysis = checker.analyze_feed(xml_content)
                if full_analysis["total_products"] == 0:
                    raise ValueError("Aucun produit trouvé dans le feed")
                
                first_product = {
                    "product_brand": "Feed Analysis",
                    "product_category": "Multiple Categories"
                }
                
                full_analysis["xml_content"] = xml_content
                
                acp_analysis = full_analysis["acp"]
                google_ai_analysis = full_analysis["google_ai"]
                
                global_summary_html = f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px;">
                    <div class="category-card">
                        <div class="category-header">
                            <h2 class="category-title" style="color: #0079B2;">🔵 ACP Readiness (OpenAI)</h2>
                        </div>
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; font-weight: bold; color: #0079B2; margin-bottom: 8px;">{acp_analysis['global_score']}%</div>
                            <div style="color: #141414; font-weight: 500; font-size: 16px;">Score global sur {full_analysis['total_products']} produits</div>
                        </div>
                    </div>
                    <div class="category-card">
                        <div class="category-header">
                            <h2 class="category-title" style="color: #34a853;">🟢 Google AI Shopping</h2>
                        </div>
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; font-weight: bold; color: #34a853; margin-bottom: 8px;">{google_ai_analysis['global_score']}%</div>
                            <div style="color: #141414; font-weight: 500; font-size: 16px;">Score global sur {full_analysis['total_products']} produits</div>
                        </div>
                    </div>
                </div>
                """
                
                priorities_html = f"""
                <div class="category-card">
                    <div class="category-header">
                        <h2 class="category-title">🎯 Top 5 Priorités d'Implémentation</h2>
                    </div>
                    <div style="padding: 20px;">
                        <div style="margin-bottom: 16px; padding: 16px; background: #fef2f2; border-left: 4px solid #E53935; border-radius: 4px;">
                            <div style="color: #141414; font-weight: 600; font-size: 16px;">P1 - Champs ACP Critiques</div>
                            <div style="color: #666666; font-size: 13px;">Ajouter enable_search, enable_checkout, inventory_quantity • Score ACP: {acp_analysis['global_score']}%</div>
                        </div>
                        <div style="margin-bottom: 16px; padding: 16px; background: #fffbeb; border-left: 4px solid #FB8C00; border-radius: 4px;">
                            <div style="color: #141414; font-weight: 600; font-size: 16px;">P2 - Enrichissement Google AI</div>
                            <div style="color: #666666; font-size: 13px;">Compléter color, size, material • Score Google AI: {google_ai_analysis['global_score']}%</div>
                        </div>
                    </div>
                </div>
                """
                
                acp_hero_html = checker._generate_feed_hero_html(first_product, acp_analysis)
                acp_ai_html = checker._generate_feed_ai_analysis_html(acp_analysis)
                acp_seo_html = checker._generate_feed_category_section_html("SEO & Page Optimization", acp_analysis)
                acp_openai_html = checker._generate_feed_category_section_html("OpenAI Flags", acp_analysis)
                acp_basic_html = checker._generate_feed_category_section_html("Basic Product Data", acp_analysis)
                acp_content_html = checker._generate_feed_category_section_html("Product Content", acp_analysis)
                acp_merchant_html = checker._generate_feed_category_section_html("Merchant Info", acp_analysis)
                
                google_hero_html = checker._generate_google_ai_hero_html(google_ai_analysis)
                google_ai_html = checker._generate_google_ai_analysis_html(google_ai_analysis)
                google_sections_html = checker._generate_google_ai_category_section_html(google_ai_analysis)
                
                product_details_html = checker._generate_product_details_html(full_analysis)
                
                json_data = {
                    "total_products": full_analysis["total_products"],
                    "acp": acp_analysis,
                    "google_ai": google_ai_analysis,
                    "generated_at": datetime.now().isoformat()
                }
                
                json_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(json_data, json_file, indent=2, ensure_ascii=False)
                json_file.close()
                
                yield (
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=True, value=""),
                    gr.update(visible=True),
                    global_summary_html,
                    priorities_html,
                    acp_hero_html,
                    acp_ai_html,
                    acp_seo_html,
                    acp_openai_html,
                    acp_basic_html,
                    acp_content_html,
                    acp_merchant_html,
                    google_hero_html,
                    google_ai_html,
                    google_sections_html,
                    product_details_html,
                    json_file.name,
                    json_data
                )
                
            except Exception as e:
                error_html = f"""
                <div class="category-card">
                    <div style="color: #E53935; font-weight: 600;">Erreur d'analyse</div>
                    <p style="color: #777777; margin-top: 8px;">{str(e)}</p>
                </div>
                """
                yield (
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False, value=""),
                    gr.update(visible=True),
                    error_html, "", "", "", "", "", "", "", "", "", "", "", "", None, {}
                )
        
        analyze_btn.click(
            analyze_feed_new,
            inputs=[file_input],
            outputs=[hero_section, loading_section, nav_section, results_container, global_summary, priorities_section, acp_hero, acp_ai_analysis, acp_seo_section, acp_openai_section, acp_basic_data_section, acp_product_content_section, acp_merchant_info_section, google_hero, google_ai_analysis, google_sections, product_details_section, json_export, json_content]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch()
