from flask import Blueprint, request, jsonify
import sqlite3
from database import get_db_connection
from auth import login_required, owner_required

items_bp = Blueprint("items", __name__)

@items_bp.route("/items", methods=["GET"])
@login_required
def get_items():
    """GET /items - List all food menu items."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_id, item_name, unit, price FROM items ORDER BY item_id ASC")
    items = cursor.fetchall()
    conn.close()

    item_list = [
        {
            "item_id": row["item_id"],
            "item_name": row["item_name"],
            "unit": row["unit"],
            "price": round(float(row["price"]), 2)
        }
        for row in items
    ]
    return jsonify({"items": item_list}), 200

@items_bp.route("/items", methods=["POST"])
@owner_required
def add_item():
    """
    POST /items - Add a new food item (owner only).
    Accepts JSON: { "item_name": "...", "unit": "...", "price": 0.0 }
    """
    data = request.get_json(silent=True) or request.form
    item_name = data.get("item_name", "").strip() if data else ""
    unit = data.get("unit", "pieces").strip() if data else "pieces"
    
    price_val = 0.0
    if data and "price" in data:
        try:
            price_val = float(data.get("price", 0.0))
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400

    if not item_name:
        return jsonify({"error": "Item name is required"}), 400
    if not unit:
        unit = "pieces"
    if price_val < 0:
        return jsonify({"error": "Price cannot be negative"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO items (item_name, unit, price) VALUES (?, ?, ?)",
            (item_name, unit, price_val)
        )
        new_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Item '{item_name}' already exists in food menu"}), 400
    except Exception as e:
        conn.close()
        return jsonify({"error": "Server error while adding item"}), 500

    conn.close()
    return jsonify({
        "success": True,
        "message": f"Item '{item_name}' added successfully",
        "item": {
            "item_id": new_id,
            "item_name": item_name,
            "unit": unit,
            "price": round(price_val, 2)
        }
    }), 201

@items_bp.route("/items/<int:item_id>", methods=["DELETE"])
@owner_required
def delete_item(item_id):
    """
    DELETE /items/<item_id> - Remove a food item (owner only).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    cursor.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"Item ID {item_id} deleted successfully"}), 200
