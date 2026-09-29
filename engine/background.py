"""
engine/background.py
Generate normal background auth/email/endpoint events.
All randomness via engine.rng.RNGTree.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from engine.rng import RNGTree
from engine.world import _gen_ip, _deterministic_id

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

AUTH_METHODS = ["password", "mfa", "sso", "certificate", "token"]
GEO_COUNTRIES = ["US", "CA", "GB", "DE", "AU", "SG", "FR", "IN"]
GEO_CITIES = {
    "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    "CA": ["Toronto", "Vancouver", "Montreal"],
    "GB": ["London", "Manchester", "Edinburgh"],
    "DE": ["Berlin", "Munich", "Hamburg"],
    "AU": ["Sydney", "Melbourne", "Brisbane"],
    "SG": ["Singapore"],
    "FR": ["Paris", "Lyon"],
    "IN": ["Mumbai", "Delhi", "Bangalore"],
}

PROCESS_NAMES_NORMAL = [
    "explorer.exe", "chrome.exe", "outlook.exe", "teams.exe",
    "python.exe", "svchost.exe", "lsass.exe", "winword.exe",
    "excel.exe", "slack.exe", "zoom.exe", "code.exe",
    "bash", "python3", "systemd", "sshd", "cron",
]

PARENT_PROCESSES = [
    "explorer.exe", "services.exe", "svchost.exe", "bash", "init", "systemd"
]

EMAIL_SUBJECTS_NORMAL = [
    "Q{q} all-hands recap",
    "Project {p} update",
    "Team lunch on {day}",
    "New hire announcement",
    "HR policy reminder",
    "Budget approval request",
    "Weekly standup notes",
    "System maintenance window",
]


def _random_ts(
    rng, start: datetime, end: datetime, hour_profile: list[float]
) -> datetime:
    """Sample a random timestamp weighted by hour_profile."""
    # pick day
    delta_days = (end - start).days
    day_offset = int(rng.integers(0, max(delta_days, 1)))
    # pick hour using profile
    hour = int(rng.choice(24, p=hour_profile))
    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))
    ts = start + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
    return ts


def generate_auth_events(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    plan_seed: int,
    duration_days: int,
    start_time: datetime,
    rng: RNGTree,
) -> pd.DataFrame:
    """Generate normal authentication events for all users."""
    rng_bg = rng.child("background")
    end_time = start_time + timedelta(days=duration_days)

    records: list[dict] = []
    user_device_map: dict[str, list[str]] = {}

    # build user -> devices map
    for _, dev in devices_df.iterrows():
        uid = dev["owner_user_id"]
        user_device_map.setdefault(uid, []).append(dev["device_id"])

    all_device_ids = devices_df["device_id"].tolist()

    for idx, user in users_df.iterrows():
        uid = user["user_id"]
        hour_profile = user["_hour_profile"]
        events_per_day = user["_events_per_day"]
        n_events = int(rng_bg.poisson(events_per_day * duration_days))

        owned_devs = user_device_map.get(uid, [])
        if not owned_devs:
            # assign a random device if user has none
            owned_devs = [all_device_ids[int(rng_bg.integers(0, len(all_device_ids)))]]

        for j in range(n_events):
            ts = _random_ts(rng_bg, start_time, end_time, hour_profile)
            # 90% from home country, 10% roaming
            if rng_bg.random() < 0.90:
                country = user["home_country"]
                cities = GEO_CITIES.get(country, ["Unknown"])
                city = cities[int(rng_bg.integers(0, len(cities)))]
            else:
                country = GEO_COUNTRIES[int(rng_bg.integers(0, len(GEO_COUNTRIES)))]
                cities = GEO_CITIES.get(country, ["Unknown"])
                city = cities[int(rng_bg.integers(0, len(cities)))]

            # 95% use own device, 5% shared
            if rng_bg.random() < 0.95 and owned_devs:
                device_id = owned_devs[int(rng_bg.integers(0, len(owned_devs)))]
            else:
                device_id = all_device_ids[int(rng_bg.integers(0, len(all_device_ids)))]

            method = AUTH_METHODS[int(rng_bg.integers(0, len(AUTH_METHODS)))]
            # failure rate 2-5%
            fail_rate = rng_bg.uniform(0.02, 0.05)
            outcome = "failure" if rng_bg.random() < fail_rate else "success"
            src_ip = _gen_ip(rng_bg)

            event_id = _deterministic_id("AEV", len(records), plan_seed)
            records.append(
                {
                    "event_id": event_id,
                    "ts": ts.isoformat(),
                    "user_id": uid,
                    "device_id": device_id,
                    "src_ip": src_ip,
                    "geo_country": country,
                    "geo_city": city,
                    "auth_method": method,
                    "outcome": outcome,
                    "label": "normal",
                    "scenario_id": None,
                }
            )

    df = pd.DataFrame(records)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts").reset_index(drop=True)
    return df


def generate_email_events(
    users_df: pd.DataFrame,
    plan_seed: int,
    duration_days: int,
    start_time: datetime,
    rng: RNGTree,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate normal email + email_events records."""
    rng_bg = rng.child("background")
    end_time = start_time + timedelta(days=duration_days)
    user_ids = users_df["user_id"].tolist()

    emails: list[dict] = []
    email_events: list[dict] = []

    QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
    PROJECTS = ["Alpha", "Beta", "Gamma", "Delta"]
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for idx, user in users_df.iterrows():
        uid = user["user_id"]
        hour_profile = user["_hour_profile"]
        # ~2 emails received per day
        n_emails = int(rng_bg.poisson(2 * duration_days))
        for j in range(n_emails):
            ts = _random_ts(rng_bg, start_time, end_time, hour_profile)
            # sender is a random other user or external
            if rng_bg.random() < 0.6 and len(user_ids) > 1:
                other_ids = [u for u in user_ids if u != uid]
                sender_user = other_ids[int(rng_bg.integers(0, len(other_ids)))]
                sender_row = users_df[users_df["user_id"] == sender_user].iloc[0]
                sender_addr = sender_row["email"]
            else:
                sender_addr = f"external{rng_bg.integers(1,999)}@example.org"

            subj_tmpl = EMAIL_SUBJECTS_NORMAL[int(rng_bg.integers(0, len(EMAIL_SUBJECTS_NORMAL)))]
            subject = subj_tmpl.format(
                q=QUARTERS[int(rng_bg.integers(0, 4))],
                p=PROJECTS[int(rng_bg.integers(0, 4))],
                day=DAYS[int(rng_bg.integers(0, 5))],
            )
            email_id = _deterministic_id("EML", len(emails), plan_seed)
            emails.append(
                {
                    "email_id": email_id,
                    "ts": ts.isoformat(),
                    "sender": sender_addr,
                    "recipient_user_id": uid,
                    "subject": subject,
                    "body_text": f"[Normal email body placeholder - {subject}]",
                    "language": "en",
                    "label": "normal",
                    "scenario_id": None,
                }
            )
            # email events: delivered + maybe opened
            ev_id = _deterministic_id("EEV", len(email_events), plan_seed)
            email_events.append(
                {
                    "email_event_id": ev_id,
                    "email_id": email_id,
                    "user_id": uid,
                    "ts": ts.isoformat(),
                    "event_type": "delivered",
                }
            )
            if rng_bg.random() < 0.60:
                open_ts = ts + timedelta(minutes=int(rng_bg.integers(1, 120)))
                ev_id2 = _deterministic_id("EEV", len(email_events), plan_seed)
                email_events.append(
                    {
                        "email_event_id": ev_id2,
                        "email_id": email_id,
                        "user_id": uid,
                        "ts": open_ts.isoformat(),
                        "event_type": "opened",
                    }
                )

    emails_df = pd.DataFrame(emails)
    email_ev_df = pd.DataFrame(email_events)
    if not emails_df.empty:
        emails_df["ts"] = pd.to_datetime(emails_df["ts"])
        emails_df = emails_df.sort_values("ts").reset_index(drop=True)
    if not email_ev_df.empty:
        email_ev_df["ts"] = pd.to_datetime(email_ev_df["ts"])
        email_ev_df = email_ev_df.sort_values("ts").reset_index(drop=True)
    return emails_df, email_ev_df


