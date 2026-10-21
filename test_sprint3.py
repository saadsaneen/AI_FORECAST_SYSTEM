import unittest
import os
import sqlite3
import json
from datetime import datetime, timedelta
from app import app
from database import init_db, DB_NAME, get_db_connection

class TestSprint3(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-sprint3'
        self.client = app.test_client()

        # Reset DB for clean state
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except Exception:
                pass
        init_db()

        # Setup owner and staff accounts
        # Owner
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        self.client.get('/logout')

        # Register staff user
        self.client.post('/register', json={"name": "staff_ramesh", "password": "rameshpassword123"})

    def test_01_waste_log_table_exists(self):
        """1. Verify waste_log table exists in database schema."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(waste_log)")
        columns = [row["name"] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("waste_id", columns)
        self.assertIn("date", columns)
        self.assertIn("item_id", columns)
        self.assertIn("quantity_wasted", columns)
        self.assertIn("unit", columns)
        self.assertIn("logged_by", columns)

    def test_02_owner_can_add_waste(self):
        """2. Verify Owner can add a waste entry."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        today_str = datetime.now().strftime("%Y-%m-%d")

        res = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 5.5, "date": today_str})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["waste"]["quantity_wasted"], 5.5)

    def test_03_staff_can_add_waste(self):
        """3. Verify Staff can add a waste entry."""
        self.client.post('/login', json={"name": "staff_ramesh", "password": "rameshpassword123"})
        today_str = datetime.now().strftime("%Y-%m-%d")

        res = self.client.post('/waste', json={"item_id": 2, "quantity_wasted": 3.0, "date": today_str})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["waste"]["quantity_wasted"], 3.0)

    def test_04_empty_quantity_rejected(self):
        """4. Verify empty quantity is rejected."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        res = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": None})
        self.assertEqual(res.status_code, 400)
        self.assertIn("positive number", res.get_json().get("error", ""))

    def test_05_zero_or_negative_quantity_rejected(self):
        """5. Verify zero or negative quantity is rejected."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        
        # Zero quantity
        res0 = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 0})
        self.assertEqual(res0.status_code, 400)

        # Negative quantity
        res_neg = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": -4.5})
        self.assertEqual(res_neg.status_code, 400)

    def test_06_invalid_item_rejected(self):
        """6. Verify invalid item_id is rejected."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        res = self.client.post('/waste', json={"item_id": 99999, "quantity_wasted": 2.0})
        self.assertEqual(res.status_code, 400)
        self.assertIn("does not exist", res.get_json().get("error", ""))

    def test_07_future_date_rejected(self):
        """7. Verify future date is rejected."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        future_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        res = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 2.0, "date": future_str})
        self.assertEqual(res.status_code, 400)
        self.assertIn("future", res.get_json().get("error", ""))

    def test_08_owner_sees_all_entries(self):
        """8. Verify Owner sees all waste entries across all users."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Owner adds waste
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 10, "date": today_str})
        self.client.get('/logout')

        # Staff adds waste
        self.client.post('/login', json={"name": "staff_ramesh", "password": "rameshpassword123"})
        self.client.post('/waste', json={"item_id": 2, "quantity_wasted": 5, "date": today_str})
        self.client.get('/logout')

        # Owner checks GET /waste
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        res = self.client.get('/waste')
        self.assertEqual(res.status_code, 200)
        waste_list = res.get_json().get("waste", [])
        self.assertEqual(len(waste_list), 2, "Owner should see all 2 waste entries!")

    def test_09_staff_sees_only_own_entries(self):
        """9. Verify Staff sees ONLY their own waste entries."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Owner adds waste
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 10, "date": today_str})
        self.client.get('/logout')

        # Staff adds waste
        self.client.post('/login', json={"name": "staff_ramesh", "password": "rameshpassword123"})
        self.client.post('/waste', json={"item_id": 2, "quantity_wasted": 5, "date": today_str})

        # Staff checks GET /waste
        res = self.client.get('/waste')
        self.assertEqual(res.status_code, 200)
        waste_list = res.get_json().get("waste", [])
        self.assertEqual(len(waste_list), 1, "Staff should see ONLY their own 1 waste entry!")
        self.assertEqual(waste_list[0]["logged_by_name"], "staff_ramesh")

    def test_10_owner_can_delete(self):
        """10. Verify Owner can delete waste entry."""
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        res_add = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 4.0})
        waste_id = res_add.get_json()["waste"]["waste_id"]

        # Owner deletes waste
        res_del = self.client.delete(f'/waste/{waste_id}')
        self.assertEqual(res_del.status_code, 200)

        # Confirm deleted
        res_get = self.client.get('/waste')
        waste_list = res_get.get_json().get("waste", [])
        self.assertEqual(len(waste_list), 0)

    def test_11_staff_cannot_delete(self):
        """11. Verify Staff gets 403 Forbidden when attempting to delete waste entry."""
        # Owner adds entry
        self.client.post('/login', json={"name": "owner", "password": "owner123"})
        res_add = self.client.post('/waste', json={"item_id": 1, "quantity_wasted": 4.0})
        waste_id = res_add.get_json()["waste"]["waste_id"]
        self.client.get('/logout')

        # Staff attempts deletion
        self.client.post('/login', json={"name": "staff_ramesh", "password": "rameshpassword123"})
        res_del = self.client.delete(f'/waste/{waste_id}')
        self.assertEqual(res_del.status_code, 403, "SECURITY FAIL: Staff was able to delete waste entry!")
        self.assertIn("Owner privilege required", res_del.get_json().get("error", ""))

if __name__ == "__main__":
    unittest.main()
