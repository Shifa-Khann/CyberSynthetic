"""
pages/2_Data.py
Data Explorer — View, filter, and inspect generated tables with full profiling.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from engine.ui_styles import inject_css, sidebar_nav

st.set_page_config(
    page_title="Data Explorer · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Data Explorer")
st.markdown("Inspect, filter, analyze, and deeply profile every table in the active dataset.")
st.divider()

result = st.session_state.get("last_result") or st.session_state.get("last_upload_result")

if not result:
    st.info("No active dataset found in memory. Navigate to Generate Data to generate or upload a dataset first.")
    st.stop()

if "tables" in result:
    tables = result["tables"]
elif "synthetic" in result:
    tables = {"synthetic": result["synthetic"]}
else:
    st.warning("No data tables found in current session.")
    st.stop()

# Filter out empty tables
tables = {k: v for k, v in tables.items() if isinstance(v, pd.DataFrame) and not v.empty}
if not tables:
    st.warning("All tables in active dataset are empty.")
    st.stop()

# ── Table Selector ────────────────────────────────────────────────────────────
col_sel, col_info = st.columns([2, 5], gap="large")
with col_sel:
    st.markdown("<div class='section-title'>Active Table Selector</div>", unsafe_allow_html=True)
    table_name = st.selectbox("Select Table", list(tables.keys()), label_visibility="collapsed")

df = tables[table_name]

with col_info:
    st.markdown("<div class='section-title'>Table Metadata Overview</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Rows", f"{len(df):,}")
    m2.metric("Columns", f"{len(df.columns)}")
    m3.metric("Null Values", f"{df.isnull().sum().sum():,}")
    m4.metric("Memory Size", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_view, tab_stats, tab_charts, tab_profile = st.tabs([
    "Data View & Export",
    "Statistical Summary",
    "Distribution Charts",
    "Automated Data Profile",
])

# ── Tab 1: Data View ──────────────────────────────────────────────────────────
with tab_view:
    ur_cols = [c for c in df.columns if c.endswith("_ur")]
    col_opts = st.columns([3, 2])
    with col_opts[0]:
        search = st.text_input("Filter rows (substring search across columns)", placeholder="e.g. malicious, 10.0.0.")
    with col_opts[1]:
        show_ur = False
        if ur_cols:
            show_ur = st.toggle("Show Urdu Columns Only", value=False)

    display_df = df
    if show_ur:
        base_id_cols = [c for c in df.columns if c.endswith("_id") or c == "ts"]
        display_df = df[base_id_cols + ur_cols]

    if search:
        mask = display_df.apply(
            lambda col: col.astype(str).str.contains(search, case=False, na=False)
        ).any(axis=1)
        display_df = display_df[mask]
        st.caption(f"Showing {len(display_df):,} matching rows")

    st.dataframe(display_df.astype(str), use_container_width=True, height=450)

    st.download_button(
        f"Download {table_name}.csv",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{table_name}.csv",
        mime="text/csv",
        key=f"dl_exp_{table_name}",
    )

# ── Tab 2: Statistical Summary ────────────────────────────────────────────────
with tab_stats:
    st.markdown("#### Descriptive Statistics")
    desc_df = df.describe(include="all").T.reset_index().rename(columns={"index": "Column"})
    desc_df = desc_df.fillna("-")
    st.dataframe(desc_df, use_container_width=True, height=350)

    st.markdown("#### Column Type & Null Breakdown")
    info_rows = []
    for col in df.columns:
        s = df[col]
        info_rows.append({
            "Column": col,
            "Data Type": str(s.dtype),
            "Non-Null Count": s.count(),
            "Null Count": s.isnull().sum(),
            "Null Ratio": f"{s.isnull().mean():.1%}",
            "Unique Values": s.nunique(),
            "Mode / Most Frequent": str(s.mode().iloc[0]) if not s.mode().empty else "-",
        })
    info_df = pd.DataFrame(info_rows)
    st.dataframe(info_df, use_container_width=True)

    st.download_button(
        "Download Column Statistics CSV",
        data=info_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{table_name}_stats.csv",
        mime="text/csv",
    )

# ── Tab 3: Distribution Charts ────────────────────────────────────────────────
with tab_charts:
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    c_chart1, c_chart2 = st.columns(2)

    with c_chart1:
        if numeric_cols:
            st.markdown("#### Numeric Distribution")
            chosen_num = st.selectbox("Select numeric column", numeric_cols, key="chart_num")
            fig_hist = px.histogram(
                df,
                x=chosen_num,
                color_discrete_sequence=["#2563eb"],
                template="plotly_dark",
                title=f"Histogram — {chosen_num}",
            )
            fig_hist.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No numeric columns found in this table.")

    with c_chart2:
        if cat_cols:
            st.markdown("#### Categorical Frequency")
            chosen_cat = st.selectbox("Select categorical column", cat_cols, key="chart_cat")
            vc = df[chosen_cat].value_counts().head(20).reset_index()
            vc.columns = [chosen_cat, "Count"]
            fig_bar = px.bar(
                vc,
                x=chosen_cat,
                y="Count",
                color="Count",
                color_continuous_scale="Blues",
                template="plotly_dark",
                title=f"Value Frequency — {chosen_cat}",
            )
            fig_bar.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c_chart3, c_chart4 = st.columns(2)

    with c_chart3:
        if "ts" in df.columns:
            st.markdown("#### Event Volume Over Time")
            df_ts = df.copy()
            df_ts["ts"] = pd.to_datetime(df_ts["ts"], errors="coerce")
            df_ts = df_ts.dropna(subset=["ts"])
            if not df_ts.empty:
                df_ts["date"] = df_ts["ts"].dt.date
                daily = df_ts.groupby("date").size().reset_index(name="Count")
                fig_area = px.area(
                    daily,
                    x="date",
                    y="Count",
                    color_discrete_sequence=["#8b5cf6"],
                    template="plotly_dark",
                    title="Daily Event Activity",
                )
                fig_area.update_layout(
                    plot_bgcolor="#111827",
                    paper_bgcolor="#111827",
                    font_color="#f9fafb",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig_area, use_container_width=True)

    with c_chart4:
        if len(numeric_cols) >= 2:
            st.markdown("#### Pairwise Correlation Heatmap")
            corr_df = df[numeric_cols].corr().fillna(0)
            fig_corr = px.imshow(
                corr_df,
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                template="plotly_dark",
                title="Correlation Heatmap",
            )
            fig_corr.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

# ── Tab 4: Full Data Profile (sweetviz) ───────────────────────────────────────
with tab_profile:
    st.markdown("#### Automated Sweetviz Data Profiling")
    st.caption(
        "Generate a complete interactive profiling report analyzing distributions, missing values, "
        "associations, and field health using sweetviz."
    )

    sample_size = min(len(df), 5000)
    col_pr1, col_pr2 = st.columns([1, 3])
    with col_pr1:
        do_profile = st.button("Run Profile Analysis", type="primary")
    with col_pr2:
        if sample_size < len(df):
            st.caption(f"Profile will sample {sample_size:,} of {len(df):,} rows for execution speed.")

    if do_profile:
        try:
            import sweetviz as sv

            with st.spinner("Generating profile report..."):
                sample_df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
                for col in sample_df.columns:
                    if sample_df[col].dtype == object:
                        sample_df[col] = sample_df[col].astype(str)

                report = sv.analyze(sample_df, target_feat=None)
                tmp_path = pathlib.Path("outputs") / f"sweetviz_{table_name}.html"
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                report.show_html(str(tmp_path), open_browser=False)

                html_content = tmp_path.read_text(encoding="utf-8")

            st.success("Data profile report generated successfully.")
            components.html(html_content, height=800, scrolling=True)

            st.download_button(
                "Download Profile Report (HTML)",
                data=html_content.encode("utf-8"),
                file_name=f"{table_name}_profile.html",
                mime="text/html",
            )

        except ImportError:
            st.error("sweetviz library is not installed.")
        except Exception as exc:
            st.error(f"Profiling failed: {exc}")
