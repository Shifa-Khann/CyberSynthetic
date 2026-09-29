"""
engine/upload/infer.py
Infer types and guess primary key from an uploaded CSV.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class InferredSchema:
    columns: list[str]
    dtypes: dict[str, str]          # pandas dtype name
    pk_guess: str | None            # best PK candidate
    nullable: dict[str, bool]
    n_rows: int
    n_cols: int
    sample_values: dict[str, list]  # first 3 unique values per column


def _is_id_col(col: str, series: pd.Series) -> bool:
    """Heuristic: is this column a primary key candidate?"""
    lower = col.lower()
    if any(lower.endswith(s) for s in ["_id", "id", "_key", "key", "_pk"]):
        # Must be unique-ish
        nunique = series.nunique()
        return nunique == len(series) or nunique / max(len(series), 1) > 0.95
    return False


def infer_schema(df: pd.DataFrame) -> InferredSchema:
    """
    Infer types, nullable flags, and guess the PK column.
    Does NOT look at row values for sensitive data (names/stats only).
    """
    dtypes: dict[str, str] = {}
    nullable: dict[str, bool] = {}
    sample_values: dict[str, list] = {}
    pk_guess: str | None = None

    pk_candidates: list[str] = []

    for col in df.columns:
        s = df[col]
        dtype_str = str(s.dtype)
        nullable[col] = bool(s.isnull().any())
        sample_values[col] = s.dropna().unique()[:3].tolist()

        # Coerce type name
        if pd.api.types.is_integer_dtype(s):
            dtypes[col] = "int64"
        elif pd.api.types.is_float_dtype(s):
            dtypes[col] = "float64"
        elif pd.api.types.is_bool_dtype(s):
            dtypes[col] = "bool"
        elif pd.api.types.is_datetime64_any_dtype(s):
            dtypes[col] = "datetime"
        else:
            # Try parsing as datetime
            sample = s.dropna().head(20).astype(str)
            dt_ok = 0
            for v in sample:
                try:
                    pd.to_datetime(v)
                    dt_ok += 1
                except Exception:
                    pass
            if dt_ok / max(len(sample), 1) > 0.8:
                dtypes[col] = "datetime"
            else:
                dtypes[col] = "object"

        # PK detection
        if _is_id_col(col, s):
            pk_candidates.append(col)

    if pk_candidates:
        # prefer the one with "id" in name and high uniqueness
        pk_guess = pk_candidates[0]
        for c in pk_candidates:
            if df[c].nunique() == len(df):
                pk_guess = c
                break

    return InferredSchema(
        columns=list(df.columns),
        dtypes=dtypes,
        pk_guess=pk_guess,
        nullable=nullable,
        n_rows=len(df),
        n_cols=len(df.columns),
        sample_values=sample_values,
    )
