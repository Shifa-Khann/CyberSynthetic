"""
engine/evaluate/fidelity.py
Statistical fidelity metrics: KS complement, TV complement, correlation similarity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def ks_complement(real: pd.Series, synthetic: pd.Series) -> float:
    """
    1 - KS statistic. Higher = more similar distributions.
    Returns value in [0, 1].
    """
    r = real.dropna().to_numpy(dtype=float)
    s = synthetic.dropna().to_numpy(dtype=float)
    if len(r) < 2 or len(s) < 2:
        return 1.0
    stat, _ = stats.ks_2samp(r, s)
    return float(1.0 - stat)


def tv_complement(real: pd.Series, synthetic: pd.Series) -> float:
    """
    1 - Total Variation distance for categorical columns.
    Returns value in [0, 1].
    """
    r_counts = real.value_counts(normalize=True)
    s_counts = synthetic.value_counts(normalize=True)
    all_cats = set(r_counts.index) | set(s_counts.index)
    tv = 0.5 * sum(
        abs(r_counts.get(c, 0.0) - s_counts.get(c, 0.0)) for c in all_cats
    )
    return float(1.0 - tv)


def correlation_similarity(
    real: pd.DataFrame, synthetic: pd.DataFrame, numeric_cols: list[str]
) -> float:
    """
    Mean absolute difference of pairwise correlation matrices.
    Returns 1 - mean_abs_diff (higher = more similar).
    """
    cols = [c for c in numeric_cols if c in real.columns and c in synthetic.columns]
    if len(cols) < 2:
        return 1.0
    r_corr = real[cols].corr().values
    s_corr = synthetic[cols].corr().values
    mask = ~(np.isnan(r_corr) | np.isnan(s_corr))
    if mask.sum() == 0:
        return 1.0
    mean_diff = np.abs(r_corr[mask] - s_corr[mask]).mean()
    return float(1.0 - mean_diff)


def compute_fidelity(
    real_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
) -> dict[str, float]:
    """
    Compute fidelity metrics between real and synthetic DataFrames.
    Returns dict with per-column and aggregate scores.
    """
    scores: dict[str, float] = {}

    numeric_cols = real_df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = real_df.select_dtypes(include=["object", "category"]).columns.tolist()

    ks_scores: list[float] = []
    tv_scores: list[float] = []

    for col in numeric_cols:
        if col in synthetic_df.columns:
            s = ks_complement(real_df[col], synthetic_df[col])
            scores[f"ks_{col}"] = s
            ks_scores.append(s)

    for col in categorical_cols:
        if col in synthetic_df.columns:
            s = tv_complement(real_df[col], synthetic_df[col])
            scores[f"tv_{col}"] = s
            tv_scores.append(s)

    scores["ks_mean"] = float(np.mean(ks_scores)) if ks_scores else 1.0
    scores["tv_mean"] = float(np.mean(tv_scores)) if tv_scores else 1.0
    scores["corr_sim"] = correlation_similarity(real_df, synthetic_df, numeric_cols)
    scores["fidelity_overall"] = float(
        np.mean([scores["ks_mean"], scores["tv_mean"], scores["corr_sim"]])
    )

    return scores


evaluate_fidelity = compute_fidelity
