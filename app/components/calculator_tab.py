"""
Potability Calculator & Lab Sample Checker Component for AquaSure Streamlit Application
Interactive tool enabling users/engineers to enter laboratory test parameters, compute WAWQI,
and receive real-time ML potability predictions and water treatment guidance.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.wqi_engine import compute_sample_wqi
from src.potability_classifier import predict_single_sample
from src.config import WQI_PARAM_STANDARDS

def render_calculator_tab():
    st.markdown("### Interactive Potability Calculator & Lab Sample Checker")
    st.markdown("Input laboratory test measurements for any groundwater sample to compute the **Weighted Arithmetic WQI**, predict **machine learning potability**, and receive custom purification recommendations.")
    
    # Pre-set presets for convenient testing
    col_pre, col_blank = st.columns([1, 2])
    with col_pre:
        preset = st.selectbox(
            "Quick Load Test Presets:",
            ["Custom Input", "Pristine Drinking Water (Grade A)", "Agricultural Well with High Nitrate (Grade D)", "Coastal Saline Well with High TDS (Grade E)"]
        )
        
    # Default values based on preset
    presets_data = {
        "Custom Input": {"ph": 7.3, "tds": 420.0, "ec": 650.0, "hardness": 180.0, "ca": 55.0, "mg": 22.0, "cl": 120.0, "so4": 85.0, "no3": 22.0, "f": 0.65},
        "Pristine Drinking Water (Grade A)": {"ph": 7.2, "tds": 210.0, "ec": 320.0, "hardness": 95.0, "ca": 28.0, "mg": 12.0, "cl": 45.0, "so4": 30.0, "no3": 8.0, "f": 0.4},
        "Agricultural Well with High Nitrate (Grade D)": {"ph": 7.6, "tds": 980.0, "ec": 1450.0, "hardness": 450.0, "ca": 110.0, "mg": 45.0, "cl": 310.0, "so4": 180.0, "no3": 85.0, "f": 1.2},
        "Coastal Saline Well with High TDS (Grade E)": {"ph": 8.1, "tds": 2850.0, "ec": 4200.0, "hardness": 780.0, "ca": 190.0, "mg": 85.0, "cl": 1420.0, "so4": 420.0, "no3": 35.0, "f": 0.9}
    }
    
    current_values = presets_data[preset]
    
    st.markdown("#### Enter Hydrochemical Parameters:")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        val_ph = st.number_input("pH (4.0 - 10.0):", min_value=4.0, max_value=11.0, value=float(current_values["ph"]), step=0.1)
        val_tds = st.number_input("Total Dissolved Solids (TDS, mg/L):", min_value=0.0, max_value=20000.0, value=float(current_values["tds"]), step=10.0)
        val_ec = st.number_input("Electrical Conductivity (EC, µS/cm):", min_value=0.0, max_value=30000.0, value=float(current_values["ec"]), step=25.0)
        val_hardness = st.number_input("Total Hardness (mg/L CaCO3):", min_value=0.0, max_value=5000.0, value=float(current_values["hardness"]), step=10.0)
        
    with c2:
        val_ca = st.number_input("Calcium (Ca, mg/L):", min_value=0.0, max_value=1500.0, value=float(current_values["ca"]), step=5.0)
        val_mg = st.number_input("Magnesium (Mg, mg/L):", min_value=0.0, max_value=1000.0, value=float(current_values["mg"]), step=5.0)
        val_cl = st.number_input("Chloride (Cl, mg/L):", min_value=0.0, max_value=10000.0, value=float(current_values["cl"]), step=10.0)
        
    with c3:
        val_so4 = st.number_input("Sulphate (SO4, mg/L):", min_value=0.0, max_value=3000.0, value=float(current_values["so4"]), step=5.0)
        val_no3 = st.number_input("Nitrate (NO3, mg/L):", min_value=0.0, max_value=1000.0, value=float(current_values["no3"]), step=1.0)
        val_f = st.number_input("Fluoride (F, mg/L):", min_value=0.0, max_value=15.0, value=float(current_values["f"]), step=0.05)
        
    sample_payload = {
        "ph": val_ph,
        "tds": val_tds,
        "ec": val_ec,
        "hardness": val_hardness,
        "ca": val_ca,
        "mg": val_mg,
        "cl": val_cl,
        "so4": val_so4,
        "no3": val_no3,
        "f": val_f
    }
    
    st.markdown("---")
    
    # Perform Evaluation
    wqi_res = compute_sample_wqi(pd.Series(sample_payload))
    ml_res = predict_single_sample(sample_payload)
    
    # Results Display
    st.markdown("### Analysis Results & Potability Verdict")
    
    res_col1, res_col2 = st.columns([1, 1])
    
    with res_col1:
        # Gauge chart for WQI
        wqi_val = wqi_res["wqi"]
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=wqi_val,
            title={'text': f"WQI Score: {wqi_res['category']} (Grade {wqi_res['grade']})", 'font': {'size': 18}},
            gauge={
                'axis': {'range': [0, 150]},
                'bar': {'color': wqi_res['color']},
                'steps': [
                    {'range': [0, 25], 'color': '#d1fae5'},
                    {'range': [25, 50], 'color': '#cffafe'},
                    {'range': [50, 75], 'color': '#fef3c7'},
                    {'range': [75, 100], 'color': '#ffedd5'},
                    {'range': [100, 150], 'color': '#fee2e2'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(t=40, b=10, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with res_col2:
        st.markdown("#### Potability Assessment")
        if wqi_res["is_potable"]:
            st.success(f"✅ **Verdict: {wqi_res['potability']}**")
        elif "Basic" in wqi_res["potability"]:
            st.warning(f"⚠️ **Verdict: {wqi_res['potability']}**")
        else:
            st.error(f"🚨 **Verdict: {wqi_res['potability']}**")
            
        st.markdown(f"**Random Forest ML Confidence:** `{ml_res['potability_confidence']*100:.1f}%` ({ml_res['verdict']})")
        
        # Violations display
        if wqi_res["violations"]:
            st.markdown("##### ⚠️ Standard Limit Violations:")
            for v in wqi_res["violations"]:
                st.markdown(f"- 🔴 {v}")
        else:
            st.markdown("##### ✅ Compliance:")
            st.markdown("- All parameters remain within BIS 10500 permissible drinking standards.")
            
    # Remediation Action Blueprint
    st.markdown("#### Recommended Water Treatment Technology:")
    treatment_recs = []
    if val_no3 > 45.0:
        treatment_recs.append("🧪 **Nitrate Removal:** Install strong base anion exchange (SBA) resin or reverse osmosis (RO) system.")
    if val_f > 1.5:
        treatment_recs.append("💎 **Defluoridation:** Deploy activated alumina filter cartridge or Nalgonda technique.")
    if val_tds > 1000.0 or val_cl > 500.0:
        treatment_recs.append("🌊 **Desalination:** Commercial Reverse Osmosis (RO) with semi-permeable thin-film membrane.")
    if val_hardness > 300.0:
        treatment_recs.append("🧼 **Water Softening:** Cation exchange water softener to eliminate scale formation and hardness ions.")
    if not treatment_recs:
        treatment_recs.append("💧 **Standard Disinfection:** Multi-stage sediment filtration (5 micron) followed by UV (ultraviolet) sterilization is sufficient for safe consumption.")
        
    for tr in treatment_recs:
        st.info(tr)
