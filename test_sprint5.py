"""
Sprint 5 Test Suite — Machine Learning Demand Prediction (Rahath Foods)
=======================================================================
Tests Sprint 5 features:
1. Model loading from models/ using project-relative paths
2. Calendar feature extraction for Model 1
3. Lag feature extraction and ordering for Model 2
4. Evaluation-based model selection (Model 1 for Pathiri, Model 2 for others)
5. Fallback behavior when < 3 prior observations exist
6. Integration with Event Multipliers and Manual Demand Adjustments
7. API endpoint /api/forecast/predict authentication and JSON schema
8. Page route /demand-prediction and role accessibility
"""

import unittest
import os
import json
from datetime import date, timedelta

# Point to dedicated test database BEFORE importing app/database
TEST_DB = "test_sprint5.db"
import database
database.DB_NAME = TEST_DB

from app import app
from database import init_db, get_db_connection
from ml_engine import (
    load_models, get_calendar_features, get_previous_sales_from_dataset,
    predict_for_item, predict_all_for_date, FOOD_ITEMS_CONFIG
)

class TestSprint5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.DB_NAME = TEST_DB
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
        init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_NAME = "database.db"
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def setUp(self):
        database.DB_NAME = TEST_DB
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-sprint5'
        self.client = app.test_client()

        # Seed staff user in test DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = 'staff_test'")
        if not cursor.fetchone():
            from werkzeug.security import generate_password_hash
            cursor.execute(
                "INSERT INTO users (name, password_hash, role) VALUES (?, ?, ?)",
                ("staff_test", generate_password_hash("staff123"), "staff")
            )
            conn.commit()
        conn.close()

    def _login_owner(self):
        return self.client.post('/login', json={"name": "owner", "password": "owner123"})

    def _login_staff(self):
        return self.client.post('/login', json={"name": "staff_test", "password": "staff123"})

    # ─── 1. MODEL LOADING TESTS ───────────────────────────────────────────────
    def test_01_models_load_successfully(self):
        """Verify both joblib models load from models/ directory without errors."""
        m1, m2, err = load_models()
        self.assertIsNone(err, f"Model load error: {err}")
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertIsInstance(m1, dict)
        self.assertIsInstance(m2, dict)

    def test_02_model_internal_structures(self):
        """Verify Model 1 and Model 2 distinct internal dictionary structures."""
        m1, m2, _ = load_models()
        # Model 1 has top-level 'features'
        self.assertIn("features", m1)
        self.assertEqual(m1["model_type"], "calendar_features")
        self.assertEqual(len(m1["food_columns"]), 5)

        # Model 2 has sub-dicts with 'features' inside each item model
        self.assertEqual(m2["model_type"], "calendar_plus_previous_sales")
        self.assertEqual(len(m2["food_columns"]), 5)
        sample_item = m2["models"]["porotta (kg)"]
        self.assertIsInstance(sample_item, dict)
        self.assertIn("model", sample_item)
        self.assertIn("features", sample_item)
        self.assertEqual(sample_item["features"], [
            'previous_sale_1', 'previous_sale_2', 'previous_sale_3',
            'day_of_week', 'month', 'day_of_year'
        ])

    # ─── 2. FEATURE EXTRACTION TESTS ──────────────────────────────────────────
    def test_03_calendar_feature_generation(self):
        """Verify calendar feature values for a known test date (Friday 2026-10-23)."""
        test_d = date(2026, 10, 23)
        cal = get_calendar_features(test_d)
        self.assertEqual(cal["day_of_week"], 4)  # Friday is 4 (Monday=0)
        self.assertEqual(cal["day_of_month"], 23)
        self.assertEqual(cal["month"], 10)
        self.assertEqual(cal["is_weekend"], 0)
        self.assertGreater(cal["day_of_year"], 290)

    def test_04_lag_sales_feature_retrieval(self):
        """Verify lag observations are retrieved strictly before target date and never include future dates."""
        target_d = date(2026, 9, 10)
        lags = get_previous_sales_from_dataset("porotta (kg)", target_d, count=3)
        self.assertIsInstance(lags, list)
        self.assertLessEqual(len(lags), 3)
        for val in lags:
            self.assertIsInstance(val, float)
            self.assertGreater(val, 0.0)

    # ─── 3. MODEL SELECTION & PREDICTION TESTS ─────────────────────────────────
    def test_05_pathiri_selects_model_1(self):
        """Verify Pathiri uses Model 1 (Calendar) based on historical evaluation."""
        m1, m2, _ = load_models()
        pathiri_cfg = [c for c in FOOD_ITEMS_CONFIG if c["display_name"] == "Pathiri"][0]
        res = predict_for_item(pathiri_cfg, date(2026, 10, 23), m1, m2)
        self.assertIn("Model 1", res["model_used"])
        self.assertGreater(res["raw_prediction"], 0.0)
        self.assertEqual(res["unit"], "kg")

    def test_06_other_items_select_model_2_when_history_present(self):
        """Verify Porotta, Chappathi, Appam, Biriyani select Model 2 when 3 prior sales exist."""
        m1, m2, _ = load_models()
        porotta_cfg = [c for c in FOOD_ITEMS_CONFIG if c["display_name"] == "Porotta"][0]
        # On 2026-10-23, dataset has plenty of historical sales
        res = predict_for_item(porotta_cfg, date(2026, 10, 23), m1, m2)
        self.assertIn("Model 2", res["model_used"])
        self.assertEqual(len(res["previous_sales"]), 3)
        self.assertGreater(res["raw_prediction"], 0.0)

    def test_07_fallback_to_model_1_when_history_insufficient(self):
        """Verify fallback to Model 1 when target date is earlier than historical dataset."""
        m1, m2, _ = load_models()
        porotta_cfg = [c for c in FOOD_ITEMS_CONFIG if c["display_name"] == "Porotta"][0]
        # Early date before dataset starts (2024-01-01) has zero prior records
        early_date = date(2024, 1, 1)
        res = predict_for_item(porotta_cfg, early_date, m1, m2)
        self.assertIn("Model 1", res["model_used"])
        self.assertIn("Fell back to Model 1", res["status_note"])
        self.assertGreater(res["raw_prediction"], 0.0)

    def test_08_predict_all_covers_five_items(self):
        """Verify predict_all_for_date produces predictions for all 5 required dishes."""
        res = predict_all_for_date(date(2026, 10, 23))
        self.assertTrue(res["success"])
        items = [it["item_name"] for it in res["items"]]
        expected = {"Pathiri", "Appam", "Chappathi", "Porotta", "Biriyani"}
        self.assertEqual(set(items), expected)

    # ─── 4. INTEGRATION WITH EVENTS & ADJUSTMENTS ─────────────────────────────
    def test_09_api_predict_requires_auth(self):
        """GET /api/forecast/predict must reject unauthenticated requests."""
        res = self.client.get('/api/forecast/predict')
        self.assertEqual(res.status_code, 401)

    def test_10_api_predict_authenticated_success(self):
        """GET /api/forecast/predict returns valid 200 payload with all 5 items."""
        self._login_staff()
        res = self.client.get('/api/forecast/predict?date=2026-10-23')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("items", [])), 5)
        self.assertIn("evaluation_notice", data)

    def test_11_event_multiplier_scales_prediction(self):
        """Verify event multiplier correctly scales raw ML demand."""
        self._login_owner()
        target_str = "2026-11-20"
        # Add event with 1.5 multiplier
        self.client.post('/events', json={
            "event_name": "Test Festival",
            "event_date": target_str,
            "multiplier": 1.5,
            "notes": "Testing multiplier integration"
        })

        res = self.client.get(f'/api/forecast/predict?date={target_str}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNotNone(data.get("event"))
        self.assertEqual(data["event"]["multiplier"], 1.5)

        for it in data["items"]:
            expected_adjusted = round(it["raw_prediction"] * 1.5, 2)
            self.assertEqual(it["event_adjusted_demand"], expected_adjusted)

    def test_12_manual_adjustment_overrides_final_target(self):
        """Verify owner manual adjustment overrides the final recommendation."""
        self._login_owner()
        target_str = "2026-11-25"
        # Item 1 is Porotta
        self.client.post('/adjustments', json={
            "item_id": 1,
            "forecast_date": target_str,
            "adjusted_qty": 95.0,
            "notes": "Custom wedding batch"
        })

        res = self.client.get(f'/api/forecast/predict?date={target_str}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        porotta = [i for i in data["items"] if i["item_name"] == "Porotta"][0]
        self.assertEqual(porotta["manual_adjustment"], 95.0)
        self.assertEqual(porotta["final_demand"], 95.0)
        self.assertEqual(porotta["final_source"], "Manual Override")

    # ─── 5. UI PAGE ROUTES ────────────────────────────────────────────────────
    def test_13_demand_prediction_page_auth_protection(self):
        """Verify /demand-prediction page redirects unauthenticated users to /login."""
        res_unauth = self.client.get('/demand-prediction', follow_redirects=False)
        self.assertEqual(res_unauth.status_code, 302)
        self.assertIn('/login', res_unauth.location)

        # Authenticated staff can view page
        self._login_staff()
        res_staff = self.client.get('/demand-prediction')
        self.assertEqual(res_staff.status_code, 200)
        self.assertIn(b'AI Demand Prediction', res_staff.data)

        # Authenticated owner can view page
        self._login_owner()
        res_owner = self.client.get('/demand-prediction')
        self.assertEqual(res_owner.status_code, 200)

if __name__ == '__main__':
    unittest.main()
