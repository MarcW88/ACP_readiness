import streamlit as st
import json
from core.mapper import FieldMapper
from core.generator import ACPFeedGenerator
from core.analyzer import MigrationAnalyzer
from core.models import ACPProduct


def render():
    """Render Step 3: ACP JSON Output + Action Plan"""

    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h2 style="font-size: 1.5rem; font-weight: 600; color: #111827; margin: 0 0 8px 0;">JSON ACP + Plan d'action</h2>
        <p style="font-size: 14px; color: #6b7280; margin: 0;">Votre feed converti et les prochaines actions de migration.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("step_2_complete"):
        st.markdown('<div style="padding:2rem;text-align:center;color:#9ca3af;font-size:14px;">Configurez d\'abord le mapping dans l\'onglet Mapping.</div>', unsafe_allow_html=True)
        return

    parse_result = st.session_state.get("parse_result")
    mapper = st.session_state.get("mapper")

    if not parse_result or not mapper:
        st.markdown('<div style="padding:2rem;text-align:center;color:#9ca3af;font-size:14px;">Données manquantes.</div>', unsafe_allow_html=True)
        return

    # Apply mapping to all products
    with st.spinner("Conversion en cours..."):
        acp_products = []
        errors = []
        for i, product in enumerate(parse_result.products):
            try:
                acp_product = mapper.apply_mapping(product)
                acp_products.append(acp_product)
            except Exception as e:
                errors.append(f"Produit {i+1}: {str(e)}")

        st.session_state["acp_products"] = acp_products

    if errors:
        with st.expander(f"{len(errors)} erreurs de conversion"):
            for err in errors[:10]:
                st.text(err)

    # Generate feed
    generator = ACPFeedGenerator()
    feed = generator.generate(acp_products, metadata={
        "feed_id": f"feed_{st.session_state.get('file_name', 'export')}",
        "target_country": "FR"
    })
    feed_json = generator.to_json(feed)
    stats = generator.get_stats(acp_products)

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Produits", f"{stats['total_products']:,}")
    with col2:
        st.metric("Variantes", f"{stats['total_variants']:,}")
    with col3:
        st.metric("Taille", f"{len(feed_json) / 1024:.1f} KB")
    with col4:
        req_pct = stats["completeness"]["variant_required"] * 100
        st.metric("Requis", f"{req_pct:.0f}%")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # JSON output + download
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;margin-bottom:12px;">Feed ACP JSON</p>', unsafe_allow_html=True)

    sample_json = generator.generate_sample(acp_products, n=3)
    st.code(sample_json, language="json")

    st.download_button(
        "Télécharger le Feed ACP complet",
        data=feed_json,
        file_name="acp_feed.json",
        mime="application/json",
        use_container_width=True
    )

    # Migration Analysis & Action Plan
    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;margin-bottom:12px;">Plan d\'action</p>', unsafe_allow_html=True)

    analyzer = MigrationAnalyzer()
    report = analyzer.analyze(acp_products)
    summary = analyzer.get_readiness_summary(report)

    st.session_state["migration_report"] = report

    # Readiness score
    score = summary["score"]
    score_color = "#166534" if score >= 80 else "#92400e" if score >= 50 else "#991b1b"
    st.markdown(f"""
    <div style="padding:16px 20px;background:#fafafa;border-radius:8px;border:1px solid #f0f0f0;margin-bottom:1.5rem;">
        <div style="display:flex;align-items:baseline;gap:12px;">
            <span style="font-size:2rem;font-weight:700;color:{score_color};">{score}%</span>
            <span style="font-size:14px;color:#6b7280;">{summary['message']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Action items
    if report.action_plan:
        p1_actions = [a for a in report.action_plan if a.priority == "P1"]
        p2_actions = [a for a in report.action_plan if a.priority == "P2"]
        p3_actions = [a for a in report.action_plan if a.priority == "P3"]

        if p1_actions:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#991b1b;margin:1rem 0 0.5rem 0;">P1 — Indispensable</p>', unsafe_allow_html=True)
            for action in p1_actions:
                st.markdown(f"""
                <div style="padding:10px 14px;margin:6px 0;background:white;border:1px solid #fecaca;border-radius:6px;">
                    <div style="font-size:13px;font-weight:500;color:#111827;">{action.field}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:2px;">{action.description}</div>
                </div>
                """, unsafe_allow_html=True)

        if p2_actions:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#92400e;margin:1rem 0 0.5rem 0;">P2 — Discovery</p>', unsafe_allow_html=True)
            for action in p2_actions:
                st.markdown(f"""
                <div style="padding:10px 14px;margin:6px 0;background:white;border:1px solid #fde68a;border-radius:6px;">
                    <div style="font-size:13px;font-weight:500;color:#111827;">{action.field}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:2px;">{action.description}</div>
                </div>
                """, unsafe_allow_html=True)

        if p3_actions:
            st.markdown('<p style="font-size:13px;font-weight:600;color:#1e40af;margin:1rem 0 0.5rem 0;">P3 — Nice to have</p>', unsafe_allow_html=True)
            for action in p3_actions:
                st.markdown(f"""
                <div style="padding:10px 14px;margin:6px 0;background:white;border:1px solid #bfdbfe;border-radius:6px;">
                    <div style="font-size:13px;font-weight:500;color:#111827;">{action.field}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:2px;">{action.description}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:16px;background:#f0fdf4;border-radius:6px;font-size:14px;color:#166534;">Feed complet — aucune action requise.</div>', unsafe_allow_html=True)

    st.session_state["step_3_complete"] = True
