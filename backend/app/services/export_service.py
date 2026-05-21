"""
ComplianceOS — Export Service
==============================
Generates CSV and PDF exports for obligations, evidence documents,
and compliance reports.

All functions are synchronous and return raw bytes — callers wrap them
in FastAPI StreamingResponse.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# CSV exports
# ─────────────────────────────────────────────────────────────────────────────

_OBLIGATION_FIELDS = [
    "id",
    "regulation_code",
    "regulator",
    "country",
    "description",
    "obligation_type",
    "deadline",
    "created_at",
]

_EVIDENCE_FIELDS = [
    "id",
    "title",
    "doc_type",
    "confidence_score",
    "custody_hash",
    "uploaded_by",
    "created_at",
]


def export_obligations_csv(obligations: list[dict]) -> bytes:
    """
    Serialize a list of obligation dicts to UTF-8 CSV bytes.

    If the list is empty a single informational row is emitted so that the
    file is never completely blank.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_OBLIGATION_FIELDS, extrasaction="ignore")
    writer.writeheader()

    if not obligations:
        writer.writerow({f: "No obligations found" if f == "id" else "" for f in _OBLIGATION_FIELDS})
    else:
        for row in obligations:
            writer.writerow({f: row.get(f, "") for f in _OBLIGATION_FIELDS})

    return buf.getvalue().encode("utf-8")


