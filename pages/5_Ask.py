"""
pages/5_Ask.py
Analytics & Profiling — Natural language queries, Python analytics, and sweetviz profiling.
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
    page_title="Analytics & Profiling · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Analytics & Profiling Engine")
st.markdown(
    "Query and visualize active synthetic datasets using Natural Language prompts or Quick Presets. "
    "Powered by Pandas, Plotly, and Sweetviz."
)
st.divider()

result = st.session_state.get("last_result") or st.session_state.get("last_upload_result")

if not result:
    st.info("No active dataset found. Navigate to Generate Data to run or upload a dataset first.")
    st.stop()

if "tables" in result:
    tables = result["tables"]
elif "synthetic" in result:
    tables = {"synthetic": result["synthetic"]}
else:
    st.warning("No data tables found in current session.")
    st.stop()

tables = {k: v for k, v in tables.items() if isinstance(v, pd.DataFrame) and not v.empty}
if not tables:
    st.warning("All tables in active dataset are empty.")
    st.stop()

# SQLite path
db_path = None
if "run_id" in result:
    possible_db = pathlib.Path("outputs") / result["run_id"] / "db.sqlite"
    if possible_db.exists():
        db_path = possible_db

# ── Table Selector ────────────────────────────────────────────────────────────
table_name = st.selectbox("Select Active Table for Analysis", list(tables.keys()))
df = tables[table_name]
st.caption(f"Active table `{table_name}` — {len(df):,} rows × {len(df.columns)} columns")

numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

st.divider()

# ── Quick Preset Buttons ──────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Quick Analytics Presets</div>", unsafe_allow_html=True)
p1, p2, p3, p4, p5, p6 = st.columns(6)
if p1.button("Statistical Summary", use_container_width=True):
    st.session_state["ask_query"] = "statistical summary"
if p2.button("Data Types & Info", use_container_width=True):
    st.session_state["ask_query"] = "info"
if p3.button("Correlation Matrix", use_container_width=True):
    st.session_state["ask_query"] = "correlation"
if p4.button("Null Value Check", use_container_width=True):
    st.session_state["ask_query"] = "null values"
if p5.button("Value Frequencies", use_container_width=True):
    st.session_state["ask_query"] = "value counts"
if p6.button("Full Profile Report", use_container_width=True):
    st.session_state["ask_query"] = "profile report"

# ── Query Input ───────────────────────────────────────────────────────────────
query = st.text_input(
    "Natural Language Query / Command",
    value=st.session_state.get("ask_query", "statistical summary"),
    placeholder=(
        "e.g. 'statistical summary' · 'histogram of severity' · "
        "'correlation' · 'null values' · 'profile report'"
    ),
    label_visibility="collapsed",
)

if not query:
    st.stop()

st.markdown("---")
q = query.lower().strip()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Statistical Summary
# ═══════════════════════════════════════════════════════════════════════════════
if any(k in q for k in ["describe", "statistical summary", "stats", "summary"]):
    st.markdown("### Statistical Summary")
    try:
        summary = df.describe(include="all").T.reset_index().rename(columns={"index": "Column"})
        summary = summary.fillna("-")
        st.dataframe(summary, use_container_width=True, height=450)
        st.download_button(
            "Download Summary CSV",
            data=summary.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{table_name}_summary.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error computing summary: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Info / Schema
# ═══════════════════════════════════════════════════════════════════════════════
elif any(k in q for k in ["info", "data types", "dtypes", "schema", "structure"]):
    st.markdown("### Data Schema & Column Breakdown")
    info_rows = []
    for col in df.columns:
        s = df[col]
        info_rows.append({
            "Column": col,
            "Dtype": str(s.dtype),
            "Non-Null Count": s.count(),
            "Null Count": s.isnull().sum(),
            "Null Ratio": f"{s.isnull().mean():.1%}",
            "Unique Count": s.nunique(),
            "Sample Value": str(s.dropna().iloc[0]) if s.dropna().shape[0] > 0 else "-",
        })
    info_df = pd.DataFrame(info_rows)
    st.dataframe(info_df, use_container_width=True, height=450)
    st.caption(f"Memory footprint: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    st.download_button(
        "Download Schema CSV",
        data=info_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{table_name}_schema.csv",
        mime="text/csv",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Correlation Heatmap
# ═══════════════════════════════════════════════════════════════════════════════
elif any(k in q for k in ["correlation", "corr", "heatmap"]):
    st.markdown("### Correlation Matrix Heatmap")
    num_df = df.select_dtypes(include=np.number)
    if num_df.shape[1] < 2:
        st.info("Not enough numeric columns in this table to compute correlation matrix.")
    else:
        corr = num_df.corr().fillna(0)
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            template="plotly_dark",
            title="Pairwise Feature Correlation",
        )
        fig.update_layout(
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font_color="#f9fafb",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.download_button(
            "Download Correlation Matrix CSV",
            data=corr.to_csv().encode("utf-8-sig"),
            file_name=f"{table_name}_correlation.csv",
            mime="text/csv",
        )

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Null Value Check
# ═══════════════════════════════════════════════════════════════════════════════
elif any(k in q for k in ["null", "missing", "nan"]):
    st.markdown("### Missing / Null Value Audit")
    null_s = df.isnull().sum()
    null_df = pd.DataFrame({"Column": null_s.index, "Null Count": null_s.values})
    null_df["Null Ratio %"] = (null_df["Null Count"] / len(df) * 100).round(2)
    null_df = null_df.sort_values("Null Count", ascending=False)

    st.dataframe(null_df, use_container_width=True)

    if null_df["Null Count"].sum() == 0:
        st.success("Clean dataset: Zero null / missing values detected across all columns.")
    else:
        fig = px.bar(
            null_df[null_df["Null Count"] > 0],
            x="Column",
            y="Null Ratio %",
            color="Null Ratio %",
            color_continuous_scale="Oranges",
            template="plotly_dark",
            title="Null Value Ratio by Column",
        )
        fig.update_layout(
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font_color="#f9fafb",
        )
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Value Counts / Frequencies
# ═══════════════════════════════════════════════════════════════════════════════
elif any(k in q for k in ["value count", "frequency", "top value", "counts"]):
    st.markdown("### Categorical Value Frequencies")
    if not cat_cols:
        st.info("No categorical text columns found in this table.")
    else:
        target_cat = cat_cols[0]
        for c in cat_cols:
            if c.lower() in q:
                target_cat = c
                break
        st.caption(f"Showing value frequencies for column `{target_cat}`")
        vc = df[target_cat].value_counts().head(25).reset_index()
        vc.columns = [target_cat, "Count"]
        st.dataframe(vc, use_container_width=True, height=300)
        fig = px.bar(
            vc,
            x=target_cat,
            y="Count",
            color="Count",
            color_continuous_scale="Blues",
            template="plotly_dark",
            title=f"Top Value Counts — {target_cat}",
        )
        fig.update_layout(
            plot_bgcolor="#111827",
            paper_bgcolor="#111827",
            font_color="#f9fafb",
        )
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. Full Sweetviz Profile
# ═══════════════════════════════════════════════════════════════════════════════
elif any(k in q for k in ["profile", "profiling", "report", "full analysis"]):
    st.markdown("### Automated Data Profile Report")
    try:
        import sweetviz as sv

        sample_size = min(len(df), 5000)
        if sample_size < len(df):
            st.caption(f"Sampling {sample_size:,} of {len(df):,} rows for execution speed.")

        with st.spinner("Generating profile report..."):
            sample_df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
            for col in sample_df.columns:
                if sample_df[col].dtype == object:
                    sample_df[col] = sample_df[col].astype(str)
            report = sv.analyze(sample_df)
            tmp_path = pathlib.Path("outputs") / f"sweetviz_{table_name}.html"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            report.show_html(str(tmp_path), open_browser=False)
            html_content = tmp_path.read_text(encoding="utf-8")

        st.success("Sweetviz profile report generated.")
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

# ═══════════════════════════════════════════════════════════════════════════════
# 7. SQL query
# ═══════════════════════════════════════════════════════════════════════════════
elif db_path and any(k in q for k in ["select", "from", "where", "group by"]):
    from engine.query import run_query
    try:
        cleaned_sql, result_df = run_query(query, db_path)
        st.markdown("### SQL Execution Result")
        st.code(cleaned_sql, language="sql")
        st.dataframe(result_df, use_container_width=True, height=350)
        st.download_button(
            "Download Query Result CSV",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="query_result.csv",
            mime="text/csv",
        )
    except Exception as exc:
        st.error(f"SQL execution error: {exc}")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. Column-specific visualization
# ═══════════════════════════════════════════════════════════════════════════════
else:
    matched_col = next((c for c in df.columns if c.lower() in q), None)
    if matched_col:
        st.markdown(f"### Visualization — `{matched_col}`")
        if matched_col in numeric_cols:
            fig = px.histogram(
                df,
                x=matched_col,
                color_discrete_sequence=["#2563eb"],
                template="plotly_dark",
                title=f"Distribution of {matched_col}",
            )
            fig.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            vc = df[matched_col].value_counts().head(20).reset_index()
            vc.columns = [matched_col, "Count"]
            st.dataframe(vc, use_container_width=True, height=300)
            fig = px.bar(
                vc,
                x=matched_col,
                y="Count",
                color="Count",
                template="plotly_dark",
                title=f"Value Frequencies — {matched_col}",
            )
            fig.update_layout(
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font_color="#f9fafb",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("### Data Overview")
        st.dataframe(df.head(50).astype(str), use_container_width=True, height=400)

# ── Always show download button ───────────────────────────────────────────────
st.divider()
st.download_button(
    f"Download {table_name}.csv",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"{table_name}_export.csv",
    mime="text/csv",
    key=f"dl_ask_{table_name}",
)
