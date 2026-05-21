import streamlit as st


def render():
    """Render Step 4: Checkout Readiness Checklist (educational, no code)"""

    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <h2 style="font-size: 1.5rem; font-weight: 600; color: #111827; margin: 0 0 8px 0;">Checkout Readiness</h2>
        <p style="font-size: 14px; color: #6b7280; margin: 0;">Cadrage de ce qu'il faudra mettre en place pour ACP Checkout.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Section 1: PSP & Payments
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Payment Service Provider</p>', unsafe_allow_html=True)

    psp = st.selectbox(
        "Quel PSP utilisez-vous actuellement ?",
        ["Sélectionnez...", "Stripe", "Adyen", "Checkout.com", "Mollie", "PayPal", "Autre"],
        key="checklist_psp"
    )

    if psp == "Stripe":
        st.success("✅ **Stripe** est le premier PSP compatible ACP via les *Shared Payment Tokens*.")
        st.markdown("[→ Documentation Stripe Agentic Commerce](https://docs.stripe.com/agentic-commerce)")
    elif psp == "Adyen":
        st.info("🔵 **Adyen** a endorsé UCP (Google). Compatibilité ACP à confirmer.")
    elif psp == "Checkout.com":
        st.success("✅ **Checkout.com** supporte ACP (tokenisation déléguée) et UCP (Google Pay).")
    elif psp in ["Mollie", "PayPal", "Autre"]:
        st.warning(f"⚠️ **{psp}** : compatibilité ACP non confirmée pour l'instant. Contactez votre PSP.")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Section 2: API Readiness
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">API & Endpoints</p>', unsafe_allow_html=True)

    st.markdown("""
    ACP Checkout requiert **5 endpoints REST** que votre backend doit exposer :
    """)

    endpoints = [
        ("POST /checkout_sessions", "Créer une session de checkout", "checklist_ep1"),
        ("GET /checkout_sessions/{id}", "Récupérer l'état d'une session", "checklist_ep2"),
        ("POST /checkout_sessions/{id}", "Mettre à jour (items, address, fulfillment)", "checklist_ep3"),
        ("POST /checkout_sessions/{id}/complete", "Finaliser le paiement", "checklist_ep4"),
        ("POST /checkout_sessions/{id}/cancel", "Annuler la session", "checklist_ep5"),
    ]

    api_ready_count = 0
    for endpoint, desc, key in endpoints:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"`{endpoint}` — {desc}")
        with col2:
            if st.checkbox("Prêt", key=key):
                api_ready_count += 1

    st.progress(api_ready_count / len(endpoints),
                text=f"Endpoints prêts : {api_ready_count}/{len(endpoints)}")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Section 3: Capabilities
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Capabilities & Négociation</p>', unsafe_allow_html=True)

    st.markdown("""
    À chaque réponse checkout, le seller doit déclarer ses *capabilities* :
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("Payment handlers déclarés (ex: tokenized card)", key="cap_payment")
        st.checkbox("Interventions supportées (3DS, biometric, etc.)", key="cap_interventions")
    with col2:
        st.checkbox("Extensions activées (discounts, loyalty, etc.)", key="cap_extensions")
        st.checkbox("Fulfillment options configurées", key="cap_fulfillment")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Section 4: Order Management
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Order Management</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("Calcul de taxes dynamique", key="om_taxes")
        st.checkbox("Calcul de frais de port", key="om_shipping")
        st.checkbox("Gestion d'inventaire temps réel", key="om_inventory")
    with col2:
        st.checkbox("Webhook pour statut de commande", key="om_webhooks")
        st.checkbox("Gestion des retours", key="om_returns")
        st.checkbox("Support multi-devises", key="om_currencies")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Section 5: Security
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Sécurité</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.checkbox("Auth Bearer Token sur tous les endpoints", key="sec_auth")
        st.checkbox("HTTPS obligatoire", key="sec_https")
    with col2:
        st.checkbox("PCI DSS compliance (via PSP)", key="sec_pci")
        st.checkbox("Rate limiting", key="sec_rate")

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)

    # Summary
    st.markdown('<p style="font-size:14px;font-weight:600;color:#111827;">Résumé</p>', unsafe_allow_html=True)

    all_checks = [
        st.session_state.get(f"checklist_ep{i}", False) for i in range(1, 6)
    ] + [
        st.session_state.get("cap_payment", False),
        st.session_state.get("cap_interventions", False),
        st.session_state.get("cap_extensions", False),
        st.session_state.get("cap_fulfillment", False),
        st.session_state.get("om_taxes", False),
        st.session_state.get("om_shipping", False),
        st.session_state.get("om_inventory", False),
        st.session_state.get("om_webhooks", False),
        st.session_state.get("sec_auth", False),
        st.session_state.get("sec_https", False),
        st.session_state.get("sec_pci", False),
    ]

    total_checked = sum(all_checks)
    total_items = len(all_checks)
    checkout_score = round(total_checked / total_items * 100) if total_items > 0 else 0

    score_color = "#166534" if checkout_score >= 80 else "#92400e" if checkout_score >= 40 else "#6b7280"
    message = "Prêt pour un PoC ACP Checkout." if checkout_score >= 80 else "Quelques éléments à mettre en place." if checkout_score >= 40 else "Cadrage en cours."
    st.markdown(f"""
    <div style="padding:16px 20px;background:#fafafa;border-radius:8px;border:1px solid #f0f0f0;">
        <div style="display:flex;align-items:baseline;gap:12px;">
            <span style="font-size:2rem;font-weight:700;color:{score_color};">{checkout_score}%</span>
            <span style="font-size:14px;color:#6b7280;">{message}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid #f0f0f0;margin:1.5rem 0;">', unsafe_allow_html=True)
    st.markdown("""
    <p style="font-size:12px;color:#9ca3af;line-height:1.8;">
        <a href="https://www.agenticcommerce.dev/docs" style="color:#6b7280;text-decoration:none;">ACP Documentation →</a><br>
        <a href="https://www.agenticcommerce.dev/docs/reference/checkout" style="color:#6b7280;text-decoration:none;">Checkout API Reference →</a><br>
        <a href="https://docs.stripe.com/agentic-commerce" style="color:#6b7280;text-decoration:none;">Stripe Agentic Commerce →</a>
    </p>
    """, unsafe_allow_html=True)
