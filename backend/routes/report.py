"""
AquaSure Backend - PDF Report Generation
POST /api/generate-pdf  - Generate and return a PDF assessment report
"""

import io
from datetime import date as _date
from flask import Blueprint, jsonify, request, send_file

report_bp = Blueprint("report", __name__)

GRADE_COLORS = {
    "A": (22, 163, 74),
    "B": (2, 132, 199),
    "C": (217, 119, 6),
    "D": (234, 88, 12),
    "E": (220, 38, 38),
}
STATUS_COLORS = {
    "normal":             (22, 163, 74),
    "above_acceptable":   (217, 119, 6),
    "above_permissible":  (220, 38, 38),
}


def _rgb(t):
    from reportlab.lib.colors import Color
    return Color(t[0]/255, t[1]/255, t[2]/255)


def _build_pdf(data: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    blue   = colors.HexColor("#0284c7")
    dark   = colors.HexColor("#0f172a")
    muted  = colors.HexColor("#64748b")
    light  = colors.HexColor("#f8fafc")
    border = colors.HexColor("#e2e8f0")

    h1 = ParagraphStyle("h1", fontSize=22, textColor=blue, fontName="Helvetica-Bold", spaceAfter=2)
    h2 = ParagraphStyle("h2", fontSize=14, textColor=dark, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle("h3", fontSize=11, textColor=dark, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", fontSize=9.5, textColor=colors.HexColor("#334155"), leading=14)
    small = ParagraphStyle("small", fontSize=8, textColor=muted, leading=12)
    center = ParagraphStyle("center", fontSize=9, textColor=muted, alignment=TA_CENTER)

    grade  = data.get("grade", "?")
    gc     = _rgb(GRADE_COLORS.get(grade, (100, 116, 139)))
    wqi    = data.get("wqi", "—")

    story = []

    # Header
    story.append(Paragraph("AquaSure", h1))
    story.append(Paragraph("Groundwater Quality Assessment Report", ParagraphStyle(
        "sub", fontSize=12, textColor=muted, fontName="Helvetica", spaceAfter=6)))
    story.append(HRFlowable(width="100%", thickness=1.5, color=blue, spaceAfter=10))

    # Sample Details table
    story.append(Paragraph("Sample Details", h2))
    sample_rows = [
        ["Sample Name",      data.get("sample_name", "—")],
        ["District",         data.get("district", "—") or "—"],
        ["Assessment Date",  data.get("assessment_date", _date.today().isoformat())],
        ["Parameters Tested", ", ".join(data.get("params_tested", [])) or "—"],
    ]
    t = Table(sample_rows, colWidths=[5*cm, 12*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1), light),
        ("TEXTCOLOR",    (0,0), (0,-1), muted),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9.5),
        ("GRID",         (0,0), (-1,-1), 0.5, border),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, light]),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Overall Result box
    story.append(Paragraph("Overall Assessment", h2))
    result_rows = [
        ["WQI Score",        f"{wqi}"],
        ["Grade",            grade],
        ["Category",         data.get("category", "—")],
        ["Potability",       data.get("potability", "—")],
        ["Assessment",       data.get("overall_assessment", "—")],
    ]
    rt = Table(result_rows, colWidths=[5*cm, 12*cm])
    rt.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), colors.white),
        ("BACKGROUND",   (0,0), (0,-1), light),
        ("TEXTCOLOR",    (0,0), (0,-1), muted),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (1,0), (1,0), gc),
        ("FONTNAME",     (1,0), (1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (1,0), (1,0), 14),
        ("FONTSIZE",     (0,0), (-1,-1), 9.5),
        ("GRID",         (0,0), (-1,-1), 0.5, border),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ]))
    story.append(rt)
    story.append(Spacer(1, 10))

    # Parameter Assessment table
    story.append(Paragraph("Parameter Assessment (BIS IS 10500:2012)", h2))
    headers = [["Parameter", "Measured", "Acceptable\nLimit", "Permissible\nLimit", "Status"]]
    prows = []
    for p in data.get("parameters", []):
        sc   = p.get("status_code", "normal")
        sc_color = _rgb(STATUS_COLORS.get(sc, (100,116,139)))
        prows.append([
            p.get("name", ""),
            f"{p.get('value', '—')} {p.get('unit', '')}",
            str(p.get("acceptable_limit", "—")),
            str(p.get("permissible_limit", "—")),
            p.get("status", "—"),
        ])

    if prows:
        pt = Table(headers + prows, colWidths=[5.5*cm, 3.2*cm, 2.5*cm, 2.8*cm, 3*cm])
        style_cmds = [
            ("BACKGROUND",   (0,0), (-1,0), blue),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 8.5),
            ("GRID",         (0,0), (-1,-1), 0.5, border),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, light]),
            ("ALIGN",        (1,0), (-1,-1), "CENTER"),
            ("LEFTPADDING",  (0,0), (-1,-1), 6),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ]
        # Color status cells
        for i, p in enumerate(data.get("parameters", []), start=1):
            sc = p.get("status_code", "normal")
            sc_rgb = _rgb(STATUS_COLORS.get(sc, (100,116,139)))
            style_cmds.append(("TEXTCOLOR", (4, i), (4, i), sc_rgb))
            style_cmds.append(("FONTNAME",  (4, i), (4, i), "Helvetica-Bold"))
        pt.setStyle(TableStyle(style_cmds))
        story.append(pt)
    story.append(Spacer(1, 10))

    # Violations
    violations = data.get("violations", [])
    if violations:
        story.append(Paragraph("BIS Violations", h2))
        for v in violations:
            story.append(Paragraph(f"• {v}", ParagraphStyle(
                "viol", fontSize=9, textColor=colors.HexColor("#dc2626"), leading=13)))
        story.append(Spacer(1, 6))

    # Recommendations
    story.append(Paragraph("Recommendations", h2))
    for r in data.get("recommendations", []):
        story.append(Paragraph(f"• {r}", body))
    story.append(Spacer(1, 10))

    # Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=border, spaceAfter=6))
    story.append(Paragraph("Disclaimer", h3))
    story.append(Paragraph(data.get("disclaimer", ""), small))
    story.append(Spacer(1, 6))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=border, spaceAfter=4))
    story.append(Paragraph(
        f"Generated by AquaSure  |  BIS IS 10500:2012 Standards  |  {_date.today().isoformat()}",
        center))

    doc.build(story)
    buf.seek(0)
    return buf.read()


@report_bp.route("/api/generate-pdf", methods=["POST"])
def generate_pdf():
    try:
        data = request.get_json(force=True, silent=True) or {}
        if not data:
            return jsonify({"error": "Assessment data required in request body."}), 400

        pdf_bytes = _build_pdf(data)
        sample = str(data.get("sample_name", "Report")).replace(" ", "_")
        dt     = str(data.get("assessment_date", _date.today().isoformat()))
        fname  = f"AquaSure_Report_{sample}_{dt}.pdf"

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=fname,
        )

    except ImportError:
        return jsonify({"error": "ReportLab is not installed. Run: pip install reportlab"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
