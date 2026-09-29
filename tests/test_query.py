"""
tests/test_query.py
Tests for NL-to-SQL query safety and execution.
"""
import sqlite3
import pandas as pd
import pytest

from engine.query import run_nl_query, validate_sql_query


@pytest.fixture
def sample_sqlite(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    df = pd.DataFrame({
        "alert_id": [1, 2, 3],
        "severity": ["HIGH", "MEDIUM", "LOW"],
        "user_id": ["U001", "U002", "U003"]
    })
    df.to_sql("alerts", conn, index=False)
    conn.close()
    return db_path


def test_validate_sql_valid():
    sql = validate_sql_query("SELECT * FROM alerts WHERE severity = 'HIGH'")
    assert "LIMIT" in sql.upper()


def test_validate_sql_blocks_dml():
    with pytest.raises(ValueError, match="SELECT"):
        validate_sql_query("DROP TABLE alerts")

    with pytest.raises(ValueError, match="SELECT"):
        validate_sql_query("DELETE FROM alerts")


def test_run_nl_query_canned(sample_sqlite):
    sql, df = run_nl_query("SELECT * FROM alerts WHERE severity = 'HIGH'", sample_sqlite)
    assert not df.empty
    assert "severity" in df.columns
