"""
engine/evaluate/privacy.py
Empirical privacy risk indicators.
No guarantees — these are heuristic risk signals only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances


def exact_match_rate(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> float:
    """
    Fraction of synthetic rows that exactly match a real row.
    (Exact copy detection.)
    """
    if real_df.empty or synthetic_df.empty:
        return 0.0
    real_str = set(real_df.apply(lambda r: r.to_json(), axis=1).tolist())
    syn_strs = synthetic_df.apply(lambda r: r.to_json(), axis=1)
    matches = syn_strs.isin(real_str).sum()
    return float(matches / len(synthetic_df))


def _numeric_arrays(real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> tuple:
    """Get aligned numeric arrays from both DataFrames."""
    common = [c for c in real_df.select_dtypes(include=[np.number]).columns
              if c in synthetic_df.columns]
    if not common:
        return None, None
    R = real_df[common].fillna(0).values.astype(float)
    S = synthetic_df[common].fillna(0).values.astype(float)
    return R, S


def dcr_score(real_df: pd.DataFrame, synthetic_df: pd.DataFrame, sample_n: int = 500) -> float:
    """
    Distance to Closest Record (DCR) score.
    Mean min-distance from synthetic to real, normalized by real-to-real baseline.
    Higher is better (more private). Returns value in [0, ∞).
    """
    R, S = _numeric_arrays(real_df, synthetic_df)
    if R is None or len(R) < 2 or len(S) < 2:
        return float("nan")

    # Sample for speed
    r_idx = np.random.default_rng(42).choice(len(R), min(sample_n, len(R)), replace=False)
    s_idx = np.random.default_rng(43).choice(len(S), min(sample_n, len(S)), replace=False)
    R_s = R[r_idx]
    S_s = S[s_idx]

    # Synthetic -> real distances
    d_syn_real = pairwise_distances(S_s, R_s, metric="euclidean").min(axis=1).mean()

    # Real -> real (leave-one-out) baseline
    d_real_real = pairwise_distances(R_s, R_s, metric="euclidean")
    np.fill_diagonal(d_real_real, np.inf)
    d_rr = d_real_real.min(axis=1).mean()

    if d_rr == 0:
        return float("nan")
    return float(d_syn_real / d_rr)


def nearest_neighbor_ratio(
    real_df: pd.DataFrame, synthetic_df: pd.DataFrame, sample_n: int = 500
) -> float:
    """
    Nearest-neighbour adversarial accuracy proxy.
    Returns fraction of synthetic records closer to real than to synthetic (risk signal).
    Lower is better (< 0.5 suggests good privacy).
    """
    R, S = _numeric_arrays(real_df, synthetic_df)
    if R is None or len(R) < 2 or len(S) < 2:
        return float("nan")

    r_idx = np.random.default_rng(44).choice(len(R), min(sample_n, len(R)), replace=False)
    s_idx = np.random.default_rng(45).choice(len(S), min(sample_n, len(S)), replace=False)
    R_s = R[r_idx]
    S_s = S[s_idx]

    d_to_real = pairwise_distances(S_s, R_s, metric="euclidean").min(axis=1)
    d_to_syn = pairwise_distances(S_s, S_s, metric="euclidean")
    np.fill_diagonal(d_to_syn, np.inf)
    d_to_syn = d_to_syn.min(axis=1)

    closer_to_real = (d_to_real < d_to_syn).mean()
    return float(closer_to_real)


def synthetic_safety_lint(df: pd.DataFrame) -> list[str]:
    """
    Heuristic checks for unsafe synthetic content.
    Returns list of warning strings.
    """
    warnings: list[str] = []
    RESERVED_PREFIXES = ("10.", "192.168.", "203.0.113.", "198.51.100.", "192.0.2.")
    SAFE_DOMAINS = ("example.com", "example.org")

    for col in df.select_dtypes(include=["object"]).columns:
        vals = df[col].dropna().astype(str)
        # IP check
        looks_ip = vals.str.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        if looks_ip.any():
            bad_ips = vals[looks_ip & ~vals.apply(
                lambda ip: any(ip.startswith(p) for p in RESERVED_PREFIXES)
            )]
            if not bad_ips.empty:
                warnings.append(f"[{col}] Non-reserved IPs: {bad_ips.unique()[:3].tolist()}")
        # Email check
        looks_email = vals.str.contains("@", na=False)
        if looks_email.any():
            bad_emails = vals[looks_email & ~vals.apply(
                lambda e: any(e.endswith(d) for d in SAFE_DOMAINS)
            )]
            if not bad_emails.empty:
                warnings.append(f"[{col}] Non-safe emails: {bad_emails.unique()[:3].tolist()}")

    return warnings


def compute_privacy(
    real_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
) -> dict[str, float | list]:
    """
    Compute all empirical privacy risk indicators.
    Wording: these are risk indicators, NOT privacy guarantees.
    """
    scores: dict = {}

    if real_df is not None and not real_df.empty:
        scores["exact_match_rate"] = exact_match_rate(real_df, synthetic_df)
        scores["dcr_score"] = dcr_score(real_df, synthetic_df)
        scores["nn_ratio"] = nearest_neighbor_ratio(real_df, synthetic_df)
    else:
        scores["exact_match_rate"] = 0.0
        scores["dcr_score"] = float("nan")
        scores["nn_ratio"] = float("nan")
        scores["note"] = "No real data provided; exact_match_rate set to 0"

    scores["safety_warnings"] = synthetic_safety_lint(synthetic_df)
    return scores
