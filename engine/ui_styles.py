"""
engine/ui_styles.py
Enterprise SaaS styling and unified sidebar component for CyberSynthetic UI.
Deployment-ready clean dark theme with custom SVG brand assets and zero emojis.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* Hide default auto-generated Streamlit page navigation to prevent duplicates */
[data-testid="stSidebarNav"] {
    display: none !important;
}

/* ── App Background ── */
.stApp {
    background-color: #0b0f19 !important;
}

.main .block-container {
    background-color: #0b0f19;
    color: #f3f4f6;
    padding: 2rem 2.5rem 3.5rem;
    max-width: 1280px;
}

/* ── Sidebar Styling ── */
section[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: 1px solid #1f2937 !important;
}

section[data-testid="stSidebar"] * {
    color: #9ca3af !important;
}

section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] strong {
    color: #f9fafb !important;
}

section[data-testid="stSidebar"] .stPageLink a {
    color: #9ca3af !important;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    display: block;
    transition: all 0.15s ease-in-out;
}

section[data-testid="stSidebar"] .stPageLink a:hover {
    background: #1f2937;
    color: #3b82f6 !important;
}

/* Active sidebar page highlight */
section[data-testid="stSidebar"] .stPageLink a[aria-current="page"] {
    background: rgba(37, 99, 235, 0.12);
    color: #60a5fa !important;
    font-weight: 600;
    border-left: 3px solid #2563eb;
}

/* ── Buttons ── */
.stButton > button {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid #3b82f6 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.15s ease-in-out !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
}

.stButton > button:hover {
    background: #1d4ed8 !important;
    border-color: #60a5fa !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
}

.stDownloadButton > button {
    background: #1f2937 !important;
    border: 1px solid #374151 !important;
    color: #60a5fa !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.825rem !important;
    padding: 0.45rem 1rem !important;
    transition: all 0.15s ease-in-out !important;
}

.stDownloadButton > button:hover {
    background: #2563eb !important;
    border-color: #3b82f6 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
}

/* ── Metric Cards ── */
[data-testid="stMetric"] {
    background-color: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
}

[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

[data-testid="stMetricValue"] {
    color: #f9fafb !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}

/* ── Input Controls ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select, div[data-baseweb="select"] {
    background-color: #111827 !important;
    border: 1px solid #374151 !important;
    border-radius: 6px !important;
    color: #f9fafb !important;
    font-size: 0.875rem !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25) !important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #9ca3af !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.5rem 0.9rem !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom-color: #2563eb !important;
}

/* ── DataFrames ── */
.stDataFrame {
    border-radius: 8px !important;
    border: 1px solid #1f2937 !important;
    overflow: hidden !important;
    background-color: #111827 !important;
}

/* ── Custom Cards & Badges ── */
.card-panel {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}

.section-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.5rem;
}

.tag {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.tag-blue   { background: rgba(37, 99, 235, 0.15); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.3); }
.tag-green  { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.tag-amber  { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.tag-red    { background: rgba(239, 68, 68, 0.15);  color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.tag-purple { background: rgba(139, 92, 246, 0.15); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.3); }

/* ── Divider ── */
hr {
    border-color: #1f2937 !important;
    margin: 1.25rem 0 !important;
}

/* ── Alert boxes ── */
.stAlert {
    border-radius: 6px !important;
    background-color: #111827 !important;
    border: 1px solid #1f2937 !important;
}

</style>
"""


def inject_css():
    """Inject corporate dark theme CSS into the Streamlit session."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_nav():
    """Render a clean, professional sidebar navigation with SVG brand logo."""
    with st.sidebar:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:0.75rem; padding: 0.25rem 0 0.5rem;">
                <svg width="30" height="30" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="32" height="32" rx="7" fill="#2563EB"/>
                    <path d="M16 6L24 10.5V19.5L16 24L8 19.5V10.5L16 6Z" stroke="#FFFFFF" stroke-width="2" stroke-linejoin="round"/>
                    <circle cx="16" cy="15" r="3" fill="#FFFFFF"/>
                </svg>
                <div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #F9FAFB; letter-spacing: -0.02em; line-height:1.1;">CyberSynthetic</div>
                    <div style="font-size: 0.68rem; font-weight: 600; color: #6B7280; letter-spacing: 0.05em; text-transform:uppercase;">Enterprise Data Platform</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown(
            "<div style='font-size:0.7rem; font-weight:700; color:#6b7280; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;'>Platform Navigation</div>",
            unsafe_allow_html=True,
        )

        st.page_link("app.py", label="Home")
        st.page_link("pages/1_Create.py", label="Generate Data")
        st.page_link("pages/2_Data.py", label="Data Explorer")
        st.page_link("pages/3_Quality.py", label="Quality Scorecard")
        st.page_link("pages/4_Runs.py", label="Execution History")
        st.page_link("pages/5_Ask.py", label="Analytics & Profiling")
        st.page_link("pages/6_Lineage.py", label="Incident Lineage")

        st.divider()
        st.markdown(
            """
            <div style="font-size: 0.72rem; color: #6b7280; line-height: 1.4;">
                RFC-Compliant Synthetic Engine<br>
                Zero Real Credentials / Keys<br>
                Bilingual English &amp; Urdu
            </div>
            """,
            unsafe_allow_html=True,
        )
