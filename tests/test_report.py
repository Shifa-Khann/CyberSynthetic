"""
tests/test_report.py
Tests for ReportLab incident PDF generation (English and Urdu).
"""
import pathlib
import pandas as pd
import pytest

from engine.report import generate_incident_pdf


def test_generate_incident_pdf(tmp_path):
    pdf_path = tmp_path / "test_report.pdf"

    inc = pd.Series({
        "incident_id": "INC-1001",
        "title": "Unusual Authentication Spike",
        "severity": "HIGH",
        "start_time": "2026-09-29T10:00:00Z",
        "end_time": "2026-09-29T11:00:00Z",
        "victim_user_id": "USR-001",
        "primary_device_id": "DEV-001",
        "mitre_tactics": "Initial Access",
    })

    alerts = pd.DataFrame([
        {"alert_id": "ALT-01", "ts": "2026-09-29T09:55:00Z", "alert_type": "Brute Force", "severity": "HIGH", "status": "OPEN"}
    ])

    indicators = pd.DataFrame()
    narrative = "Suspicious login pattern detected from remote subnet."

    res_path = generate_incident_pdf(
        incident=inc,
        alerts=alerts,
        indicators=indicators,
        narrative=narrative,
        out_path=pdf_path,
        language="en"
    )

    assert pathlib.Path(res_path).exists()
    assert pathlib.Path(res_path).stat().st_size > 0


def test_generate_incident_pdf_urdu(tmp_path):
    pdf_path = tmp_path / "test_report_ur.pdf"

    inc = pd.Series({
        "incident_id": "INC-1002",
        "title": "مشکوک لاگ ان",
        "severity": "HIGH",
        "start_time": "2026-09-29T10:00:00Z",
        "end_time": "2026-09-29T11:00:00Z",
        "victim_user_id": "USR-001",
        "primary_device_id": "DEV-001",
        "mitre_tactics": "Initial Access",
    })

    alerts = pd.DataFrame()
    indicators = pd.DataFrame()
    narrative = "سکیورٹی واقعے کی رپورٹ INC-1002"

    res_path = generate_incident_pdf(
        incident=inc,
        alerts=alerts,
        indicators=indicators,
        narrative=narrative,
        out_path=pdf_path,
        language="ur"
    )

    assert pathlib.Path(res_path).exists()
    assert pathlib.Path(res_path).stat().st_size > 0
