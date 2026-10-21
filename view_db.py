import sqlite3

DB_NAME = "database.db"

def inspect_database():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row["name"] for row in cursor.fetchall()]

    print("=" * 60)
    print(" 🗄️  SQLITE DATABASE INSPECTOR (database.db)")
    print("=" * 60)
    print(f" Tables Found ({len(tables)}): {', '.join(tables)}\n")

    for table in tables:
        print("-" * 60)
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()["count"]
        print(f" 📋 TABLE: '{table}' (Total Rows: {count})")
        print("-" * 60)

        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row["name"] for row in cursor.fetchall()]
        print(f" Columns: {', '.join(columns)}")

        cursor.execute(f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT 10")
        rows = cursor.fetchall()

        if rows:
            print("\n Sample Data (Recent 10 Rows):")
            for row in rows:
                row_dict = dict(row)
                print("  •", row_dict)
        else:
            print("  (Table is empty)")
        print("\n")

    conn.close()

if __name__ == "__main__":
    inspect_database()
