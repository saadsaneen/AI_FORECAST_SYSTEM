"""
Sprint 5 — Machine Learning Prediction Engine (Rahath Foods)
============================================================
Loads pre-trained joblib models from `models/` directory using project-relative paths.
Generates calendar and lag features, executes predictions, handles missing history,
and implements evaluation-guided model selection:
- Pathiri: Model 1 (Calendar Features) — achieved lower MAE in evaluation.
- Appam, Chappathi, Porotta, Biriyani: Model 2 (Calendar + Previous 3 Sales) — lower MAE in evaluation.
- Fallback: If fewer than 3 prior sales exist before the target date, falls back to Model 1 with clear explanation.
"""

import os
import csv
import warnings
from datetime import datetime, date

# Suppress scikit-learn unpickling version warnings
warnings.filterwarnings("ignore", category=UserWarning)

import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL1_PATH = os.path.join(BASE_DIR, "models", "rahath_model1_calendar.joblib")
MODEL2_PATH = os.path.join(BASE_DIR, "models", "rahath_model2_previous_sales.joblib")
SALES_CSV_PATH = os.path.join(BASE_DIR, "datasets", "sales_dataset.csv")

# Food columns expected by the models and their display mapping
FOOD_ITEMS_CONFIG = [
    {
        "column": "pathiri (kg)",
        "display_name": "Pathiri",
        "unit": "kg",
        "preferred_model": "model1",
        "selection_reason": "Evaluated with lower MAE using Model 1 (Calendar Features)."
    },
    {
        "column": "appam (kg)",
        "display_name": "Appam",
        "unit": "kg",
        "preferred_model": "model2",
        "selection_reason": "Evaluated with lower MAE using Model 2 (Previous Sales Features)."
    },
    {
        "column": "chappathi (kg)",
        "display_name": "Chappathi",
        "unit": "kg",
        "preferred_model": "model2",
        "selection_reason": "Evaluated with lower MAE using Model 2 (Previous Sales Features)."
    },
    {
        "column": "porotta (kg)",
        "display_name": "Porotta",
        "unit": "kg",
        "preferred_model": "model2",
        "selection_reason": "Evaluated with lower MAE using Model 2 (Previous Sales Features)."
    },
    {
        "column": "biriyani (kg)",
        "display_name": "Biriyani",
        "unit": "kg",
        "preferred_model": "model2",
        "selection_reason": "Evaluated with lower MAE using Model 2 (Previous Sales Features)."
    }
]

# Cached models
_loaded_model1 = None
_loaded_model2 = None
_load_error = None


def load_models():
    """Load both joblib model bundles from models/ directory."""
    global _loaded_model1, _loaded_model2, _load_error

    if _loaded_model1 is not None and _loaded_model2 is not None:
        return _loaded_model1, _loaded_model2, None

    try:
        if not os.path.exists(MODEL1_PATH):
            raise FileNotFoundError(f"Model 1 file not found at: {MODEL1_PATH}")
        if not os.path.exists(MODEL2_PATH):
            raise FileNotFoundError(f"Model 2 file not found at: {MODEL2_PATH}")

        _loaded_model1 = joblib.load(MODEL1_PATH)
        _loaded_model2 = joblib.load(MODEL2_PATH)
        _load_error = None
        return _loaded_model1, _loaded_model2, None
    except Exception as e:
        _load_error = str(e)
        return None, None, _load_error


def get_calendar_features(target_date: date):
    """
    Generate calendar features matching Model 1:
    day_of_week: 0 (Monday) to 6 (Sunday)
    day_of_month: 1 to 31
    month: 1 to 12
    day_of_year: 1 to 366
    is_weekend: 1 if Saturday or Sunday, else 0
    """
    dow = target_date.weekday()
    return {
        "day_of_week": dow,
        "day_of_month": target_date.day,
        "month": target_date.month,
        "day_of_year": target_date.timetuple().tm_yday,
        "is_weekend": 1 if dow in (5, 6) else 0
    }


