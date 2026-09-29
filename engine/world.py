"""
engine/world.py
Generate users and devices — the stable "world" layer.
All randomness via engine.rng.RNGTree.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
from faker import Faker

from engine.rng import RNGTree

# Faker locale list (English only; Urdu added by localize.py)
_FAKE = Faker("en_US")
Faker.seed(0)  # faker seed is reset per call via rng

GEO_COUNTRIES = ["US", "PK", "UK", "CA", "DE", "AE", "JP", "FR"]
GEO_CITIES = {
    "US": ["New York", "San Francisco", "Chicago", "Seattle"],
    "PK": ["Karachi", "Lahore", "Islamabad", "Rawalpindi"],
    "UK": ["London", "Manchester", "Birmingham"],
    "AE": ["Dubai", "Abu Dhabi"],
    "DE": ["Berlin", "Munich", "Frankfurt"],
    "CA": ["Toronto", "Vancouver", "Montreal"],
    "JP": ["Tokyo", "Osaka"],
    "FR": ["Paris", "Lyon"],
}

DEPARTMENTS = [
    "Engineering", "Finance", "HR", "IT", "Legal",
    "Marketing", "Operations", "Sales", "Security", "Executive",
]

ROLES = ["analyst", "engineer", "manager", "director", "admin", "intern"]

OS_LIST = ["Windows 11", "Windows 10", "Ubuntu 22.04", "macOS 14", "RHEL 9"]

PRIVILEGE_LEVELS = ["standard", "elevated", "admin", "superadmin"]

CRITICALITY_LEVELS = ["low", "medium", "high", "critical"]

# Reserved IP blocks (AGENTS.md rule 6)
_IP_POOLS = [
    ("10.0.", 0, 255),        # 10.0.x.y
    ("192.168.", 0, 255),     # 192.168.x.y
    ("203.0.113.", 1, 254),   # TEST-NET-3
    ("198.51.100.", 1, 254),  # TEST-NET-2
    ("192.0.2.", 1, 254),     # TEST-NET-1
]


def _gen_ip(rng) -> str:
    pool_idx = rng.integers(0, len(_IP_POOLS))
    prefix, lo, hi = _IP_POOLS[pool_idx]
    third = rng.integers(0, 256)
    fourth = rng.integers(lo, hi + 1)
    return f"{prefix}{third}.{fourth}"


def _gen_hostname(rng, dept: str, idx: int) -> str:
    prefix = dept[:3].upper()
    suffix = rng.integers(100, 999)
    return f"{prefix}-WS-{suffix:03d}-{idx:04d}"


# ──────────────────────────────────────────────
# Data classes (light wrappers for clarity)
# ──────────────────────────────────────────────

@dataclass
class UserRecord:
    user_id: str
    username: str
    full_name: str
    email: str
    department: str
    role: str
    privilege_level: str
    home_country: str
    home_city: str
    # hour-of-day login probability profile (24 floats summing to 1)
    hour_profile: list[float] = field(repr=False)
    # baseline event rate: expected auth events per day
    events_per_day: float = 8.0


@dataclass
class DeviceRecord:
    device_id: str
    hostname: str
    os: str
    ip_address: str
    owner_user_id: str
    criticality: str


# ──────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────

def _make_hour_profile(rng) -> list[float]:
    """
    Generate a plausible working-hours login probability profile.
    Peak is randomly centred in 08-18 range, with small off-hours noise.
    """
    probs = rng.exponential(scale=0.5, size=24)
    # boost work hours (8-18)
    probs[8:18] *= rng.uniform(2.0, 5.0, size=10)
    total = probs.sum()
    return (probs / total).tolist()


def _deterministic_id(prefix: str, index: int, seed: int) -> str:
    """Build a short deterministic ID from prefix + index + seed."""
    raw = f"{prefix}{index}{seed}".encode()
    h = hashlib.sha256(raw).hexdigest()[:8]
    return f"{prefix.upper()}-{h}"


def generate_users(plan_seed: int, n_users: int, rng: "RNGTree") -> pd.DataFrame:
    """
    Return a DataFrame matching the `users` schema in TRD §3.
    IDs, usernames, emails — all synthetic, no real data.
    """
    rng_w = rng.child("world")
    Faker.seed(int(rng_w.integers(0, 2**31)))
    fake = Faker("en_US")

    records: list[dict] = []
    for i in range(n_users):
        dept = DEPARTMENTS[int(rng_w.integers(0, len(DEPARTMENTS)))]
        role = ROLES[int(rng_w.integers(0, len(ROLES)))]
        # privilege skewed toward standard
        priv = rng_w.choice(
            PRIVILEGE_LEVELS,
            p=[0.70, 0.18, 0.10, 0.02],
        )
        first = fake.first_name()
        last = fake.last_name()
        full_name = f"{first} {last}"
        username = f"{first[0].lower()}{last.lower()}{rng_w.integers(10,99)}"
        email = f"{username}@example.com"
        user_id = _deterministic_id("USR", i, plan_seed)
        city = fake.city()
        records.append(
            {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "full_name_ur": "",  # filled by localize.py
                "email": email,
                "department": dept,
                "role": role,
                "privilege_level": priv,
                "home_country": "US",
                "home_city": city,
                "home_city_ur": "",  # filled by localize.py
                "_hour_profile": _make_hour_profile(rng_w),
                "_events_per_day": float(rng_w.integers(4, 20)),
            }
        )

    return pd.DataFrame(records)


def generate_devices(
    plan_seed: int, n_devices: int, users_df: pd.DataFrame, rng: "RNGTree"
) -> pd.DataFrame:
    """
    Return a DataFrame matching the `devices` schema in TRD §3.
    Each device is assigned to a random owner user.
    """
    rng_w = rng.child("world")
    user_ids = users_df["user_id"].tolist()

    records: list[dict] = []
    for i in range(n_devices):
        owner_idx = int(rng_w.integers(0, len(user_ids)))
        owner = user_ids[owner_idx]
        owner_row = users_df[users_df["user_id"] == owner].iloc[0]
        dept = owner_row["department"]
        os_ = OS_LIST[int(rng_w.integers(0, len(OS_LIST)))]
        crit = rng_w.choice(
            CRITICALITY_LEVELS, p=[0.40, 0.35, 0.18, 0.07]
        )
        device_id = _deterministic_id("DEV", i, plan_seed)
        records.append(
            {
                "device_id": device_id,
                "hostname": _gen_hostname(rng_w, dept, i),
                "os": os_,
                "ip_address": _gen_ip(rng_w),
                "owner_user_id": owner,
                "criticality": crit,
            }
        )

    return pd.DataFrame(records)
