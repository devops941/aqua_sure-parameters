"""
Trends Tab Component for AquaSure Streamlit Application
Multi-year temporal and seasonal groundwater quality dynamics across Tamil Nadu (2020–2025).
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_trends_tab(df: pd.DataFrame):
    st.markdown("### Temporal & Multi-Year Trends (2020–2025)")
    st.markdown("Examine how groundwater quality, ionic concentrations, and WQI categories evolved across Tamil Nadu over the 5-year monitoring horizon.")
    
    # 1. Multi-District Annual WQI Trajectory
    st.markdown("#### District Annual WQI Comparison (2020–2025)")
    
    all_districts = sorted(df["district"].dropna().unique().tolist())
    default_selection = ["Chennai", "Coimbatore", "Madurai", "Salem", "Kanyakumari"]
    default_districts = [d for d in default_selection if d in all_districts]
    
    selected_compare = st.multiselect(
        "Select Districts to Compare Over Time:",
        options=all_districts,
        default=default_districts
    )
    
    if selected_compare:
        df_comp = df[df["district"].isin(selected_compare)].copy()
        annual_dist = df_comp.groupby(["district", "year"])["wqi"].median().reset_index()
        
        fig_trend = px.line(
            annual_dist,
            x="year",
            y="wqi",
            color="district",
            markers=True,
            title="Annual Median WQI Trajectory (Lower is Better Quality)",
            labels={"year": "Monitoring Year", "wqi": "Median WQI", "district": "District"}
        )
        # Add horizontal threshold line for Potable limit (50)
        fig_trend.add_hline(y=50, line_dash="dash", line_color="#10b981", annotation_text="Potable Threshold (WQI = 50)")
        fig_trend.add_hline(y=100, line_dash="dot", line_color="#ef4444", annotation_text="Hazardous Threshold (WQI = 100)")
        fig_trend.update_layout(xaxis=dict(tickmode="linear", dtick=1), height=400, margin=dict(t=40, b=20, l=10, r=10))
        st.plotly_chart(fig_trend, use_container_width=True)
    
    st.markdown("---")
    
    # 2. Key Contaminants Multi-Year Evolution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Statewide Annual Mean Contaminant Evolution")
        param_to_trend = st.selectbox(
            "Select Chemical Parameter:",
            ["tds", "no3", "f", "hardness", "cl", "ec"],
            format_func=lambda x: {
                "tds": "Total Dissolved Solids (TDS)",
                "no3": "Nitrate (NO3)",
                "f": "Fluoride (F)",
                "hardness": "Total Hardness",
                "cl": "Chloride (Cl)",
                "ec": "Electrical Conductivity (EC)"
            }[x]
        )
        
        annual_param = df.groupby("year")[param_to_trend].agg(["mean", "median"]).reset_index()
        
        fig_param = go.Figure()
        fig_param.add_trace(go.Bar(
            x=annual_param["year"],
            y=annual_param["mean"],
            name="Annual Mean",
            marker_color="#0284c7"
        ))
        fig_param.add_trace(go.Scatter(
            x=annual_param["year"],
            y=annual_param["median"],
            name="Annual Median",
            mode="lines+markers",
            line=dict(color="#f97316", width=2.5)
        ))
        fig_param.update_layout(
            xaxis=dict(tickmode="linear", dtick=1),
            yaxis_title=f"{param_to_trend.upper()} Concentration",
            xaxis_title="Year",
            height=340,
            margin=dict(t=20, b=20, l=10, r=10)
        )
        st.plotly_chart(fig_param, use_container_width=True)
        
    with col2:
        st.markdown("#### Seasonal / Monthly Recharge & Dilution Patterns")
        # Group by month
        df_valid_month = df[df["month"].notna()].copy()
        df_valid_month["month_name"] = pd.to_datetime(df_valid_month["month"], format="%m").dt.strftime("%b")
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        monthly_wqi = df_valid_month.groupby(["month", "month_name"])["wqi"].median().reset_index()
        monthly_wqi = monthly_wqi.sort_values(by="month")
        
        fig_season = px.bar(
            monthly_wqi,
            x="month_name",
            y="wqi",
            color="wqi",
            color_continuous_scale="Blues_r",
            title="Monthly Median WQI (Demonstrating Monsoon Dilution)",
            labels={"month_name": "Month", "wqi": "Median WQI"}
        )
        fig_season.update_layout(height=340, margin=dict(t=40, b=20, l=10, r=10))
        st.plotly_chart(fig_season, use_container_width=True)
