"""
Overview Tab Component for AquaSure Streamlit Application
Displays statewide hydrochemical insights, WQI categorical breakdown, and district leaderboards.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_overview_tab(df_filtered: pd.DataFrame, df_summary: pd.DataFrame):
    st.markdown("### 🏛️ Executive Groundwater Quality Summary (2020–2025)")
    st.markdown("Macro-level environmental surveillance across all **38 administrative districts** of Tamil Nadu utilizing official Central and State Ground Water laboratory records.")
    
    total_samples = len(df_filtered)
    
    # 1. Executive Summary Callout Box
    st.markdown("""
    <div style="background: #f8fafc; border-left: 4px solid #0284c7; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin: 0px 0px 6px 0px; color: #0f172a;">Key Hydrochemical Findings & Strategic Observations:</h4>
        <ul style="margin: 0px; padding-left: 20px; color: #334155; font-size: 0.92rem; line-height: 1.6;">
            <li><b>Regional Disparity:</b> Kanyakumari district leads the state with <b>52.2% potable observation wells</b>, heavily recharged by Western Ghats precipitation.</li>
            <li><b>Nitrate Enrichment:</b> Intensive agricultural fertilizer and poultry runoff in western/inland agro-belts (<b>Namakkal 81.2%</b>, <b>Erode 76.4%</b>, <b>Tiruppur 75.3%</b>) has caused widespread nitrate levels exceeding the 45 mg/L drinking threshold.</li>
            <li><b>Geogenic Fluoride:</b> Deep crystalline rock weathering contributes to severe fluoride exceedances (>1.5 mg/L) across <b>Dharmapuri</b> and <b>Salem</b>.</li>
            <li><b>Coastal Salinity:</b> Marine intrusion and brackish groundwater zones dominate coastal taluks of <b>Nagapattinam</b> and <b>Ramanathapuram</b>.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Charts Row: Categorical Distribution & Key Exceedances
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### 📊 WQI Rating Distribution (Brown et al. Scale)")
        cat_order = ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]
        color_map = {
            "Excellent": "#10b981",
            "Good": "#06b6d4",
            "Poor": "#f59e0b",
            "Very Poor": "#f97316",
            "Unsuitable for Drinking": "#ef4444"
        }
        
        cat_counts = df_filtered["wqi_category"].value_counts().reindex(cat_order).fillna(0).reset_index()
        cat_counts.columns = ["Category", "Count"]
        cat_counts["Percentage"] = (cat_counts["Count"] / total_samples) * 100
        
        fig_donut = px.pie(
            cat_counts,
            values="Count",
            names="Category",
            color="Category",
            color_discrete_map=color_map,
            hole=0.48
        )
        fig_donut.update_traces(
            textposition='inside',
            textinfo='percent+label',
            marker=dict(line=dict(color='#ffffff', width=2))
        )
        fig_donut.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=340
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_chart2:
        st.markdown("#### 🚨 Percentage of Wells Violating BIS Permissible Limits")
        exceed_data = []
        if "no3" in df_filtered:
            no3_ex = (df_filtered["no3"] > 45.0).sum() / total_samples * 100
            exceed_data.append({"Contaminant": "Nitrate (NO3 > 45 mg/L)", "Rate": round(no3_ex, 1)})
        if "tds" in df_filtered:
            tds_ex = (df_filtered["tds"] > 2000.0).sum() / total_samples * 100
            exceed_data.append({"Contaminant": "TDS (> 2000 mg/L)", "Rate": round(tds_ex, 1)})
        if "f" in df_filtered:
            f_valid = df_filtered["f"].dropna()
            f_ex = (f_valid > 1.5).sum() / len(f_valid) * 100 if len(f_valid) > 0 else 0
            exceed_data.append({"Contaminant": "Fluoride (F > 1.5 mg/L)", "Rate": round(f_ex, 1)})
        if "hardness" in df_filtered:
            h_ex = (df_filtered["hardness"] > 600.0).sum() / total_samples * 100
            exceed_data.append({"Contaminant": "Hardness (> 600 mg/L)", "Rate": round(h_ex, 1)})
        if "cl" in df_filtered:
            cl_ex = (df_filtered["cl"] > 1000.0).sum() / total_samples * 100
            exceed_data.append({"Contaminant": "Chloride (> 1000 mg/L)", "Rate": round(cl_ex, 1)})
            
        df_ex = pd.DataFrame(exceed_data).sort_values(by="Rate", ascending=True)
        
        fig_bar = px.bar(
            df_ex,
            x="Rate",
            y="Contaminant",
            orientation="h",
            text="Rate",
            color="Rate",
            color_continuous_scale="Reds"
        )
        fig_bar.update_traces(
            texttemplate='<b>%{text:.1f}%</b>',
            textposition='outside',
            marker=dict(line=dict(color='#b91c1c', width=1))
        )
        fig_bar.update_layout(
            coloraxis_showscale=False,
            xaxis_title="% Exceedance Rate",
            yaxis_title="",
            margin=dict(t=10, b=10, l=10, r=40),
            height=340
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("---")
    
    # 3. District Leaderboards (Top 5 Cleanest vs Top 5 Vulnerable)
    st.markdown("### 🏆 District Groundwater Vulnerability Rankings")
    col_rank1, col_rank2 = st.columns(2)
    
    with col_rank1:
        st.markdown("🟢 **Top 5 Cleanest Aquifers (Lowest Median WQI)**")
        top_clean = df_summary[["district", "median_wqi", "overall_status", "potable_pct"]].head(5).copy()
        top_clean.columns = ["District", "Median WQI", "Classification", "Potable Wells (%)"]
        st.dataframe(
            top_clean.style.format({"Median WQI": "{:.1f}", "Potable Wells (%)": "{:.1f}%"})
            .background_gradient(subset=["Potable Wells (%)"], cmap="Greens"),
            use_container_width=True,
            hide_index=True
        )
        
    with col_rank2:
        st.markdown("🔴 **Top 5 Critical Contamination Zones (Highest Median WQI)**")
        top_vuln = df_summary[["district", "median_wqi", "overall_status", "potable_pct", "primary_concern"]].tail(5).iloc[::-1].copy()
        top_vuln.columns = ["District", "Median WQI", "Classification", "Potable Wells (%)", "Primary Contaminant Concern"]
        st.dataframe(
            top_vuln.style.format({"Median WQI": "{:.1f}", "Potable Wells (%)": "{:.1f}%"})
            .background_gradient(subset=["Median WQI"], cmap="Reds"),
            use_container_width=True,
            hide_index=True
        )
