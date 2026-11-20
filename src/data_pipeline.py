"""
AquaSure Data Pipeline Module
Cleans, standardizes, validates, and processes the raw Tamil Nadu groundwater quality dataset
without synthetic hallucinations or overwriting the original raw dataset.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.config import (
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    PROCESSED_CSV_PATH,
    FILTERED_2020_2025_PATH,
    FILTERED_CSV_PATH,
    RAW_TO_CLEAN_COLS,
    DISTRICT_ALIASES,
    WQI_PARAM_STANDARDS,
    TN_38_DISTRICTS
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_raw_dataset(csv_path=RAW_DATA_PATH) -> pd.DataFrame:
    """Loads the original raw CSV safely in read-only mode."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Raw dataset not found at {csv_path}")
    logger.info(f"Loading raw dataset from {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    logger.info(f"Raw dataset loaded: {df.shape[0]:,} rows, {df.shape[1]} columns.")
    return df

def clean_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw dataset:
    - Renames columns to standardized clean names
    - Strips whitespace
    - Normalizes district names across all 38 TN districts
    - Parses sampling dates (dayfirst=True)
    - Coerces hydrochemical parameters to numeric
    - Sanitizes physically impossible sensor drops (e.g. pH=0, negative values)
    """
    logger.info("Standardizing column names...")
    # Rename columns that exist in the mapping
    rename_dict = {k: v for k, v in RAW_TO_CLEAN_COLS.items() if k in df.columns}
    df = df.rename(columns=rename_dict).copy()
    
    # Clean text columns
    text_cols = ["station_code", "station_name", "agency_name", "state", "district", "tahsil_name"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "-": None, "--": None, "": None})
            
    # Normalize district names
    if "district" in df.columns:
        df["district"] = df["district"].str.title()
        df["district"] = df["district"].replace(DISTRICT_ALIASES)
        logger.info(f"Districts present after normalization: {df['district'].nunique()} districts.")
        
    # Date parsing
    if "sample_date" in df.columns:
        logger.info("Parsing sample dates...")
        df["parsed_date"] = pd.to_datetime(df["sample_date"], dayfirst=True, errors="coerce")
        df["year"] = df["parsed_date"].dt.year
        df["month"] = df["parsed_date"].dt.month
        df["year_month"] = df["parsed_date"].dt.to_period("M").astype(str)
        # Handle cases where year is missing from unparseable dates
        valid_dates = df["parsed_date"].notna().sum()
        logger.info(f"Successfully parsed {valid_dates:,} dates out of {len(df):,}.")
    
    # Numeric sanitization for chemical parameters
    chem_cols = [
        "ec", "ph", "tds", "no3", "no3_n", "hardness", "co3", "ca",
        "cl", "hco3", "k", "mg", "na", "so4", "f", "na_pct", "rsc", "sar"
    ]
    
    logger.info("Coercing chemical parameters to numeric and validating physical bounds...")
    for col in chem_cols:
        if col in df.columns:
            # Replace non-numeric symbols like '--', 'b', spaces
            df[col] = pd.to_numeric(df[col].replace({"--": np.nan, "b": np.nan, "-": np.nan}), errors="coerce")
            # Replace negative values with NaN (impossible for concentration)
            df.loc[df[col] < 0, col] = np.nan
            
    # Physical plausibility corrections without data hallucination:
    # 1. pH in natural groundwater cannot be 0. pH < 4.0 or > 11.5 indicates corrupted sensor readout
    if "ph" in df.columns:
        invalid_ph = (df["ph"] < 4.0) | (df["ph"] > 11.5)
        logger.info(f"Detected {invalid_ph.sum()} invalid pH readings (<4 or >11.5), converting to NaN.")
        df.loc[invalid_ph, "ph"] = np.nan
        
    # 2. TDS cannot be 0 mg/L in groundwater. If EC is present and positive, TDS ~= 0.64 * EC
    if "tds" in df.columns and "ec" in df.columns:
        zero_tds = (df["tds"] == 0) & (df["ec"] > 0)
        logger.info(f"Correcting {zero_tds.sum()} zero TDS readings using standard hydrochemical ratio (0.64 * EC).")
        df.loc[zero_tds, "tds"] = (df.loc[zero_tds, "ec"] * 0.64).round(2)
        df.loc[df["tds"] == 0, "tds"] = np.nan
        
    # Ensure coordinates are floats
    for coord in ["latitude", "longitude"]:
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")
            
    logger.info("Clean and validation step completed.")
    return df

def filter_analytical_window(df: pd.DataFrame, start_year: int = 2020, end_year: int = 2025) -> pd.DataFrame:
    """Filters dataset to the requested analysis window (2020–2025)."""
    if "year" not in df.columns:
        raise ValueError("Year column not found in DataFrame.")
    filtered_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    logger.info(f"Filtered analytical window ({start_year}–{end_year}): {len(filtered_df):,} records across {filtered_df['district'].nunique()} districts.")
    return filtered_df

def run_pipeline():
    """Executes the complete data preparation pipeline."""
    df_raw = load_raw_dataset()
    df_clean = clean_and_validate(df_raw)
    
    # Save full clean data
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(PROCESSED_DATA_PATH, index=False)
    # Save CSV version for universal access
    df_clean.to_csv(PROCESSED_CSV_PATH, index=False)
    logger.info(f"Saved full clean dataset to {PROCESSED_DATA_PATH} & {PROCESSED_CSV_PATH}")
    
    # Filter 2020–2025 window
    df_2020_2025 = filter_analytical_window(df_clean, 2020, 2025)
    df_2020_2025.to_parquet(FILTERED_2020_2025_PATH, index=False)
    df_2020_2025.to_csv(FILTERED_CSV_PATH, index=False)
    logger.info(f"Saved 2020–2025 dataset to {FILTERED_2020_2025_PATH} & {FILTERED_CSV_PATH}")
    
    return df_clean, df_2020_2025

if __name__ == "__main__":
    run_pipeline()
