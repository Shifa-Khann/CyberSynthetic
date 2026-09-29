"""
tests/test_integrity.py
PK uniqueness, FK validity, temporal order, derived values, safety checks.
"""
from datetime import datetime

import pandas as pd
import pytest

from engine.plan import Plan
from engine.rng import make_rng_tree
from engine.world import generate_users, generate_devices
from engine.background import generate_auth_events
from engine.attacks import generate_attacks
from engine.detect import generate_alerts, correlate_incidents, generate_indicators
from engine.validate import validate_dataset, ValidationResult


@pytest.fixture(scope="module")
def small_dataset():
    """Generate a small but complete dataset for testing."""
    plan = Plan(seed=42, users=10, devices=8, duration_days=3, difficulty="easy",
                domains=["auth"], language="en")
    rng = make_rng_tree(plan.seed)
    start = datetime(2024, 1, 1)

    users_df = generate_users(plan.seed, plan.users, rng)
    devices_df = generate_devices(plan.seed, plan.devices, users_df, rng)
    auth_bg = generate_auth_events(users_df, devices_df, plan.seed, plan.duration_days, start, rng)
    attack_tables = generate_attacks(
        users_df, devices_df, start, plan.duration_days, plan.seed,
        plan.difficulty, plan.domains, rng
    )
    auth_df = pd.concat([auth_bg, attack_tables.get("auth_events", pd.DataFrame())], ignore_index=True)
    if not auth_df.empty and "ts" in auth_df.columns:
        auth_df["ts"] = auth_df["ts"].astype(str)
        auth_df.sort_values("ts", inplace=True)
        auth_df.reset_index(drop=True, inplace=True)
    alerts_df = generate_alerts(pd.DataFrame() if auth_df.empty else auth_df,
                                pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
                                users_df, devices_df, plan.seed, rng)
    incidents_df, alerts_df = correlate_incidents(alerts_df, plan.seed, rng)
    indicators_df = generate_indicators(incidents_df, alerts_df, auth_df, plan.seed)

    return {
        "users": users_df,
        "devices": devices_df,
        "auth": auth_df,
        "alerts": alerts_df,
        "incidents": incidents_df,
        "indicators": indicators_df,
    }


def test_user_pk_unique(small_dataset):
    users = small_dataset["users"]
    assert users["user_id"].nunique() == len(users), "user_id must be unique"


def test_device_pk_unique(small_dataset):
    devices = small_dataset["devices"]
    assert devices["device_id"].nunique() == len(devices), "device_id must be unique"


def test_auth_event_pk_unique(small_dataset):
    auth = small_dataset["auth"]
    assert auth["event_id"].nunique() == len(auth), "auth event_id must be unique"


def test_device_fk_to_users(small_dataset):
    devices = small_dataset["devices"]
    users = small_dataset["users"]
    valid_user_ids = set(users["user_id"])
    assert devices["owner_user_id"].isin(valid_user_ids).all(), \
        "All device owner_user_ids must reference valid users"


def test_auth_event_user_fk(small_dataset):
    auth = small_dataset["auth"]
    users = small_dataset["users"]
    valid_user_ids = set(users["user_id"])
    assert auth["user_id"].isin(valid_user_ids).all(), \
        "All auth event user_ids must reference valid users"


def test_alert_pk_unique(small_dataset):
    alerts = small_dataset["alerts"]
    if alerts.empty:
        pytest.skip("No alerts generated")
    assert alerts["alert_id"].nunique() == len(alerts), "alert_id must be unique"


def test_temporal_order(small_dataset):
    """Alert ts must be >= source event ts."""
    auth = small_dataset["auth"]
    alerts = small_dataset["alerts"]
    if alerts.empty or auth.empty:
        pytest.skip("Not enough data for temporal check")

    merged = alerts.merge(
        auth[["event_id", "ts"]].rename(columns={"ts": "event_ts"}),
        left_on="source_event_id",
        right_on="event_id",
        how="inner",
    )
    if merged.empty:
        pytest.skip("No matching event IDs to check")

    merged["ts"] = pd.to_datetime(merged["ts"])
    merged["event_ts"] = pd.to_datetime(merged["event_ts"])
    bad = merged[merged["ts"] < merged["event_ts"]]
    assert len(bad) == 0, f"Found {len(bad)} alerts with ts < source event ts"


def test_reserved_ips(small_dataset):
    auth = small_dataset["auth"]
    RESERVED = ("10.", "192.168.", "203.0.113.", "198.51.100.", "192.0.2.")
    bad = auth[~auth["src_ip"].apply(lambda ip: any(ip.startswith(p) for p in RESERVED))]
    assert len(bad) == 0, f"Non-reserved IPs found: {bad['src_ip'].unique()[:5].tolist()}"


def test_validate_dataset_passes(small_dataset):
    d = small_dataset
    result: ValidationResult = validate_dataset(
        d["users"], d["devices"], d["auth"],
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
        d["alerts"], d["incidents"], d["indicators"],
    )
    assert result.passed, f"Validation failed:\n{result}"
