"""
AquaSure End-to-End Pipeline Execution Script
Runs cleaning, WQI vector calculation, potability indicators, and generates 38-district summaries.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import logging
import os
from src.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    PROCESSED_CSV_PATH,
    FILTERED_2020_2025_PATH,
    FILTERED_CSV_PATH,
    DISTRICT_SUMMARY_PATH
)
from src.data_pipeline import load_raw_dataset, clean_and_validate, filter_analytical_window
from src.wqi_engine import calculate_wqi_vectorized, generate_district_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting AquaSure Data & WQI Pipeline...")
    
    # 1. Load Raw
    df_raw = load_raw_dataset(RAW_DATA_PATH)
    
    # 2. Clean & Validate
    df_clean = clean_and_validate(df_raw)
    
    # 3. Calculate Vectorized WQI across all records
    logger.info("Computing Weighted Arithmetic WQI & potability status for all records...")
    df_wqi = calculate_wqi_vectorized(df_clean)
    
    # Save full processed dataset
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_wqi.to_parquet(PROCESSED_DATA_PATH, index=False)
    df_wqi.to_csv(PROCESSED_CSV_PATH, index=False)
    logger.info(f"Full WQI dataset saved to {PROCESSED_DATA_PATH} & CSV ({len(df_wqi):,} records)")
    
    # 4. Filter Target Window: 2020–2025
    df_2020_2025 = filter_analytical_window(df_wqi, start_year=2020, end_year=2025)
    df_2020_2025.to_parquet(FILTERED_2020_2025_PATH, index=False)
    df_2020_2025.to_csv(FILTERED_CSV_PATH, index=False)
    logger.info(f"Analytical Window (2020–2025) saved to {FILTERED_2020_2025_PATH} ({len(df_2020_2025):,} records)")
    
    # 5. Generate District-Level Summary for 2020–2025
    logger.info("Generating District-Level WQI Summary for all 38 districts (2020–2025)...")
    district_summary = generate_district_summary(df_2020_2025)
    district_summary.to_csv(DISTRICT_SUMMARY_PATH, index=False)
    logger.info(f"Saved District Summary to {DISTRICT_SUMMARY_PATH} ({len(district_summary)} districts)")
    
    print("\n" + "="*80)
    print("AQUASURE PIPELINE SUMMARY (2020–2025 TARGET PERIOD)")
    print("="*80)
    print(f"Total Evaluated Samples (2020-2025): {len(df_2020_2025):,}")
    print(f"Districts Covered: {district_summary['district'].nunique()} out of 38")
    print(f"Statewide Mean WQI: {df_2020_2025['wqi'].mean():.2f}")
    print(f"Statewide Median WQI: {df_2020_2025['wqi'].median():.2f}")
    print(f"Overall Potable Samples: {(df_2020_2025['is_potable'].sum() / len(df_2020_2025))*100:.1f}%")
    print("\nWQI Category Breakdown (2020–2025):")
    cat_counts = df_2020_2025['wqi_category'].value_counts()
    for cat, cnt in cat_counts.items():
        pct = (cnt / len(df_2020_2025)) * 100
        print(f"  - {cat:25s}: {cnt:6,d} ({pct:5.1f}%)")
        
    print("\nTop 5 Districts with BEST Groundwater Quality (Lowest Median WQI):")
    print(district_summary[["district", "median_wqi", "overall_status", "potable_pct"]].head(5).to_string(index=False))
    
    print("\nTop 5 Districts with HIGHEST Contamination Risk (Highest Median WQI):")
    print(district_summary[["district", "median_wqi", "overall_status", "potable_pct", "primary_concern"]].tail(5).to_string(index=False))
    print("="*80)

if __name__ == "__main__":
    main()
