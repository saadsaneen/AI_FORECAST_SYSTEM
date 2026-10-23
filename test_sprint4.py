"""
Sprint 4 Test Suite — Food Demand Forecasting System (Rahath Foods)
===================================================================
Tests Sprint 4 features:
1. Weather Integration (/weather/current, /weather/forecast)
2. Events Management (/events GET, POST, DELETE) with Multipliers
3. Manual Demand Adjustments (/adjustments GET, POST, DELETE)
4. Role-based Access Control (Owner vs Staff vs Unauthenticated)
5. Page Routes (/events, /demand-adjustment)
6. Forecast Summary endpoint (/forecast/summary)
"""

import unittest
import os
import json
import sqlite3
from datetime import date, timedelta

import database

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DB = os.path.join(PROJECT_DIR, "test_sprint4.db")
PRODUCTION_DB = os.path.abspath(database.DB_NAME)
database.DB_NAME = TEST_DB

from app import app
from database import init_db, get_db_connection


def _ensure_test_db_is_isolated():
    same_path = os.path.realpath(TEST_DB) == os.path.realpath(PRODUCTION_DB)
    same_file = (
        os.path.exists(TEST_DB)
        and os.path.exists(PRODUCTION_DB)
        and os.path.samefile(TEST_DB, PRODUCTION_DB)
    )
    if same_path or same_file:
        raise RuntimeError("Sprint 4 tests must not use the production database")


