"""
AquaSure Machine Learning Potability Classifier
Trains and validates ML models (Random Forest, Gradient Boosting, Logistic Regression)
to predict groundwater potability and extract hydrochemical risk drivers.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, accuracy_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import logging

from src.config import BASE_DIR, FILTERED_2020_2025_PATH

logger = logging.getLogger(__name__)
MODEL_DIR = BASE_DIR / "data" / "models"
MODEL_PATH = MODEL_DIR / "potability_rf_model.joblib"

FEATURE_COLS = ["ph", "tds", "ec", "hardness", "ca", "mg", "cl", "so4", "no3", "f"]

def prepare_ml_data(df: pd.DataFrame):
    """Prepares feature matrix X and target y for potability classification."""
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_features].copy()
    y = df["is_potable"].astype(int)
    return X, y, available_features

def train_potability_model(df_path=FILTERED_2020_2025_PATH):
    """Trains a Random Forest classifier with median imputation and scaling."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(df_path) if str(df_path).endswith(".parquet") else pd.read_csv(df_path)
    
    X, y, features = prepare_ml_data(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42, n_jobs=-1))
    ])
    
    logger.info("Training Potability Random Forest Classifier...")
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    roc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=["Non-Potable", "Potable"])
    
    # Feature importances
    rf = pipeline.named_steps["classifier"]
    feature_importances = dict(zip(features, rf.feature_importances_))
    sorted_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))
    
    model_artifact = {
        "pipeline": pipeline,
        "features": features,
        "accuracy": acc,
        "roc_auc": roc,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "feature_importances": sorted_importances
    }
    
    joblib.dump(model_artifact, MODEL_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")
    logger.info(f"Model Accuracy: {acc*100:.2f}%, ROC-AUC: {roc:.4f}")
    
    return model_artifact

def load_or_train_model():
    """Loads existing trained model or trains a new one if not present."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return train_potability_model()

def predict_single_sample(sample_dict: dict) -> dict:
    """Predicts potability probability for an individual test sample."""
    artifact = load_or_train_model()
    pipeline = artifact["pipeline"]
    features = artifact["features"]
    
    row_data = {feat: sample_dict.get(feat, np.nan) for feat in features}
    input_df = pd.DataFrame([row_data])
    
    proba_potable = float(pipeline.predict_proba(input_df)[0][1])
    is_potable = proba_potable >= 0.5
    
    return {
        "is_potable": is_potable,
        "potability_confidence": round(proba_potable if is_potable else (1 - proba_potable), 4),
        "potability_probability": round(proba_potable, 4),
        "verdict": "Potable (Safe for Consumption)" if is_potable else "Non-Potable (Requires Remediation)"
    }

if __name__ == "__main__":
    train_potability_model()