def generate_process_events(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    plan_seed: int,
    duration_days: int,
    start_time: datetime,
    rng: RNGTree,
) -> pd.DataFrame:
    """Generate normal endpoint process events."""
    rng_bg = rng.child("background")
    end_time = start_time + timedelta(days=duration_days)

    user_device_map: dict[str, list[str]] = {}
    for _, dev in devices_df.iterrows():
        user_device_map.setdefault(dev["owner_user_id"], []).append(dev["device_id"])
    all_device_ids = devices_df["device_id"].tolist()

    records: list[dict] = []
    for _, user in users_df.iterrows():
        uid = user["user_id"]
        hour_profile = user["_hour_profile"]
        n_procs = int(rng_bg.poisson(5 * duration_days))
        owned_devs = user_device_map.get(uid, all_device_ids[:1])
        for _ in range(n_procs):
            ts = _random_ts(rng_bg, start_time, end_time, hour_profile)
            device_id = owned_devs[int(rng_bg.integers(0, len(owned_devs)))]
            proc = PROCESS_NAMES_NORMAL[int(rng_bg.integers(0, len(PROCESS_NAMES_NORMAL)))]
            parent = PARENT_PROCESSES[int(rng_bg.integers(0, len(PARENT_PROCESSES)))]
            event_id = _deterministic_id("PEV", len(records), plan_seed)
            records.append(
                {
                    "event_id": event_id,
                    "ts": ts.isoformat(),
                    "device_id": device_id,
                    "user_id": uid,
                    "process_name": proc,
                    "parent_process": parent,
                    "command_line": f"{proc} --normal",
                    "label": "normal",
                    "scenario_id": None,
                }
            )

    df = pd.DataFrame(records)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts").reset_index(drop=True)
    return df
