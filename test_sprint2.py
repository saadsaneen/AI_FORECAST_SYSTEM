import unittest
import os
import sqlite3
import json
from datetime import datetime, timedelta
from app import app
from database import init_db, DB_NAME, get_db_connection
from import_historical_data import import_historical_data, CSV_FILENAME

class TestSprint2(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-sprint2'
        self.client = app.test_client()

        # Reset database for fresh test state
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except Exception:
                pass
        init_db()

        # Login owner
        self.client.post('/login', json={"name": "owner", "password": "owner123"})

    def test_01_sales_table_created(self):
        """Verify sales_record table exists in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(sales_record)")
        columns = [row["name"] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("sale_id", columns)
        self.assertIn("date", columns)
        self.assertIn("item_id", columns)
        self.assertIn("quantity_sold", columns)
        self.assertIn("unit", columns)
        self.assertIn("logged_by", columns)

    def test_02_post_sales_validation(self):
        """Verify POST /sales validation logic for positive quantity, valid item, and non-future date."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        future_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")

        # 1. Invalid item ID
        res1 = self.client.post('/sales', json={"item_id": 9999, "quantity_sold": 10, "date": today_str})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("does not exist", res1.get_json().get("error", ""))

        # 2. Non-positive quantity
        res2 = self.client.post('/sales', json={"item_id": 1, "quantity_sold": -5, "date": today_str})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("positive number", res2.get_json().get("error", ""))

        # 3. Future date
        res3 = self.client.post('/sales', json={"item_id": 1, "quantity_sold": 10, "date": future_str})
        self.assertEqual(res3.status_code, 400)
        self.assertIn("future", res3.get_json().get("error", ""))

        # 4. Valid Sales Entry
        res4 = self.client.post('/sales', json={"item_id": 1, "quantity_sold": 25.5, "date": today_str})
        self.assertEqual(res4.status_code, 201)
        data = res4.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["sale"]["quantity_sold"], 25.5)

    def test_03_staff_can_add_and_view_sales(self):
        """Verify staff role can log and view sales entries."""
        # Register and login staff
        self.client.post('/register', json={"name": "staff_member", "password": "staffpass123"})
        self.client.post('/login', json={"name": "staff_member", "password": "staffpass123"})

        today_str = datetime.now().strftime("%Y-%m-%d")

        # Post sale as staff
        res_post = self.client.post('/sales', json={"item_id": 2, "quantity_sold": 15, "date": today_str})
        self.assertEqual(res_post.status_code, 201)

        # GET sales as staff
        res_get = self.client.get('/sales')
        self.assertEqual(res_get.status_code, 200)
        sales = res_get.get_json().get("sales", [])
        self.assertGreaterEqual(len(sales), 1)

    def test_04_get_sales_filtering(self):
        """Verify GET /sales filtering by date range and item_id."""
        # Insert sample sales across multiple dates
        self.client.post('/sales', json={"item_id": 1, "quantity_sold": 10, "date": "2026-09-10"})
        self.client.post('/sales', json={"item_id": 2, "quantity_sold": 20, "date": "2026-09-15"})
        self.client.post('/sales', json={"item_id": 1, "quantity_sold": 30, "date": "2026-09-20"})

        # Filter by item_id = 1
        res_item = self.client.get('/sales?item_id=1')
        sales_item = res_item.get_json().get("sales", [])
        self.assertTrue(all(s["item_id"] == 1 for s in sales_item))

        # Filter by date range
        res_range = self.client.get('/sales?start_date=2026-09-12&end_date=2026-09-18')
        sales_range = res_range.get_json().get("sales", [])
        self.assertEqual(len(sales_range), 1)
        self.assertEqual(sales_range[0]["date"], "2026-09-15")

    def test_05_csv_import_script(self):
        """Verify import_historical_data.py imports valid rows and reports unmatched items."""
        # Create temporary test CSV
        test_csv = "test_import.csv"
        with open(test_csv, "w", encoding="utf-8") as f:
            f.write("date,item,quantity_sold,unit,is_event\n")
            f.write("2026-09-01,porotta,40,pieces,0\n")
            f.write("2026-09-01,BIRIYANI,15,plates,0\n")
            f.write("2026-09-01,Invalid Dish,10,plates,0\n")
            f.write("2026-09-01,Porotta,,pieces,0\n")

        # Swap CSV filename temporarily
        import import_historical_data
        old_filename = import_historical_data.CSV_FILENAME
        import_historical_data.CSV_FILENAME = test_csv

        try:
            import_historical_data.import_historical_data()
        finally:
            import_historical_data.CSV_FILENAME = old_filename
            if os.path.exists(test_csv):
                os.remove(test_csv)

        # Check imported rows in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM sales_record")
        count = cursor.fetchone()["count"]
        conn.close()

        self.assertEqual(count, 2, "Expected 2 valid imported rows from test CSV!")

if __name__ == "__main__":
    unittest.main()
