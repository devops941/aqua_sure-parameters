import pandas as pd
import numpy as np
import json
import os

CSV_PATH = "data/raw/tamilnadu_groundwater_2020_2025.csv"

def inspect():
    print(f"=== AQUASURE DATASET INSPECTION ===")
    print(f"Dataset path: {os.path.abspath(CSV_PATH)}")
    print(f"File size: {os.path.getsize(CSV_PATH) / (1024*1024):.2f} MB")
    
    # 2. Read dataset
    df = pd.read_csv(CSV_PATH, low_memory=False)
    total_rows, total_cols = df.shape
    print(f"Total Rows: {total_rows:,}")
    print(f"Total Columns: {total_cols}")
    
    # 3. Columns
    print("\n--- Columns List ---")
    for idx, col in enumerate(df.columns, 1):
        print(f"{idx:2d}. {col}")
        
    # 4. Data types
    print("\n--- Data Types ---")
    print(df.dtypes)
    
    # 5. Date column and date format
    date_col = "Sample Collection Date"
    print(f"\n--- Date Column: {date_col} ---")
    sample_dates = df[date_col].dropna().head(10).tolist()
    print("Sample date strings:", sample_dates)
    
    # Parse dates with format detection
    # Typical formats: DD-MM-YYYY or YYYY-MM-DD
    df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
    df['year'] = df['parsed_date'].dt.year
    unparseable_dates = df[date_col].notna() & df['parsed_date'].isna()
    print(f"Unparseable date count: {unparseable_dates.sum()}")
    
    # Year distribution
    print("\n--- Record Counts by Year (All Years Found) ---")
    year_counts = df['year'].value_counts(dropna=False).sort_index()
    print(year_counts)
    
    print("\n--- Records 2020 - 2025 specifically ---")
    for yr in range(2020, 2026):
        count = (df['year'] == yr).sum()
        print(f"Year {yr}: {count:,} records")
    total_2020_2025 = ((df['year'] >= 2020) & (df['year'] <= 2025)).sum()
    print(f"Total 2020-2025 records: {total_2020_2025:,} (out of {total_rows:,})")

    # 6, 7, 8. District Verification
    district_col = "District"
    raw_districts = df[district_col].dropna().unique()
    raw_districts_sorted = sorted([str(d).strip() for d in raw_districts])
    print(f"\n--- District Analysis ---")
    print(f"Unique districts found in dataset ({len(raw_districts_sorted)}):")
    print(", ".join(raw_districts_sorted))
    
    # Standard 38 districts of Tamil Nadu
    tn_38_districts = [
        "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
        "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
        "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
        "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
        "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi",
        "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli",
        "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur",
        "Vellore", "Viluppuram", "Virudhunagar"
    ]
    
    dataset_districts_clean = set(d.title() for d in raw_districts_sorted)
    tn_38_set = set(tn_38_districts)
    
    matched = dataset_districts_clean.intersection(tn_38_set)
    missing = tn_38_set - dataset_districts_clean
    extra = dataset_districts_clean - tn_38_set
    
    print(f"\nTotal expected TN districts: 38")
    print(f"Direct matched districts: {len(matched)}")
    print(f"Missing TN districts: {sorted(list(missing))}")
    print(f"Extra or alternate spellings: {sorted(list(extra))}")
    
    print("\nDistrict Record Counts (Top 10 & Bottom 10):")
    dist_counts = df[district_col].value_counts()
    print("--- Top 10 Districts by Record Count ---")
    print(dist_counts.head(10))
    print("--- Bottom 10 Districts by Record Count ---")
    print(dist_counts.tail(10))
    
    # 10. Water-quality parameters
    wq_params = [
        "Electric Conductivity (EC_GEN)",
        "Potential of Hydrogen_Gen (pH_GEN)",
        "Total Dissolved Solids (TDS)",
        "Nitrate (NO3)",
        "Nitrate N (NO3-N)",
        "Total Hardness (HAR_Total)",
        "Carbonate (CO3)",
        "Calcium (Ca)",
        "Chloride (Cl)",
        "Bicarbonate (HCO3)",
        "Potassium (K)",
        "Magnesium (Mg)",
        "Sodium (Na)",
        "Sulphate (SO4)",
        "Fluoride (F)",
        "Sodium Percent (Na%)",
        "Residual Sodium Carbonate (RSC)",
        "Sodium Adsorption Ratio (SAR)"
    ]
    
    print("\n--- Water Quality Parameters & Missingness ---")
    param_stats = []
    for p in wq_params:
        if p in df.columns:
            # Check non-numeric strings
            num_series = pd.to_numeric(df[p], errors='coerce')
            missing_count = num_series.isna().sum()
            missing_pct = (missing_count / total_rows) * 100
            min_val = num_series.min()
            max_val = num_series.max()
            mean_val = num_series.mean()
            median_val = num_series.median()
            param_stats.append({
                "Parameter": p,
                "Present": True,
                "Missing_Count": int(missing_count),
                "Missing_Pct": round(missing_pct, 2),
                "Min": round(float(min_val), 2) if pd.notna(min_val) else None,
                "Mean": round(float(mean_val), 2) if pd.notna(mean_val) else None,
                "Median": round(float(median_val), 2) if pd.notna(median_val) else None,
                "Max": round(float(max_val), 2) if pd.notna(max_val) else None
            })
            print(f"{p:35s} | Missing: {missing_pct:5.2f}% ({missing_count:,}/{total_rows:,}) | Range: [{min_val}, {max_val}]")
        else:
            param_stats.append({"Parameter": p, "Present": False})
            print(f"{p:35s} | NOT IN DATASET")
            
    # 11. Missing value overview for all columns
    print("\n--- Missing Values Across All Columns ---")
    missing_all = df.isnull().sum()
    missing_pct_all = (missing_all / total_rows) * 100
    missing_df = pd.DataFrame({"Missing Count": missing_all, "Missing %": missing_pct_all})
    print(missing_df[missing_df["Missing Count"] > 0])
    
    # 12. Duplicate and Invalid Records
    duplicate_full = df.duplicated().sum()
    duplicate_station_date = df.duplicated(subset=['Station Code', 'Sample Collection Date']).sum()
    print(f"\n--- Duplicates & Invalid Records ---")
    print(f"Exact row duplicates: {duplicate_full}")
    print(f"Duplicates on (Station Code + Sample Date): {duplicate_station_date}")
    
    # Invalid records check (e.g. pH <= 0 or pH > 14, TDS < 0, etc.)
    ph_numeric = pd.to_numeric(df['Potential of Hydrogen_Gen (pH_GEN)'], errors='coerce')
    invalid_ph = ((ph_numeric < 0) | (ph_numeric > 14)).sum()
    tds_numeric = pd.to_numeric(df['Total Dissolved Solids (TDS)'], errors='coerce')
    invalid_tds = (tds_numeric < 0).sum()
    ec_numeric = pd.to_numeric(df['Electric Conductivity (EC_GEN)'], errors='coerce')
    invalid_ec = (ec_numeric < 0).sum()
    print(f"Invalid pH (<0 or >14): {invalid_ph}")
    print(f"Negative TDS (<0): {invalid_tds}")
    print(f"Negative EC (<0): {invalid_ec}")
    
    # 13. WQI Sufficiency
    # Standard WQI parameters: pH, TDS, EC, Total Hardness, Calcium, Magnesium, Chloride, Sulphate, Nitrate, Fluoride
    core_wqi_params = ['Potential of Hydrogen_Gen (pH_GEN)', 'Total Dissolved Solids (TDS)', 'Electric Conductivity (EC_GEN)', 
                       'Total Hardness (HAR_Total)', 'Calcium (Ca)', 'Magnesium (Mg)', 'Chloride (Cl)', 'Sulphate (SO4)', 
                       'Nitrate (NO3)', 'Fluoride (F)']
    core_present = [p for p in core_wqi_params if p in df.columns]
    print(f"\n--- WQI Sufficiency Check ---")
    print(f"Core WQI parameters required: {len(core_wqi_params)}")
    print(f"Core WQI parameters present: {len(core_present)} -> {core_present}")
    
    # Save inspection summary to JSON for reference
    summary = {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "columns": list(df.columns),
        "total_2020_2025": int(total_2020_2025),
        "year_counts": {str(k): int(v) for k, v in year_counts.items()},
        "unique_districts": len(raw_districts_sorted),
        "districts": raw_districts_sorted,
        "duplicate_full": int(duplicate_full),
        "duplicate_station_date": int(duplicate_station_date),
        "param_stats": param_stats
    }
    with open("scripts/inspection_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved inspection summary to scripts/inspection_summary.json")

if __name__ == "__main__":
    inspect()
