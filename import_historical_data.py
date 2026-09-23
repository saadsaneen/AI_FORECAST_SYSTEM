import csv
import os
import sqlite3
from database import get_db_connection, init_db

CSV_FILENAME = "historical_sales.csv"

def import_historical_data():
    """
    Imports historical sales data from historical_sales.csv into the sales_record table.
    Matches item names case-insensitively and logs by the owner user account.
    """
    if not os.path.exists(CSV_FILENAME):
        print(f"[ERROR] File '{CSV_FILENAME}' not found in project directory.")
        return

    # Ensure database tables exist
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Get Owner user_id
    cursor.execute("SELECT user_id FROM users WHERE role = 'owner' LIMIT 1")
    owner = cursor.fetchone()
    if not owner:
        cursor.execute("SELECT user_id FROM users LIMIT 1")
        owner = cursor.fetchone()
    
    owner_id = owner["user_id"] if owner else 1

    # 2. Build case-insensitive items lookup dictionary
    cursor.execute("SELECT item_id, item_name, unit FROM items")
    db_items = cursor.fetchall()
    
    # Map lowercase item name -> (item_id, unit)
    items_map = {row["item_name"].strip().lower(): (row["item_id"], row["unit"]) for row in db_items}

    imported_count = 0
    skipped_count = 0
    total_processed = 0
    unmatched_items = set()

    # 3. Process CSV
    with open(CSV_FILENAME, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_processed += 1
            date_str = row.get("date", "").strip()
            item_raw = row.get("item", "").strip()
            qty_raw = row.get("quantity_sold", "").strip()

            # Skip blank or invalid quantity
            if not qty_raw:
                skipped_count += 1
                continue

            try:
                quantity_sold = float(qty_raw)
                if quantity_sold <= 0:
                    skipped_count += 1
                    continue
            except (ValueError, TypeError):
                skipped_count += 1
                continue

            # Match item name case-insensitively
            item_key = item_raw.lower()
            if item_key not in items_map:
                if item_raw:
                    unmatched_items.add(item_raw)
                skipped_count += 1
                continue

            item_id, unit = items_map[item_key]

            # Use date from CSV or default to today if missing
            if not date_str:
                date_str = sqlite3.connect(":memory:").execute("SELECT DATE('now')").fetchone()[0]

            try:
                cursor.execute(
                    """
                    INSERT INTO sales_record (date, item_id, quantity_sold, unit, logged_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (date_str, item_id, quantity_sold, unit, owner_id)
                )
                imported_count += 1
            except Exception as e:
                print(f"[WARNING] Failed to insert row {total_processed}: {e}")
                skipped_count += 1

    conn.commit()
    conn.close()

    # 4. Print Summary Report
    print("=" * 55)
    print("📊 HISTORICAL SALES DATA IMPORT SUMMARY")
    print("=" * 55)
    print(f" Total Rows Processed  : {total_processed}")
    print(f" Rows Imported        : {imported_count}")
    print(f" Rows Skipped         : {skipped_count}")
    
    if unmatched_items:
        print("\n ⚠️ Unmatched Item Names (Not found in Food Menu):")
        for item in sorted(unmatched_items):
            print(f"   - '{item}'")
        print(" (Tip: Add these items to your Food Menu or fix spelling in CSV)")
    else:
        print("\n ✅ All valid item names matched successfully!")
    
    print("=" * 55)

if __name__ == "__main__":
    import_historical_data()
