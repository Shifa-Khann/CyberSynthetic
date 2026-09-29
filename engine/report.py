"""
engine/report.py
Generate incident PDF reports in English and Urdu.
Uses ReportLab + arabic-reshaper + python-bidi for RTL text.
"""
from __future__ import annotations

import pathlib
import re
from typing import Any

import pandas as pd


def _reshape_urdu(text: str) -> str:
    """Apply arabic-reshaper + bidi for proper Urdu display in PDFs."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text


def _ids_stay_ltr(text: str) -> str:
    """IDs and IPs should remain LTR inside Urdu text."""
    # Wrap LTR sequences with PDF-safe markers — handled by keeping as separate paragraphs
    return text


def _get_fonts() -> tuple[str, str]:
    """Return (regular_font, bold_font) names, registering Noto Naskh if available."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_paths = [
            pathlib.Path("data") / "NotoNaskhArabic-Regular.ttf",
            pathlib.Path("C:/Windows/Fonts/NotoNaskhArabic-Regular.ttf"),
        ]
        for fp in font_paths:
            if fp.exists():
                pdfmetrics.registerFont(TTFont("NotoNaskh", str(fp)))
                return "NotoNaskh", "NotoNaskh"
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold"


def generate_incident_pdf(
    incident: pd.Series,
    alerts: pd.DataFrame,
    indicators: pd.DataFrame,
    narrative: str,
    out_path: pathlib.Path,
    language: str = "en",
) -> pathlib.Path:
    """
    Generate a PDF incident report.
    Returns the path to the generated file.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
    except ImportError:
        out_path.write_text(f"[PDF generation requires reportlab]\n{narrative}", encoding="utf-8")
        return out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    font_reg, font_bold = _get_fonts()

    is_urdu = language == "ur"
    alignment = TA_RIGHT if is_urdu else TA_LEFT

    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontName=font_bold, fontSize=16,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"],
        fontName=font_bold, fontSize=12,
        alignment=alignment,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName=font_reg, fontSize=10,
        alignment=alignment,
        leading=16,
    )

    inc_id = incident.get("incident_id", "INC-???")
    sev = incident.get("severity", "unknown")
    start = incident.get("start_time", "")
    end = incident.get("end_time", "")
    victim = incident.get("victim_user_id", "")
    device = incident.get("primary_device_id", "")
    tactics = incident.get("mitre_tactics", "")

    story = []

    if is_urdu:
        title_text = _reshape_urdu(f"سکیورٹی واقعے کی رپورٹ {inc_id}")
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.5*cm))

        fields = [
            ("واقعہ شناخت", inc_id),
            ("شدت", _reshape_urdu(str(sev))),
            ("آغاز وقت", str(start)),
            ("اختتام وقت", str(end)),
            ("متاثرہ صارف", str(victim)),
            ("بنیادی ڈیوائس", str(device)),
            ("MITRE حکمت عملی", str(tactics)),
        ]
        for label, value in fields:
            reshaped_label = _reshape_urdu(label)
            story.append(Paragraph(f"<b>{reshaped_label}:</b> {value}", body_style))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(_reshape_urdu("واقعے کی تفصیل"), heading_style))
        story.append(Spacer(1, 0.2*cm))
        narr_reshaped = _reshape_urdu(narrative)
        story.append(Paragraph(narr_reshaped, body_style))
    else:
        story.append(Paragraph(f"Security Incident Report: {inc_id}", title_style))
        story.append(Spacer(1, 0.5*cm))

        fields = [
            ("Incident ID", inc_id),
            ("Severity", str(sev).upper()),
            ("Start Time", str(start)),
            ("End Time", str(end)),
            ("Victim User", str(victim)),
            ("Primary Device", str(device)),
            ("MITRE Tactics", str(tactics)),
        ]
        for label, value in fields:
            story.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Incident Narrative", heading_style))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(narrative, body_style))

    # Alerts table
    story.append(Spacer(1, 0.5*cm))
    if is_urdu:
        story.append(Paragraph(_reshape_urdu("الرٹس"), heading_style))
    else:
        story.append(Paragraph("Related Alerts", heading_style))
    story.append(Spacer(1, 0.2*cm))

    if not alerts.empty:
        cols_to_show = ["alert_id", "ts", "alert_type", "severity", "status"]
        cols_present = [c for c in cols_to_show if c in alerts.columns]
        alert_data = [cols_present] + alerts[cols_present].fillna("").values.tolist()
        tbl = Table(alert_data, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightyellow]),
        ]))
        story.append(tbl)

    doc.build(story)
    return out_path


def generate_reports(
    incidents_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    indicators_df: pd.DataFrame,
    narratives: dict[str, str],
    out_dir: pathlib.Path,
    language: str = "en",
) -> list[pathlib.Path]:
    """Generate one PDF per incident. Returns list of generated paths."""
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    generated: list[pathlib.Path] = []

    if incidents_df.empty:
        return generated

    for _, inc in incidents_df.iterrows():
        inc_id = inc["incident_id"]
        inc_alerts = alerts_df[alerts_df.get("incident_id", pd.Series()) == inc_id] if not alerts_df.empty else pd.DataFrame()
        inc_indicators = indicators_df[indicators_df.get("incident_id", pd.Series()) == inc_id] if not indicators_df.empty else pd.DataFrame()
        narrative = narratives.get(inc_id, "No narrative available.")

        suffix = "_ur" if language == "ur" else ""
        out_path = reports_dir / f"{inc_id}{suffix}.pdf"
        try:
            p = generate_incident_pdf(inc, inc_alerts, inc_indicators, narrative, out_path, language)
            generated.append(p)
        except Exception as e:
            # Don't let PDF failure crash the pipeline
            print(f"[report.py] Failed to generate PDF for {inc_id}: {e}")

    return generated
