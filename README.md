# 💧 AquaSure – Smart Water Quality Index & Potability Indicator Analysis

A complete, production-grade groundwater quality analytics platform covering all **38 administrative districts of Tamil Nadu, India** for the monitoring horizon **2020–2025**, utilizing genuine State and Central Ground Water Department laboratory monitoring datasets.

---

## 📌 Project Highlights & Real Data Validation

* **Primary Raw Dataset:** Official Tamil Nadu State Groundwater hydrochemical survey (`data/raw/tamilnadu_groundwater_2020_2025.csv`, 19.37 MB, 113,586 records across 28 parameters).
* **Target Analytical Window:** **17,889 laboratory-tested observation wells** between **2020 and 2025**.
* **District Coverage:** **100% of all 38 districts of Tamil Nadu** are verified and present.
* **Standards Enforced:** **BIS 10500:2012** (Bureau of Indian Standards Drinking Water Specifications) and **World Health Organization (WHO)** guidelines.
* **WQI Methodology:** **Weighted Arithmetic Water Quality Index (WAWQI)** with dynamically normalized unit weights ($W_i$) to eliminate bias from missing sensor measurements.
* **Potability Machine Learning Model:** Random Forest Classifier trained on hydrochemical vectors achieving **98.46% accuracy** and **0.9983 ROC-AUC**.
* **Report Generation:** Automated publication-grade PDF water quality scorecards generated on demand via **ReportLab**.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Core & Analytics** | Python 3.12, Pandas, NumPy, SciPy |
| **Data Visualization** | Plotly Express & Graph Objects, Matplotlib, Seaborn |
| **Machine Learning** | Scikit-learn (Random Forest, Gradient Boosting, Pipeline) |
| **Web Dashboard** | Streamlit |
| **Document Generation** | ReportLab (A4 PDF Scorecard Engine) |

---

## 📂 Project Architecture

```
Aqua_sure/
├── data/
│   ├── raw/
│   │   └── tamilnadu_groundwater_2020_2025.csv      # Original untouched CSV (19.37 MB)
│   ├── processed/
│   │   ├── tn_groundwater_clean.parquet             # Cleaned & typed dataset (113,586 rows)
│   │   ├── tn_groundwater_2020_2025.parquet         # Target window slice (17,889 rows)
│   │   └── district_wqi_summary.csv                 # 38-district aggregated metrics
│   └── models/
│       └── potability_rf_model.joblib               # Pre-trained Random Forest model
├── src/
│   ├── config.py                                    # BIS/WHO standards, canonical 38 districts
│   ├── data_pipeline.py                             # Clean, validate, type-cast, coordinate sanitizer
│   ├── wqi_engine.py                                # WAWQI vector math & potability classifier
│   ├── potability_classifier.py                     # ML pipeline, feature importances, inference
│   └── report_generator.py                          # ReportLab PDF scorecard generator
├── app/
│   ├── streamlit_app.py                             # Main Streamlit web application
│   └── components/
│       ├── overview_tab.py                          # Statewide KPIs & exceedance charts
│       ├── map_tab.py                               # High-res GIS observation well map
│       ├── district_analytics_tab.py                # 38-district drilldown & PDF exporter
│       ├── trends_tab.py                            # 2020–2025 multi-year & seasonal dynamics
│       ├── correlation_tab.py                       # SciPy & Seaborn hydrochemical correlation
│       └── calculator_tab.py                        # Live WQI & ML potability lab tester
├── scripts/
│   ├── inspect_dataset.py                           # Automated data audit script
│   └── run_pipeline.py                              # End-to-end data processing script
├── reports/                                         # Generated district PDF scorecards
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run the Application

### 1. Ensure Dependencies are Installed
```bash
pip install -r requirements.txt
```

### 2. Run Data Pipeline (Already Pre-computed)
```bash
python scripts/run_pipeline.py
```

### 3. Launch the Streamlit Dashboard
```bash
streamlit run app/streamlit_app.py
```

The application will launch locally at `http://localhost:8501`.

---

## 📊 Core Analytical Findings (2020–2025)

1. **Statewide Potability:** Across 17,889 monitoring records, **12.5%** of groundwater sources are immediately potable without intensive remediation.
2. **Top Pristine Aquifers:** **Kanyakumari** exhibits the best overall groundwater quality (median WQI: 44.3, Grade B, 52.2% potable), supported by Western Ghats precipitation recharge.
3. **Primary Contamination Hotspots:**
   * **Nitrate (NO3 > 45 mg/L):** Severe non-point pollution in intensive agriculture and poultry belts (**Namakkal 81.2%**, **Erode 76.4%**, **Tiruppur 75.3%**, **Salem 71.1%**).
   * **Fluoride (F > 1.5 mg/L):** Geological dissolution from Precambrian crystalline rocks in **Dharmapuri**, **Salem**, and **Krishnagiri**.
   * **Salinity / High TDS (> 2000 mg/L):** Marine intrusion and coastal brackish conditions in **Nagapattinam**, **Ramanathapuram**, and **Thoothukudi**.
