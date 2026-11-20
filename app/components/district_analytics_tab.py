"""
District Analytics Component for AquaSure Streamlit Application
Detailed drilldown for all 38 districts of Tamil Nadu with automated ReportLab PDF scorecard download.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
from src.config import WQI_PARAM_STANDARDS, TN_38_DISTRICTS, REPORTS_DIR
from src.report_generator import generate_district_pdf

def render_district_analytics_tab(df: pd.DataFrame, df_summary: pd.DataFrame):
    st.markdown("### District-Level Groundwater Quality Drilldown")
    st.markdown("Select any of the **38 Tamil Nadu districts** to analyze specific hydrochemical profiles and export official audit scorecards.")
    
    # District Selector
    available_districts = sorted(df["district"].dropna().unique().tolist())
    
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        selected_district = st.selectbox(
            "Select District:",
            options=available_districts,
            index=available_districts.index("Chennai") if "Chennai" in available_districts else 0
        )
    with col_sel2:
        st.write("")
        st.write("")
        # PDF Generation Button
        pdf_path = REPORTS_DIR / f"AquaSure_{selected_district.replace(' ', '_')}_Scorecard.pdf"
        df_dist = df[df["district"] == selected_district].copy()
        
        # Pre-generate PDF for download
        if st.button("📄 Generate Audit Scorecard (PDF)", use_container_width=True):
            with st.spinner("Generating official ReportLab PDF..."):
                generated_path = generate_district_pdf(selected_district, df_dist)
                with open(generated_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="⬇️ Download Scorecard PDF",
                    data=pdf_bytes,
                    file_name=f"AquaSure_{selected_district}_Scorecard.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF Scorecard Generated Successfully!")
                
    st.markdown("---")
    
    # District KPIs
    total_wells = len(df_dist)
    dist_median_wqi = df_dist["wqi"].median()
    dist_mean_wqi = df_dist["wqi"].mean()
    dist_potable = (df_dist["is_potable"] == True).sum()
    dist_potable_pct = (dist_potable / total_wells) * 100 if total_wells > 0 else 0
    
    # State comparison
    state_median_wqi = df["wqi"].median()
    wqi_diff = dist_median_wqi - state_median_wqi
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Monitoring Stations", f"{total_wells:,}")
    with k2:
        delta_label = f"{abs(wqi_diff):.1f} vs State Avg"
        st.metric(
            "Median WQI",
            f"{dist_median_wqi:.1f}",
            delta=delta_label if wqi_diff <= 0 else f"+{delta_label}",
            delta_color="inverse"
        )
    with k3:
        status_name = "Good" if dist_median_wqi <= 50 else ("Poor" if dist_median_wqi <= 75 else ("Very Poor" if dist_median_wqi <= 100 else "Unsuitable"))
        st.metric("Overall Category", status_name)
    with k4:
        st.metric("Potable Safe Wells", f"{dist_potable_pct:.1f}%", f"{dist_potable} of {total_wells}")
        
    st.markdown("---")
    
    # Hydrochemical Parameter Details vs BIS 10500 Standards
    col_t1, col_t2 = st.columns([3, 2])
    
    with col_t1:
        st.markdown(f"#### Hydrochemical Profile: {selected_district}")
        param_rows = []
        for param, meta in WQI_PARAM_STANDARDS.items():
            if param in df_dist.columns:
                s = df_dist[param].dropna()
                if len(s) > 0:
                    mean_val = s.mean()
                    max_val = s.max()
                    exceed_count = (s > meta["standard_permissible"]).sum()
                    exceed_pct = (exceed_count / len(s)) * 100
                    
                    status = "✅ Favorable"
                    if exceed_pct > 20:
                        status = "🚨 Severe Violation"
                    elif exceed_pct > 0:
                        status = "⚠️ Moderate Exceedance"
                        
                    param_rows.append({
                        "Parameter": meta["name"].split(" (")[0],
                        "Unit": meta["unit"],
                        "BIS Acceptable": meta["standard_acceptable"],
                        "District Mean": round(mean_val, 1),
                        "Max Observed": round(max_val, 1),
                        "Exceedance (%)": f"{exceed_pct:.1f}%",
                        "Compliance": status
                    })
                    
        df_param_table = pd.DataFrame(param_rows)
        st.dataframe(df_param_table, use_container_width=True, hide_index=True)
        
    with col_t2:
        st.markdown("#### WQI Grade Distribution")
        grade_order = ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]
        color_map = {
            "Excellent": "#10b981",
            "Good": "#06b6d4",
            "Poor": "#f59e0b",
            "Very Poor": "#f97316",
            "Unsuitable for Drinking": "#ef4444"
        }
        
        grade_dist = df_dist["wqi_category"].value_counts().reindex(grade_order).fillna(0).reset_index()
        grade_dist.columns = ["Category", "Count"]
        
        fig_pie = px.pie(
            grade_dist,
            values="Count",
            names="Category",
            color="Category",
            color_discrete_map=color_map,
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=310)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    # Exceedance bar chart for this district
    st.markdown(f"#### Major Ion Balance & Limits: {selected_district}")
    ions = ["ca", "mg", "cl", "so4", "no3", "f"]
    ion_names = ["Calcium", "Magnesium", "Chloride", "Sulphate", "Nitrate", "Fluoride"]
    ion_means = [df_dist[c].mean() if c in df_dist else 0 for c in ions]
    ion_stds = [WQI_PARAM_STANDARDS[c]["standard_acceptable"] for c in ions]
    
    fig_ions = go.Figure()
    fig_ions.add_trace(go.Bar(
        name="District Mean Concentration",
        x=ion_names,
        y=ion_means,
        marker_color="#0284c7"
    ))
    fig_ions.add_trace(go.Bar(
        name="BIS Desirable Standard Limit",
        x=ion_names,
        y=ion_stds,
        marker_color="#94a3b8"
    ))
    fig_ions.update_layout(
        barmode='group',
        yaxis_title="Concentration (mg/L)",
        xaxis_title="Hydrochemical Parameter",
        margin=dict(t=20, b=20, l=10, r=10),
        height=340
    )
    st.plotly_chart(fig_ions, use_container_width=True)
