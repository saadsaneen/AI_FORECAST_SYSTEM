# Waste logging is functional from this sprint onward, but historical waste data was not available prior to this system, so waste-based prediction improvement (BL-05) is not yet data-validated and is scoped as future work.

from flask import Blueprint, request, jsonify, session
import sqlite3
from datetime import datetime
from database import get_db_connection
from auth import login_required, owner_required

waste_bp = Blueprint("waste", __name__)

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

@waste_bp.route("/waste", methods=["POST"])
@login_required
def add_waste():
    """
    POST /waste
    Adds a new waste log entry. Both owner and staff can add waste.
    Accepts JSON: { "item_id": 1, "quantity_wasted": 2.5, "date": "YYYY-MM-DD" }
    """
    data = request.get_json(silent=True) or request.form
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    item_id_raw = data.get("item_id")
    quantity_raw = data.get("quantity_wasted")
    date_raw = data.get("date", "").strip() if isinstance(data.get("date"), str) else ""

    # 1. Validate Item ID
    try:
        item_id = int(item_id_raw)
    except (ValueError, TypeError):
        return jsonify({"error": "Please select a valid food item"}), 400

    # 2. Validate Quantity Wasted
    try:
        quantity_wasted = float(quantity_raw)
        if quantity_wasted <= 0:
            return jsonify({"error": "Quantity wasted must be a positive number"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity wasted must be a valid positive number"}), 400

    # 3. Validate Date (No Future Dates Allowed)
    is_valid_date, date_str_or_err = validate_date(date_raw)
    if not is_valid_date:
        return jsonify({"error": date_str_or_err}), 400
    waste_date = date_str_or_err

    # 4. Fetch Item Unit from Database (Never trusted from client input)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, unit FROM items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return jsonify({"error": "Selected food item does not exist"}), 400

    unit = item["unit"]
    item_name = item["item_name"]

    # 5. User identity set from session only (Never trusted from client input)
    logged_by = session.get("user_id")
    logged_by_name = session.get("name")

    # 6. Insert Waste Record
    try:
        cursor.execute(
            """
            INSERT INTO waste_log (date, item_id, quantity_wasted, unit, logged_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (waste_date, item_id, quantity_wasted, unit, logged_by)
        )
        waste_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": "Failed to save waste record to database"}), 500

    conn.close()

    return jsonify({
        "success": True,
        "message": f"Waste of {quantity_wasted} {unit} of '{item_name}' logged successfully",
        "waste": {
            "waste_id": waste_id,
            "date": waste_date,
            "item_id": item_id,
            "item_name": item_name,
            "quantity_wasted": round(quantity_wasted, 2),
            "unit": unit,
            "logged_by": logged_by,
            "logged_by_name": logged_by_name
        }
    }), 201

@waste_bp.route("/waste", methods=["GET"])
@login_required
def get_waste():
    """
    GET /waste
    Lists waste entries with optional filters ?date= and ?item_id=.
    Role-based visibility:
    - Owner sees ALL waste entries across all users.
    - Staff sees ONLY their own waste entries (logged_by = session['user_id']), enforced server-side.
    """
    filter_date = request.args.get("date", "").strip()
    filter_item_id = request.args.get("item_id", "").strip()

    role = session.get("role")
    user_id = session.get("user_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT w.waste_id, w.date, w.item_id, w.quantity_wasted, w.unit, w.logged_by,
               i.item_name, u.name as logged_by_name
        FROM waste_log w
        JOIN items i ON w.item_id = i.item_id
        JOIN users u ON w.logged_by = u.user_id
        WHERE 1=1
    """
    params = []

    # SERVER-SIDE ROLE ENFORCEMENT
    if role != "owner":
        query += " AND w.logged_by = ?"
        params.append(user_id)

    if filter_date:
        query += " AND w.date = ?"
        params.append(filter_date)

    if filter_item_id:
        try:
            query += " AND w.item_id = ?"
            params.append(int(filter_item_id))
        except ValueError:
            pass

    query += " ORDER BY w.date DESC, w.waste_id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    waste_list = [
        {
            "waste_id": row["waste_id"],
            "date": row["date"],
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "quantity_wasted": round(float(row["quantity_wasted"]), 2),
            "unit": row["unit"],
            "logged_by": row["logged_by"],
            "logged_by_name": row["logged_by_name"]
        }
        for row in rows
    ]

    return jsonify({"waste": waste_list}), 200

@waste_bp.route("/waste/<int:waste_id>", methods=["DELETE"])
@owner_required
def delete_waste(waste_id):
    """
    DELETE /waste/<id>
    Owner only. Staff attempting this receives HTTP 403 Forbidden via @owner_required decorator.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM waste_log WHERE waste_id = ?", (waste_id,))
    entry = cursor.fetchone()

    if not entry:
        conn.close()
        return jsonify({"error": "Waste record not found"}), 404

    cursor.execute("DELETE FROM waste_log WHERE waste_id = ?", (waste_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Waste record ID {waste_id} deleted successfully"}), 200
