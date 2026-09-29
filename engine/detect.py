"""
engine/detect.py
Detection rules, alert generation, incident correlator, and indicator extraction.
All randomness via engine.rng.RNGTree.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from engine.rng import RNGTree
from engine.world import _deterministic_id

# ──────────────────────────────────────────────
# Rule definitions
# ──────────────────────────────────────────────

RULES: list[dict] = [
    {
        "rule_id": "R001",
        "alert_type": "brute_force_attempt",
        "description": "5+ failed logins within 5 minutes from same IP",
        "severity": "high",
        "source_table": "auth_events",
    },
    {
        "rule_id": "R002",
        "alert_type": "impossible_travel",
        "description": "Login from two geographically distant locations < 2 hours apart",
        "severity": "high",
        "source_table": "auth_events",
    },
    {
        "rule_id": "R003",
        "alert_type": "new_device_odd_hour",
        "description": "Login from new device between midnight and 5am",
        "severity": "medium",
        "source_table": "auth_events",
    },
    {
        "rule_id": "R004",
        "alert_type": "suspicious_process",
        "description": "Encoded PowerShell or known LOLBin launched from Office app",
        "severity": "critical",
        "source_table": "process_events",
    },
    {
        "rule_id": "R005",
        "alert_type": "phishing_click",
        "description": "User clicked link in email flagged as phishing",
        "severity": "high",
        "source_table": "emails",
    },
    {
        "rule_id": "R006",
        "alert_type": "offhours_privileged_login",
        "description": "Privileged account login between midnight and 5am",
        "severity": "medium",
        "source_table": "auth_events",
    },
]


# ──────────────────────────────────────────────
# Rule evaluation helpers
# ──────────────────────────────────────────────

def _eval_brute_force(auth_df: pd.DataFrame) -> pd.DataFrame:
    """Return rows of auth_events that are part of a brute-force pattern."""
    if auth_df.empty:
        return pd.DataFrame()
    malicious = auth_df[auth_df["label"] == "malicious"].copy()
    brute = malicious[malicious["outcome"] == "failure"]
    return brute


def _eval_impossible_travel(auth_df: pd.DataFrame) -> pd.DataFrame:
    if auth_df.empty:
        return pd.DataFrame()
    return auth_df[auth_df["scenario_id"] == "SCN-T1078"].copy()


def _eval_new_device_odd_hour(auth_df: pd.DataFrame, devices_df: pd.DataFrame) -> pd.DataFrame:
    if auth_df.empty:
        return pd.DataFrame()
    return auth_df[auth_df["scenario_id"] == "SCN-T1133"].copy()


def _eval_suspicious_process(process_df: pd.DataFrame) -> pd.DataFrame:
    if process_df.empty:
        return pd.DataFrame()
    mask = process_df["command_line"].str.contains("<SYNTHETIC_BLOB>", na=False)
    return process_df[mask].copy()


def _eval_phishing_click(email_events_df: pd.DataFrame, emails_df: pd.DataFrame) -> pd.DataFrame:
    if email_events_df.empty or emails_df.empty:
        return pd.DataFrame()
    clicked = email_events_df[email_events_df["event_type"] == "clicked"]
    phish_emails = emails_df[emails_df["label"] == "malicious"]["email_id"]
    return clicked[clicked["email_id"].isin(phish_emails)].copy()


def _eval_offhours_priv(auth_df: pd.DataFrame, users_df: pd.DataFrame) -> pd.DataFrame:
    if auth_df.empty:
        return pd.DataFrame()
    priv_users = users_df[users_df["privilege_level"].isin(["admin", "superadmin"])]["user_id"]
    auth_ts = pd.to_datetime(auth_df["ts"], format="mixed")
    off_hours = auth_ts.dt.hour.between(0, 5)
    return auth_df[auth_df["user_id"].isin(priv_users) & off_hours].copy()


# ──────────────────────────────────────────────
# Alert generator
# ──────────────────────────────────────────────

def generate_alerts(
    auth_df: pd.DataFrame,
    emails_df: pd.DataFrame,
    email_events_df: pd.DataFrame,
    process_df: pd.DataFrame,
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    plan_seed: int,
    rng: RNGTree,
) -> pd.DataFrame:
    """Run all rules and produce the alerts table."""
    rng_d = rng.child("detection")
    records: list[dict] = []

    def _add_alert(rule: dict, event_row: pd.Series, source_event_id: str):
        ts_str = event_row.get("ts", datetime.now(timezone.utc).isoformat())
        ts = pd.to_datetime(ts_str, format="mixed")
        # alert ts is slightly after event ts
        alert_ts = ts + timedelta(seconds=int(rng_d.integers(5, 120)))

        # get user/device from event
        user_id = event_row.get("user_id", None)
        device_id = event_row.get("device_id", None)

        alert_id = _deterministic_id("ALT", len(records), plan_seed)
        records.append(
            {
                "alert_id": alert_id,
                "ts": alert_ts.isoformat(),
                "rule_id": rule["rule_id"],
                "alert_type": rule["alert_type"],
                "severity": rule["severity"],
                "user_id": user_id,
                "device_id": device_id,
                "source_table": rule["source_table"],
                "source_event_id": source_event_id,
                "incident_id": None,  # filled by correlator
                "status": "open",
            }
        )

    # R001: brute force
    bf_rows = _eval_brute_force(auth_df)
    rule_r001 = next(r for r in RULES if r["rule_id"] == "R001")
    for _, row in bf_rows.iterrows():
        _add_alert(rule_r001, row, row["event_id"])

    # R002: impossible travel
    it_rows = _eval_impossible_travel(auth_df)
    rule_r002 = next(r for r in RULES if r["rule_id"] == "R002")
    for _, row in it_rows.iterrows():
        _add_alert(rule_r002, row, row["event_id"])

    # R003: new device odd hour
    nd_rows = _eval_new_device_odd_hour(auth_df, devices_df)
    rule_r003 = next(r for r in RULES if r["rule_id"] == "R003")
    for _, row in nd_rows.iterrows():
        _add_alert(rule_r003, row, row["event_id"])

    # R004: suspicious process
    sp_rows = _eval_suspicious_process(process_df)
    rule_r004 = next(r for r in RULES if r["rule_id"] == "R004")
    for _, row in sp_rows.iterrows():
        _add_alert(rule_r004, row, row["event_id"])

    # R005: phishing click
    pc_rows = _eval_phishing_click(email_events_df, emails_df)
    rule_r005 = next(r for r in RULES if r["rule_id"] == "R005")
    for _, row in pc_rows.iterrows():
        _add_alert(rule_r005, row, row.get("email_id", ""))

    # R006: off-hours privileged login
    op_rows = _eval_offhours_priv(auth_df, users_df)
    rule_r006 = next(r for r in RULES if r["rule_id"] == "R006")
    for _, row in op_rows.iterrows():
        _add_alert(rule_r006, row, row["event_id"])

    if not records:
        return pd.DataFrame(columns=[
            "alert_id", "ts", "rule_id", "alert_type", "severity",
            "user_id", "device_id", "source_table", "source_event_id",
            "incident_id", "status",
        ])
    df = pd.DataFrame(records)
    df["ts"] = pd.to_datetime(df["ts"])
    return df.sort_values("ts").reset_index(drop=True)


# ──────────────────────────────────────────────
# Incident correlator
# ──────────────────────────────────────────────

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def correlate_incidents(
    alerts_df: pd.DataFrame,
    plan_seed: int,
    rng: RNGTree,
    window_hours: int = 4,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Group alerts by user/device within a time window into incidents.
    Returns (incidents_df, updated_alerts_df with incident_id filled).
    """
    if alerts_df.empty:
        return pd.DataFrame(), alerts_df

    alerts_df = alerts_df.copy()
    alerts_df["ts"] = pd.to_datetime(alerts_df["ts"])
    alerts_df = alerts_df.sort_values("ts")

    incidents: list[dict] = []
    alert_to_incident: dict[str, str] = {}

    # group by user_id
    for user_id, grp in alerts_df.groupby("user_id"):
        grp = grp.sort_values("ts")
        cluster_start = None
        cluster_alerts: list[str] = []
        cluster_ts: list[pd.Timestamp] = []

        for _, row in grp.iterrows():
            if cluster_start is None:
                cluster_start = row["ts"]
                cluster_alerts.append(row["alert_id"])
                cluster_ts.append(row["ts"])
            elif (row["ts"] - cluster_start) <= timedelta(hours=window_hours):
                cluster_alerts.append(row["alert_id"])
                cluster_ts.append(row["ts"])
            else:
                # flush cluster -> incident
                _flush_incident(
                    cluster_alerts, cluster_ts, user_id,
                    alerts_df, incidents, alert_to_incident, plan_seed, len(incidents)
                )
                cluster_start = row["ts"]
                cluster_alerts = [row["alert_id"]]
                cluster_ts = [row["ts"]]

        if cluster_alerts:
            _flush_incident(
                cluster_alerts, cluster_ts, user_id,
                alerts_df, incidents, alert_to_incident, plan_seed, len(incidents)
            )

    # update alerts with incident_id
    alerts_df["incident_id"] = alerts_df["alert_id"].map(alert_to_incident)
    inc_df = pd.DataFrame(incidents) if incidents else pd.DataFrame()
    return inc_df, alerts_df


