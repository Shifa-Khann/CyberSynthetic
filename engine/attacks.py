"""
engine/attacks.py
Attack scenario generators and hard-negative generators.
All randomness via engine.rng.RNGTree.

Scenarios implemented:
  T1110  - failed-login burst then success (brute force)
  T1078  - impossible travel (login from two distant countries)
  T1133  - new device at odd hour on privileged account
  T1566  - phishing email -> click -> encoded PowerShell placeholder
  T1098  - off-hours privilege change
  HN_*   - hard negatives (business travel, forgotten password, new laptop,
             admin patch window, newsletter click)
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from engine.rng import RNGTree
from engine.world import _gen_ip, _deterministic_id, GEO_COUNTRIES, GEO_CITIES

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

AUTH_METHODS = ["password", "mfa", "sso", "certificate"]
PROCESS_NAMES_ATK = [
    "powershell.exe", "cmd.exe", "wscript.exe", "mshta.exe",
    "regsvr32.exe", "rundll32.exe", "mimikatz.exe",
]
PARENT_PROCESSES_ATK = ["explorer.exe", "winword.exe", "outlook.exe"]


def _pick_privileged_user(users_df: pd.DataFrame, rng) -> pd.Series | None:
    priv_users = users_df[users_df["privilege_level"].isin(["admin", "superadmin"])]
    if priv_users.empty:
        priv_users = users_df
    idx = int(rng.integers(0, len(priv_users)))
    return priv_users.iloc[idx]


def _pick_device_for_user(devices_df: pd.DataFrame, user_id: str, rng) -> str | None:
    devs = devices_df[devices_df["owner_user_id"] == user_id]
    if devs.empty:
        devs = devices_df
    return devs.iloc[int(rng.integers(0, len(devs)))]["device_id"]


def _ts_offset(base: datetime, rng, min_min: int = 1, max_min: int = 30) -> datetime:
    return base + timedelta(minutes=int(rng.integers(min_min, max_min)))


# ──────────────────────────────────────────────
# Scenario: T1110 Brute-force then success
# ──────────────────────────────────────────────

def scenario_brute_force(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    difficulty: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = _pick_privileged_user(users_df, rng_a)
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    # pick a random time in the window
    day = int(rng_a.integers(0, duration_days))
    hour = int(rng_a.integers(0, 6))  # odd hours
    base_ts = start_time + timedelta(days=day, hours=hour)

    n_failures = {"easy": 3, "medium": 8, "hard": 20}.get(difficulty, 8)
    src_ip = _gen_ip(rng_a)
    records: list[dict] = []

    # failures
    for i in range(n_failures):
        ts = base_ts + timedelta(seconds=int(rng_a.integers(5, 60)) * i)
        eid = _deterministic_id("AEV", event_offset + len(records), plan_seed)
        records.append(
            {
                "event_id": eid,
                "ts": ts.isoformat(),
                "user_id": user["user_id"],
                "device_id": device_id,
                "src_ip": src_ip,
                "geo_country": "RU",
                "geo_city": "Moscow",
                "auth_method": "password",
                "outcome": "failure",
                "label": "malicious",
                "scenario_id": scenario_id,
            }
        )

    # success after bursts
    success_ts = base_ts + timedelta(seconds=int(rng_a.integers(300, 900)))
    eid = _deterministic_id("AEV", event_offset + len(records), plan_seed)
    records.append(
        {
            "event_id": eid,
            "ts": success_ts.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": src_ip,
            "geo_country": "RU",
            "geo_city": "Moscow",
            "auth_method": "password",
            "outcome": "success",
            "label": "malicious",
            "scenario_id": scenario_id,
        }
    )
    return pd.DataFrame(records)


# ──────────────────────────────────────────────
# Scenario: T1078 Impossible travel
# ──────────────────────────────────────────────

def scenario_impossible_travel(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    difficulty: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = users_df.iloc[int(rng_a.integers(0, len(users_df)))]
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    day = int(rng_a.integers(0, duration_days))
    hour = int(rng_a.integers(8, 18))
    ts1 = start_time + timedelta(days=day, hours=hour)
    # impossible: 30 minutes later from a different continent
    ts2 = ts1 + timedelta(minutes=int(rng_a.integers(10, 60)))

    records = [
        {
            "event_id": _deterministic_id("AEV", event_offset, plan_seed),
            "ts": ts1.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": _gen_ip(rng_a),
            "geo_country": user["home_country"],
            "geo_city": user["home_city"],
            "auth_method": "password",
            "outcome": "success",
            "label": "suspicious",
            "scenario_id": scenario_id,
        },
        {
            "event_id": _deterministic_id("AEV", event_offset + 1, plan_seed),
            "ts": ts2.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": _gen_ip(rng_a),
            "geo_country": "CN",
            "geo_city": "Beijing",
            "auth_method": "password",
            "outcome": "success",
            "label": "suspicious",
            "scenario_id": scenario_id,
        },
    ]
    return pd.DataFrame(records)


# ──────────────────────────────────────────────
# Scenario: T1133 New device odd hour (privileged)
# ──────────────────────────────────────────────

def scenario_new_device_odd_hour(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    difficulty: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = _pick_privileged_user(users_df, rng_a)

    day = int(rng_a.integers(1, duration_days))
    hour = int(rng_a.integers(1, 5))  # 1-4am
    ts = start_time + timedelta(days=day, hours=hour)

    # unassigned/other device from devices_df
    new_device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)
    src_ip = _gen_ip(rng_a)

    records = [
        {
            "event_id": _deterministic_id("AEV", event_offset, plan_seed),
            "ts": ts.isoformat(),
            "user_id": user["user_id"],
            "device_id": new_device_id,
            "src_ip": src_ip,
            "geo_country": user["home_country"],
            "geo_city": user["home_city"],
            "auth_method": "password",
            "outcome": "success",
            "label": "suspicious",
            "scenario_id": scenario_id,
        }
    ]
    return pd.DataFrame(records)


# ──────────────────────────────────────────────
# Scenario: T1566 Phishing kill chain
# ──────────────────────────────────────────────

def scenario_phishing_killchain(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    difficulty: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (auth_events, emails, email_events, process_events)."""
    rng_a = rng.child("attacks")
    user = users_df.iloc[int(rng_a.integers(0, len(users_df)))]
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    day = int(rng_a.integers(1, duration_days))
    hour = int(rng_a.integers(9, 17))
    ts_phish = start_time + timedelta(days=day, hours=hour)

    # phishing email
    email_id = _deterministic_id("EML", event_offset, plan_seed)
    emails = [
        {
            "email_id": email_id,
            "ts": ts_phish.isoformat(),
            "sender": "attacker@malicious.example.org",
            "recipient_user_id": user["user_id"],
            "subject": "Urgent: Reset your password immediately",
            "body_text": "[SYNTHETIC PHISHING BODY - no real payload]",
            "language": "en",
            "label": "malicious",
            "scenario_id": scenario_id,
        }
    ]
    # email events: delivered -> clicked
    ts_click = ts_phish + timedelta(minutes=int(rng_a.integers(5, 30)))
    email_events = [
        {
            "email_event_id": _deterministic_id("EEV", event_offset, plan_seed),
            "email_id": email_id,
            "user_id": user["user_id"],
            "ts": ts_phish.isoformat(),
            "event_type": "delivered",
        },
        {
            "email_event_id": _deterministic_id("EEV", event_offset + 1, plan_seed),
            "email_id": email_id,
            "user_id": user["user_id"],
            "ts": ts_click.isoformat(),
            "event_type": "clicked",
        },
    ]
    # process: encoded powershell placeholder
    ts_proc = ts_click + timedelta(minutes=int(rng_a.integers(1, 10)))
    process_events = [
        {
            "event_id": _deterministic_id("PEV", event_offset, plan_seed),
            "ts": ts_proc.isoformat(),
            "device_id": device_id,
            "user_id": user["user_id"],
            "process_name": "powershell.exe",
            "parent_process": "outlook.exe",
            "command_line": "powershell.exe -enc <SYNTHETIC_BLOB>",
            "label": "malicious",
            "scenario_id": scenario_id,
        }
    ]
    # new-IP auth after phish
    ts_auth = ts_proc + timedelta(minutes=int(rng_a.integers(5, 30)))
    auth_events = [
        {
            "event_id": _deterministic_id("AEV", event_offset, plan_seed),
            "ts": ts_auth.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": _gen_ip(rng_a),
            "geo_country": "NG",
            "geo_city": "Lagos",
            "auth_method": "password",
            "outcome": "success",
            "label": "malicious",
            "scenario_id": scenario_id,
        }
    ]
    return (
        pd.DataFrame(auth_events),
        pd.DataFrame(emails),
        pd.DataFrame(email_events),
        pd.DataFrame(process_events),
    )


