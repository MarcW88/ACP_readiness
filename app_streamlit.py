import streamlit as st
import xml.etree.ElementTree as ET
import json
import re
from collections import defaultdict, Counter
from typing import Dict, List
import base64
from datetime import datetime

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
                if product:
                    products.append(product)
                
            return products
        except Exception as e:
            raise ValueError(f"Erreur parsing XML: {str(e)}")

    def _extract_product_data(self, item) -> Dict:
        """Extract and normalize product data from XML item"""
        def get_text(tag):
            ns = "http://base.google.com/ns/1.0"
            elem = item.find(f'.//{{{ns}}}{tag}')
            if elem is not None:
                return elem.text
            elem = item.find(f'.//{tag}')
            return elem.text if elem is not None else None

        def get_direct_text(tag):
            elem = item.find(f'./{tag}')
            return elem.text if elem is not None else None

        price_str = get_text('price') or ""
        price_match = re.match(r'([\d.,]+)\s*(\w+)', price_str)
        price = float(price_match.group(1).replace(',', '.')) if price_match else None
        currency = price_match.group(2) if price_match else None

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
            return f"{product_name} présente une excellente compatibilité avec l'AI Shopping."
        elif score >= 50:
            return f"{product_name} nécessite des améliorations modérées pour optimiser sa compatibilité AI Shopping."
        else:
            critical_missing = [e["field"] for e in errors[:3]]
            return f"{product_name} présente des lacunes importantes. Champs critiques: {', '.join(critical_missing)}."

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
        
        google_ai_results = [self.check_google_ai_product(p) for p in products]
        google_ai_global_score = sum(r["score_google_ai"] for r in google_ai_results) / total_products if total_products > 0 else 0
        
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
        
        field_analysis = self._analyze_fields_detailed(products)
        
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