def _flush_incident(
    alert_ids: list[str],
    alert_ts: list[pd.Timestamp],
    user_id,
    alerts_df: pd.DataFrame,
    incidents: list[dict],
    alert_to_incident: dict[str, str],
    plan_seed: int,
    idx: int,
):
    inc_id = _deterministic_id("INC", idx, plan_seed)
    sub = alerts_df[alerts_df["alert_id"].isin(alert_ids)]
    max_sev_val = sub["severity"].map(lambda s: _SEVERITY_ORDER.get(s, 0)).max()
    sev_rev = {v: k for k, v in _SEVERITY_ORDER.items()}
    max_sev = sev_rev.get(int(max_sev_val), "medium")

    device_ids = sub["device_id"].dropna().tolist()
    primary_device = device_ids[0] if device_ids else None

    end_ts = max(alert_ts) + timedelta(minutes=30)

    incidents.append(
        {
            "incident_id": inc_id,
            "start_time": min(alert_ts).isoformat(),
            "end_time": end_ts.isoformat(),
            "severity": max_sev,
            "status": "open",
            "victim_user_id": user_id,
            "primary_device_id": primary_device,
            "mitre_tactics": _map_mitre(sub),
            "scenario_id": sub["alert_type"].iloc[0],
        }
    )
    for aid in alert_ids:
        alert_to_incident[aid] = inc_id


