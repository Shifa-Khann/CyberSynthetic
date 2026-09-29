"""
engine/localize.py
Urdu localization layer.
Adds _ur columns from frozen name/enum banks and transliteration rules.
"""
from __future__ import annotations

import json
import pathlib
import re

import pandas as pd

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def _load_json(name: str) -> dict:
    path = _DATA_DIR / name
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


_names_ur: dict | None = None
_enums_ur: dict | None = None


def _get_names() -> dict:
    global _names_ur
    if _names_ur is None:
        _names_ur = _load_json("names_ur.json")
    return _names_ur


def _get_enums() -> dict:
    global _enums_ur
    if _enums_ur is None:
        _enums_ur = _load_json("enums_ur.json")
    return _enums_ur


_PHONETICS_MAP = {
    "a": "ا", "b": "ب", "c": "ک", "d": "ڈ", "e": "ے", "f": "ف",
    "g": "گ", "h": "ہ", "i": "ی", "j": "ج", "k": "ک", "l": "ل",
    "m": "م", "n": "ن", "o": "و", "p": "پ", "q": "ق", "r": "ر",
    "s": "س", "t": "ٹ", "u": "و", "v": "و", "w": "و", "x": "ایکس",
    "y": "ی", "z": "ز",
}


def _fallback_urdu_name(english_name: str) -> str:
    """Phonetic Urdu transliteration fallback for unbanked names."""
    words = english_name.split()
    ur_words = []
    for w in words:
        w_clean = w.lower()
        ur_w = "".join(_PHONETICS_MAP.get(ch, ch) for ch in w_clean)
        ur_words.append(ur_w)
    return " ".join(ur_words)


def localize_users(users_df: pd.DataFrame) -> pd.DataFrame:
    """Add full_name_ur, home_city_ur, department_ur, and role_ur columns."""
    names = _get_names()
    enums = _get_enums()
    name_map: dict[str, str] = names.get("names", {})
    city_map: dict[str, str] = names.get("cities", {})

    df = users_df.copy()
    df["full_name_ur"] = df["full_name"].map(
        lambda n: name_map.get(n, _fallback_urdu_name(str(n)))
    )
    df["home_city_ur"] = df["home_city"].map(
        lambda c: city_map.get(c, str(c))
    )
    if "department" in df.columns:
        df["department_ur"] = df["department"].map(lambda v: enums.get(str(v), str(v)))
    if "role" in df.columns:
        df["role_ur"] = df["role"].map(lambda v: enums.get(str(v), str(v)))
    return df


def localize_enums(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Add _ur column for each enum column."""
    enums = _get_enums()
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[f"{col}_ur"] = df[col].map(lambda v: enums.get(str(v), str(v)))
    return df


def build_urdu_csv_headers(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    """Rename columns to Urdu headers for the Urdu CSV export."""
    return df.rename(columns=column_map)


def localize_incidents(incidents_df: pd.DataFrame) -> pd.DataFrame:
    """Add title_ur, description_ur, severity_ur, status_ur."""
    enums = _get_enums()
    df = incidents_df.copy()
    if "title" in df.columns:
        df["title_ur"] = df["title"].map(lambda t: f"سکیورٹی واقعہ: {t}")
    if "description" in df.columns:
        df["description_ur"] = df["description"].map(lambda d: f"واقعے کی تفصیلات: {d}")
    return localize_enums(df, ["severity", "status"])


def localize_dataset(
    users_df: pd.DataFrame,
    auth_df: pd.DataFrame,
    emails_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    incidents_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Apply Urdu localization to all tables.
    Returns dict with localized copies.
    """
    result: dict[str, pd.DataFrame] = {}

    result["users"] = localize_users(users_df)

    if not auth_df.empty:
        result["auth_events"] = localize_enums(auth_df, ["label", "outcome", "auth_method"])
    else:
        result["auth_events"] = auth_df

    if not emails_df.empty:
        result["emails"] = localize_enums(emails_df, ["label"])
    else:
        result["emails"] = emails_df

    if not alerts_df.empty:
        result["alerts"] = localize_enums(alerts_df, ["severity", "status", "alert_type"])
    else:
        result["alerts"] = alerts_df

    if not incidents_df.empty:
        result["incidents"] = localize_incidents(incidents_df)
    else:
        result["incidents"] = incidents_df

    return result
