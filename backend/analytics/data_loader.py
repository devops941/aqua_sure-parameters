"""
AquaSure Backend - Data Loader
Loads the processed groundwater parquet file and caches it in memory.
Pre-computes heavy aggregations at startup so API responses are instant.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = BASE_DIR / "data" / "processed" / "tn_groundwater_2020_2025.parquet"

_dataframe_cache: pd.DataFrame | None = None
_result_cache: dict = {}


def get_dataframe() -> pd.DataFrame:
    global _dataframe_cache
    if _dataframe_cache is None:
        if not PARQUET_PATH.exists():
            raise FileNotFoundError(
                f"Processed parquet file not found at {PARQUET_PATH}. "
                "Run the data pipeline first."
            )
        df = pd.read_parquet(PARQUET_PATH)
        if "sample_date" in df.columns:
            df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce")
        if "year" not in df.columns and "sample_date" in df.columns:
            df["year"] = df["sample_date"].dt.year
        _dataframe_cache = df
    return _dataframe_cache


def cache_set(key: str, value) -> None:
    _result_cache[key] = value


def cache_get(key: str):
    return _result_cache.get(key)


def reload_dataframe() -> pd.DataFrame:
    global _dataframe_cache
    _dataframe_cache = None
    _result_cache.clear()
    return get_dataframe()
