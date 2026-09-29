"""
engine/export.py
Export generated datasets to CSV, JSON, SQLite, and manifest.
Computes dataset hash for reproducibility verification.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
from datetime import datetime, timezone

import pandas as pd


def _sha256_df(df: pd.DataFrame) -> str:
    """SHA-256 over sorted CSV bytes of a DataFrame."""
    if df.empty:
        return hashlib.sha256(b"").hexdigest()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def compute_dataset_hash(tables: dict[str, pd.DataFrame]) -> str:
    """
    Deterministic hash over all tables.
    Same seed + plan => same hash.
    """
    h = hashlib.sha256()
    for name in sorted(tables.keys()):
        df = tables[name]
        h.update(name.encode())
        h.update(_sha256_df(df).encode())
    return h.hexdigest()


# ──────────────────────────────────────────────
# Export helpers
# ──────────────────────────────────────────────

def export_csv(tables: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> None:
    csv_dir = out_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(csv_dir / f"{name}.csv", index=False, encoding="utf-8-sig")


def export_csv_urdu(tables: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> None:
    """Export tables with _ur columns only (for Urdu view)."""
    csv_ur_dir = out_dir / "csv_ur"
    csv_ur_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        if df.empty:
            continue
        # Keep ID/numeric columns + _ur columns
        ur_cols = [c for c in df.columns if c.endswith("_ur")]
        id_cols = [c for c in df.columns if c.endswith("_id") or c == "ts"]
        keep = list(dict.fromkeys(id_cols + ur_cols))
        keep = [c for c in keep if c in df.columns]
        if ur_cols:
            df[keep].to_csv(csv_ur_dir / f"{name}_ur.csv", index=False, encoding="utf-8-sig")


def export_json(tables: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> None:
    json_dir = out_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        if df.empty:
            continue
        records = df.to_dict(orient="records")
        # Convert timestamps to string
        for rec in records:
            for k, v in rec.items():
                if hasattr(v, "isoformat"):
                    rec[k] = v.isoformat()
        (json_dir / f"{name}.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def export_sqlite(tables: dict[str, pd.DataFrame], out_dir: pathlib.Path) -> pathlib.Path:
    """Write all tables to SQLite with proper types."""
    db_path = out_dir / "db.sqlite"
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        # Create schema with FK constraints
        conn.execute("PRAGMA foreign_keys = ON;")
        for name, df in tables.items():
            if df.empty:
                continue
            # Write dataframe; pandas infers types
            df_write = df.copy()
            # Convert timestamps to ISO strings for SQLite
            for col in df_write.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
                df_write[col] = df_write[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
            df_write.to_sql(name, conn, if_exists="replace", index=False)
    finally:
        conn.close()
    return db_path


def write_manifest(
    run_id: str,
    plan_dict: dict,
    dataset_hash: str,
    scores: dict,
    out_dir: pathlib.Path,
    table_shapes: dict[str, tuple[int, int]],
) -> None:
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan": plan_dict,
        "dataset_hash": dataset_hash,
        "scores": scores,
        "tables": {name: {"rows": s[0], "cols": s[1]} for name, s in table_shapes.items()},
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ──────────────────────────────────────────────
# Main export entry point
# ──────────────────────────────────────────────

def export_all(
    run_id: str,
    tables: dict[str, pd.DataFrame],
    plan_dict: dict,
    scores: dict,
    base_outputs: pathlib.Path = pathlib.Path("outputs"),
) -> pathlib.Path:
    """
    Export everything for a run. Returns the run output directory.
    """
    out_dir = base_outputs / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_hash = compute_dataset_hash(tables)

    export_csv(tables, out_dir)
    export_json(tables, out_dir)
    export_sqlite(tables, out_dir)

    table_shapes = {k: (len(v), len(v.columns)) for k, v in tables.items()}
    write_manifest(run_id, plan_dict, dataset_hash, scores, out_dir, table_shapes)

    return out_dir
