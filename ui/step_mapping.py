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

    st.markdown("### 🔗 Étape 2 — Mapping vers ACP Feed API")

    if not st.session_state.get("step_1_complete"):
        st.warning("⚠️ Veuillez d'abord uploader un fichier dans l'étape 1.")
        return

    parse_result = st.session_state.get("parse_result")
    if not parse_result:
        st.warning("⚠️ Pas de données à mapper.")
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

    st.markdown("""
    Configurez le mapping entre vos champs source et les champs ACP Feed API.  
    Le mapping par défaut est pré-rempli en fonction du format détecté.
    """)

    # Group rules by product/variant
    product_rules = [r for r in mapper.rules if r.acp_field.startswith("product.")]
    variant_rules = [r for r in mapper.rules if r.acp_field.startswith("variant.")]

    updated_rules = []

    # Product fields section
    st.markdown("#### 📦 Product Fields")
    for rule in product_rules:
        updated_rule = _render_mapping_row(rule, source_fields, parse_result, parser, is_required=rule.acp_field in ["product.id", "product.title"])
        updated_rules.append(updated_rule)

    st.markdown("---")

    # Variant fields section
    st.markdown("#### 🏷️ Variant Fields")
    for rule in variant_rules:
        is_req = rule.acp_field in ["variant.id", "variant.price", "variant.availability"]
        updated_rule = _render_mapping_row(rule, source_fields, parse_result, parser, is_required=is_req)
        updated_rules.append(updated_rule)

    # Update mapper with any changes
    mapper.rules = updated_rules
    st.session_state["mapper"] = mapper

    # Summary
    st.markdown("---")
    mapped = [r for r in updated_rules if r.source_field and r.transform != "none"]
    unmapped = [r for r in updated_rules if not r.source_field or r.transform == "none"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Champs mappés", f"{len(mapped)} / {len(updated_rules)}")
    with col2:
        if unmapped:
            unmapped_names = [r.acp_field for r in unmapped]
            st.warning(f"Non mappés : {', '.join(unmapped_names)}")
        else:
            st.success("Tous les champs sont mappés !")

    st.session_state["step_2_complete"] = True
    st.success("✅ Mapping configuré. Passez à l'étape suivante pour générer le JSON ACP.")


def _render_mapping_row(rule, source_fields, parse_result, parser, is_required=False):
    """Render a single mapping row with source selector and transform"""
    field_label = rule.acp_field.replace("product.", "").replace("variant.", "")
    badge = "🔴 Required" if is_required else "🔵 Recommended"

    with st.container():
        cols = st.columns([2, 2, 2, 1])

        with cols[0]:
            st.markdown(f"**{rule.acp_field}** <small>{badge}</small>", unsafe_allow_html=True)

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