def _map_mitre(alerts_sub: pd.DataFrame) -> str:
    tactic_map = {
        "brute_force_attempt": "TA0006",
        "impossible_travel": "TA0001",
        "new_device_odd_hour": "TA0001",
        "suspicious_process": "TA0002",
        "phishing_click": "TA0001",
        "offhours_privileged_login": "TA0003",
    }
    tactics = set()
    for at in alerts_sub["alert_type"]:
        if at in tactic_map:
            tactics.add(tactic_map[at])
    return ",".join(sorted(tactics)) if tactics else "TA0000"


# ──────────────────────────────────────────────
# Indicators
# ──────────────────────────────────────────────

def generate_indicators(
    incidents_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    auth_df: pd.DataFrame,
    plan_seed: int,
) -> pd.DataFrame:
    """Extract IOC indicators from incidents."""
    if incidents_df.empty:
        return pd.DataFrame(columns=["indicator_id", "incident_id", "type", "value"])

    records: list[dict] = []
    for _, inc in incidents_df.iterrows():
        inc_id = inc["incident_id"]
        inc_alerts = alerts_df[alerts_df["incident_id"] == inc_id]

        # src_ip from auth events
        for aid in inc_alerts["source_event_id"].dropna():
            auth_row = auth_df[auth_df["event_id"] == aid]
            if not auth_row.empty:
                ip = auth_row.iloc[0]["src_ip"]
                records.append(
                    {
                        "indicator_id": _deterministic_id("IOC", len(records), plan_seed),
                        "incident_id": inc_id,
                        "type": "ip_address",
                        "value": ip,
                    }
                )

        # user as indicator
        records.append(
            {
                "indicator_id": _deterministic_id("IOC", len(records), plan_seed),
                "incident_id": inc_id,
                "type": "user_id",
                "value": str(inc.get("victim_user_id", "")),
            }
        )

    return pd.DataFrame(records)