# Streamlit UI
st.set_page_config(
    page_title="AI Commerce Readiness Checker",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0079B2, #00A3E0);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .score-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🛒 AI Commerce Readiness Checker</h1>
    <p>Analysez votre feed Google Merchant Center pour optimiser votre visibilité dans l'AI Shopping</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📚 Documentation")
    
    with st.expander("ACP (OpenAI) - Champs Requis"):
        st.markdown("""
        - **enable_search**: Permet aux agents IA de rechercher le produit
        - **enable_checkout**: Permet aux agents IA d'effectuer l'achat
        - **inventory_quantity**: Quantité en stock
        - **seller_name, seller_url**: Informations sur le vendeur
        - **return_policy, return_window**: Politique de retour
        """)
    
    with st.expander("Google AI Shopping - Core Fields (60%)"):
        st.markdown("""
        - title, description, image_link, price, currency
        - availability, brand, link, product_category
        - gtin ou mpn (au moins un requis)
        """)
    
    with st.expander("Google AI Shopping - Enriched (30%)"):
        st.markdown("""
        - additional_image_link, color, size, gender
        - age_group, material, weight
        """)
    
    with st.expander("Google AI Shopping - Agentic (10%)"):
        st.markdown("""
        - inventory_quantity, item_group_id
        """)

# File upload
uploaded_file = st.file_uploader(
    "📁 Sélectionnez votre fichier XML",
    type=['xml'],
    help="Upload votre feed Google Merchant Center au format XML"
)

if uploaded_file is not None:
    with st.spinner("⏳ Analyse en cours..."):
        try:
            xml_content = uploaded_file.read().decode('utf-8')
            checker = CommerceReadinessChecker()
            full_analysis = checker.analyze_feed(xml_content)
            
            if full_analysis["total_products"] == 0:
                st.error("❌ Aucun produit trouvé dans le feed")
            else:
                acp_analysis = full_analysis["acp"]
                google_ai_analysis = full_analysis["google_ai"]
                
                # Summary Section
                st.header("📊 Résumé Global")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div class="score-card">
                        <h3 style="color: #0079B2;">🔵 ACP Readiness (OpenAI)</h3>
                        <div class="metric-value" style="color: #0079B2;">{:.1f}%</div>
                        <p>Score global sur {:,} produits</p>
                        <p style="font-size: 14px; color: #666;">Prêt pour agents ChatGPT</p>
                    </div>
                    """.format(acp_analysis['global_score'], full_analysis['total_products']), unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div class="score-card">
                        <h3 style="color: #34a853;">🟢 Google AI Shopping</h3>
                        <div class="metric-value" style="color: #34a853;">{:.1f}%</div>
                        <p>Score global sur {:,} produits</p>
                        <p style="font-size: 14px; color: #666;">AI Mode + Gemini + Shopping Graph</p>
                    </div>
                    """.format(google_ai_analysis['global_score'], full_analysis['total_products']), unsafe_allow_html=True)
                
                # Priorities
                st.header("🎯 Top Priorités d'Implémentation")
                
                st.info("""
                **P1 - Champs ACP Critiques** (🔵 OpenAI ACP)
                - Ajouter enable_search, enable_checkout, inventory_quantity
                - Score actuel ACP: {:.1f}%
                
                **P2 - Enrichissement Google AI** (🟢 Google AI)
                - Compléter color, size, material
                - Score actuel Google AI: {:.1f}%
                """.format(acp_analysis['global_score'], google_ai_analysis['global_score']))
                
                # Tabs
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "🔵 ACP (OpenAI)", 
                    "🟢 Google AI Shopping", 
                    "📋 Analyse par Champ", 
                    "🔍 Détail par Produit", 
                    "📄 Export JSON"
                ])
                
                with tab1:
                    st.subheader("ACP (OpenAI) - Analyse Détaillée")
                    
                    for category_name, fields in acp_analysis["field_analysis"].items():
                        with st.expander(f"📁 {category_name}"):
                            field_data = []
                            for field in fields:
                                status_color = {
                                    "pass": "🟢",
                                    "warning": "🟡",
                                    "fail": "🔴",
                                    "not_set": "⚪"
                                }.get(field["status_class"], "⚪")
                                
                                field_data.append({
                                    "Champ": field["field"],
                                    "Statut": f"{status_color} {field['status']}",
                                    "Couverture": f"{field['coverage']}%",
                                    "Produits": f"{field['count']:,}/{full_analysis['total_products']:,}",
                                    "Description": field["description"]
                                })
                            
                            st.dataframe(
                                pd.DataFrame(field_data) if 'pd' in locals() else field_data,
                                use_container_width=True,
                                hide_index=True
                            )
                
                with tab2:
                    st.subheader("Google AI Shopping - Analyse Détaillée")
                    
                    # Group by impact
                    by_impact = {"Core": [], "Enriched": [], "Agentic": []}
                    for field_info in google_ai_analysis["field_coverage"]:
                        impact = field_info["impact"]
                        if impact in by_impact:
                            by_impact[impact].append(field_info)
                    
                    for impact, fields in by_impact.items():
                        if not fields:
                            continue
                        
                        impact_colors = {
                            "Core": "#E53935",
                            "Enriched": "#FB8C00",
                            "Agentic": "#0079B2"
                        }
                        
                        st.markdown(f"""
                        <h4 style="color: {impact_colors.get(impact, '#141414')};">{impact} Fields</h4>
                        """, unsafe_allow_html=True)
                        
                        field_data = []
                        for field_info in sorted(fields, key=lambda x: x["coverage"]):
                            coverage_pct = field_info["coverage"] * 100
                            if coverage_pct >= 80:
                                status = "✅ Excellent"
                            elif coverage_pct >= 50:
                                status = "⚠️ Partiel"
                            else:
                                status = "❌ Manquant"
                            
                            field_data.append({
                                "Champ": field_info["field"].replace("_", " ").title(),
                                "Couverture": f"{coverage_pct:.1f}%",
                                "Statut": status,
                                "Impact": field_info["impact"]
                            })
                        
                        st.dataframe(field_data, use_container_width=True, hide_index=True)
                
                with tab3:
                    st.subheader("Analyse Détaillée par Champ")
                    
                    for category_name, fields in full_analysis["field_analysis"].items():
                        with st.expander(f"📁 {category_name}"):
                            for field in fields:
                                if field["status_class"] in ["fail", "warning"]:
                                    st.error(f"❌ **{field['field']}**: {field['description']} ({field['coverage']}% couverture)")
                                elif field["status_class"] == "pass":
                                    st.success(f"✅ **{field['field']}**: Conforme ({field['coverage']}% couverture)")
                                else:
                                    st.info(f"⚪ **{field['field']}**: Non renseigné ({field['coverage']}% couverture)")
                
                with tab4:
                    st.subheader("Détail par Produit")
                    
                    products = checker.parse_xml_feed(xml_content)
                    sample_count = min(len(products), 10)
                    sample_products = products[:sample_count]
                    
                    st.info(f"Analyse de {sample_count} produits sur {full_analysis['total_products']} total")
                    
                    for i, product in enumerate(sample_products):
                        with st.expander(f"Produit {i+1}: {product.get('title', 'Sans titre')[:50]}"):
                            product_analysis = checker._analyze_single_product(product)
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric("Score", f"{product_analysis['score']}%")
                            
                            with col2:
                                st.write(f"**ID:** {product.get('id', 'N/A')}")
                                st.write(f"**Catégorie:** {product.get('product_category', 'N/A')}")
                            
                            st.write("**Champs manquants (Errors):**")
                            for error in product_analysis["errors"]:
                                st.error(f"• {error['field']}: {error['message']}")
                            
                            st.write("**Avertissements (Warnings):**")
                            for warning in product_analysis["warnings"]:
                                st.warning(f"• {warning['field']}: {warning['message']}")
                
                with tab5:
                    st.subheader("Export JSON")
                    
                    json_data = {
                        "total_products": full_analysis["total_products"],
                        "acp": acp_analysis,
                        "google_ai": google_ai_analysis,
                        "generated_at": datetime.now().isoformat()
                    }
                    
                    st.json(json_data)
                    
                    st.download_button(
                        label="📥 Télécharger le rapport JSON",
                        data=json.dumps(json_data, indent=2, ensure_ascii=False),
                        file_name=f"acp_readiness_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
            st.exception(e)
else:
    st.info("👆 Veuillez uploader un fichier XML pour commencer l'analyse")
