import unittest
import os
import sqlite3
import json
from app import app
from database import init_db, DB_NAME, get_db_connection

class TestSprint1(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

        # Remove existing test DB if any and re-init
        if os.path.exists(DB_NAME):
            try:
                os.remove(DB_NAME)
            except Exception:
                pass
        init_db()

    def test_01_database_seeding(self):
        """Verify owner user and 4 default food menu items are seeded."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE name = ?", ("owner",))
        owner = cursor.fetchone()
        self.assertIsNotNone(owner)
        self.assertEqual(owner["role"], "owner")

        cursor.execute("SELECT item_name FROM items")
        items = [row["item_name"] for row in cursor.fetchall()]
        self.assertIn("Porotta", items)
        self.assertIn("Pathiri", items)
        self.assertIn("Chappathi", items)
        self.assertIn("Biriyani", items)
        conn.close()

    def test_02_registration_hardcodes_staff_role(self):
        """Verify registration ignores role parameter and hardcodes role='staff'."""
        # Attempt to exploit registration by submitting role="owner"
        res = self.client.post('/register', json={
            "name": "hacker_staff",
            "password": "staffpassword123",
            "role": "owner" # Hacking attempt
        })
        self.assertEqual(res.status_code, 201)

        # Inspect database row
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE name = ?", ("hacker_staff",))
        user = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "staff", "SECURITY FAIL: Role was not hardcoded to 'staff'!")

    def test_03_registration_rejects_duplicate_username(self):
        """Verify registration rejects duplicate usernames."""
        self.client.post('/register', json={"name": "staff1", "password": "pass"})
        res = self.client.post('/register', json={"name": "staff1", "password": "pass"})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("already exists", data.get("error", ""))

    def test_04_login_generic_error_on_failure(self):
        """Verify login returns 401 with generic error message on invalid credentials."""
        res = self.client.post('/login', json={"name": "owner", "password": "wrongpassword"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Invalid username or password")

        res2 = self.client.post('/login', json={"name": "nonexistent_user", "password": "any"})
        self.assertEqual(res2.status_code, 401)
        data2 = res2.get_json()
        self.assertEqual(data2.get("error"), "Invalid username or password")

    def test_05_session_check_and_logout(self):
        """Verify login sets session and logout clears it."""
        # Check initial session
        res0 = self.client.get('/session-check')
        self.assertFalse(res0.get_json().get("logged_in"))

        # Login owner
        res1 = self.client.post('/login', json={"name": "owner", "password": "owner123"})
        self.assertEqual(res1.status_code, 200)

        # Check active session
        res2 = self.client.get('/session-check')
        session_data = res2.get_json()
        self.assertTrue(session_data.get("logged_in"))
        self.assertEqual(session_data["user"]["name"], "owner")
        self.assertEqual(session_data["user"]["role"], "owner")

        # Logout
        res3 = self.client.get('/logout')
        self.assertEqual(res3.status_code, 200)

        # Verify session cleared
        res4 = self.client.get('/session-check')
        self.assertFalse(res4.get_json().get("logged_in"))

    def test_06_staff_blocked_from_items_post_delete(self):
        """Verify staff role gets 403 Forbidden when calling POST/DELETE /items directly."""
        # Register and login staff
        self.client.post('/register', json={"name": "chef_ramesh", "password": "rameshpass"})
        self.client.post('/login', json={"name": "chef_ramesh", "password": "rameshpass"})

        # Try to add item
        res_post = self.client.post('/items', json={"item_name": "Meals", "unit": "plates"})
        self.assertEqual(res_post.status_code, 403, "SECURITY FAIL: Staff was able to add item!")
        self.assertIn("Owner privilege required", res_post.get_json().get("error", ""))

        # Try to delete item ID 1
        res_del = self.client.delete('/items/1')
        self.assertEqual(res_del.status_code, 403, "SECURITY FAIL: Staff was able to delete item!")

    def test_07_owner_items_management(self):
        """Verify owner can view, add with price, and delete items."""
        # Login owner
        self.client.post('/login', json={"name": "owner", "password": "owner123"})

        # GET items
        res_get = self.client.get('/items')
        self.assertEqual(res_get.status_code, 200)
        initial_items = res_get.get_json().get("items", [])
        self.assertEqual(len(initial_items), 4)

        # POST add item with price
        res_post = self.client.post('/items', json={"item_name": "Fish Curry", "unit": "plates", "price": 120.50})
        self.assertEqual(res_post.status_code, 201)
        new_item = res_post.get_json().get("item")
        item_id = new_item["item_id"]
        self.assertEqual(new_item["price"], 120.50)

        # GET items again
        res_get2 = self.client.get('/items')
        items2 = res_get2.get_json().get("items", [])
        self.assertEqual(len(items2), 5)
        added_item = next(item for item in items2 if item["item_id"] == item_id)
        self.assertEqual(added_item["price"], 120.50)

        # DELETE item
        res_del = self.client.delete(f'/items/{item_id}')
        self.assertEqual(res_del.status_code, 200)

        # GET items after delete
        res_get3 = self.client.get('/items')
        items3 = res_get3.get_json().get("items", [])
        self.assertEqual(len(items3), 4)

if __name__ == "__main__":
    unittest.main()
