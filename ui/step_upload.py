import streamlit as st
from core.parser import FeedParser


def render():
    """Render Step 1: Upload & Detection"""

    st.markdown("""
    <div style="background: linear-gradient(135deg, #0079B2, #00A3E0); padding: 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; font-size: 2rem;">🚀 ACP Migration Assistant</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;">
            Transformez votre feed actuel en ACP Feed API 2026-04-17
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📁 Étape 1 — Upload & Détection")
    st.markdown("""
    Uploadez votre feed produit actuel. Les formats supportés :
    - **XML** — Google Merchant Center
    - **JSON** — Shopify, ACP Feed API existant
    - **CSV/TSV** — Export tabulaire
    """)

    uploaded_file = st.file_uploader(
        "Sélectionnez votre fichier feed",
        type=["xml", "json", "csv", "tsv"],
        help="Formats supportés : Google Merchant Center XML, Shopify JSON, CSV/TSV"
    )

    if uploaded_file is not None:
        with st.spinner("Analyse du fichier..."):
            try:
                content = uploaded_file.read().decode("utf-8")
                parser = FeedParser()
                result = parser.parse(content)

                if result.total_products == 0:
                    st.error("❌ Aucun produit trouvé dans le fichier. Vérifiez le format.")
                    return

                # Store in session
                st.session_state["parse_result"] = result
                st.session_state["raw_content"] = content
                st.session_state["file_name"] = uploaded_file.name

                # Display detection results
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Produits détectés", f"{result.total_products:,}")
                with col2:
                    format_labels = {
                        "gmc_xml": "Google Merchant Center (XML)",
                        "shopify_json": "Shopify (JSON)",
                        "acp_json": "ACP Feed API (JSON)",
                        "csv": "CSV/TSV",
                    }
                    st.metric("Format détecté", format_labels.get(result.format, "Inconnu"))
                with col3:
                    st.metric("Champs disponibles", f"{len(result.available_fields)}")

                # Show field coverage summary
                st.markdown("#### 📊 Champs détectés dans votre feed")

                high_coverage = {k: v for k, v in result.available_fields.items() if v >= 0.8}
                medium_coverage = {k: v for k, v in result.available_fields.items() if 0.3 <= v < 0.8}
                low_coverage = {k: v for k, v in result.available_fields.items() if v < 0.3 and v > 0}

                if high_coverage:
                    st.success(f"**Bien remplis (>80%)** : {', '.join(high_coverage.keys())}")
                if medium_coverage:
                    st.warning(f"**Partiels (30-80%)** : {', '.join(medium_coverage.keys())}")
                if low_coverage:
                    st.error(f"**Faibles (<30%)** : {', '.join(low_coverage.keys())}")

                # Show samples
                with st.expander("👀 Aperçu des données (3 premiers produits)"):
                    for i, prod in enumerate(result.products[:3]):
                        st.json(prod)

                st.success("✅ Feed analysé avec succès. Passez à l'étape suivante pour configurer le mapping.")

                # Enable next step
                st.session_state["step_1_complete"] = True

            except Exception as e:
                st.error(f"❌ Erreur lors du parsing : {str(e)}")
                st.session_state["step_1_complete"] = False
    else:
        st.info("💡 Uploadez un fichier pour commencer la migration vers ACP Feed API.")
        st.session_state["step_1_complete"] = False
