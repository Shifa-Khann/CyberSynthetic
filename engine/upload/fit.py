"""
engine/upload/fit.py
Fit a GaussianCopula (default) or CTGAN/TVAE model on the uploaded DataFrame.
All randomness is passed via RNG seed — not via bare random calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from engine.upload.classify import ColRole


@dataclass
class FittedModel:
    """Container for a fitted SDV model."""
    model_type: str
    model: object
    column_roles: dict[str, ColRole]
    metadata: dict


def fit_model(
    df: pd.DataFrame,
    column_roles: dict[str, ColRole],
    model_type: Literal["gaussian_copula", "ctgan", "tvae"] = "gaussian_copula",
    seed: int = 42,
) -> FittedModel:
    """
    Fit a generative model on the DataFrame.
    Only column names and summary statistics are used to configure the model.

    Args:
        df: The uploaded DataFrame (real data; never sent to external API).
        column_roles: Column role classifications.
        model_type: Which SDV model to use.
        seed: Random seed for reproducibility.

    Returns:
        FittedModel with the trained model.
    """
    from sdv.single_table import GaussianCopulaSynthesizer, CTGANSynthesizer, TVAESynthesizer
    from sdv.metadata import SingleTableMetadata

    meta = SingleTableMetadata()
    meta.detect_from_dataframe(df)

    # Override SDV metadata based on our classification
    for col, role in column_roles.items():
        if col not in df.columns:
            continue
        if role == ColRole.ID:
            meta.update_column(col, sdtype="id")
        elif role == ColRole.DATETIME:
            meta.update_column(col, sdtype="datetime")
        elif role == ColRole.CATEGORICAL:
            meta.update_column(col, sdtype="categorical")
        elif role == ColRole.NUMERIC:
            meta.update_column(col, sdtype="numerical")
        elif role == ColRole.BOOLEAN:
            meta.update_column(col, sdtype="boolean")
        elif role in (ColRole.NAME, ColRole.TEXT):
            meta.update_column(col, sdtype="categorical")

    if model_type == "gaussian_copula":
        synthesizer = GaussianCopulaSynthesizer(meta, enforce_min_max_values=True)
    elif model_type == "ctgan":
        synthesizer = CTGANSynthesizer(meta, epochs=100)
    elif model_type == "tvae":
        synthesizer = TVAESynthesizer(meta, epochs=100)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    synthesizer.fit(df)

    return FittedModel(
        model_type=model_type,
        model=synthesizer,
        column_roles=column_roles,
        metadata=meta.to_dict(),
    )


fit_generator = fit_model
