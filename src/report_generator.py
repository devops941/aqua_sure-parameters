"""
AquaSure ReportLab PDF Report Generator Module
Generates comprehensive groundwater quality audit scorecards and analytical reports
for any of the 38 districts of Tamil Nadu or statewide overviews.
"""

import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

from src.config import REPORTS_DIR, WQI_PARAM_STANDARDS, TN_38_DISTRICTS, DISTRICT_SUMMARY_PATH

def generate_district_pdf(district_name: str, df_district: pd.DataFrame, output_path: str = None) -> str:
    """
    Generates a publication-grade PDF water quality scorecard for a given district.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        safe_name = district_name.replace(" ", "_")
        output_path = str(REPORTS_DIR / f"AquaSure_{safe_name}_Scorecard.pdf")
        
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0284c7"),
        alignment=TA_CENTER
    )
    
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        alignment=TA_JUSTIFY
    )
    
    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_RIGHT
    )
    
    kpi_num_style = ParagraphStyle(
        "KpiNum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER
    )
    
    kpi_label_style = ParagraphStyle(
        "KpiLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER
    )
    
    elements = []
    
    # Header Banner
    elements.append(Paragraph("AquaSure – Smart Water Analytics Platform", title_style))
    elements.append(Paragraph(f"GROUNDWATER QUALITY & POTABILITY SCORECARD: {district_name.upper()}", subtitle_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Analysis Period: 2020–2025 | Standard: BIS 10500:2012 / WHO | Report Date: {datetime.now().strftime('%d %B %Y')}", meta_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))
    
    # 1. District Executive Summary Metrics
    total_samples = len(df_district)
    valid_wqi = df_district["wqi"].dropna()
    median_wqi = round(valid_wqi.median(), 2) if len(valid_wqi) > 0 else 0.0
    mean_wqi = round(valid_wqi.mean(), 2) if len(valid_wqi) > 0 else 0.0
    potable_count = (df_district["is_potable"] == True).sum()
    potable_pct = round((potable_count / total_samples) * 100, 1) if total_samples > 0 else 0.0
    
    # Status & color
    if median_wqi <= 25:
        wqi_status = "Grade A (Excellent)"
        status_color = colors.HexColor("#10b981")
    elif median_wqi <= 50:
        wqi_status = "Grade B (Good)"
        status_color = colors.HexColor("#06b6d4")
    elif median_wqi <= 75:
        wqi_status = "Grade C (Poor)"
        status_color = colors.HexColor("#f59e0b")
    elif median_wqi <= 100:
        wqi_status = "Grade D (Very Poor)"
        status_color = colors.HexColor("#f97316")
    else:
        wqi_status = "Grade E (Unsuitable)"
        status_color = colors.HexColor("#ef4444")
        
    kpi_data = [
        [
            Paragraph(f"{total_samples:,}", kpi_num_style),
            Paragraph(f"{median_wqi:.1f}", kpi_num_style),
            Paragraph(wqi_status, kpi_num_style),
            Paragraph(f"{potable_pct:.1f}%", kpi_num_style)
        ],
        [
            Paragraph("TOTAL SAMPLING WELLS", kpi_label_style),
            Paragraph("MEDIAN WQI SCORE", kpi_label_style),
            Paragraph("WATER QUALITY RATING", kpi_label_style),
            Paragraph("POTABLE SAFE WELLS", kpi_label_style)
        ]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[130, 130, 140, 122])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 14))
    
    # 2. Executive Overview
    elements.append(Paragraph("1. Executive Hydrochemical Assessment", section_heading))
    overview_text = (
        f"This hydrochemical scorecard assesses the groundwater resources of <b>{district_name}</b> district "
        f"across the active monitoring period (2020–2025), utilizing <b>{total_samples:,}</b> laboratory-tested "
        f"groundwater observation well records. The computed median Weighted Arithmetic Water Quality Index (WAWQI) "
        f"is <b>{median_wqi:.2f}</b>, classifying the regional groundwater baseline as <b>{wqi_status}</b>. "
        f"Approximately <b>{potable_pct:.1f}%</b> of sampled sources meet direct potable standards without advanced remediation, "
        f"while <b>{100 - potable_pct:.1f}%</b> require treatment before potable consumption due to chemical limit exceedances."
    )
    elements.append(Paragraph(overview_text, body_style))
    elements.append(Spacer(1, 12))
    
    # 3. Hydrochemical Parameter Analysis Table
    elements.append(Paragraph("2. Hydrochemical Parameter Distribution vs. BIS 10500:2012 Standards", section_heading))
    
    param_table_data = [
        [
            Paragraph("<b>Parameter</b>", kpi_label_style),
            Paragraph("<b>Unit</b>", kpi_label_style),
            Paragraph("<b>BIS Acceptable</b>", kpi_label_style),
            Paragraph("<b>Observed Mean</b>", kpi_label_style),
            Paragraph("<b>Observed Max</b>", kpi_label_style),
            Paragraph("<b>Exceedance (%)</b>", kpi_label_style)
        ]
    ]
    
    for param_key, meta in WQI_PARAM_STANDARDS.items():
        if param_key in df_district.columns:
            s = df_district[param_key].dropna()
            if len(s) > 0:
                mean_v = s.mean()
                max_v = s.max()
                exceed_count = (s > meta["standard_permissible"]).sum()
                exceed_pct = (exceed_count / len(s)) * 100.0
                
                # Flag high exceedance with red tint
                param_name = meta["name"].split(" (")[0]
                exceed_cell = Paragraph(f"<font color='{'#dc2626' if exceed_pct > 15 else '#16a34a'}'><b>{exceed_pct:.1f}%</b></font>", kpi_label_style)
                
                param_table_data.append([
                    Paragraph(param_name, body_style),
                    Paragraph(meta["unit"], body_style),
                    Paragraph(str(meta["standard_acceptable"]), body_style),
                    Paragraph(f"{mean_v:.1f}", body_style),
                    Paragraph(f"{max_v:.1f}", body_style),
                    exceed_cell
                ])
                
    chem_table = Table(param_table_data, colWidths=[140, 65, 85, 75, 75, 82])
    chem_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(chem_table)
    elements.append(Spacer(1, 14))
    
    # 4. Critical Water Quality Concerns & Remediation Action Plan
    elements.append(Paragraph("3. Strategic Contamination Risk & Remediation Blueprint", section_heading))
    
    # Calculate specific risks
    no3_s = df_district["no3"].dropna() if "no3" in df_district else pd.Series([])
    f_s = df_district["f"].dropna() if "f" in df_district else pd.Series([])
    tds_s = df_district["tds"].dropna() if "tds" in df_district else pd.Series([])
    
    no3_risk = ((no3_s > 45.0).sum() / len(no3_s) * 100) if len(no3_s) > 0 else 0
    f_risk = ((f_s > 1.5).sum() / len(f_s) * 100) if len(f_s) > 0 else 0
    tds_risk = ((tds_s > 2000.0).sum() / len(tds_s) * 100) if len(tds_s) > 0 else 0
    
    recommendations = []
    if no3_risk > 20.0:
        recommendations.append(
            f"<b>Nitrate Enrichment Alert ({no3_risk:.1f}% wells exceeded 45 mg/L):</b> Highly elevated nitrate indicates "
            f"agricultural fertilizer seepage and untreated wastewater infiltration. Recommended intervention: Mandatory ion-exchange "
            f"or biological denitrification before public supply; promote precision agriculture and bio-fertilizers in rural recharge zones."
        )
    if f_risk > 10.0:
        recommendations.append(
            f"<b>Fluoride Geological Leaching ({f_risk:.1f}% wells exceeded 1.5 mg/L):</b> High fluoride presents severe risks "
            f"of dental and skeletal fluorosis. Recommended intervention: Deploy decentralized Nalgonda technique or Activated Alumina "
            f"filtration units at community wellheads; augment rainwater harvesting to dilute aquifer mineral concentration."
        )
    if tds_risk > 15.0:
        recommendations.append(
            f"<b>Salinity & Total Dissolved Solids ({tds_risk:.1f}% wells exceeded 2000 mg/L):</b> Indicates brackish groundwater or "
            f"marine salt-water intrusion. Recommended intervention: Install commercial RO (Reverse Osmosis) desalinization and "
            f"construct managed aquifer recharge (check dams / percolation ponds) to raise the groundwater table."
        )
    if not recommendations:
        recommendations.append(
            "<b>Favorable Aquifer Profile:</b> Primary ionic parameters remain largely within permissible thresholds. Standard "
            "sand-gravel filtration and chlorination/UV disinfection is sufficient for continuous municipal drinking water distribution."
        )
        
    for rec in recommendations:
        elements.append(Paragraph(f"• {rec}", body_style))
        elements.append(Spacer(1, 4))
        
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94a3b8"), spaceAfter=8))
    elements.append(Paragraph("AquaSure Analytical Engine | Generated using Python ReportLab & BIS 10500 Guidelines | Confidential & Public Health Advisory", meta_style))
    
    doc.build(elements)
    return output_path

if __name__ == "__main__":
    from src.data_pipeline import filter_analytical_window
    df = pd.read_parquet("data/processed/tn_groundwater_2020_2025.parquet")
    sample_district = "Kanyakumari"
    df_sample = df[df["district"] == sample_district]
    pdf = generate_district_pdf(sample_district, df_sample)
    print(f"Generated test PDF: {pdf}")
