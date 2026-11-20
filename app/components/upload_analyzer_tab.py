"""
Custom CSV Batch Analyzer Component for AquaSure Streamlit Application
Enables users, researchers, and government officials to upload their own groundwater hydrochemical
datasets (CSV), compute automated WQI, generate GIS visualizations, and download audited results.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

from src.wqi_engine import calculate_wqi_vectorized
from src.config import WQI_PARAM_STANDARDS, WQI_CATEGORIES
from app.components.map_tab import plot_scatter_map

COLOR_MAP = {
    "Excellent": "#10b981",
    "Good": "#06b6d4",
    "Poor": "#f59e0b",
    "Very Poor": "#f97316",
    "Unsuitable for Drinking": "#ef4444"
}

# Standard hydrochemical parameters and aliases
FUZZY_COL_MAPPINGS = {
    "ph": ["ph", "ph_gen", "potential_of_hydrogen", "ph_val", "ph_level", "ph_value"],
    "tds": ["tds", "total_dissolved_solids", "tds_val", "total_solids"],
    "ec": ["ec", "ec_gen", "electric_conductivity", "electrical_conductivity", "conductivity"],
    "hardness": ["hardness", "har_total", "total_hardness", "th", "hardness_total"],
    "ca": ["ca", "calcium", "ca2", "ca_val"],
    "mg": ["mg", "magnesium", "mg2", "mg_val"],
    "cl": ["cl", "chloride", "chlorides", "cl_val"],
    "so4": ["so4", "sulphate", "sulfate", "so42", "sulphates", "sulfates"],
    "no3": ["no3", "nitrate", "nitrates", "no3_val"],
    "f": ["f", "fluoride", "fluorides", "f_val"],
    "district": ["district", "dist", "location", "region", "city"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng", "long"],
    "station_name": ["station_name", "station", "well_name", "sample_name", "site"]
}

def auto_map_columns(df: pd.DataFrame):
    """Intelligently detects and maps user CSV columns using exact normalized token matching."""
    col_map = {}
    already_assigned = set()
    
    for raw_col in df.columns:
        norm_name = str(raw_col).strip().lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
        for target, aliases in FUZZY_COL_MAPPINGS.items():
            if target in already_assigned:
                continue
            if norm_name in aliases:
                col_map[raw_col] = target
                already_assigned.add(target)
                break
                
    df_renamed = df.rename(columns=col_map)
    return df_renamed, col_map

def generate_sample_csv() -> bytes:
    """Generates a downloadable sample CSV template for testing."""
    sample_data = {
        "District": ["Madurai", "Salem", "Chennai", "Coimbatore", "Kanyakumari", "Dharmapuri", "Thanjavur"],
        "Station_Name": ["Well_A1", "Borewell_S2", "Community_C3", "Industrial_CB4", "Spring_K5", "Deep_D6", "Delta_T7"],
        "Latitude": [9.9252, 11.6643, 13.0827, 11.0168, 8.0883, 12.1211, 10.7870],
        "Longitude": [78.1198, 78.1460, 80.2707, 76.9558, 77.5385, 78.1582, 79.1378],
        "pH": [7.4, 7.8, 7.2, 7.1, 7.0, 7.9, 7.3],
        "TDS": [480, 1150, 750, 410, 220, 890, 520],
        "EC": [720, 1780, 1150, 640, 340, 1380, 810],
        "Hardness": [210, 480, 310, 180, 95, 360, 230],
        "Calcium": [62, 120, 75, 48, 26, 90, 68],
        "Magnesium": [22, 45, 30, 15, 8, 33, 24],
        "Chloride": [140, 320, 210, 110, 45, 240, 160],
        "Sulphate": [95, 210, 140, 80, 32, 170, 110],
        "Nitrate": [28, 78, 35, 20, 9, 58, 32],
        "Fluoride": [0.75, 1.3, 0.6, 0.45, 0.35, 2.1, 0.8]
    }
    df_sample = pd.DataFrame(sample_data)
    csv_buf = io.StringIO()
    df_sample.to_csv(csv_buf, index=False)
    return csv_buf.getvalue().encode("utf-8")

def render_upload_analyzer_tab():
    st.markdown("### 📁 Custom Groundwater Dataset Batch Analyzer")
    st.markdown("Upload your own hydrochemical dataset in **CSV format** (e.g. from district water labs, private borewell surveys, or other regions) to perform instant automated WQI evaluation, spatial mapping, and export enriched audit reports.")
    
    # Template Download & Info Bar
    c_info1, c_info2 = st.columns([3, 1])
    with c_info1:
        st.info("💡 **Supported Columns:** `pH`, `TDS`, `EC`, `Hardness`, `Calcium`, `Magnesium`, `Chloride`, `Sulphate`, `Nitrate`, `Fluoride`, `Latitude`, `Longitude`, `District`. Column names are automatically recognized even with minor spelling variations.")
    with c_info2:
        sample_bytes = generate_sample_csv()
        st.download_button(
            label="📥 Download Sample CSV",
            data=sample_bytes,
            file_name="AquaSure_Sample_Groundwater_Template.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    st.markdown("---")
    
    # File Uploader
    uploaded_file = st.file_uploader(
        "Choose a Groundwater CSV file to analyze:",
        type=["csv"],
        help="Upload a CSV file containing chemical concentrations (mg/L)."
    )
    
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            st.success(f"✅ Successfully loaded `{uploaded_file.name}` with **{len(df_uploaded):,} rows** and **{len(df_uploaded.columns)} columns**.")
            
            # Auto-map columns
            df_mapped, detected_map = auto_map_columns(df_uploaded)
            
            # Show detected schema badge pills
            detected_chem = [k for k in detected_map.values() if k in WQI_PARAM_STANDARDS]
            st.caption(f"🔍 **Auto-detected Parameters ({len(detected_chem)}):** {', '.join(detected_chem)}")
            
            if len(detected_chem) < 2:
                st.warning("⚠️ At least 2 hydrochemical parameters (e.g., pH, TDS, EC, Hardness, Nitrate) are required to calculate WQI. Please check your column headers.")
                st.write("First 5 rows of your file:")
                st.dataframe(df_uploaded.head())
                return
                
            # Coerce chemical columns to numeric
            for c in detected_chem:
                df_mapped[c] = pd.to_numeric(df_mapped[c], errors="coerce")
                
            # Calculate WQI vectorially
            with st.spinner("Executing Weighted Arithmetic WQI math and ML potability evaluation..."):
                df_analyzed = calculate_wqi_vectorized(df_mapped)
                
            st.markdown("---")
            
            # Executive Summary KPI Metrics Row
            total_samples = len(df_analyzed)
            valid_wqi = df_analyzed["wqi"].dropna()
            med_wqi = valid_wqi.median()
            mean_wqi = valid_wqi.mean()
            potable_cnt = (df_analyzed["is_potable"] == True).sum()
            potable_pct = (potable_cnt / total_samples) * 100 if total_samples > 0 else 0
            
            status_text = "Good" if med_wqi <= 50 else ("Poor" if med_wqi <= 75 else ("Very Poor" if med_wqi <= 100 else "Unsuitable"))
            
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Total Samples Evaluated", f"{total_samples:,}")
            with k2:
                st.metric("Median WQI Score", f"{med_wqi:.1f}")
            with k3:
                st.metric("Overall Quality Category", status_text)
            with k4:
                st.metric("Potable Safe Samples", f"{potable_pct:.1f}%", f"{potable_cnt} of {total_samples}")
                
            st.markdown("---")
            
            # Charts Row: Categorical Donut & Exceedance Bar
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                st.markdown("#### WQI Classification Distribution")
                cat_order = ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]
                cat_counts = df_analyzed["wqi_category"].value_counts().reindex(cat_order).fillna(0).reset_index()
                cat_counts.columns = ["Category", "Count"]
                
                fig_cat = px.pie(
                    cat_counts,
                    values="Count",
                    names="Category",
                    color="Category",
                    color_discrete_map=COLOR_MAP,
                    hole=0.45
                )
                fig_cat.update_traces(textposition='inside', textinfo='percent+label')
                fig_cat.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=320)
                st.plotly_chart(fig_cat, use_container_width=True)
                
            with col_c2:
                st.markdown("#### Parameter Exceedance vs BIS Limits")
                ex_data = []
                for p in detected_chem:
                    meta = WQI_PARAM_STANDARDS[p]
                    s = df_analyzed[p].dropna()
                    if len(s) > 0:
                        ex_cnt = (s > meta["standard_permissible"]).sum()
                        ex_pct = (ex_cnt / len(s)) * 100
                        ex_data.append({"Parameter": meta["name"].split(" (")[0], "Exceedance (%)": round(ex_pct, 1)})
                        
                df_ex_chart = pd.DataFrame(ex_data).sort_values(by="Exceedance (%)", ascending=True)
                
                fig_ex = px.bar(
                    df_ex_chart,
                    x="Exceedance (%)",
                    y="Parameter",
                    orientation="h",
                    text="Exceedance (%)",
                    color="Exceedance (%)",
                    color_continuous_scale="Reds"
                )
                fig_ex.update_traces(texttemplate='<b>%{text:.1f}%</b>', textposition='outside')
                fig_ex.update_layout(coloraxis_showscale=False, height=320, margin=dict(t=10, b=10, l=10, r=40))
                st.plotly_chart(fig_ex, use_container_width=True)
                
            # Optional GIS Map if latitude & longitude are present
            if "latitude" in df_analyzed.columns and "longitude" in df_analyzed.columns:
                df_geo = df_analyzed.dropna(subset=["latitude", "longitude"]).copy()
                if len(df_geo) > 0:
                    st.markdown("#### 🗺️ Geospatial Distribution of Uploaded Samples")
                    map_center_lat = float(df_geo["latitude"].median())
                    map_center_lon = float(df_geo["longitude"].median())
                    
                    fig_map = plot_scatter_map(
                        df_geo,
                        lat="latitude",
                        lon="longitude",
                        color="wqi_category",
                        color_discrete_map=COLOR_MAP,
                        zoom=7,
                        center={"lat": map_center_lat, "lon": map_center_lon},
                        mapbox_style="carto-positron",
                        hover_name="station_name" if "station_name" in df_geo.columns else None
                    )
                    fig_map.update_layout(height=450, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_map, use_container_width=True)
                    
            # Analyzed Data Table with Export
            st.markdown("#### 📑 Analyzed Hydrochemical Dataset with Calculated WQI Scores")
            st.dataframe(df_analyzed.head(50), use_container_width=True)
            
            # Export enriched CSV button
            csv_enriched = io.StringIO()
            df_analyzed.to_csv(csv_enriched, index=False)
            
            st.download_button(
                label="⬇️ Download Full Audited Results (CSV with WQI Scores)",
                data=csv_enriched.getvalue().encode("utf-8"),
                file_name=f"AquaSure_Audited_{uploaded_file.name}",
                mime="text/csv",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Error reading or analyzing uploaded file: {e}")
    else:
        # Placeholder banner when no file is uploaded yet
        st.markdown("""
        <div style="border: 2px dashed #cbd5e1; border-radius: 12px; padding: 40px 20px; text-align: center; background: #f8fafc; margin-top: 20px;">
            <div style="font-size: 2.5rem; margin-bottom: 10px;">📊</div>
            <h4 style="margin: 0px 0px 8px 0px; color: #1e293b;">No Custom Dataset Uploaded Yet</h4>
            <p style="color: #64748b; font-size: 0.92rem; max-width: 500px; margin: 0 auto 16px auto;">
                Drag and drop any water laboratory CSV above, or download our ready-to-use sample template to test batch WQI calculations.
            </p>
        </div>
        """, unsafe_allow_html=True)
