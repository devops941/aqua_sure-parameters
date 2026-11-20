"""
Map Tab Component for AquaSure Streamlit Application
Interactive Geospatial GIS visualizer for Tamil Nadu groundwater monitoring stations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

COLOR_MAP = {
    "Excellent": "#10b981",
    "Good": "#06b6d4",
    "Poor": "#f59e0b",
    "Very Poor": "#f97316",
    "Unsuitable for Drinking": "#ef4444"
}

def plot_scatter_map(df, **kwargs):
    """Compatible with Plotly 7+ (scatter_map) and legacy Plotly (scatter_mapbox)."""
    if hasattr(px, "scatter_map"):
        if "mapbox_style" in kwargs:
            kwargs["map_style"] = kwargs.pop("mapbox_style")
        return px.scatter_map(df, **kwargs)
    elif hasattr(px, "scatter_mapbox"):
        if "map_style" in kwargs:
            kwargs["mapbox_style"] = kwargs.pop("map_style")
        return px.scatter_mapbox(df, **kwargs)
    else:
        return px.scatter_geo(df, **kwargs)

def render_map_tab(df: pd.DataFrame, df_summary: pd.DataFrame):
    st.markdown("### Interactive Geospatial Groundwater Map")
    st.markdown("Explore observation well locations, hydrochemical concentrations, and WQI classifications across Tamil Nadu.")
    
    # Map Controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    
    with col_ctrl1:
        map_mode = st.radio(
            "Visualization Mode:",
            ["Individual Observation Wells (High Resolution)", "District Centroids Aggregation"],
            horizontal=True
        )
    
    with col_ctrl2:
        selected_category = st.multiselect(
            "Filter by WQI Grade:",
            options=["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"],
            default=["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]
        )
        
    with col_ctrl3:
        size_param = st.selectbox(
            "Marker Size Metric:",
            ["Fixed Size", "Total Dissolved Solids (TDS)", "Nitrate (NO3)", "Fluoride (F)", "Total Hardness"]
        )
        
    param_col_map = {
        "Total Dissolved Solids (TDS)": "tds",
        "Nitrate (NO3)": "no3",
        "Fluoride (F)": "f",
        "Total Hardness": "hardness"
    }

    if map_mode == "Individual Observation Wells (High Resolution)":
        # Filter data
        map_df = df[df["wqi_category"].isin(selected_category)].copy()
        
        # Limit rows for smooth rendering if dataset is huge, but sample stratified
        if len(map_df) > 8000:
            map_df = map_df.sample(n=8000, random_state=42)
            st.caption("ℹ️ Displaying a representative sample of 8,000 monitoring stations for optimal map responsiveness.")
        else:
            st.caption(f"ℹ️ Displaying {len(map_df):,} monitoring stations.")
            
        size_arg = None
        if size_param != "Fixed Size":
            actual_col = param_col_map[size_param]
            map_df["size_metric"] = map_df[actual_col].fillna(0).clip(lower=0)
            size_arg = "size_metric"
            
        # Hover info
        map_df["hover_text"] = (
            "<b>Station:</b> " + map_df["station_name"].fillna("Unknown") + "<br>" +
            "<b>Code:</b> " + map_df["station_code"].fillna("-") + "<br>" +
            "<b>District:</b> " + map_df["district"] + "<br>" +
            "<b>WQI Score:</b> " + map_df["wqi"].astype(str) + " (" + map_df["wqi_category"] + ")<br>" +
            "<b>Status:</b> " + map_df["potability_status"] + "<br>" +
            "<b>TDS:</b> " + map_df["tds"].round(1).astype(str) + " mg/L<br>" +
            "<b>NO3:</b> " + map_df["no3"].round(1).astype(str) + " mg/L<br>" +
            "<b>Fluoride:</b> " + map_df["f"].round(2).astype(str) + " mg/L"
        )
        
        fig = plot_scatter_map(
            map_df,
            lat="latitude",
            lon="longitude",
            color="wqi_category",
            color_discrete_map=COLOR_MAP,
            category_orders={"wqi_category": ["Excellent", "Good", "Poor", "Very Poor", "Unsuitable for Drinking"]},
            size=size_arg,
            size_max=14 if size_arg else None,
            zoom=6.3,
            center={"lat": 11.1271, "lon": 78.6569},
            mapbox_style="carto-positron",
            hover_name="station_name",
            custom_data=["station_code", "district", "wqi", "wqi_category", "potability_status"]
        )
        
        if not size_arg:
            fig.update_traces(marker=dict(size=6, opacity=0.75))
            
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=620,
            legend=dict(
                title="WQI Classification",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        # District Centroids Aggregation Mode
        # Compute district centroids from station coordinates
        dist_centroids = df.groupby("district").agg(
            lat=("latitude", "mean"),
            lon=("longitude", "mean")
        ).reset_index()
        
        merged_dist = pd.merge(df_summary, dist_centroids, on="district")
        
        fig = plot_scatter_map(
            merged_dist,
            lat="lat",
            lon="lon",
            color="overall_status",
            color_discrete_map=COLOR_MAP,
            size="total_samples",
            size_max=28,
            zoom=6.3,
            center={"lat": 11.1271, "lon": 78.6569},
            mapbox_style="carto-positron",
            hover_name="district",
            hover_data={
                "lat": False,
                "lon": False,
                "median_wqi": True,
                "potable_pct": True,
                "total_samples": True,
                "primary_concern": True
            }
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=620,
            legend=dict(
                title="District Status",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig, use_container_width=True)
