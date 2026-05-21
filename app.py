import streamlit as st

st.set_page_config(
    page_title="ACP Migration Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        font-size: 15px;
        font-weight: 500;
        padding: 0 24px;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0079B2 !important;
        color: white !important;
    }
    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }
    .stMetric {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    ## 🚀 ACP Migration Assistant
    
    Transformez votre feed produit en **ACP Feed API 2026-04-17**.
    
    ---
    """)

    st.markdown("### 📋 Étapes")
    steps = [
        ("1️⃣", "Upload & Détection", "step_1_complete"),
        ("2️⃣", "Mapping des champs", "step_2_complete"),
        ("3️⃣", "JSON ACP + Plan", "step_3_complete"),
        ("4️⃣", "Checklist Checkout", None),
    ]
    for icon, label, key in steps:
        done = st.session_state.get(key, False) if key else False
        status = "✅" if done else "⬜"
        st.markdown(f"{status} {icon} {label}")

    st.markdown("---")

    st.markdown("""
    ### 📚 ACP Feed API
    
    **Requis Product** : `id`, `title`  
    **Recommandés** : `description`, `url`, `media`
    
    **Requis Variant** : `id`, `price`, `availability`  
    **Recommandés** : `title`, `categories`, `seller`, `variant_options`
    
    ---
    
    [📖 Docs ACP](https://www.agenticcommerce.dev/docs)  
    [🐙 GitHub ACP](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol)
    """)

# Main content with tabs
from ui import step_upload, step_mapping, step_output, step_checklist

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Upload",
    "2️⃣ Mapping",
    "3️⃣ JSON ACP + Plan",
    "4️⃣ Checkout Readiness"
])

with tab1:
    step_upload.render()

with tab2:
    step_mapping.render()

with tab3:
    step_output.render()

with tab4:
    step_checklist.render()
