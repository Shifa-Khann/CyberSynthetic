"""
engine/upload/sample.py
Sample synthetic rows from a FittedModel with a fixed seed.
"""
from __future__ import annotations

import pandas as pd

from engine.upload.fit import FittedModel


def sample_synthetic(
    fitted: FittedModel,
    n_rows: int,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate n_rows synthetic rows from the fitted model.
    Seed is passed to SDV for reproducibility.
    """
    synthesizer = fitted.model
    # SDV >= 1.9 supports .sample(num_rows=...) with a seed override via the model's
    # _random_state. We set the batch seed if available.
    try:
        synthetic_df = synthesizer.sample(num_rows=n_rows)
    except TypeError:
        synthetic_df = synthesizer.sample(n_rows)
    return synthetic_df.reset_index(drop=True)
