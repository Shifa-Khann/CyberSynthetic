"""
engine/validate.py
Integrity checks: PK uniqueness, FK validity, temporal order, derived values.
Called after generation and before export. Fails loudly on violations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ValidationResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def __str__(self) -> str:
        lines = []
        if self.passed:
            lines.append("✅ Validation PASSED")
        else:
            lines.append("❌ Validation FAILED")
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARN:  {w}")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# Checks
# ──────────────────────────────────────────────

def _check_pk_unique(df: pd.DataFrame, col: str, table: str, r: ValidationResult) -> None:
    if df.empty:
        return
    dups = df[df.duplicated(subset=[col], keep=False)]
    if not dups.empty:
        r.fail(f"[{table}] Duplicate {col}: {dups[col].unique()[:5].tolist()}")


def _check_fk(
    child_df: pd.DataFrame,
    child_col: str,
    parent_df: pd.DataFrame,
    parent_col: str,
    child_table: str,
    parent_table: str,
    r: ValidationResult,
    allow_null: bool = True,
) -> None:
    if child_df.empty or parent_df.empty:
        return
    child_vals = child_df[child_col].dropna() if allow_null else child_df[child_col]
    parent_vals = set(parent_df[parent_col].tolist())
    orphans = child_vals[~child_vals.isin(parent_vals)]
    if not orphans.empty:
        r.fail(
            f"[{child_table}.{child_col}] → [{parent_table}.{parent_col}] "
            f"orphan FK values: {orphans.unique()[:5].tolist()}"
        )


def _check_temporal_order(
    events_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    r: ValidationResult,
) -> None:
    """Each alert ts must be >= its source event ts."""
    if events_df.empty or alerts_df.empty:
        return
    alerts = alerts_df.copy()
    alerts["ts"] = pd.to_datetime(alerts["ts"], format="mixed")
    events_df = events_df.copy()
    events_df["ts"] = pd.to_datetime(events_df["ts"], format="mixed")

    # merge on event_id
    merged = alerts.merge(
        events_df[["event_id", "ts"]].rename(columns={"ts": "event_ts"}),
        left_on="source_event_id",
        right_on="event_id",
        how="left",
    )
    bad = merged.dropna(subset=["event_ts"])
    bad = bad[bad["ts"] < bad["event_ts"]]
    if not bad.empty:
        r.fail(
            f"[alerts] {len(bad)} alerts have ts < source event ts"
        )


def _check_incident_derived(
    incidents_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    r: ValidationResult,
) -> None:
    """
    incident.start_time = min(alert.ts for alerts in incident)
    incident.severity   = max(alert.severity)
    """
    if incidents_df.empty or alerts_df.empty:
        return
    sev_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    sev_rev = {v: k for k, v in sev_order.items()}
    alerts_df = alerts_df.copy()
    alerts_df["ts"] = pd.to_datetime(alerts_df["ts"], format="mixed")

    for _, inc in incidents_df.iterrows():
        inc_id = inc["incident_id"]
        inc_alerts = alerts_df[alerts_df["incident_id"] == inc_id]
        if inc_alerts.empty:
            r.warn(f"[incidents] {inc_id} has no linked alerts")
            continue
        expected_start = inc_alerts["ts"].min()
        actual_start = pd.to_datetime(inc["start_time"], format="mixed")
        if actual_start > expected_start:
            r.fail(
                f"[incidents] {inc_id} start_time {actual_start} > min alert ts {expected_start}"
            )
        expected_sev = sev_rev.get(
            int(inc_alerts["severity"].map(lambda s: sev_order.get(s, 0)).max()), "low"
        )
        if inc["severity"] != expected_sev:
            r.fail(
                f"[incidents] {inc_id} severity mismatch: "
                f"stored={inc['severity']}, expected={expected_sev}"
            )


def _check_label_balance(auth_df: pd.DataFrame, r: ValidationResult) -> None:
    if auth_df.empty:
        return
    vc = auth_df["label"].value_counts(normalize=True)
    if "malicious" in vc and vc["malicious"] > 0.5:
        r.warn(
            f"[auth_events] malicious ratio={vc['malicious']:.2%} > 50% — dataset may be unrealistic"
        )


def _check_reserved_ips(auth_df: pd.DataFrame, r: ValidationResult) -> None:
    """Ensure all IPs are in reserved/TEST-NET ranges."""
    RESERVED_PREFIXES = ("10.", "192.168.", "203.0.113.", "198.51.100.", "192.0.2.")
    if auth_df.empty or "src_ip" not in auth_df.columns:
        return
    bad_ips = auth_df[
        ~auth_df["src_ip"].apply(lambda ip: any(ip.startswith(p) for p in RESERVED_PREFIXES))
    ]["src_ip"].unique()
    if len(bad_ips) > 0:
        r.fail(f"[auth_events] Non-reserved IPs detected: {bad_ips[:5].tolist()}")


def _check_email_domains(emails_df: pd.DataFrame, r: ValidationResult) -> None:
    """Ensure all email addresses use example.com / example.org domains."""
    SAFE_DOMAINS = ("example.com", "example.org")
    if emails_df.empty:
        return
    for col in ["sender"]:
        if col not in emails_df.columns:
            continue
        bad = emails_df[
            ~emails_df[col].apply(
                lambda e: any(e.endswith(d) for d in SAFE_DOMAINS) if isinstance(e, str) else True
            )
        ]
        if not bad.empty:
            r.fail(f"[emails.{col}] Non-example domain emails: {bad[col].unique()[:3].tolist()}")


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────

def validate_dataset(
    users_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    auth_df: pd.DataFrame,
    emails_df: pd.DataFrame,
    email_events_df: pd.DataFrame,
    process_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    incidents_df: pd.DataFrame,
    indicators_df: pd.DataFrame,
) -> ValidationResult:
    """Run all integrity checks. Returns ValidationResult."""
    r = ValidationResult()

    # PK uniqueness
    _check_pk_unique(users_df, "user_id", "users", r)
    _check_pk_unique(devices_df, "device_id", "devices", r)
    if not auth_df.empty:
        _check_pk_unique(auth_df, "event_id", "auth_events", r)
    if not emails_df.empty:
        _check_pk_unique(emails_df, "email_id", "emails", r)
    if not email_events_df.empty:
        _check_pk_unique(email_events_df, "email_event_id", "email_events", r)
    if not process_df.empty:
        _check_pk_unique(process_df, "event_id", "process_events", r)
    if not alerts_df.empty:
        _check_pk_unique(alerts_df, "alert_id", "alerts", r)
    if not incidents_df.empty:
        _check_pk_unique(incidents_df, "incident_id", "incidents", r)

    # FK validity
    _check_fk(devices_df, "owner_user_id", users_df, "user_id", "devices", "users", r)
    if not auth_df.empty:
        _check_fk(auth_df, "user_id", users_df, "user_id", "auth_events", "users", r)
        _check_fk(auth_df, "device_id", devices_df, "device_id", "auth_events", "devices", r, allow_null=True)
    if not email_events_df.empty and not emails_df.empty:
        _check_fk(email_events_df, "email_id", emails_df, "email_id", "email_events", "emails", r)
    if not process_df.empty:
        _check_fk(process_df, "user_id", users_df, "user_id", "process_events", "users", r)
        _check_fk(process_df, "device_id", devices_df, "device_id", "process_events", "devices", r)

    # Temporal order
    if not auth_df.empty and not alerts_df.empty:
        _check_temporal_order(auth_df, alerts_df, r)

    # Derived values
    if not incidents_df.empty and not alerts_df.empty:
        _check_incident_derived(incidents_df, alerts_df, r)

    # Safety checks
    _check_reserved_ips(auth_df, r)
    _check_email_domains(emails_df, r)

    # Label balance
    _check_label_balance(auth_df, r)

    return r
