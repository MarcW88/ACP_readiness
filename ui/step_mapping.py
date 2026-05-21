import streamlit as st
from core.mapper import FieldMapper, FIELD_ALIASES
from core.parser import FeedParser


TRANSFORMS = ["direct", "to_array", "split", "prefix", "map_values", "to_seller", "to_options", "constant", "template", "format_price", "none"]

TRANSFORM_LABELS = {
    "direct": "Direct (copie la valeur)",
    "to_array": "Vers Array (valeur → [valeur])",
    "split": "Split (sépare par délimiteur)",
    "prefix": "Préfixe (ajoute un préfixe)",
    "map_values": "Mapping de valeurs",
    "to_seller": "Vers Seller ({name, url})",
    "to_options": "Vers Options (combine color/size/etc.)",
    "constant": "Valeur constante",
    "template": "Template (format personnalisé)",
    "format_price": "Format prix (montant + devise)",
    "none": "Non mappé",
}


def render():
    """Render Step 2: Field Mapping"""

    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h2 style="font-size: 1.5rem; font-weight: 600; color: #111827; margin: 0 0 8px 0;">Mapping</h2>
        <p style="font-size: 14px; color: #6b7280; margin: 0;">Configurez la correspondance entre vos champs source et ACP Feed API.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("step_1_complete"):
        st.markdown('<div style="padding:2rem;text-align:center;color:#9ca3af;font-size:14px;">Uploadez d\'abord un fichier dans l\'onglet Upload.</div>', unsafe_allow_html=True)
        return

    parse_result = st.session_state.get("parse_result")
    if not parse_result:
        st.markdown('<div style="padding:2rem;text-align:center;color:#9ca3af;font-size:14px;">Pas de données à mapper.</div>', unsafe_allow_html=True)
        return

    # Determine preset based on format
    format_to_preset = {
        "gmc_xml": "gmc_to_acp",
        "shopify_json": "shopify_to_acp",
        "acp_json": "gmc_to_acp",
        "csv": "gmc_to_acp",
    }

    preset = format_to_preset.get(parse_result.format, "gmc_to_acp")

    # Initialize mapper
    if "mapper" not in st.session_state or st.session_state.get("mapper_preset") != preset:
        mapper = FieldMapper(preset)
        # Auto-map based on available fields
        available = list(parse_result.available_fields.keys())
        mapper.auto_map(available)
        st.session_state["mapper"] = mapper
        st.session_state["mapper_preset"] = preset

    mapper = st.session_state["mapper"]
    source_fields = ["(non mappé)"] + sorted(parse_result.available_fields.keys())
    parser = FeedParser()

    # Group rules by product/variant
    product_rules = [r for r in mapper.rules if r.acp_field.startswith("product.")]
    variant_rules = [r for r in mapper.rules if r.acp_field.startswith("variant.")]

    updated_rules = []

    # Product fields section
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;margin:1.5rem 0 0.75rem 0;">Product</p>', unsafe_allow_html=True)
    for rule in product_rules:
        updated_rule = _render_mapping_row(rule, source_fields, parse_result, parser, is_required=rule.acp_field in ["product.id", "product.title"])
        updated_rules.append(updated_rule)

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Variant fields section
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;margin:0 0 0.75rem 0;">Variant</p>', unsafe_allow_html=True)
    for rule in variant_rules:
        is_req = rule.acp_field in ["variant.id", "variant.price", "variant.availability"]
        updated_rule = _render_mapping_row(rule, source_fields, parse_result, parser, is_required=is_req)
        updated_rules.append(updated_rule)

    # Update mapper with any changes
    mapper.rules = updated_rules
    st.session_state["mapper"] = mapper

    # Summary
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)
    mapped = [r for r in updated_rules if r.source_field and r.transform != "none"]
    unmapped = [r for r in updated_rules if not r.source_field or r.transform == "none"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Mappés", f"{len(mapped)} / {len(updated_rules)}")
    with col2:
        st.metric("Non mappés", f"{len(unmapped)}")

    if unmapped:
        unmapped_names = [r.acp_field for r in unmapped]
        st.markdown(f'<div style="font-size:13px;color:#9ca3af;margin-top:8px;">Non mappés : {', '.join(unmapped_names)}</div>', unsafe_allow_html=True)

    st.session_state["step_2_complete"] = True
    st.markdown('<div style="margin-top:1.5rem;padding:12px 16px;background:#f9fafb;border-radius:6px;border:1px solid #f0f0f0;font-size:14px;color:#374151;">Mapping configuré. Passez à l\'onglet <strong>JSON ACP + Plan</strong>.</div>', unsafe_allow_html=True)


def _render_mapping_row(rule, source_fields, parse_result, parser, is_required=False):
    """Render a single mapping row with source selector and transform"""
    field_label = rule.acp_field.replace("product.", "").replace("variant.", "")
    if is_required:
        badge_html = '<span style="font-size:10px;padding:1px 6px;background:#fef2f2;color:#991b1b;border-radius:3px;margin-left:6px;">required</span>'
    else:
        badge_html = '<span style="font-size:10px;padding:1px 6px;background:#eff6ff;color:#1e40af;border-radius:3px;margin-left:6px;">recommended</span>'

    with st.container():
        cols = st.columns([2, 2, 2, 1])

        with cols[0]:
            st.markdown(f'<span style="font-size:13px;font-weight:500;color:#111827;">{rule.acp_field}</span>{badge_html}', unsafe_allow_html=True)

        with cols[1]:
            current_source = rule.source_field if rule.source_field else "(non mappé)"
            idx = source_fields.index(current_source) if current_source in source_fields else 0
            selected_source = st.selectbox(
                f"Source → {rule.acp_field}",
                source_fields,
                index=idx,
                key=f"src_{rule.acp_field}",
                label_visibility="collapsed"
            )

        with cols[2]:
            current_transform = rule.transform if rule.transform else "direct"
            t_idx = TRANSFORMS.index(current_transform) if current_transform in TRANSFORMS else 0
            selected_transform = st.selectbox(
                f"Transform → {rule.acp_field}",
                TRANSFORMS,
                index=t_idx,
                format_func=lambda x: TRANSFORM_LABELS.get(x, x),
                key=f"tf_{rule.acp_field}",
                label_visibility="collapsed"
            )

        with cols[3]:
            # Show coverage indicator
            if selected_source != "(non mappé)":
                coverage = parse_result.available_fields.get(selected_source, 0)
                if coverage >= 0.95:
                    st.markdown("✅")
                elif coverage >= 0.5:
                    st.markdown("⚠️")
                else:
                    st.markdown("❌")
            else:
                st.markdown("—")

    # Build updated rule
    new_source = selected_source if selected_source != "(non mappé)" else None
    new_transform = selected_transform if new_source else "none"

    from core.models import MappingRule
    return MappingRule(
        acp_field=rule.acp_field,
        source_field=new_source,
        transform=new_transform,
        params=rule.params
    )
