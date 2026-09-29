"""
engine/upload/classify.py
Classify each column into semantic roles: id / categorical / numeric / datetime / name / text.
Uses column names and summary statistics only — no raw row values sent externally.
"""
from __future__ import annotations

import re
from enum import Enum

import pandas as pd

from engine.upload.infer import InferredSchema


class ColRole(str, Enum):
    ID = "id"
    CATEGORICAL = "categorical"
    NUMERIC = "numeric"
    DATETIME = "datetime"
    NAME = "name"
    TEXT = "text"
    BOOLEAN = "boolean"


_ID_PATTERNS = re.compile(r"(^|_)(id|key|pk|uuid|guid)($|_)", re.I)
_NAME_PATTERNS = re.compile(r"(name|full_name|first|last|username|login|user|person)", re.I)
_DATE_PATTERNS = re.compile(r"(ts|timestamp|date|time|created|updated|at)($|_)", re.I)
_TEXT_PATTERNS = re.compile(r"(body|text|description|comment|message|content|narrative)", re.I)


def classify_columns(
    df: pd.DataFrame, schema: InferredSchema
) -> dict[str, ColRole]:
    """
    Classify each column into a semantic role.
    Returns dict mapping column name -> ColRole.
    """
    roles: dict[str, ColRole] = {}

    for col in schema.columns:
        dtype = schema.dtypes.get(col, "object")
        s = df[col]
        nunique = s.nunique()
        n = len(s)
        cardinality_ratio = nunique / max(n, 1)

        # ── ID ──
        if col == schema.pk_guess or _ID_PATTERNS.search(col):
            roles[col] = ColRole.ID
            continue

        # ── Datetime ──
        if dtype == "datetime" or _DATE_PATTERNS.search(col):
            roles[col] = ColRole.DATETIME
            continue

        # ── Boolean ──
        if dtype == "bool":
            roles[col] = ColRole.BOOLEAN
            continue

        # ── Numeric ──
        if dtype in ("int64", "float64"):
            roles[col] = ColRole.NUMERIC
            continue

        # ── Text (object, high cardinality, matches text pattern) ──
        if dtype == "object" and _TEXT_PATTERNS.search(col):
            roles[col] = ColRole.TEXT
            continue

        # ── Name ──
        if dtype == "object" and _NAME_PATTERNS.search(col):
            roles[col] = ColRole.NAME
            continue

        # ── Categorical vs Text by cardinality ──
        if dtype == "object":
            if cardinality_ratio < 0.20 or nunique <= 30:
                roles[col] = ColRole.CATEGORICAL
            else:
                roles[col] = ColRole.TEXT
            continue

        roles[col] = ColRole.CATEGORICAL

    return roles
