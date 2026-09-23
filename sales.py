from flask import Blueprint, request, jsonify, session
import sqlite3
from datetime import datetime
from database import get_db_connection
from auth import login_required

sales_bp = Blueprint("sales", __name__)

def validate_date(date_str):
    """
    Validates date string format (YYYY-MM-DD) and checks it is not in the future.
    Returns (is_valid, parsed_date_or_error_msg)
    """
    if not date_str:
        return True, datetime.now().strftime("%Y-%m-%d")
    
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        if parsed_date > today:
            return False, "Date cannot be in the future"
        return True, parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format"

@sales_bp.route("/sales", methods=["POST"])
@login_required
def add_sale():
    """
    POST /sales
    Adds a new sales entry. Any logged-in user (owner or staff) can record sales.
    Accepts JSON: { "item_id": 1, "quantity_sold": 15, "date": "YYYY-MM-DD" }
    """
    data = request.get_json(silent=True) or request.form
    if not data:
        return jsonify({"error": "Invalid JSON or form payload"}), 400

    item_id = data.get("item_id")
    quantity_raw = data.get("quantity_sold")
    date_raw = data.get("date", "").strip() if isinstance(data.get("date"), str) else ""

    # 1. Validate Item ID
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Please select a valid food item"}), 400

    # 2. Validate Quantity
    try:
        quantity_sold = float(quantity_raw)
        if quantity_sold <= 0:
            return jsonify({"error": "Quantity sold must be a positive number"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity sold must be a valid positive number"}), 400

    # 3. Validate Date (No Future Dates Allowed)
    is_valid_date, date_str_or_err = validate_date(date_raw)
    if not is_valid_date:
        return jsonify({"error": date_str_or_err}), 400
    sale_date = date_str_or_err

    # 4. Check Item Existence & Fetch Unit
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, unit FROM items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return jsonify({"error": "Selected food item does not exist"}), 400

    unit = item["unit"]
    item_name = item["item_name"]
    logged_by = session.get("user_id")
    logged_by_name = session.get("name")

    # 5. Insert Sales Record
    try:
        cursor.execute(
            """
            INSERT INTO sales_record (date, item_id, quantity_sold, unit, logged_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sale_date, item_id, quantity_sold, unit, logged_by)
        )
        sale_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": "Failed to save sales record to database"}), 500

    conn.close()

    return jsonify({
        "success": True,
        "message": f"Sale of {quantity_sold} {unit} of '{item_name}' recorded successfully",
        "sale": {
            "sale_id": sale_id,
            "date": sale_date,
            "item_id": item_id,
            "item_name": item_name,
            "quantity_sold": round(quantity_sold, 2),
            "unit": unit,
            "logged_by": logged_by,
            "logged_by_name": logged_by_name
        }
    }), 201

@sales_bp.route("/sales", methods=["GET"])
@login_required
def get_sales():
    """
    GET /sales
    List sales entries. Supported query params:
    - ?date=YYYY-MM-DD
    - ?item_id=N
    - ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """
    filter_date = request.args.get("date", "").strip()
    filter_item_id = request.args.get("item_id", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT s.sale_id, s.date, s.item_id, s.quantity_sold, s.unit, s.logged_by,
               i.item_name, i.price, u.name as logged_by_name
        FROM sales_record s
        JOIN items i ON s.item_id = i.item_id
        JOIN users u ON s.logged_by = u.user_id
        WHERE 1=1
    """
    params = []

    if filter_date:
        query += " AND s.date = ?"
        params.append(filter_date)

    if filter_item_id:
        try:
            query += " AND s.item_id = ?"
            params.append(int(filter_item_id))
        except ValueError:
            pass

    if start_date:
        query += " AND s.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND s.date <= ?"
        params.append(end_date)

    query += " ORDER BY s.date DESC, s.sale_id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    sales_list = [
        {
            "sale_id": row["sale_id"],
            "date": row["date"],
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "quantity_sold": round(float(row["quantity_sold"]), 2),
            "unit": row["unit"],
            "price": round(float(row["price"]), 2),
            "logged_by": row["logged_by"],
            "logged_by_name": row["logged_by_name"]
        }
        for row in rows
    ]

    # Summary aggregation
    summary_query = """
        SELECT i.item_id, i.item_name, s.unit, 
               SUM(s.quantity_sold) as total_quantity, 
               COUNT(s.sale_id) as records_count
        FROM sales_record s
        JOIN items i ON s.item_id = i.item_id
        WHERE 1=1
    """
    summary_params = []

    if filter_date:
        summary_query += " AND s.date = ?"
        summary_params.append(filter_date)

    if filter_item_id:
        try:
            summary_query += " AND s.item_id = ?"
            summary_params.append(int(filter_item_id))
        except ValueError:
            pass

    if start_date:
        summary_query += " AND s.date >= ?"
        summary_params.append(start_date)

    if end_date:
        summary_query += " AND s.date <= ?"
        summary_params.append(end_date)

    summary_query += " GROUP BY i.item_id, i.item_name, s.unit ORDER BY total_quantity DESC"

    cursor.execute(summary_query, summary_params)
    summary_rows = cursor.fetchall()

    summary_list = [
        {
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "unit": row["unit"],
            "total_quantity": round(float(row["total_quantity"]), 2),
            "records_count": row["records_count"]
        }
        for row in summary_rows
    ]

    conn.close()
    return jsonify({
        "sales": sales_list,
        "summary": summary_list
    }), 200
