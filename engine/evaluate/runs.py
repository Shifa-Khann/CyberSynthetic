"""
engine/evaluate/runs.py
Scorecard row storage: writes one row per run to outputs/runs.json.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any

_RUNS_FILE = pathlib.Path("outputs") / "runs.json"


def load_runs() -> list[dict]:
    """Load all historical runs from the runs file."""
    if not _RUNS_FILE.exists():
        return []
    try:
        with open(_RUNS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_run(
    run_id: str,
    seed: int,
    plan_hash: str,
    dataset_hash: str,
    mode: str,
    calibration_source: str,
    scores: dict[str, Any],
    table_shapes: dict[str, tuple[int, int]],
) -> dict:
    """
    Append a scorecard row to runs.json.
    Returns the saved row dict.
    """
    runs = load_runs()

    row = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "plan_hash": plan_hash,
        "dataset_hash": dataset_hash,
        "mode": mode,
        "calibration_source": calibration_source,
        "scores": scores,
        "table_shapes": {k: list(v) for k, v in table_shapes.items()},
    }

    runs.append(row)

    _RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RUNS_FILE, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2, default=str)

    return row


def get_runs_df() -> "pd.DataFrame":
    """Return runs history as a flattened DataFrame for display."""
    import pandas as pd

    runs = load_runs()
    if not runs:
        return pd.DataFrame()

    rows = []
    for r in runs:
        flat = {
            "run_id": r["run_id"],
            "created_at": r["created_at"],
            "seed": r["seed"],
            "mode": r["mode"],
            "dataset_hash": r.get("dataset_hash", ""),
            "calibration_source": r.get("calibration_source", ""),
        }
        scores = r.get("scores", {})
        flat.update({f"score_{k}": v for k, v in scores.items() if isinstance(v, (int, float))})
        rows.append(flat)

    return pd.DataFrame(rows)
