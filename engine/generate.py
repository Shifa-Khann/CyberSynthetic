"""
engine/generate.py
Top-level orchestrator for scenario-mode generation.
Wires together: world -> background -> attacks -> detect -> validate -> localize -> export.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from datetime import datetime, timezone

import pandas as pd

from engine.plan import Plan
from engine.rng import RNGTree, make_rng_tree
from engine.world import generate_users, generate_devices
from engine.background import generate_auth_events, generate_email_events, generate_process_events
from engine.attacks import generate_attacks
from engine.detect import generate_alerts, correlate_incidents, generate_indicators
from engine.validate import validate_dataset, ValidationResult
from engine.localize import localize_dataset
from engine.export import export_all, compute_dataset_hash
from engine.evaluate.fidelity import compute_fidelity
from engine.evaluate.utility import compute_utility
from engine.evaluate.privacy import compute_privacy
from engine.evaluate.runs import save_run
from engine.report import generate_reports


def _plan_hash(plan: Plan) -> str:
    return hashlib.sha256(plan.model_dump_json().encode()).hexdigest()[:16]


def _make_run_id(plan: Plan) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"RUN-{ts}-{_plan_hash(plan)}"


def run_scenario(
    plan: Plan,
    output_base: pathlib.Path = pathlib.Path("outputs"),
    real_df: pd.DataFrame | None = None,
) -> dict:
    """
    Execute a full scenario-mode generation run.

    Args:
        plan: Validated Plan object.
        output_base: Where to write outputs.
        real_df: Optional reference real DataFrame for utility comparison.

    Returns:
        dict with keys: run_id, out_dir, tables, validation, scores, dataset_hash
    """
    run_id = _make_run_id(plan)
    rng = make_rng_tree(plan.seed)
    start_time = datetime(2024, 1, 1, tzinfo=None)  # fixed epoch for reproducibility

    # ── 1. WORLD ──
    users_df = generate_users(plan.seed, plan.users, rng)
    devices_df = generate_devices(plan.seed, plan.devices, users_df, rng)

    # ── 2. BACKGROUND ──
    auth_bg = generate_auth_events(
        users_df, devices_df, plan.seed, plan.duration_days, start_time, rng
    )
    emails_bg, email_events_bg = pd.DataFrame(), pd.DataFrame()
    process_bg = pd.DataFrame()

    if "email" in plan.domains:
        emails_bg, email_events_bg = generate_email_events(
            users_df, plan.seed, plan.duration_days, start_time, rng
        )
    if "endpoint" in plan.domains:
        process_bg = generate_process_events(
            users_df, devices_df, plan.seed, plan.duration_days, start_time, rng
        )

    # ── 3. ATTACKS ──
    attack_tables = generate_attacks(
        users_df, devices_df, start_time, plan.duration_days,
        plan.seed, plan.difficulty, plan.domains, rng
    )

    # Merge background + attacks
    auth_df = _concat_safe([auth_bg, attack_tables.get("auth_events", pd.DataFrame())])
    emails_df = _concat_safe([emails_bg, attack_tables.get("emails", pd.DataFrame())])
    email_events_df = _concat_safe([email_events_bg, attack_tables.get("email_events", pd.DataFrame())])
    process_df = _concat_safe([process_bg, attack_tables.get("process_events", pd.DataFrame())])

    # Sort by ts
    for df in [auth_df, emails_df, email_events_df, process_df]:
        if not df.empty and "ts" in df.columns:
            df["ts"] = df["ts"].astype(str)
            df.sort_values("ts", inplace=True)
            df.reset_index(drop=True, inplace=True)

    # ── 4. DETECTION ──
    alerts_df = generate_alerts(
        auth_df, emails_df, email_events_df, process_df,
        users_df, devices_df, plan.seed, rng
    )
    incidents_df, alerts_df = correlate_incidents(alerts_df, plan.seed, rng)
    indicators_df = generate_indicators(incidents_df, alerts_df, auth_df, plan.seed)

    # ── 5. VALIDATE ──
    val_result = validate_dataset(
        users_df, devices_df, auth_df, emails_df, email_events_df,
        process_df, alerts_df, incidents_df, indicators_df
    )

    # ── 6. LOCALIZE ──
    if plan.language in ("ur", "both"):
        localized = localize_dataset(users_df, auth_df, emails_df, alerts_df, incidents_df)
        users_df = localized["users"]
        auth_df = localized["auth_events"]
        emails_df = localized["emails"]
        alerts_df = localized["alerts"]
        incidents_df = localized["incidents"]

    # ── 7. TABLE ASSEMBLY ──
    tables = {
        "users": users_df.drop(columns=["_hour_profile", "_events_per_day"], errors="ignore"),
        "devices": devices_df,
        "auth_events": auth_df,
        "alerts": alerts_df,
        "incidents": incidents_df,
        "indicators": indicators_df,
    }
    if not emails_df.empty:
        tables["emails"] = emails_df
    if not email_events_df.empty:
        tables["email_events"] = email_events_df
    if not process_df.empty:
        tables["process_events"] = process_df

    dataset_hash = compute_dataset_hash(tables)

    # ── 8. EVALUATE ──
    scores: dict = {}
    # Fidelity on auth_events vs a differently-seeded run would be ideal;
    # here we use internal consistency as proxy
    if not auth_df.empty and len(auth_df) > 20:
        # split synthetic in half as proxy comparison
        half = len(auth_df) // 2
        fid = compute_fidelity(auth_df.iloc[:half], auth_df.iloc[half:])
        scores.update({f"fidelity_{k}": v for k, v in fid.items()})

    if not auth_df.empty and "label" in auth_df.columns:
        util = compute_utility(auth_df, real_df, target_col="label")
        scores.update({f"utility_{k}": v for k, v in util.items()
                       if isinstance(v, (int, float))})
        scores["utility_reference_source"] = util.get("reference_source", "proxy")

    priv = compute_privacy(real_df if real_df is not None else pd.DataFrame(), auth_df)
    scores.update({f"privacy_{k}": v for k, v in priv.items()
                   if isinstance(v, (int, float))})

    # Label balance
    if not auth_df.empty and "label" in auth_df.columns:
        vc = auth_df["label"].value_counts(normalize=True)
        for lbl, frac in vc.items():
            scores[f"label_frac_{lbl}"] = float(frac)

    # Integrity
    scores["integrity_passed"] = val_result.passed
    scores["integrity_errors"] = len(val_result.errors)

    # ── 9. EXPORT ──
    out_dir = export_all(run_id, tables, plan.model_dump(), scores, output_base)

    # Urdu CSV export
    if plan.language in ("ur", "both"):
        from engine.export import export_csv_urdu
        export_csv_urdu(tables, out_dir)

    # ── 10. REPORTS ──
    narratives: dict[str, str] = {}
    if plan.generate_documents and not incidents_df.empty:
        from engine.llm import generate_incident_narrative
        for _, inc in incidents_df.iterrows():
            facts = inc.to_dict()
            narratives[inc["incident_id"]] = generate_incident_narrative(facts, language="en")
        generate_reports(incidents_df, alerts_df, indicators_df, narratives, out_dir, language="en")

        if plan.language in ("ur", "both"):
            narratives_ur: dict[str, str] = {}
            for _, inc in incidents_df.iterrows():
                facts = inc.to_dict()
                narratives_ur[inc["incident_id"]] = generate_incident_narrative(facts, language="ur")
            generate_reports(incidents_df, alerts_df, indicators_df, narratives_ur, out_dir, language="ur")

    # ── 11. RUN RECORD ──
    table_shapes = {k: (len(v), len(v.columns)) for k, v in tables.items()}
    save_run(
        run_id=run_id,
        seed=plan.seed,
        plan_hash=_plan_hash(plan),
        dataset_hash=dataset_hash,
        mode="scenario",
        calibration_source="expert_prior",
        scores=scores,
        table_shapes=table_shapes,
    )

    return {
        "run_id": run_id,
        "out_dir": out_dir,
        "tables": tables,
        "validation": val_result,
        "scores": scores,
        "dataset_hash": dataset_hash,
        "plan": plan,
    }


def _concat_safe(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame()
    return pd.concat(non_empty, ignore_index=True)
