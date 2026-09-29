"""
app.py — CyberSynthetic Platform Entry Point
Enterprise Synthetic Data Platform for HackDataV2.
"""
import streamlit as st
from dotenv import load_dotenv
from engine.ui_styles import inject_css, sidebar_nav

load_dotenv()

st.set_page_config(
    page_title="CyberSynthetic Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
sidebar_nav()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="tag tag-blue">HackDataV2 · Synthetic Data Engine</div>',
    unsafe_allow_html=True,
)
st.title("CyberSynthetic Platform")
st.markdown(
    "Generate high-fidelity, RFC-compliant synthetic cybersecurity datasets using Natural Language prompts "
    "or by fitting statistical models on uploaded CSV files. Support for tabular, relational SQLite, and PDF document outputs."
)

st.divider()

# ── Metrics KPI Summary ───────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(label="Data Domains", value="7 Schemas", delta="Auth, Endpoint, Alerts...")
with c2:
    st.metric(label="Output Modes", value="3 Formats", delta="CSV, SQLite, PDF Report")
with c3:
    st.metric(label="Input Options", value="2 Modes", delta="Prompt or CSV Upload")
with c4:
    st.metric(label="Supported Languages", value="EN / UR", delta="Bilingual Support")

st.markdown("<br>", unsafe_allow_html=True)

# ── Feature Overview Cards ───────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown('<span class="tag tag-blue">Input Flexibility</span>', unsafe_allow_html=True)
        st.markdown("#### Prompt &amp; Upload Modes")
        st.write(
            "Describe complex security scenarios in natural language (English or Urdu) or upload real CSV datasets to auto-infer schemas and sample statistics."
        )

with col2:
    with st.container(border=True):
        st.markdown('<span class="tag tag-green">Output Formats</span>', unsafe_allow_html=True)
        st.markdown("#### Multi-Modal Synthesis")
        st.write(
            "Export single-table CSVs, multi-table SQLite databases with foreign key integrity, and bilingual PDF incident reports."
        )

with col3:
    with st.container(border=True):
        st.markdown('<span class="tag tag-purple">Analytics &amp; Profiling</span>', unsafe_allow_html=True)
        st.markdown("#### Deep Data Profiling")
        st.write(
            "Execute natural language SQL queries, run Python analytics, and generate full Sweetviz statistical profile reports with one click."
        )

st.markdown("<br>", unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)

with col4:
    with st.container(border=True):
        st.markdown('<span class="tag tag-amber">Quality Evaluation</span>', unsafe_allow_html=True)
        st.markdown("#### Fidelity &amp; Utility Scoring")
        st.write(
            "Evaluate KS complement, Total Variation distance, correlation similarity, TSTR/TRTS F1, AUROC scores, and privacy Distance-to-Closest-Record."
        )

with col5:
    with st.container(border=True):
        st.markdown('<span class="tag tag-blue">Reproducibility</span>', unsafe_allow_html=True)
        st.markdown("#### Seeded Generation Tree")
        st.write(
            "Deterministic generation trees using NumPy SeedSequence. Same seed + plan guarantees exact dataset SHA-256 hashes."
        )

with col6:
    with st.container(border=True):
        st.markdown('<span class="tag tag-red">Privacy &amp; Safety</span>', unsafe_allow_html=True)
        st.markdown("#### RFC-Safe Security Data")
        st.write(
            "All generated IP addresses use reserved IANA ranges (10.0.0.0/8, 192.168.0.0/16, 203.0.113.0/24). Zero real credentials."
        )

st.divider()

# ── Navigation Shortcuts ─────────────────────────────────────────────────────
st.markdown("### Platform Modules")
qa1, qa2, qa3, qa4 = st.columns(4)

with qa1:
    if st.button("Generate Dataset", use_container_width=True):
        st.switch_page("pages/1_Create.py")
with qa2:
    if st.button("Explore Active Data", use_container_width=True):
        st.switch_page("pages/2_Data.py")
with qa3:
    if st.button("View Quality Scorecard", use_container_width=True):
        st.switch_page("pages/3_Quality.py")
with qa4:
    if st.button("Query &amp; Profile Data", use_container_width=True):
        st.switch_page("pages/5_Ask.py")
