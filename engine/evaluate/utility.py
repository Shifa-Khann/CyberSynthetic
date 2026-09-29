"""
engine/evaluate/utility.py
Utility evaluation: TSTR, TRTS, TRTR via F1, PR-AUC, AUROC.
Label-leaking columns are excluded per AGENTS.md rule 9.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score,
    average_precision_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Columns that must be excluded from utility evaluation (label leakage)
LABEL_LEAKING_COLS = {
    "alert_type", "scenario_id", "label", "incident_id",
    "alert_id", "event_id", "email_id", "email_event_id",
}


def _prepare_features(df: pd.DataFrame, target_col: str) -> tuple[np.ndarray, np.ndarray]:
    """One-hot encode categoricals, drop leaking cols, return (X, y)."""
    df = df.copy()
    drop_cols = (LABEL_LEAKING_COLS - {target_col}) & set(df.columns)
    df = df.drop(columns=list(drop_cols), errors="ignore")

    # Encode target
    le = LabelEncoder()
    y = le.fit_transform(df[target_col].fillna("normal").astype(str))
    df = df.drop(columns=[target_col])

    # Drop string ID-like cols
    id_cols = [c for c in df.columns if c.endswith("_id") or c == "ts"]
    df = df.drop(columns=id_cols, errors="ignore")

    # One-hot categorical
    cat_cols = df.select_dtypes(include=["object", "category"]).columns
    df = pd.get_dummies(df, columns=cat_cols.tolist(), drop_first=True)

    # Fill NAs
    df = df.fillna(0)

    return df.values.astype(float), y


def _clf_metrics(X_train: np.ndarray, y_train: np.ndarray,
                  X_test: np.ndarray, y_test: np.ndarray) -> dict[str, float]:
    """Train RF, return F1, PR-AUC, AUROC."""
    clf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1, max_depth=6)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    # For binary: use average="binary"; multiclass: "macro"
    n_classes = len(np.unique(y_train))
    avg = "binary" if n_classes == 2 else "macro"

    f1 = f1_score(y_test, y_pred, average=avg, zero_division=0)

    try:
        if n_classes == 2:
            y_prob = clf.predict_proba(X_test)[:, 1]
            pr_auc = average_precision_score(y_test, y_prob)
            auroc = roc_auc_score(y_test, y_prob)
        else:
            y_prob = clf.predict_proba(X_test)
            pr_auc = average_precision_score(y_test, y_prob, average="macro", multi_class="ovr")
            auroc = roc_auc_score(y_test, y_prob, average="macro", multi_class="ovr")
    except Exception:
        pr_auc = float("nan")
        auroc = float("nan")

    return {"f1": float(f1), "pr_auc": float(pr_auc), "auroc": float(auroc)}


def compute_utility(
    synthetic_df: pd.DataFrame,
    real_df: pd.DataFrame | None = None,
    target_col: str = "label",
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict[str, float | str]:
    """
    Compute TSTR, TRTS, TRTR utility scores.

    TSTR: Train on Synthetic, Test on Real
    TRTS: Train on Real, Test on Synthetic
    TRTR: Train on Real subset, Test on Real holdout (baseline)

    If real_df is None, TSTR/TRTS use a differently-seeded split of synthetic as proxy.
    Returns dict with scores and a reference_source label.
    """
    scores: dict[str, float | str] = {}

    if target_col not in synthetic_df.columns:
        return {"error": f"Target column '{target_col}' not in synthetic data"}

    # Drop rows with null target
    syn = synthetic_df.dropna(subset=[target_col])
    if len(syn) < 20:
        return {"error": "Too few rows for utility evaluation (need >= 20)"}

    X_syn, y_syn = _prepare_features(syn, target_col)

    # TRTR (real baseline)
    if real_df is not None and target_col in real_df.columns:
        real = real_df.dropna(subset=[target_col])
        if len(real) >= 20:
            X_real, y_real = _prepare_features(real, target_col)
            # align columns
            X_real_tr, X_real_te, y_real_tr, y_real_te = train_test_split(
                X_real, y_real, test_size=test_size, random_state=random_state, stratify=None
            )
            trtr = _clf_metrics(X_real_tr, y_real_tr, X_real_te, y_real_te)
            for k, v in trtr.items():
                scores[f"trtr_{k}"] = v

            # TSTR: train synthetic, test real
            X_syn_tr, _, y_syn_tr, _ = train_test_split(
                X_syn, y_syn, test_size=test_size, random_state=random_state, stratify=None
            )
            # align feature dims
            n_feat = min(X_syn_tr.shape[1], X_real_te.shape[1])
            tstr = _clf_metrics(X_syn_tr[:, :n_feat], y_syn_tr, X_real_te[:, :n_feat], y_real_te)
            for k, v in tstr.items():
                scores[f"tstr_{k}"] = v

            # TSTR/TRTR ratio
            if trtr["f1"] > 0:
                scores["tstr_trtr_ratio"] = float(tstr["f1"] / trtr["f1"])

            # TRTS: train real, test synthetic
            X_syn_te = X_syn[:len(X_real_te)]
            y_syn_te = y_syn[:len(y_real_te)]
            n_feat2 = min(X_real_tr.shape[1], X_syn_te.shape[1])
            trts = _clf_metrics(X_real_tr[:, :n_feat2], y_real_tr, X_syn_te[:, :n_feat2], y_syn_te)
            for k, v in trts.items():
                scores[f"trts_{k}"] = v

            scores["reference_source"] = "real_upload"
        else:
            real_df = None  # fall through to proxy

    if real_df is None or (isinstance(real_df, pd.DataFrame) and len(real_df) < 20):
        # Proxy: split synthetic with different seed
        X_tr, X_te, y_tr, y_te = train_test_split(
            X_syn, y_syn, test_size=test_size, random_state=random_state, stratify=None
        )
        proxy = _clf_metrics(X_tr, y_tr, X_te, y_te)
        for k, v in proxy.items():
            scores[f"tstr_{k}"] = v
            scores[f"trtr_{k}"] = v
        scores["tstr_trtr_ratio"] = 1.0
        scores["reference_source"] = "proxy (no real data)"

    return scores
