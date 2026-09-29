"""
pages/4_Runs.py
Execution History — Track, compare, and audit past generation runs.
"""
import pathlib
import sys

import streamlit as st

from engine.ui_styles import inject_css, sidebar_nav

st.set_page_config(
    page_title="Execution History · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Execution History & Audit Log")
st.markdown("Audit past generation runs, verify dataset hash reproducibility via SHA-256 signatures, and track quality score trends.")
st.divider()

from engine.evaluate.runs import get_runs_df, load_runs

runs_df = get_runs_df()

if runs_df.empty:
    st.info("No execution runs recorded yet. Generate a dataset to record historical runs here.")
    st.stop()

st.metric("Total Executed Runs Recorded", len(runs_df))

# ── Run Summary Table ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Execution Run Registry</div>", unsafe_allow_html=True)
display_cols = [c for c in runs_df.columns if not c.startswith("score_")]
st.dataframe(runs_df[display_cols], use_container_width=True, height=300)

st.download_button(
    "Download Run History CSV",
    data=runs_df[display_cols].to_csv(index=False).encode("utf-8-sig"),
    file_name="run_history.csv",
    mime="text/csv",
)

st.divider()

# ── Reproducibility ───────────────────────────────────────────────────────────
st.markdown("### Reproducibility & SHA-256 Hash Verification")
st.caption("Deterministic RNG check: Same random seed + plan specification guarantees an identical SHA-256 dataset hash.")

if len(runs_df) >= 2:
    rc1, rc2 = st.columns(2)
    with rc1:
        run_a = st.selectbox("Select Run A", runs_df["run_id"].tolist(), key="run_a")
    with rc2:
        run_b = st.selectbox("Select Run B", runs_df["run_id"].tolist(), index=1, key="run_b")

    hash_a = runs_df[runs_df["run_id"] == run_a]["dataset_hash"].iloc[0]
    hash_b = runs_df[runs_df["run_id"] == run_b]["dataset_hash"].iloc[0]

    if hash_a == hash_b:
        st.success(f"Hashes Match: {hash_a[:48]}...")
    else:
        st.info("Hashes differ (Runs executed with different seeds or plan configurations)")
        st.code(f"Run A Hash: {hash_a}\nRun B Hash: {hash_b}")
else:
    st.info("Generate at least 2 runs to compare reproducibility signatures.")

st.divider()

# ── Score Trends ──────────────────────────────────────────────────────────────
score_cols = [c for c in runs_df.columns if c.startswith("score_")]
if score_cols:
    import plotly.express as px

    st.markdown("### Historical Metric Trends")
    for col in score_cols[:4]:
        if runs_df[col].notna().any():
            fig = px.line(
                runs_df.reset_index(),
                x="created_at",
                y=col,
                markers=True,
                template="plotly_dark",
                title=col.replace("score_", "").replace("_", " ").title(),
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
                height=250,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ── Run Detail ────────────────────────────────────────────────────────────────
st.markdown("### Run JSON Details")
selected_run = st.selectbox("Select Run ID to Inspect", runs_df["run_id"].tolist(), key="detail_run")
runs_raw = load_runs()
run_detail = next((r for r in runs_raw if r["run_id"] == selected_run), None)
if run_detail:
    with st.expander(f"Inspect Full JSON Record for {selected_run}", expanded=True):
        st.json(run_detail)
