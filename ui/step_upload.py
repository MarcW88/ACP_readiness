import streamlit as st
from core.parser import FeedParser


def render():
    """Render Step 1: Upload & Detection"""

    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h2 style="font-size: 1.5rem; font-weight: 600; color: #111827; margin: 0 0 8px 0;">Upload & Détection</h2>
        <p style="font-size: 14px; color: #6b7280; margin: 0; line-height: 1.6;">
            Uploadez votre feed produit. Le format sera détecté automatiquement et converti en JSON structuré pour agents IA.
        </p>
    </div>
    """, unsafe_allow_html=True)

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
                st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Produits", f"{result.total_products:,}")
                with col2:
                    format_labels = {
                        "gmc_xml": "GMC XML",
                        "shopify_json": "Shopify JSON",
                        "acp_json": "ACP JSON",
                        "csv": "CSV/TSV",
                    }
                    st.metric("Format", format_labels.get(result.format, "Inconnu"))
                with col3:
                    st.metric("Champs", f"{len(result.available_fields)}")

                # Show field coverage summary
                st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)
                st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;margin-bottom:12px;">Couverture des champs</p>', unsafe_allow_html=True)

                high_coverage = {k: v for k, v in result.available_fields.items() if v >= 0.8}
                medium_coverage = {k: v for k, v in result.available_fields.items() if 0.3 <= v < 0.8}
                low_coverage = {k: v for k, v in result.available_fields.items() if v < 0.3 and v > 0}

                if high_coverage:
                    fields_html = " ".join([f'<span style="display:inline-block;padding:2px 8px;background:#f0fdf4;color:#166534;border-radius:4px;font-size:12px;margin:2px;">{k}</span>' for k in high_coverage.keys()])
                    st.markdown(f'<div style="margin-bottom:8px;"><span style="font-size:12px;color:#6b7280;margin-right:8px;">Complets</span>{fields_html}</div>', unsafe_allow_html=True)
                if medium_coverage:
                    fields_html = " ".join([f'<span style="display:inline-block;padding:2px 8px;background:#fffbeb;color:#92400e;border-radius:4px;font-size:12px;margin:2px;">{k}</span>' for k in medium_coverage.keys()])
                    st.markdown(f'<div style="margin-bottom:8px;"><span style="font-size:12px;color:#6b7280;margin-right:8px;">Partiels</span>{fields_html}</div>', unsafe_allow_html=True)
                if low_coverage:
                    fields_html = " ".join([f'<span style="display:inline-block;padding:2px 8px;background:#fef2f2;color:#991b1b;border-radius:4px;font-size:12px;margin:2px;">{k}</span>' for k in low_coverage.keys()])
                    st.markdown(f'<div style="margin-bottom:8px;"><span style="font-size:12px;color:#6b7280;margin-right:8px;">Faibles</span>{fields_html}</div>', unsafe_allow_html=True)

                # Show samples
                with st.expander("Aperçu des données (3 premiers produits)"):
                    for i, prod in enumerate(result.products[:3]):
                        st.json(prod)

                st.markdown('<div style="margin-top:1.5rem;padding:12px 16px;background:#f9fafb;border-radius:6px;border:1px solid #f0f0f0;font-size:14px;color:#374151;">Feed analysé. Passez à l\'onglet <strong>Mapping</strong> pour configurer la conversion.</div>', unsafe_allow_html=True)

                # Enable next step
                st.session_state["step_1_complete"] = True

            except Exception as e:
                st.error(f"❌ Erreur lors du parsing : {str(e)}")
                st.session_state["step_1_complete"] = False
    else:
        st.markdown("""
        <div style="padding: 2rem; text-align: center; color: #9ca3af; font-size: 14px;">
            Formats supportés : XML (GMC), JSON (Shopify, ACP), CSV/TSV
        </div>
        """, unsafe_allow_html=True)
        st.session_state["step_1_complete"] = False
