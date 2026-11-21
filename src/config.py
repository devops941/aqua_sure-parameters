"""
AquaSure Configuration Module
Defines BIS (10500:2012) & WHO standards, hydrochemical parameter metadata,
WQI unit weights, and classification categories for Tamil Nadu groundwater analytics.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "tamilnadu_groundwater_2020_2025.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "tn_groundwater_clean.parquet"
PROCESSED_CSV_PATH = DATA_DIR / "processed" / "tn_groundwater_clean.csv"
FILTERED_2020_2025_PATH = DATA_DIR / "processed" / "tn_groundwater_2020_2025.parquet"
FILTERED_CSV_PATH = DATA_DIR / "processed" / "tn_groundwater_2020_2025.csv"
DISTRICT_SUMMARY_PATH = DATA_DIR / "processed" / "district_wqi_summary.csv"
REPORTS_DIR = BASE_DIR / "reports"

# Column Name Standardization Mapping
RAW_TO_CLEAN_COLS = {
    "_id": "id",
    "Station Code": "station_code",
    "Station Name": "station_name",
    "Agency Name": "agency_name",
    "State": "state",
    "District": "district",
    "Tahsil_Name": "tahsil_name",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Sample Collection Date": "sample_date",
    "Electric Conductivity (EC_GEN)": "ec",
    "Potential of Hydrogen_Gen (pH_GEN)": "ph",
    "Total Dissolved Solids (TDS)": "tds",
    "Nitrate (NO3)": "no3",
    "Nitrate N (NO3-N)": "no3_n",
    "Total Hardness (HAR_Total)": "hardness",
    "Carbonate (CO3)": "co3",
    "Calcium (Ca)": "ca",
    "Chloride (Cl)": "cl",
    "Bicarbonate (HCO3)": "hco3",
    "Potassium (K)": "k",
    "Magnesium (Mg)": "mg",
    "Sodium (Na)": "na",
    "Sulphate (SO4)": "so4",
    "Fluoride (F)": "f",
    "Sodium Percent (Na%)": "na_pct",
    "Residual Sodium Carbonate (RSC)": "rsc",
    "Sodium Adsorption Ratio (SAR)": "sar",
}

# The 38 Administrative Districts of Tamil Nadu (Standardized Canonical Spellings)
TN_38_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
    "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
    "Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
    "Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi",
    "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
    "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore",
    "Viluppuram", "Virudhunagar"
]

# Common raw spelling aliases in government datasets
DISTRICT_ALIASES = {
    "Thiruvannamalai": "Tiruvannamalai",
    "Kanchipuram": "Kancheepuram",
    "Villupuram": "Viluppuram",
    "Trichy": "Tiruchirappalli",
    "Tiruchirapalli": "Tiruchirappalli",
    "The Nilgiris": "Nilgiris",
    "Kanniyakumari": "Kanyakumari",
    "Tuticorin": "Thoothukudi",
    "Thuthukudi": "Thoothukudi"
}

# BIS 10500:2012 Drinking Water Specification & Relative Weights (wi)
# Si = Desirable/Acceptable Limit (or Permissible where standard specifies)
# Ideal Value: pH = 7.0, all others = 0.0
WQI_PARAM_STANDARDS = {
    "ph": {
        "name": "pH (Potential of Hydrogen)",
        "unit": "pH unit",
        "standard_acceptable": 8.5,
        "standard_permissible": 8.5,
        "ideal_value": 7.0,
        "weight": 4,
        "min_valid": 4.0,
        "max_valid": 11.5
    },
    "tds": {
        "name": "Total Dissolved Solids (TDS)",
        "unit": "mg/L",
        "standard_acceptable": 500.0,
        "standard_permissible": 2000.0,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 70000.0
    },
    "ec": {
        "name": "Electrical Conductivity (EC)",
        "unit": "µS/cm",
        "standard_acceptable": 750.0,
        "standard_permissible": 2250.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 70000.0
    },
    "hardness": {
        "name": "Total Hardness (as CaCO3)",
        "unit": "mg/L",
        "standard_acceptable": 200.0,
        "standard_permissible": 600.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 20000.0
    },
    "ca": {
        "name": "Calcium (Ca)",
        "unit": "mg/L",
        "standard_acceptable": 75.0,
        "standard_permissible": 200.0,
        "ideal_value": 0.0,
        "weight": 2,
        "min_valid": 0.0,
        "max_valid": 5000.0
    },
    "mg": {
        "name": "Magnesium (Mg)",
        "unit": "mg/L",
        "standard_acceptable": 30.0,
        "standard_permissible": 100.0,
        "ideal_value": 0.0,
        "weight": 2,
        "min_valid": 0.0,
        "max_valid": 4000.0
    },
    "cl": {
        "name": "Chloride (Cl)",
        "unit": "mg/L",
        "standard_acceptable": 250.0,
        "standard_permissible": 1000.0,
        "ideal_value": 0.0,
        "weight": 3,
        "min_valid": 0.0,
        "max_valid": 40000.0
    },
    "so4": {
        "name": "Sulphate (SO4)",
        "unit": "mg/L",
        "standard_acceptable": 200.0,
        "standard_permissible": 400.0,
        "ideal_value": 0.0,
        "weight": 4,
        "min_valid": 0.0,
        "max_valid": 10000.0
    },
    "no3": {
        "name": "Nitrate (NO3)",
        "unit": "mg/L",
        "standard_acceptable": 45.0,
        "standard_permissible": 45.0,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 5000.0
    },
    "f": {
        "name": "Fluoride (F)",
        "unit": "mg/L",
        "standard_acceptable": 1.0,
        "standard_permissible": 1.5,
        "ideal_value": 0.0,
        "weight": 5,
        "min_valid": 0.0,
        "max_valid": 15.0
    }
}

# WQI Categorization Scale (Brown et al. / Indian Water Quality Rating)
WQI_CATEGORIES = [
    {
        "grade": "A",
        "category": "Excellent",
        "range": (0, 25),
        "potability": "Potable",
        "color": "#10b981", # Emerald green
        "description": "Pristine water quality. Suitable for direct human consumption and all domestic uses."
    },
    {
        "grade": "B",
        "category": "Good",
        "range": (26, 50),
        "potability": "Potable",
        "color": "#06b6d4", # Cyan
        "description": "Good water quality. Suitable for drinking, cooking, and domestic use with basic disinfection."
    },
    {
        "grade": "C",
        "category": "Poor",
        "range": (51, 75),
        "potability": "Requires Treatment",
        "color": "#f59e0b", # Amber
        "description": "Moderate degradation. Not recommended for drinking without filtration/softening/reverse osmosis."
    },
    {
        "grade": "D",
        "category": "Very Poor",
        "range": (76, 100),
        "potability": "Non-Potable",
        "color": "#f97316", # Orange
        "description": "Severely degraded water quality. Suitable only for irrigation or industrial cooling after treatment."
    },
    {
        "grade": "E",
        "category": "Unsuitable for Drinking",
        "range": (101, float("inf")),
        "potability": "Hazardous / Unfit",
        "color": "#ef4444", # Red
        "description": "Critically contaminated groundwater. Poses severe health hazards if ingested without advanced chemical remediation."
    }
]
