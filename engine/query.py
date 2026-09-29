"""
engine/query.py
NL-to-SQL query runner.
- Validates with sqlglot (SELECT only, no DML/DDL)
- Runs on read-only SQLite connection
- Forces LIMIT
- Returns (sql, result_df) or raises ValueError
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

try:
    import sqlglot
    _HAS_SQLGLOT = True
except ImportError:
    _HAS_SQLGLOT = False

MAX_ROWS = 1000

# Canned fallback queries shown to user
CANNED_QUERIES = [
    {
        "label": "Top 10 users by alert count",
        "sql": "SELECT user_id, COUNT(*) as alert_count FROM alerts GROUP BY user_id ORDER BY alert_count DESC LIMIT 10",
    },
    {
        "label": "High-severity incidents",
        "sql": "SELECT * FROM incidents WHERE severity IN ('high','critical') ORDER BY start_time DESC LIMIT 100",
    },
    {
        "label": "Malicious auth events",
        "sql": "SELECT * FROM auth_events WHERE label = 'malicious' ORDER BY ts DESC LIMIT 100",
    },
    {
        "label": "Alert type distribution",
        "sql": "SELECT alert_type, COUNT(*) as count FROM alerts GROUP BY alert_type ORDER BY count DESC LIMIT 50",
    },
    {
        "label": "Recent incidents",
        "sql": "SELECT * FROM incidents ORDER BY start_time DESC LIMIT 20",
    },
    {
        "label": "Devices by criticality",
        "sql": "SELECT criticality, COUNT(*) as count FROM devices GROUP BY criticality ORDER BY count DESC",
    },
]


def _validate_sql(sql: str) -> str:
    """
    Validate that sql is a single SELECT statement.
    Returns cleaned SQL or raises ValueError.
    """
    sql = sql.strip().rstrip(";")

    # Quick reject for DML/DDL
    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
        re.IGNORECASE,
    )
    if forbidden.search(sql):
        raise ValueError("Only SELECT statements are allowed.")

    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        raise ValueError("Query must start with SELECT.")

    if _HAS_SQLGLOT:
        try:
            parsed = sqlglot.parse(sql)
            if not parsed or not isinstance(parsed[0], sqlglot.expressions.Select):
                raise ValueError("Could not parse as a SELECT statement.")
        except Exception as e:
            raise ValueError(f"SQL parse error: {e}")

    # Ensure LIMIT
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {MAX_ROWS}"
    else:
        # Cap existing LIMIT
        def _cap_limit(m):
            n = int(m.group(1))
            return f"LIMIT {min(n, MAX_ROWS)}"
        sql = re.sub(r"\bLIMIT\s+(\d+)", _cap_limit, sql, flags=re.IGNORECASE)

    return sql


def run_query(sql: str, db_path: Path) -> tuple[str, pd.DataFrame]:
    """
    Validate and run a SQL query on the read-only SQLite DB.
    Returns (cleaned_sql, result_df).
    Raises ValueError on invalid SQL or IOError if DB missing.
    """
    if not db_path.exists():
        raise IOError(f"Database not found: {db_path}")

    cleaned = _validate_sql(sql)

    # Read-only connection
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        df = pd.read_sql_query(cleaned, conn)
    finally:
        conn.close()

    return cleaned, df


def get_schema_description(db_path: Path) -> str:
    """Return a text description of all tables and columns for the LLM prompt."""
    if not db_path.exists():
        return "Database not yet generated."

    conn = sqlite3.connect(str(db_path))
    lines: list[str] = []
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor2 = conn.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor2.fetchall()]
            lines.append(f"{table}({', '.join(cols)})")
    finally:
        conn.close()

    return "\n".join(lines)


run_nl_query = run_query
validate_sql_query = _validate_sql