class TestSprint4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.DB_NAME = TEST_DB
        _ensure_test_db_is_isolated()
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass
        init_db()

    @classmethod
    def tearDownClass(cls):
        database.DB_NAME = TEST_DB
        _ensure_test_db_is_isolated()
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def setUp(self):
        database.DB_NAME = TEST_DB
        _ensure_test_db_is_isolated()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-sprint4'
        self.client = app.test_client()

        # Create staff user in test DB if not exists
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

    # ─── 1. DATABASE SCHEMA TESTS ─────────────────────────────────────────────
    def test_01_events_table_schema(self):
        """Verify 'events' table exists with all required columns."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(events)")
        cols = {row["name"] for row in cursor.fetchall()}
        conn.close()
        expected = {"event_id", "event_name", "event_date", "multiplier", "notes", "created_by"}
        self.assertTrue(expected.issubset(cols), f"Missing columns in events: {expected - cols}")

    def test_02_demand_adjustments_table_schema(self):
        """Verify 'demand_adjustments' table exists with all required columns."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(demand_adjustments)")
        cols = {row["name"] for row in cursor.fetchall()}
        conn.close()
        expected = {"adj_id", "item_id", "forecast_date", "adjusted_qty", "notes", "adjusted_by", "created_at"}
        self.assertTrue(expected.issubset(cols), f"Missing columns in demand_adjustments: {expected - cols}")

    # ─── 2. WEATHER INTEGRATION TESTS ─────────────────────────────────────────
    def test_03_weather_requires_auth(self):
        """Weather endpoints must require login."""
        res = self.client.get('/weather/current')
        self.assertEqual(res.status_code, 401)
        res2 = self.client.get('/weather/forecast')
        self.assertEqual(res2.status_code, 401)

    def test_04_weather_current_authenticated(self):
        """GET /weather/current returns live weather data or proper graceful response."""
        self._login_owner()
        res = self.client.get('/weather/current')
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()
        self.assertTrue(data.get("configured"))
        if res.status_code == 200:
            self.assertIn("current", data)
            self.assertIn("location", data)
            self.assertIn("demand_impact_note", data)
            self.assertIn("temperature_c", data["current"])

    def test_05_weather_forecast_authenticated(self):
        """GET /weather/forecast returns 3-day forecast outlook or proper graceful response."""
        self._login_staff()
        res = self.client.get('/weather/forecast')
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()
        self.assertTrue(data.get("configured"))
        if res.status_code == 200:
            self.assertIn("days", data)
            self.assertGreaterEqual(len(data["days"]), 1)
            first_day = data["days"][0]
            self.assertIn("date", first_day)
            self.assertIn("demand_impact_note", first_day)

    # ─── 3. EVENTS MANAGEMENT TESTS ───────────────────────────────────────────
    def test_06_events_unauthenticated_blocked(self):
        """Unauthenticated requests to /events must be rejected."""
        res = self.client.get('/events')
        self.assertEqual(res.status_code, 401)
        res_post = self.client.post('/events', json={"event_name": "Eid", "event_date": "2026-11-01"})
        self.assertEqual(res_post.status_code, 401)

    def test_07_staff_cannot_create_event(self):
        """Kitchen staff cannot create events (Owner only)."""
        self._login_staff()
        res = self.client.post('/events', json={
            "event_name": "Staff Created Event",
            "event_date": "2026-11-05",
            "multiplier": 1.4
        })
        self.assertEqual(res.status_code, 403)

    def test_08_owner_can_create_event(self):
        """Owner can successfully create an event with a demand multiplier."""
        self._login_owner()
        payload = {
            "event_name": "Eid Festival",
            "event_date": "2026-11-10",
            "multiplier": 1.7,
            "notes": "Large family gatherings expected, +70% demand"
        }
        res = self.client.post('/events', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["event"]["event_name"], "Eid Festival")
        self.assertEqual(data["event"]["multiplier"], 1.7)
        self.assertEqual(data["event"]["notes"], payload["notes"])
        self.assertIn("event_id", data["event"])

    def test_09_create_event_validation(self):
        """Validate event creation rules: missing name, invalid date, negative multiplier."""
        self._login_owner()
        # Missing name
        res1 = self.client.post('/events', json={"event_name": "", "event_date": "2026-11-10"})
        self.assertEqual(res1.status_code, 400)

        # Invalid date
        res2 = self.client.post('/events', json={"event_name": "Test", "event_date": "invalid-date"})
        self.assertEqual(res2.status_code, 400)

        # Non-positive multiplier
        res3 = self.client.post('/events', json={"event_name": "Test", "event_date": "2026-11-10", "multiplier": -1.0})
        self.assertEqual(res3.status_code, 400)

        # Unrealistic multiplier (> 10)
        res4 = self.client.post('/events', json={"event_name": "Test", "event_date": "2026-11-10", "multiplier": 15.0})
        self.assertEqual(res4.status_code, 400)

    def test_10_staff_can_view_events(self):
        """Staff can view events list (read-only access)."""
        self._login_staff()
        res = self.client.get('/events')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("events", data)
        self.assertGreaterEqual(len(data["events"]), 1)
        event = data["events"][0]
        self.assertIn("event_name", event)
        self.assertIn("multiplier", event)
        self.assertIn("is_past", event)

    def test_11_staff_cannot_delete_event(self):
        """Staff cannot delete events (Owner only)."""
        self._login_owner()
        res = self.client.post('/events', json={"event_name": "To Delete", "event_date": "2026-12-01"})
        event_id = res.get_json()["event"]["event_id"]

        self._login_staff()
        del_res = self.client.delete(f'/events/{event_id}')
        self.assertEqual(del_res.status_code, 403)

    def test_12_owner_can_delete_event(self):
        """Owner can successfully delete an event."""
        self._login_owner()
        res = self.client.post('/events', json={"event_name": "Temp Event", "event_date": "2026-12-05"})
        event_id = res.get_json()["event"]["event_id"]

        del_res = self.client.delete(f'/events/{event_id}')
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.get_json().get("success"))

        # Check 404 on deleting non-existent event
        del_res_again = self.client.delete(f'/events/{event_id}')
        self.assertEqual(del_res_again.status_code, 404)

    # ─── 4. MANUAL DEMAND ADJUSTMENTS TESTS ───────────────────────────────────
    def test_13_adjustments_unauthenticated_blocked(self):
        """Unauthenticated requests to /adjustments must be rejected."""
        res = self.client.get('/adjustments')
        self.assertEqual(res.status_code, 401)
        res_post = self.client.post('/adjustments', json={"item_id": 1, "forecast_date": "2026-11-01", "adjusted_qty": 50})
        self.assertEqual(res_post.status_code, 401)

    def test_14_staff_cannot_create_adjustment(self):
        """Kitchen staff cannot create or modify demand adjustments."""
        self._login_staff()
        res = self.client.post('/adjustments', json={
            "item_id": 1,
            "forecast_date": "2026-11-02",
            "adjusted_qty": 40
        })
        self.assertEqual(res.status_code, 403)

    def test_15_owner_can_create_and_upsert_adjustment(self):
        """Owner can save manual adjustment, and saving again upserts the record."""
        self._login_owner()
        payload = {
            "item_id": 1,
            "forecast_date": "2026-11-15",
            "adjusted_qty": 65.0,
            "notes": "Wedding catering booking nearby"
        }
        res = self.client.post('/adjustments', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["adjustment"]["adjusted_qty"], 65.0)

        # Upsert: Update adjustment for same item + date to 75.0
        payload["adjusted_qty"] = 75.0
        payload["notes"] = "Updated wedding guest count"
        res2 = self.client.post('/adjustments', json=payload)
        self.assertEqual(res2.status_code, 201)

        # Verify only one adjustment exists for that date and item
        res_get = self.client.get('/adjustments?forecast_date=2026-11-15&item_id=1')
        adjs = res_get.get_json()["adjustments"]
        self.assertEqual(len(adjs), 1)
        self.assertEqual(adjs[0]["adjusted_qty"], 75.0)
        self.assertEqual(adjs[0]["notes"], "Updated wedding guest count")

    def test_16_adjustment_validation(self):
        """Validate adjustment payload rules."""
        self._login_owner()
        # Invalid item
        res1 = self.client.post('/adjustments', json={"item_id": 99999, "forecast_date": "2026-11-15", "adjusted_qty": 10})
        self.assertEqual(res1.status_code, 404)

        # Negative quantity
        res2 = self.client.post('/adjustments', json={"item_id": 1, "forecast_date": "2026-11-15", "adjusted_qty": -5})
        self.assertEqual(res2.status_code, 400)

        # Invalid date
        res3 = self.client.post('/adjustments', json={"item_id": 1, "forecast_date": "bad-date", "adjusted_qty": 10})
        self.assertEqual(res3.status_code, 400)

    def test_17_owner_can_delete_adjustment(self):
        """Owner can delete an adjustment."""
        self._login_owner()
        res = self.client.post('/adjustments', json={"item_id": 2, "forecast_date": "2026-11-20", "adjusted_qty": 30})
        adj_id = res.get_json()["adjustment"]["adj_id"]

        del_res = self.client.delete(f'/adjustments/{adj_id}')
        self.assertEqual(del_res.status_code, 200)

        del_res2 = self.client.delete(f'/adjustments/{adj_id}')
        self.assertEqual(del_res2.status_code, 404)

    # ─── 5. SUMMARY STATS ENDPOINT ────────────────────────────────────────────
    def test_18_forecast_summary_endpoint(self):
        """GET /forecast/summary returns quick-glance statistics."""
        self._login_staff()
        res = self.client.get('/forecast/summary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_sales_records", data)
        self.assertIn("upcoming_events_30d", data)
        self.assertIn("next_event", data)
        self.assertIn("active_adjustments", data)

    # ─── 6. PAGE ROUTES AND ROLE ACCESS ───────────────────────────────────────
    def test_19_page_routes_protection(self):
        """Verify HTML page route access and redirects."""
        # Unauthenticated browser request redirects to /login
        res1 = self.client.get('/events', headers={"Accept": "text/html"}, follow_redirects=False)
        self.assertEqual(res1.status_code, 302)
        self.assertIn('/login', res1.location)

        res1_alias = self.client.get('/events-management', follow_redirects=False)
        self.assertEqual(res1_alias.status_code, 302)
        self.assertIn('/login', res1_alias.location)

        res2 = self.client.get('/demand-adjustment', follow_redirects=False)
        self.assertEqual(res2.status_code, 302)
        self.assertIn('/login', res2.location)

        # Staff can view /events HTML page, but redirected from /demand-adjustment to /dashboard
        self._login_staff()
        res_events = self.client.get('/events', headers={"Accept": "text/html"})
        self.assertEqual(res_events.status_code, 200)
        self.assertIn(b'Events Management', res_events.data)

        res_adj_staff = self.client.get('/demand-adjustment', follow_redirects=False)
        self.assertEqual(res_adj_staff.status_code, 302)
        self.assertIn('/dashboard', res_adj_staff.location)

        # Owner can view both pages
        self._login_owner()
        res_events_owner = self.client.get('/events', headers={"Accept": "text/html"})
        self.assertEqual(res_events_owner.status_code, 200)

        res_adj_owner = self.client.get('/demand-adjustment')
        self.assertEqual(res_adj_owner.status_code, 200)
        self.assertIn(b'Manual Demand Adjustment', res_adj_owner.data)

if __name__ == '__main__':
    unittest.main()
