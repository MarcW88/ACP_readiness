import streamlit as st

st.set_page_config(
    page_title="ACP Migration Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean & Minimal CSS — Stripe/Notion inspired
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .block-container {
        padding: 3rem 2rem 2rem 2rem;
        max-width: 1100px;
    }

    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #e5e7eb;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        font-size: 14px;
        font-weight: 500;
        color: #6b7280;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        padding: 0 20px;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #111827 !important;
        border-bottom: 2px solid #111827 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #111827;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #fafafa;
        padding: 1.25rem;
        border-radius: 8px;
        border: 1px solid #f0f0f0;
    }
    [data-testid="stMetricLabel"] {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #6b7280;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 600;
        color: #111827;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        font-size: 14px;
        padding: 0.5rem 1.25rem;
        border: 1px solid #e5e7eb;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #111827;
        color: #111827;
    }
    .stButton > button[kind="primary"] {
        background: #111827;
        color: white;
        border-color: #111827;
    }
    .stButton > button[kind="primary"]:hover {
        background: #374151;
    }

    /* Download button */
    .stDownloadButton > button {
        background: #111827;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 500;
    }
    .stDownloadButton > button:hover {
        background: #374151;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-size: 14px;
        font-weight: 500;
        color: #374151;
    }

    /* Select boxes */
    .stSelectbox > div > div {
        font-size: 13px;
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #111827;
    }

    /* Alerts */
    .stAlert {
        border-radius: 6px;
        font-size: 14px;
    }

    /* Code blocks */
    .stCodeBlock {
        border-radius: 8px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #fafafa;
        border-right: 1px solid #f0f0f0;
    }
    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1.5rem;
    }

    /* Custom classes */
    .step-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.5rem;
    }
    .step-description {
        font-size: 14px;
        color: #6b7280;
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #f0f0f0;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 2rem;">
        <div style="font-size: 18px; font-weight: 600; color: #111827; margin-bottom: 4px;">ACP Migration Assistant</div>
        <div style="font-size: 13px; color: #6b7280;">Feed → ACP Feed API 2026-04-17</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    steps = [
        ("1", "Upload & Détection", "step_1_complete"),
        ("2", "Mapping des champs", "step_2_complete"),
        ("3", "JSON ACP + Plan", "step_3_complete"),
        ("4", "Checklist Checkout", None),
    ]
    for num, label, key in steps:
        done = st.session_state.get(key, False) if key else False
        if done:
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:8px 0;"><div style="width:24px;height:24px;border-radius:50%;background:#111827;color:white;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;">{num}</div><span style="font-size:14px;color:#111827;font-weight:500;">{label}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:8px 0;"><div style="width:24px;height:24px;border-radius:50%;background:white;border:1.5px solid #d1d5db;color:#9ca3af;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:500;">{num}</div><span style="font-size:14px;color:#6b7280;">{label}</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div style="font-size: 12px; color: #9ca3af; line-height: 1.8;">
        <div style="font-weight: 600; color: #6b7280; margin-bottom: 4px;">ACP Feed API</div>
        <div><strong>Product</strong> — id, title</div>
        <div><strong>Variant</strong> — id, price, availability</div>
        <br>
        <a href="https://www.agenticcommerce.dev/docs" style="color: #6b7280; text-decoration: none;">Documentation →</a><br>
        <a href="https://github.com/agentic-commerce-protocol/agentic-commerce-protocol" style="color: #6b7280; text-decoration: none;">GitHub →</a>
    </div>
    """, unsafe_allow_html=True)

# Main content with tabs
from ui import step_upload, step_mapping, step_output, step_checklist

tab1, tab2, tab3, tab4 = st.tabs([
    "Upload",
    "Mapping",
    "JSON ACP + Plan",
    "Checkout Readiness"
])

with tab1:
    step_upload.render()

with tab2:
    step_mapping.render()

with tab3:
    step_output.render()

with tab4:
    step_checklist.render()
