"""
tests/test_upload.py
Tests for upload mode pipeline: schema inference, column classification, fitting, and sampling.
"""
import pandas as pd
import pytest

from engine.upload.infer import infer_schema
from engine.upload.classify import classify_columns, ColRole
from engine.upload.fit import fit_model
from engine.upload.sample import sample_synthetic


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "user_id": [f"U{i:03d}" for i in range(1, 51)],
        "age": [20 + (i % 30) for i in range(50)],
        "login_count": [i * 3 for i in range(50)],
        "department": ["HR", "IT", "Sales", "HR", "IT"] * 10,
        "is_active": [1, 0, 1, 1, 0] * 10,
    })


def test_schema_inference(sample_df):
    schema = infer_schema(sample_df)
    assert schema.n_rows == 50
    assert "user_id" in schema.columns
    assert schema.pk_guess == "user_id"


def test_column_classification(sample_df):
    schema = infer_schema(sample_df)
    roles = classify_columns(sample_df, schema)
    assert roles["user_id"] == ColRole.ID
    assert roles["department"] == ColRole.CATEGORICAL
    assert roles["age"] == ColRole.NUMERIC


def test_fit_and_sample(sample_df):
    schema = infer_schema(sample_df)
    roles = classify_columns(sample_df, schema)
    fitted = fit_model(sample_df, roles, seed=42)
    syn_df = sample_synthetic(fitted, n_rows=20, seed=42)
    assert len(syn_df) == 20
    assert set(syn_df.columns) == set(sample_df.columns)
