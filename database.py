import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"

def get_db_connection():
    """Establishes and returns a database connection with dict-like row formatting."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds initial owner user and menu items."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create USERS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff'
        )
    """)

    # Create ITEMS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE NOT NULL,
            unit TEXT NOT NULL DEFAULT 'pieces',
            price REAL NOT NULL DEFAULT 0.0
        )
    """)

    # Migration check: Ensure price column exists if table was created in an earlier schema
    cursor.execute("PRAGMA table_info(items)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "price" not in columns:
        cursor.execute("ALTER TABLE items ADD COLUMN price REAL NOT NULL DEFAULT 0.0")
        print("[DB] Added 'price' column to items table.")

    # Seed owner account if not exists
    cursor.execute("SELECT * FROM users WHERE name = ?", ("owner",))
    owner = cursor.fetchone()
    if not owner:
        hashed_password = generate_password_hash("owner123")
        cursor.execute(
            "INSERT INTO users (name, password_hash, role) VALUES (?, ?, ?)",
            ("owner", hashed_password, "owner")
        )
        print("[DB] Initialized default owner user ('owner' / 'owner123').")

    # Seed default items if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM items")
    count = cursor.fetchone()["count"]
    if count == 0:
        default_items = [
            ("Porotta", "pieces", 12.0),
            ("Pathiri", "pieces", 10.0),
            ("Chappathi", "pieces", 12.0),
            ("Biriyani", "plates", 160.0)
        ]
        cursor.executemany(
            "INSERT INTO items (item_name, unit, price) VALUES (?, ?, ?)",
            default_items
        )
        print("[DB] Initialized default food menu items with prices.")
    else:
        # Update zero prices if any existing seed items had default 0.0
        cursor.execute("UPDATE items SET price = 12.0 WHERE item_name IN ('Porotta', 'Chappathi') AND price = 0.0")
        cursor.execute("UPDATE items SET price = 10.0 WHERE item_name = 'Pathiri' AND price = 0.0")
        cursor.execute("UPDATE items SET price = 160.0 WHERE item_name = 'Biriyani' AND price = 0.0")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database setup complete.")
