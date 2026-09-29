"""
tests/test_repro.py
Reproducibility: same seed + plan => same dataset hash.
Different seed => different dataset hash.
"""
import pytest

from engine.plan import Plan
from engine.generate import run_scenario


def _make_plan(seed: int) -> Plan:
    return Plan(seed=seed, users=10, devices=8, duration_days=3,
                difficulty="easy", domains=["auth"], language="en",
                generate_documents=False, use_llm=False)


def test_same_seed_same_hash(tmp_path):
    """Running the same plan twice must produce the same dataset hash."""
    plan = _make_plan(42)
    r1 = run_scenario(plan, output_base=tmp_path / "r1")
    r2 = run_scenario(plan, output_base=tmp_path / "r2")
    assert r1["dataset_hash"] == r2["dataset_hash"], (
        f"Hash mismatch!\nRun1: {r1['dataset_hash']}\nRun2: {r2['dataset_hash']}"
    )


def test_different_seed_different_hash(tmp_path):
    """Different seeds must produce different dataset hashes."""
    plan_a = _make_plan(42)
    plan_b = _make_plan(99)
    r_a = run_scenario(plan_a, output_base=tmp_path / "a")
    r_b = run_scenario(plan_b, output_base=tmp_path / "b")
    assert r_a["dataset_hash"] != r_b["dataset_hash"], (
        "Different seeds should produce different hashes"
    )
