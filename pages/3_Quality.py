"""
pages/3_Quality.py
Quality Scorecard — Fidelity, utility (TSTR/TRTS/TRTR), privacy, and integrity.
"""
import pathlib
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine.ui_styles import inject_css, sidebar_nav

st.set_page_config(
    page_title="Quality Scorecard · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Quality Scorecard")
st.markdown(
    "Quantitative evaluation of synthetic dataset fidelity, machine learning utility, and privacy risk."
)
st.divider()

result = st.session_state.get("last_result") or st.session_state.get("last_upload_result")
if not result:
    st.info("No active dataset found. Navigate to Generate Data to run or upload a dataset first.")
    st.stop()

scores = result.get("scores", {})
if not scores:
    st.warning("No quality scores found for the active run.")
    st.stop()

# ── Section 1: Integrity ──────────────────────────────────────────────────────
st.markdown("### 1. Integrity & Schema Compliance")
i1, i2 = st.columns(2)
with i1:
    integrity_ok = scores.get("integrity_passed", True)
    st.metric("Integrity Check", "PASSED" if integrity_ok else "FAILED")
with i2:
    st.metric("Integrity Violation Count", scores.get("integrity_errors", 0))

val = result.get("validation")
if val:
    for e in val.errors:
        st.error(e)
    for w in val.warnings:
        st.warning(w)
    if val.passed and not val.warnings:
        st.success("All schema, primary-key, and foreign-key referential integrity constraints passed cleanly.")

st.divider()

# ── Section 2: Fidelity ───────────────────────────────────────────────────────
st.markdown("### 2. Statistical Fidelity Evaluation")
top_fid = {
    "Overall Fidelity": scores.get("fidelity_fidelity_overall"),
    "KS Complement Mean": scores.get("fidelity_ks_mean"),
    "TV Complement Mean": scores.get("fidelity_tv_mean"),
    "Correlation Sim": scores.get("fidelity_corr_sim"),
}

if any(v is not None for v in top_fid.values()):
    f1, f2, f3, f4 = st.columns(4)
    for col, (lbl, val_s) in zip([f1, f2, f3, f4], top_fid.items()):
        with col:
            if val_s is not None:
                st.metric(lbl, f"{float(val_s):.3f}")
            else:
                st.metric(lbl, "N/A")

    c_f1, c_f2 = st.columns([1, 1])

    with c_f1:
        radar_labels = list(top_fid.keys())
        radar_vals = [float(v) if v is not None else 0.0 for v in top_fid.values()]
        fig_radar = go.Figure(go.Scatterpolar(
            r=radar_vals + [radar_vals[0]],
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            fillcolor="rgba(37,99,235,0.25)",
            line=dict(color="#2563eb", width=2.5),
            name="Fidelity Score",
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#111827",
                radialaxis=dict(visible=True, range=[0, 1], color="#9ca3af", gridcolor="#1f2937"),
                angularaxis=dict(color="#f9fafb"),
            ),
            template="plotly_dark",
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            height=340,
            margin=dict(l=30, r=30, t=40, b=30),
            title=dict(text="Fidelity Dimension Radar", font=dict(color="#f9fafb", size=14)),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with c_f2:
        fid_all = {
            k.replace("fidelity_", "").replace("_", " ").title(): v
            for k, v in scores.items()
            if k.startswith("fidelity_") and isinstance(v, float)
        }
        if len(fid_all) > 1:
            fid_df = pd.DataFrame(list(fid_all.items()), columns=["Metric", "Score"]).sort_values("Score")
            fig_fid_bar = px.bar(
                fid_df, x="Score", y="Metric", orientation="h",
                color="Score", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                range_color=[0, 1],
                template="plotly_dark",
                title="All Fidelity Sub-Metrics",
            )
            fig_fid_bar.update_layout(
                plot_bgcolor="#111827", paper_bgcolor="#111827",
                font_color="#f9fafb", height=340,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_fid_bar, use_container_width=True)
else:
    st.info("Fidelity scores not available for this run.")

st.divider()

# ── Section 3: Utility ────────────────────────────────────────────────────────
st.markdown("### 3. Machine Learning Utility (TSTR / TRTS / TRTR)")
st.caption(f"Reference model source: {scores.get('utility_reference_source', 'proxy')}")

util_rows = []
for prefix in ["tstr", "trts", "trtr"]:
    row = {"Evaluation Mode": prefix.upper()}
    for m in ["f1", "pr_auc", "auroc"]:
        key = f"utility_{prefix}_{m}"
        row[m.upper()] = (
            round(float(scores[key]), 4) if key in scores else "N/A"
        )
    util_rows.append(row)

util_df = pd.DataFrame(util_rows).set_index("Evaluation Mode")
st.dataframe(util_df.astype(str), use_container_width=True)

ratio = scores.get("utility_tstr_trtr_ratio")
if ratio is not None and not (isinstance(ratio, float) and ratio != ratio):
    st.metric(
        "TSTR / TRTR F1 Utility Ratio",
        f"{float(ratio):.3f}",
        help="A ratio >= 0.8 confirms synthetic data preserves machine learning predictive performance.",
    )

st.divider()

# ── Section 4: Privacy ────────────────────────────────────────────────────────
st.markdown("### 4. Privacy Risk & Distance-to-Closest-Record")
p1, p2, p3 = st.columns(3)
priv_items = [
    ("Exact Match Rate", scores.get("privacy_exact_match_rate"), "Fraction of exact record matches (lower is better)"),
    ("DCR Distance Score", scores.get("privacy_dcr_score"), "Nearest-neighbour distance (higher is better)"),
    ("Nearest-Neighbour Ratio", scores.get("privacy_nn_ratio"), "NN Ratio < 0.5 indicates robust privacy protection"),
]
for col, (lbl, val_s, note) in zip([p1, p2, p3], priv_items):
    with col:
        if val_s is not None and not (isinstance(val_s, float) and val_s != val_s):
            st.metric(lbl, f"{float(val_s):.4f}", help=note)
        else:
            st.metric(lbl, "N/A", help=note)

safety_warns = scores.get("privacy_safety_warnings", [])
if safety_warns:
    for w in safety_warns:
        st.warning(w)
else:
    st.success("Privacy check passed: Reserved RFC IP ranges and example.com domains confirmed.")

st.divider()

# ── Raw Scores ────────────────────────────────────────────────────────────────
with st.expander("View Raw Score JSON Payload"):
    st.json({k: (float(v) if isinstance(v, float) else v) for k, v in scores.items()})
