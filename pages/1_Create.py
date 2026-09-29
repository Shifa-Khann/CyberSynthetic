"""
pages/1_Create.py
Data Generation — Natural Language / Preset or CSV Upload.
"""
import pathlib
import sys
import traceback

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from engine.ui_styles import inject_css, sidebar_nav

load_dotenv()

st.set_page_config(
    page_title="Generate Data · CyberSynthetic",
    layout="wide",
)
inject_css()
sidebar_nav()

# ─────────────────────────────────────────────────────────────────────────────
st.title("Data Generation Engine")
st.markdown(
    "Create high-fidelity synthetic cybersecurity datasets using Natural Language prompts, "
    "pre-configured attack scenario templates, or by uploading real CSV files for schema-fitted synthesis."
)
st.divider()

mode = st.radio(
    "Input Generation Mode",
    ["Natural Language & Preset Scenarios", "Upload CSV File (Schema Fitting)"],
    horizontal=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════
# MODE A — Natural Language / Preset
# ═════════════════════════════════════════════════════════════
if mode == "Natural Language & Preset Scenarios":

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown(
            "<div class='section-title'>Scenario Prompt (Natural Language)</div>",
            unsafe_allow_html=True,
        )
        nl_input = st.text_area(
            "Describe the scenario you wish to synthesize",
            placeholder=(
                "e.g. Generate 2 weeks of authentication and phishing email events for 50 users "
                "with an APT lateral movement scenario. Include Urdu translations."
            ),
            height=110,
            label_visibility="collapsed",
        )

    with col_right:
        st.markdown(
            "<div class='section-title'>Quick Preset Template</div>",
            unsafe_allow_html=True,
        )
        preset = st.selectbox(
            "Pre-configured scenario preset",
            ["small_auth", "medium_full", "hard_stealth"],
            label_visibility="collapsed",
        )
        st.caption("Select a preset template to auto-populate generation parameters.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>Synthesis Configuration</div>",
        unsafe_allow_html=True,
    )

    r1c1, r1c2, r1c3 = st.columns(3, gap="medium")
    with r1c1:
        output_format = st.selectbox(
            "Output Format",
            [
                "Relational Database (Multi-Table SQLite + CSVs)",
                "Tabular CSV (Single Table)",
                "Documents (PDF Incident Reports)",
            ],
        )
    with r1c2:
        language = st.selectbox("Output Language", ["en", "ur", "both"])
    with r1c3:
        difficulty = st.selectbox(
            "Attack Complexity", ["easy", "medium", "hard"], index=1
        )

    r2c1, r2c2, r2c3, r2c4 = st.columns(4, gap="medium")
    with r2c1:
        seed = st.number_input("Random Seed", value=42, min_value=0, max_value=99999)
    with r2c2:
        users = st.slider("User Population", 5, 500, 50)
    with r2c3:
        duration = st.slider("Timespan (Days)", 1, 90, 7)
    with r2c4:
        use_llm = st.toggle("LLM Plan Planner", value=False)

    # Determine domains & doc flag
    is_tabular = "Tabular" in output_format
    is_docs = "Documents" in output_format or "Relational" in output_format
    domains = ["auth"] if is_tabular else ["auth", "email", "endpoint"]

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Generate Synthetic Dataset", type="primary", use_container_width=True):
        from engine.plan import Plan, plan_from_dict
        from engine.generate import run_scenario
        from engine.llm import plan_from_nl

        with st.spinner("Executing synthetic data generation pipeline..."):
            try:
                if nl_input.strip() and use_llm:
                    plan_dict = plan_from_nl(nl_input.strip())
                    plan_dict.update({
                        "seed": int(seed),
                        "users": int(users),
                        "duration_days": int(duration),
                        "difficulty": difficulty,
                        "domains": domains,
                        "language": language,
                        "use_llm": use_llm,
                        "generate_documents": is_docs,
                    })
                    plan = plan_from_dict(plan_dict)
                else:
                    plan = Plan(
                        seed=int(seed),
                        users=int(users),
                        devices=max(1, int(users * 0.7)),
                        duration_days=int(duration),
                        difficulty=difficulty,
                        domains=domains,
                        language=language,
                        use_llm=use_llm,
                        generate_documents=is_docs,
                    )

                result = run_scenario(plan)
                st.session_state["last_result"] = result

            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                st.code(traceback.format_exc())
                st.stop()

        # ── Success Banner ──
        run_id = result["run_id"]
        st.success(f"Dataset Generated Successfully — Run ID: {run_id}")
        st.caption(f"SHA-256 Dataset Signature: {result['dataset_hash']}")

        # ── Validation ──
        val = result["validation"]
        if val.passed:
            st.info("Schema & referential integrity constraints validated successfully.")
        else:
            st.error("Integrity validation issues detected:")
            for err in val.errors:
                st.error(err)
        for warn in val.warnings:
            st.warning(warn)

        st.divider()

        # ── Quality Metrics ──
        scores = result["scores"]
        st.markdown("<div class='section-title'>Quality Metric Summary</div>", unsafe_allow_html=True)
        mc1, mc2, mc3, mc4 = st.columns(4)
        _metrics = [
            ("Fidelity Score", scores.get("fidelity_fidelity_overall")),
            ("TSTR F1 Score", scores.get("utility_tstr_f1")),
            ("Integrity Pass Rate", 1.0 if scores.get("integrity_passed") else 0.0),
            ("Privacy DCR Score", scores.get("privacy_dcr_score")),
        ]
        for col, (label, val_s) in zip([mc1, mc2, mc3, mc4], _metrics):
            with col:
                if val_s is not None and not (isinstance(val_s, float) and val_s != val_s):
                    st.metric(label, f"{float(val_s):.3f}")
                else:
                    st.metric(label, "N/A")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Generated Tables ──
        st.markdown("<div class='section-title'>Generated Datasets & CSV Downloads</div>", unsafe_allow_html=True)
        tables = result["tables"]

        for tbl_name, tbl_df in tables.items():
            if tbl_df.empty:
                continue
            with st.expander(
                f"Table: {tbl_name.upper()} ({len(tbl_df):,} rows × {len(tbl_df.columns)} columns)",
                expanded=(list(tables.keys()).index(tbl_name) == 0),
            ):
                st.dataframe(tbl_df.head(100).astype(str), use_container_width=True, height=280)
                st.download_button(
                    f"Download {tbl_name}.csv",
                    data=tbl_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"{tbl_name}.csv",
                    mime="text/csv",
                    key=f"dl_{tbl_name}",
                )

        # ── PDF Documents ──
        if is_docs and "out_dir" in result:
            reports_dir = pathlib.Path(result["out_dir"]) / "reports"
            if reports_dir.exists():
                pdfs = list(reports_dir.glob("*.pdf"))
                if pdfs:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<div class='section-title'>Generated Incident Documents (PDF)</div>", unsafe_allow_html=True)
                    for pdf in pdfs[:10]:
                        with open(pdf, "rb") as f:
                            st.download_button(
                                f"Download PDF: {pdf.name}",
                                data=f.read(),
                                file_name=pdf.name,
                                mime="application/pdf",
                                key=f"pdf_{pdf.name}",
                            )

        st.info("Dataset loaded into memory. Navigate to Data Explorer or Incident Lineage in the sidebar to inspect.")


# ═════════════════════════════════════════════════════════════
# MODE B — Upload CSV
# ═════════════════════════════════════════════════════════════
else:
    st.markdown("<div class='section-title'>Upload Source Data File</div>", unsafe_allow_html=True)
    st.caption("Privacy Guarantee: Column names and summary statistics are processed locally. Raw data is never sent externally.")

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"], label_visibility="collapsed")

    if uploaded_file:
        real_df = pd.read_csv(uploaded_file)
        st.success(f"Source file loaded: {len(real_df):,} rows × {len(real_df.columns)} columns")

        with st.expander("Preview Source Dataset (First 10 Rows)", expanded=True):
            st.dataframe(real_df.head(10), use_container_width=True)

        from engine.upload.infer import infer_schema
        from engine.upload.classify import classify_columns

        schema = infer_schema(real_df)
        roles = classify_columns(real_df, schema)

        st.markdown("<div class='section-title'>Inferred Schema & Column Roles</div>", unsafe_allow_html=True)
        schema_df = pd.DataFrame({
            "Column": list(roles.keys()),
            "Data Type": [schema.dtypes.get(c, "unknown") for c in roles.keys()],
            "Inferred Role": [r.value for r in roles.values()],
            "Nullable": [schema.nullable.get(c, False) for c in roles.keys()],
            "PK Candidate": ["Yes" if c == schema.pk_guess else "No" for c in roles.keys()],
        })
        st.dataframe(schema_df, use_container_width=True)

        st.markdown("<div class='section-title'>Fitted Model Options</div>", unsafe_allow_html=True)
        uc1, uc2, uc3 = st.columns(3, gap="medium")
        with uc1:
            n_rows = st.number_input("Synthetic Rows to Sample", 100, 50000, max(len(real_df), 200))
        with uc2:
            up_seed = st.number_input("Random Seed", 0, 99999, 42, key="up_seed")
        with uc3:
            model_type = st.selectbox("Generative Architecture", ["gaussian_copula", "ctgan", "tvae"])

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Fit Model & Synthesize Data", type="primary", use_container_width=True):
            from engine.upload.fit import fit_model
            from engine.upload.sample import sample_synthetic
            from engine.evaluate.fidelity import compute_fidelity
            from engine.evaluate.utility import compute_utility
            from engine.evaluate.privacy import compute_privacy
            from engine.evaluate.runs import save_run
            from engine.export import export_all, compute_dataset_hash
            from datetime import datetime, timezone

            with st.spinner(f"Fitting {model_type} model on uploaded schema..."):
                try:
                    fitted = fit_model(real_df, roles, model_type=model_type, seed=int(up_seed))
                    st.success("Model fitting completed.")
                except Exception as exc:
                    st.error(f"Fitting failed: {exc}")
                    st.stop()

            with st.spinner("Sampling synthetic rows..."):
                try:
                    synthetic_df = sample_synthetic(fitted, n_rows=int(n_rows), seed=int(up_seed))
                except Exception as exc:
                    st.error(f"Sampling failed: {exc}")
                    st.stop()

            st.success(f"Synthesized {len(synthetic_df):,} synthetic rows matching source distribution.")

            # ── Evaluation ──
            scores = {}
            fid = compute_fidelity(real_df, synthetic_df)
            scores.update({f"fidelity_{k}": v for k, v in fid.items()})

            target_candidates = [c for c in real_df.columns if c.lower() in ("label", "target", "class", "y")]
            target_col = target_candidates[0] if target_candidates else real_df.columns[-1]
            if target_col in real_df.columns and target_col in synthetic_df.columns:
                util = compute_utility(synthetic_df, real_df, target_col=target_col)
                scores.update({f"utility_{k}": v for k, v in util.items() if isinstance(v, (int, float))})

            priv = compute_privacy(real_df, synthetic_df)
            scores.update({f"privacy_{k}": v for k, v in priv.items() if isinstance(v, (int, float))})

            st.markdown("<div class='section-title'>Synthetic Data Fidelity Metrics</div>", unsafe_allow_html=True)
            fm1, fm2, fm3, fm4 = st.columns(4)
            _fid_items = [
                ("Fidelity Score", scores.get("fidelity_fidelity_overall")),
                ("KS Complement", scores.get("fidelity_ks_mean")),
                ("TV Mean Similarity", scores.get("fidelity_tv_mean")),
                ("Correlation Matrix Sim", scores.get("fidelity_corr_sim")),
            ]
            for col, (lbl, val_s) in zip([fm1, fm2, fm3, fm4], _fid_items):
                with col:
                    if val_s is not None:
                        st.metric(lbl, f"{float(val_s):.3f}")
                    else:
                        st.metric(lbl, "N/A")

            # ── Table Preview & Download ──
            st.markdown("<div class='section-title'>Synthetic Output Dataset</div>", unsafe_allow_html=True)
            st.dataframe(synthetic_df.head(100).astype(str), use_container_width=True, height=320)
            st.download_button(
                "Download Synthetic Dataset (CSV)",
                data=synthetic_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="synthetic_output.csv",
                mime="text/csv",
            )

            # ── Persist run ──
            run_id = f"RUN-UPLOAD-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
            tables = {"synthetic": synthetic_df}
            dataset_hash = compute_dataset_hash(tables)
            export_all(run_id, tables, {"mode": "upload", "seed": int(up_seed)}, scores)
            save_run(
                run_id=run_id,
                seed=int(up_seed),
                plan_hash="upload",
                dataset_hash=dataset_hash,
                mode="upload",
                calibration_source="upload",
                scores=scores,
                table_shapes={"synthetic": (len(synthetic_df), len(synthetic_df.columns))},
            )
            st.session_state["last_upload_result"] = {
                "synthetic": synthetic_df,
                "real": real_df,
                "scores": scores,
                "run_id": run_id,
            }
            st.session_state["last_result"] = {
                "tables": tables,
                "run_id": run_id,
                "scores": scores,
                "dataset_hash": dataset_hash,
            }
            st.success(f"Run saved to Execution History — ID: {run_id}")