# ──────────────────────────────────────────────
# Scenario: T1098 Off-hours privilege change
# ──────────────────────────────────────────────

def scenario_offhours_privilege(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    difficulty: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = users_df.iloc[int(rng_a.integers(0, len(users_df)))]
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    day = int(rng_a.integers(1, duration_days))
    hour = int(rng_a.integers(1, 5))
    ts = start_time + timedelta(days=day, hours=hour)

    records = [
        {
            "event_id": _deterministic_id("AEV", event_offset, plan_seed),
            "ts": ts.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": _gen_ip(rng_a),
            "geo_country": user["home_country"],
            "geo_city": user["home_city"],
            "auth_method": "password",
            "outcome": "success",
            "label": "suspicious",
            "scenario_id": scenario_id,
        }
    ]
    return pd.DataFrame(records)


# ──────────────────────────────────────────────
# Hard negatives
# ──────────────────────────────────────────────

def hard_negative_business_travel(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = users_df.iloc[int(rng_a.integers(0, len(users_df)))]
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    day = int(rng_a.integers(1, duration_days))
    hour = int(rng_a.integers(8, 18))
    ts = start_time + timedelta(days=day, hours=hour)
    # foreign country but legitimate
    countries = [c for c in GEO_COUNTRIES if c != user["home_country"]]
    country = countries[int(rng_a.integers(0, len(countries)))]
    cities = GEO_CITIES.get(country, ["Unknown"])
    city = cities[int(rng_a.integers(0, len(cities)))]

    records = [
        {
            "event_id": _deterministic_id("AEV", event_offset, plan_seed),
            "ts": ts.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": _gen_ip(rng_a),
            "geo_country": country,
            "geo_city": city,
            "auth_method": "mfa",
            "outcome": "success",
            "label": "normal",
            "scenario_id": scenario_id,
        }
    ]
    return pd.DataFrame(records)


def hard_negative_forgotten_password(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    scenario_id: str,
    rng: RNGTree,
    event_offset: int = 0,
) -> pd.DataFrame:
    rng_a = rng.child("attacks")
    user = users_df.iloc[int(rng_a.integers(0, len(users_df)))]
    device_id = _pick_device_for_user(devices_df, user["user_id"], rng_a)

    day = int(rng_a.integers(1, duration_days))
    hour = int(rng_a.integers(8, 18))
    base_ts = start_time + timedelta(days=day, hours=hour)
    src_ip = _gen_ip(rng_a)

    records: list[dict] = []
    # 2-4 failures (forgot password), then success via password reset
    for i in range(int(rng_a.integers(2, 5))):
        ts = base_ts + timedelta(seconds=30 * i)
        records.append(
            {
                "event_id": _deterministic_id("AEV", event_offset + i, plan_seed),
                "ts": ts.isoformat(),
                "user_id": user["user_id"],
                "device_id": device_id,
                "src_ip": src_ip,
                "geo_country": user["home_country"],
                "geo_city": user["home_city"],
                "auth_method": "password",
                "outcome": "failure",
                "label": "normal",
                "scenario_id": scenario_id,
            }
        )
    # reset success
    ts_reset = base_ts + timedelta(minutes=int(rng_a.integers(5, 20)))
    records.append(
        {
            "event_id": _deterministic_id("AEV", event_offset + 10, plan_seed),
            "ts": ts_reset.isoformat(),
            "user_id": user["user_id"],
            "device_id": device_id,
            "src_ip": src_ip,
            "geo_country": user["home_country"],
            "geo_city": user["home_city"],
            "auth_method": "token",
            "outcome": "success",
            "label": "normal",
            "scenario_id": scenario_id,
        }
    )
    return pd.DataFrame(records)


# ──────────────────────────────────────────────
# Top-level: build all attack + hard-negative events
# ──────────────────────────────────────────────

def generate_attacks(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    start_time: datetime,
    duration_days: int,
    plan_seed: int,
    difficulty: str,
    domains: list[str],
    rng: RNGTree,
) -> dict[str, pd.DataFrame]:
    """
    Generate all attack and hard-negative events.
    Returns dict with keys matching schema tables.
    """
    all_auth: list[pd.DataFrame] = []
    all_emails: list[pd.DataFrame] = []
    all_email_events: list[pd.DataFrame] = []
    all_process_events: list[pd.DataFrame] = []

    scenarios = [
        ("SCN-T1110", "brute_force"),
        ("SCN-T1078", "impossible_travel"),
        ("SCN-T1133", "new_device"),
        ("SCN-T1098", "offhours_priv"),
    ]
    if "email" in domains or "endpoint" in domains:
        scenarios.append(("SCN-T1566", "phishing"))

    offset = 50000  # offset to avoid ID collisions with background

    for scn_id, scn_name in scenarios:
        if scn_name == "brute_force":
            df = scenario_brute_force(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, difficulty, rng, offset
            )
            all_auth.append(df)
        elif scn_name == "impossible_travel":
            df = scenario_impossible_travel(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, difficulty, rng, offset
            )
            all_auth.append(df)
        elif scn_name == "new_device":
            df = scenario_new_device_odd_hour(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, difficulty, rng, offset
            )
            all_auth.append(df)
        elif scn_name == "offhours_priv":
            df = scenario_offhours_privilege(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, difficulty, rng, offset
            )
            all_auth.append(df)
        elif scn_name == "phishing":
            a, e, ee, pe = scenario_phishing_killchain(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, difficulty, rng, offset
            )
            all_auth.append(a)
            all_emails.append(e)
            all_email_events.append(ee)
            all_process_events.append(pe)
        offset += 100

    # Hard negatives
    hn_scenarios = [
        ("HN-BT", "biz_travel"),
        ("HN-FP", "forgotten_pw"),
    ]
    for scn_id, scn_name in hn_scenarios:
        if scn_name == "biz_travel":
            df = hard_negative_business_travel(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, rng, offset
            )
            all_auth.append(df)
        elif scn_name == "forgotten_pw":
            df = hard_negative_forgotten_password(
                users_df, devices_df, start_time, duration_days,
                plan_seed, scn_id, rng, offset
            )
            all_auth.append(df)
        offset += 100

    def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame()
        return pd.concat([f for f in frames if not f.empty], ignore_index=True)

    return {
        "auth_events": _concat(all_auth),
        "emails": _concat(all_emails),
        "email_events": _concat(all_email_events),
        "process_events": _concat(all_process_events),
    }
