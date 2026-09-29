"""
tests/test_eval.py
Tests for quality evaluation metrics: fidelity, utility (TSTR/TRTS/TRTR), and privacy risk.
"""
import numpy as np
import pandas as pd
import pytest

from engine.evaluate.fidelity import compute_fidelity
from engine.evaluate.utility import compute_utility
from engine.evaluate.privacy import compute_privacy


@pytest.fixture
def real_and_syn_dfs():
    np.random.seed(42)
    n = 100
    real_df = pd.DataFrame({
        "user_id": [f"U{i:03d}" for i in range(n)],
        "age": np.random.randint(20, 60, size=n),
        "score": np.random.uniform(0, 100, size=n),
        "dept": np.random.choice(["IT", "HR", "Sales"], size=n),
        "is_alert": np.random.choice([0, 1], size=n, p=[0.8, 0.2]),
    })

    syn_df = pd.DataFrame({
        "user_id": [f"U{i:03d}" for i in range(n)],
        "age": np.random.randint(20, 60, size=n),
        "score": np.random.uniform(0, 100, size=n),
        "dept": np.random.choice(["IT", "HR", "Sales"], size=n),
        "is_alert": np.random.choice([0, 1], size=n, p=[0.75, 0.25]),
    })
    return real_df, syn_df


def test_fidelity_metrics(real_and_syn_dfs):
    real_df, syn_df = real_and_syn_dfs
    metrics = compute_fidelity(real_df, syn_df)
    assert "fidelity_overall" in metrics
    assert 0.0 <= metrics["fidelity_overall"] <= 1.0


def test_utility_metrics(real_and_syn_dfs):
    real_df, syn_df = real_and_syn_dfs
    res = compute_utility(syn_df, real_df, target_col="is_alert")
    assert "tstr_f1" in res
    assert "trtr_f1" in res


def test_privacy_metrics(real_and_syn_dfs):
    real_df, syn_df = real_and_syn_dfs
    priv = compute_privacy(real_df, syn_df)
    assert "exact_match_rate" in priv
    assert "dcr_score" in priv
