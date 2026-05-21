import streamlit as st
import json
from core.mapper import FieldMapper
from core.generator import ACPFeedGenerator
from core.analyzer import MigrationAnalyzer
from core.models import ACPProduct


def render():
    """Render Step 3: ACP JSON Output + Action Plan"""

    st.markdown("### 📄 Étape 3 — JSON ACP généré + Plan d'action")

    if not st.session_state.get("step_2_complete"):
        st.warning("⚠️ Veuillez d'abord configurer le mapping dans l'étape 2.")
        return

    parse_result = st.session_state.get("parse_result")
    mapper = st.session_state.get("mapper")

    if not parse_result or not mapper:
        st.warning("⚠️ Données manquantes.")
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
        with st.expander(f"⚠️ {len(errors)} erreurs de conversion"):
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

    # Display results in two columns
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### 📋 ACP Feed JSON")

        # Show sample
        sample_json = generator.generate_sample(acp_products, n=3)
        st.code(sample_json, language="json")

        # Download buttons
        st.download_button(
            "⬇️ Télécharger le Feed ACP complet (JSON)",
            data=feed_json,
            file_name="acp_feed.json",
            mime="application/json",
            use_container_width=True
        )

        st.metric("Taille du fichier", f"{len(feed_json) / 1024:.1f} KB")

    with col2:
        st.markdown("#### 📊 Statistiques")

        st.metric("Produits convertis", f"{stats['total_products']:,}")
        st.metric("Variantes générées", f"{stats['total_variants']:,}")

        st.markdown("**Complétude Product :**")
        st.progress(stats["completeness"]["product_recommended"],
                    text=f"Recommandés: {stats['completeness']['product_recommended']*100:.0f}%")

        st.markdown("**Complétude Variant :**")
        st.progress(min(stats["completeness"]["variant_required"], 1.0),
                    text=f"Requis: {stats['completeness']['variant_required']*100:.0f}%")
        st.progress(min(stats["completeness"]["variant_recommended"], 1.0),
                    text=f"Recommandés: {stats['completeness']['variant_recommended']*100:.0f}%")

    # Migration Analysis & Action Plan
    st.markdown("---")
    st.markdown("#### 🎯 Plan d'action Migration")

    analyzer = MigrationAnalyzer()
    report = analyzer.analyze(acp_products)
    summary = analyzer.get_readiness_summary(report)

    st.session_state["migration_report"] = report

    # Readiness score
    score = summary["score"]
    if score >= 80:
        st.success(f"🎉 **Score de readiness : {score}%** — {summary['message']}")
    elif score >= 50:
        st.warning(f"⚠️ **Score de readiness : {score}%** — {summary['message']}")
    else:
        st.error(f"❌ **Score de readiness : {score}%** — {summary['message']}")

    # Action items
    if report.action_plan:
        p1_actions = [a for a in report.action_plan if a.priority == "P1"]
        p2_actions = [a for a in report.action_plan if a.priority == "P2"]
        p3_actions = [a for a in report.action_plan if a.priority == "P3"]

        if p1_actions:
            st.markdown("##### 🔴 P1 — Indispensable pour PoC ACP")
            for action in p1_actions:
                st.markdown(f"""
                <div style="padding: 12px; margin: 8px 0; background: #fef2f2; border-left: 4px solid #dc2626; border-radius: 4px;">
                    <strong>{action.field}</strong> — {action.action}
                    <div style="color: #666; font-size: 13px; margin-top: 4px;">{action.description}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 2px;">Effort: {action.effort} • Impact: {action.impact}</div>
                </div>
                """, unsafe_allow_html=True)

        if p2_actions:
            st.markdown("##### 🟡 P2 — Améliore la discovery")
            for action in p2_actions:
                st.markdown(f"""
                <div style="padding: 12px; margin: 8px 0; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 4px;">
                    <strong>{action.field}</strong> — {action.action}
                    <div style="color: #666; font-size: 13px; margin-top: 4px;">{action.description}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 2px;">Effort: {action.effort} • Impact: {action.impact}</div>
                </div>
                """, unsafe_allow_html=True)

        if p3_actions:
            st.markdown("##### 🔵 P3 — Nice to have")
            for action in p3_actions:
                st.markdown(f"""
                <div style="padding: 12px; margin: 8px 0; background: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 4px;">
                    <strong>{action.field}</strong> — {action.action}
                    <div style="color: #666; font-size: 13px; margin-top: 4px;">{action.description}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 2px;">Effort: {action.effort} • Impact: {action.impact}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("🎉 Aucune action requise — votre feed est complet !")

    st.session_state["step_3_complete"] = True
