"""
Correlation & Hydrochemical Tab Component for AquaSure Streamlit Application
Employs SciPy, Seaborn, Matplotlib, and Plotly to analyze hydrochemical ionic relationships,
salinity hazards (SAR vs EC), and geochemical facies.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pandas as pd
import numpy as np

def render_correlation_tab(df: pd.DataFrame):
    st.markdown("### Hydrochemical & Statistical Correlation Analysis")
    st.markdown("Investigate geochemical relationships, ionic balances, and agricultural salinity hazards using **SciPy, Seaborn, Matplotlib, and Plotly**.")
    
    # 1. Pearson / Spearman Correlation Heatmap
    st.markdown("#### 1. Ionic Species Inter-Correlation Matrix")
    
    col_opt1, col_opt2 = st.columns([1, 2])
    with col_opt1:
        corr_method = st.radio("Correlation Method:", ["Pearson (Linear)", "Spearman (Rank-order)"], horizontal=True)
        method_key = "pearson" if "Pearson" in corr_method else "spearman"
        
    chem_params = ["ph", "ec", "tds", "hardness", "ca", "mg", "cl", "so4", "no3", "f", "na", "k"]
    valid_chem = [c for c in chem_params if c in df.columns]
    
    corr_df = df[valid_chem].dropna().corr(method=method_key)
    
    fig_corr = px.imshow(
        corr_df,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        range_color=[-1, 1],
        title=f"Groundwater Chemical Correlation Matrix ({corr_method})",
        labels=dict(color="Correlation")
    )
    fig_corr.update_layout(height=480, margin=dict(t=40, b=20, l=10, r=10))
    st.plotly_chart(fig_corr, use_container_width=True)
    
    st.markdown("---")
    
    # 2. SciPy Statistical Bivariate Regression & Significance
    st.markdown("#### 2. SciPy Statistical Hypothesis & Regression Test")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        param_x = st.selectbox("Select Parameter X:", valid_chem, index=valid_chem.index("ec") if "ec" in valid_chem else 0)
    with col_p2:
        param_y = st.selectbox("Select Parameter Y:", valid_chem, index=valid_chem.index("tds") if "tds" in valid_chem else 1)
        
    sample_sub = df[[param_x, param_y]].dropna()
    if len(sample_sub) > 4000:
        sample_sub = sample_sub.sample(4000, random_state=42)
        
    # SciPy Linear Regression & Correlation
    slope, intercept, r_value, p_value, std_err = stats.linregress(sample_sub[param_x], sample_sub[param_y])
    pearson_r, p_val = stats.pearsonr(sample_sub[param_x], sample_sub[param_y])
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("Correlation (r)", f"{r_value:.4f}")
    with col_stat2:
        st.metric("R-Squared (R²)", f"{r_value**2:.4f}")
    with col_stat3:
        p_text = "< 0.0001" if p_value < 0.0001 else f"{p_value:.4f}"
        st.metric("p-value (Significance)", p_text)
    with col_stat4:
        st.metric("Regression Slope", f"{slope:.4f}")
        
    fig_scatter = px.scatter(
        sample_sub,
        x=param_x,
        y=param_y,
        opacity=0.45,
        title=f"Bivariate Regression: {param_y.upper()} vs {param_x.upper()} (r = {r_value:.3f}, R² = {r_value**2:.3f}, p {p_text})"
    )
    fig_scatter.update_traces(marker=dict(size=5, color="#0284c7"), name="Observations")
    
    # Native SciPy regression fit line
    x_min, x_max = float(sample_sub[param_x].min()), float(sample_sub[param_x].max())
    x_line = np.linspace(x_min, x_max, 100)
    y_line = slope * x_line + intercept
    fig_scatter.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode="lines",
        name=f"SciPy Fit (y = {slope:.2f}x + {intercept:.1f})",
        line=dict(color="#ef4444", width=2.5)
    ))
    fig_scatter.update_layout(height=400, margin=dict(t=40, b=20, l=10, r=10), legend=dict(orientation="h", y=1.05, x=0.7))
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("---")
    
    # 3. Agricultural & Irrigation Hazard (Wilcox / US Salinity Laboratory Diagram)
    st.markdown("#### 3. Irrigation Water Suitability: Salinity Hazard (EC) vs Sodium Hazard (SAR)")
    if "sar" in df.columns and "ec" in df.columns:
        sar_df = df[["ec", "sar", "district"]].dropna().copy()
        if len(sar_df) > 3000:
            sar_df = sar_df.sample(3000, random_state=42)
            
        fig_wilcox = px.scatter(
            sar_df,
            x="ec",
            y="sar",
            color="district",
            opacity=0.6,
            log_x=True,
            title="Sodium Adsorption Ratio (SAR) vs Electrical Conductivity (EC)",
            labels={"ec": "Electrical Conductivity (µS/cm, Log Scale)", "sar": "Sodium Adsorption Ratio (SAR)"}
        )
        fig_wilcox.add_hrect(y0=0, y1=10, line_width=0, fillcolor="green", opacity=0.08, annotation_text="Low Sodium Hazard (S1)")
        fig_wilcox.add_hrect(y0=10, y1=18, line_width=0, fillcolor="yellow", opacity=0.08, annotation_text="Medium Sodium Hazard (S2)")
        fig_wilcox.add_hrect(y0=18, y1=26, line_width=0, fillcolor="orange", opacity=0.08, annotation_text="High Sodium Hazard (S3)")
        fig_wilcox.update_layout(height=420, showlegend=False, margin=dict(t=40, b=20, l=10, r=10))
        st.plotly_chart(fig_wilcox, use_container_width=True)