def export_evidence_csv(documents: list[dict]) -> bytes:
    """
    Serialize a list of evidence-document dicts to UTF-8 CSV bytes.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EVIDENCE_FIELDS, extrasaction="ignore")
    writer.writeheader()

    for row in documents:
        writer.writerow({f: row.get(f, "") for f in _EVIDENCE_FIELDS})

    return buf.getvalue().encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# PDF export
# ─────────────────────────────────────────────────────────────────────────────

def export_compliance_report_pdf(
    entity_name: str,
    score: Any,                 # ComplianceScore dataclass
    obligations: list[Any],     # list[ObligationScore]
    alerts: list[dict],
    tenant_id: str,
) -> bytes:
    """
    Build a professional A4 compliance report PDF using reportlab.

    Parameters
    ----------
    entity_name : str
    score       : ComplianceScore instance (score_pct, total_obligations, …)
    obligations : list of ObligationScore instances from breakdown
    alerts      : list of DeadlineAlert dicts (may be empty)
    tenant_id   : str

    Returns
    -------
    bytes — raw PDF content starting with b'%PDF'
    """
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    # ── colour palette ────────────────────────────────────────────────────────
    C_PRIMARY   = HexColor("#1A56DB")   # indigo-600
    C_HEADER_BG = HexColor("#EFF6FF")   # indigo-50
    C_ROW_ALT   = HexColor("#F9FAFB")   # gray-50
    C_GREEN     = HexColor("#16A34A")   # green-600
    C_RED       = HexColor("#DC2626")   # red-600
    C_ORANGE    = HexColor("#EA580C")   # orange-600
    C_DARK      = HexColor("#111827")   # gray-900
    C_MUTED     = HexColor("#6B7280")   # gray-500

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="ComplianceOS — Compliance Report",
        author="ComplianceOS",
    )

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]

    style_title = ParagraphStyle(
        "COS_Title",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=C_PRIMARY,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    style_subtitle = ParagraphStyle(
        "COS_Sub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=C_MUTED,
        spaceAfter=2,
    )
    style_section = ParagraphStyle(
        "COS_Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=C_DARK,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    style_cell = ParagraphStyle(
        "COS_Cell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=C_DARK,
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story: list = []

    # ── Title block ───────────────────────────────────────────────────────────
    story.append(Paragraph("ComplianceOS — Compliance Report", style_title))
    story.append(Paragraph(f"Entity: <b>{entity_name}</b>", style_subtitle))
    story.append(Paragraph(f"Tenant: {tenant_id}", style_subtitle))
    story.append(Paragraph(f"Generated: {generated_at}", style_subtitle))
    story.append(Spacer(1, 0.4 * cm))

    # ── Score summary table ───────────────────────────────────────────────────
    story.append(Paragraph("Compliance Score", style_section))

    score_pct      = getattr(score, "score_pct", 0.0)
    total          = getattr(score, "total_obligations", 0)
    satisfied      = getattr(score, "satisfied_obligations", 0)
    unsatisfied    = total - satisfied

    score_color = C_GREEN if score_pct >= 80 else (C_ORANGE if score_pct >= 50 else C_RED)

    score_data = [
        ["Metric", "Value"],
        ["Score", f"{score_pct:.1f}%"],
        ["Total Obligations", str(total)],
        ["Satisfied", str(satisfied)],
        ["Unsatisfied", str(unsatisfied)],
    ]

    score_table = Table(score_data, colWidths=[8 * cm, 6 * cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_HEADER_BG, C_ROW_ALT]),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",     (1, 1), (1, 1), score_color),
        ("FONTNAME",      (1, 1), (1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (1, 1), (1, 1), 11),
        ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#D1D5DB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(score_table)

    # ── Obligations table ─────────────────────────────────────────────────────
    story.append(Paragraph("Obligations", style_section))

    ob_header = ["#", "Description", "Type", "Status"]
    ob_col_w  = [1 * cm, 11 * cm, 3 * cm, 1.5 * cm]

    ob_rows = [ob_header]
    for idx, ob in enumerate(obligations, start=1):
        desc  = getattr(ob, "title", "") or ""
        desc  = (desc[:80] + "…") if len(desc) > 80 else desc
        otype = getattr(ob, "obligation_type", "") or ""
        sat   = getattr(ob, "is_satisfied", False)
        mark  = "✓" if sat else "✗"
        ob_rows.append([
            str(idx),
            Paragraph(desc, style_cell),
            Paragraph(otype, style_cell),
            mark,
        ])

    ob_table = Table(ob_rows, colWidths=ob_col_w, repeatRows=1)

    row_colors: list = []
    for i in range(1, len(ob_rows)):
        sat = getattr(obligations[i - 1], "is_satisfied", False)
        bg  = HexColor("#F0FDF4") if sat else HexColor("#FFF7F7")
        row_colors.append(("BACKGROUND", (0, i), (-1, i), bg))

    status_text_colors: list = []
    for i in range(1, len(ob_rows)):
        sat = getattr(obligations[i - 1], "is_satisfied", False)
        fc  = C_GREEN if sat else C_RED
        status_text_colors.append(("TEXTCOLOR", (3, i), (3, i), fc))
        status_text_colors.append(("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"))

    ob_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#D1D5DB")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        *row_colors,
        *status_text_colors,
    ]))
    story.append(ob_table)

    # ── Alerts table (conditional) ────────────────────────────────────────────
    if alerts:
        story.append(Paragraph("Deadline Alerts", style_section))

        al_header = ["Regulation", "Title", "Deadline", "Days", "Severity"]
        al_col_w  = [3 * cm, 7 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm]

        al_rows = [al_header]
        for al in alerts:
            reg_code = al.get("regulation_code", "")
            title    = al.get("title", "")
            title    = (title[:60] + "…") if len(title) > 60 else title
            deadline = al.get("deadline", "")
            days     = str(al.get("days_remaining", ""))
            severity = str(al.get("severity", ""))
            al_rows.append([
                Paragraph(reg_code, style_cell),
                Paragraph(title,    style_cell),
                Paragraph(deadline, style_cell),
                days,
                severity.upper(),
            ])

        al_table = Table(al_rows, colWidths=al_col_w, repeatRows=1)

        sev_colors: list = []
        for i, al in enumerate(alerts, start=1):
            sev = str(al.get("severity", "")).lower()
            if sev == "critical":
                fc = C_RED
            elif sev == "high":
                fc = C_ORANGE
            else:
                fc = C_DARK
            sev_colors.append(("TEXTCOLOR", (4, i), (4, i), fc))
            sev_colors.append(("FONTNAME",  (4, i), (4, i), "Helvetica-Bold"))

        al_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_HEADER_BG, C_ROW_ALT]),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#D1D5DB")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            *sev_colors,
        ]))
        story.append(al_table)

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<font size='7' color='#6B7280'>"
        "This report is generated automatically by ComplianceOS. "
        "It is confidential and intended solely for the named entity and tenant."
        "</font>",
        style_normal,
    ))

    doc.build(story)
    return buf.getvalue()