def get_previous_sales_from_dataset(food_column: str, target_date: date, count: int = 3):
    """
    Retrieve the most recent valid sales observations from the original
    cleaned CSV, strictly before the target date.

    All quantities remain in kg.
    Missing values are not treated as zero.
    SQLite sales are excluded to avoid mixing units.
    """
    target_date_str = target_date.isoformat()
    observations = []

    if not os.path.exists(SALES_CSV_PATH):
        return []

    try:
        with open(SALES_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                row_date = (row.get("date") or "").strip()

                if not row_date or row_date >= target_date_str:
                    continue

                value_str = (row.get(food_column) or "").strip()

                if not value_str:
                    continue

                try:
                    value = float(value_str)
                except (ValueError, TypeError):
                    continue

                if not np.isfinite(value) or value < 0:
                    continue

                observations.append((row_date, value))

    except (OSError, csv.Error):
        return []

    observations.sort(key=lambda item: item[0])

    return [value for _, value in observations[-count:]][::-1]


def predict_for_item(item_config: dict, target_date: date, m1, m2):
    """
    Execute prediction for a single food item adhering to evaluation guidance:
    - Pathiri: Model 1
    - Appam, Chappathi, Porotta, Biriyani: Model 2 (fallback to Model 1 if < 3 prior sales)
    """
    col = item_config["column"]
    display_name = item_config["display_name"]
    unit = item_config["unit"]
    preferred = item_config["preferred_model"]
    cal_features = get_calendar_features(target_date)

    m1_sub = m1["models"].get(col) if (m1 and "models" in m1) else None
    m2_sub = m2["models"].get(col) if (m2 and "models" in m2) else None

    model_used = None
    raw_prediction = None
    previous_sales = []
    status_note = ""

    if preferred == "model1":
        if m1_sub is None:
            return {
                "item_name": display_name,
                "unit": unit,
                "error": f"Sub-model for '{col}' not found in Model 1"
            }
        features_order = m1.get("features", ['day_of_week', 'day_of_month', 'month', 'day_of_year', 'is_weekend'])
        input_df = pd.DataFrame([{k: cal_features[k] for k in features_order}])
        pred_val = float(m1_sub.predict(input_df)[0])
        model_used = "Model 1 (Calendar Features)"
        raw_prediction = max(0.0, round(pred_val, 2))
        status_note = "Model 1 selected per historical evaluation (lower MAE for Pathiri)."
    else:
        prior_sales = get_previous_sales_from_dataset(col, target_date, count=3)
        previous_sales = prior_sales

        if len(prior_sales) == 3 and m2_sub is not None:
            rf_model = m2_sub["model"]
            features_order = m2_sub.get("features", [
                "previous_sale_1", "previous_sale_2", "previous_sale_3",
                "day_of_week", "month", "day_of_year"
            ])
            feature_dict = {
                "previous_sale_1": prior_sales[0],
                "previous_sale_2": prior_sales[1],
                "previous_sale_3": prior_sales[2],
                "day_of_week": cal_features["day_of_week"],
                "month": cal_features["month"],
                "day_of_year": cal_features["day_of_year"]
            }
            input_df = pd.DataFrame([{k: feature_dict[k] for k in features_order}])
            pred_val = float(rf_model.predict(input_df)[0])
            model_used = "Model 2 (Calendar + Previous Sales)"
            raw_prediction = max(0.0, round(pred_val, 2))
            status_note = "Model 2 selected per historical evaluation (lower MAE with 3 prior sales)."
        else:
            if m1_sub is None:
                return {
                    "item_name": display_name,
                    "unit": unit,
                    "error": f"Model 2 lacks 3 prior observations and Model 1 is unavailable"
                }
            features_order = m1.get("features", ['day_of_week', 'day_of_month', 'month', 'day_of_year', 'is_weekend'])
            input_df = pd.DataFrame([{k: cal_features[k] for k in features_order}])
            pred_val = float(m1_sub.predict(input_df)[0])
            model_used = "Model 1 (Calendar Features - Fallback)"
            raw_prediction = max(0.0, round(pred_val, 2))
            prior_count = len(prior_sales)
            status_note = f"Fell back to Model 1: found only {prior_count}/3 prior recorded sales before {target_date.isoformat()}."

    return {
        "item_name": display_name,
        "unit": unit,
        "model_used": model_used,
        "selection_reason": item_config["selection_reason"],
        "raw_prediction": raw_prediction,
        "previous_sales": previous_sales,
        "status_note": status_note
    }


def predict_all_for_date(target_date: date):
    """
    Run demand forecasting for all 5 food items on the specified date.
    Returns: dict with date metadata, predictions, and any model loading notes.
    """
    m1, m2, err = load_models()
    if err:
        return {
            "success": False,
            "error": f"Failed to load trained models: {err}",
            "date": target_date.isoformat(),
            "items": []
        }

    results = []
    for item_cfg in FOOD_ITEMS_CONFIG:
        pred_dict = predict_for_item(item_cfg, target_date, m1, m2)
        results.append(pred_dict)

    return {
        "success": True,
        "date": target_date.isoformat(),
        "calendar_info": get_calendar_features(target_date),
        "items": results
    }
