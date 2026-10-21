"""
Sprint 4 — Events Management & Manual Demand Adjustments Blueprint
===================================================================
Routes:
  Events (owner-only for write, any logged-in user for read):
    POST   /events              – create a new event with multiplier
    GET    /events              – list all events
    DELETE /events/<id>         – delete an event (owner only)

  Manual Demand Adjustments (owner-only):
    POST   /adjustments         – save / overwrite a manual demand figure
    GET    /adjustments         – list saved adjustments
    DELETE /adjustments/<id>    – remove an adjustment

  Summary (all logged-in users):
    GET    /forecast/summary    – quick dashboard stats (events, adjustments)

NOTE: Actual ML demand prediction (training + model evaluation) is Sprint 5 scope.
      This sprint provides manual event-factor adjustment, not AI prediction.
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from datetime import datetime, timedelta, date

from database import get_db_connection
from auth import login_required, owner_required

forecast_bp = Blueprint("forecast", __name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _today():
    return date.today().isoformat()


def _parse_date(s, label="date"):
    """Return (date_obj, None) or (None, error_string)."""
    if not s:
        return None, None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"{label} must be in YYYY-MM-DD format"


# ─── EVENTS ──────────────────────────────────────────────────────────────────

@forecast_bp.route("/events", methods=["POST"])
@owner_required
def create_event():
    """
    POST /events
    Body (JSON): { event_name, event_date, multiplier (default 1.3), notes }
    The multiplier represents the expected demand factor on that day.
    Example: multiplier=1.5 means the owner expects ~50% more demand than usual.
    This is a manual estimate, NOT an automated ML prediction.
    """
    data = request.get_json(silent=True) or request.form
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    event_name = (data.get("event_name") or "").strip()
    event_date_raw = (data.get("event_date") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not event_name:
        return jsonify({"error": "Event name is required"}), 400

    parsed_date, err = _parse_date(event_date_raw, "event_date")
    if err:
        return jsonify({"error": err}), 400
    if parsed_date is None:
        return jsonify({"error": "Event date is required (YYYY-MM-DD)"}), 400

    try:
        multiplier = float(data.get("multiplier", 1.3))
        if multiplier <= 0:
            raise ValueError("multiplier must be positive")
        if multiplier > 10:
            raise ValueError("multiplier seems unrealistically high (max 10)")
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid multiplier: {e}"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (event_name, event_date, multiplier, notes, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (event_name, parsed_date.isoformat(), multiplier, notes or None, session["user_id"])
    )
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Event '{event_name}' on {parsed_date.isoformat()} saved successfully",
        "event": {
            "event_id": event_id,
            "event_name": event_name,
            "event_date": parsed_date.isoformat(),
            "multiplier": multiplier,
            "notes": notes or None
        }
    }), 201


@forecast_bp.route("/events", methods=["GET"])
def get_events():
    """
    GET /events — list all events ordered by date.
    If requested by browser (Accept: text/html), renders events.html.
    Otherwise returns JSON for API consumers.
    """
    # Check if request is browser navigation wanting HTML
    accept = request.headers.get("Accept", "")
    is_html_request = ("text/html" in accept and "application/json" not in accept)

    if is_html_request:
        if "user_id" not in session:
            return redirect(url_for("login_page"))
        return render_template("events.html", name=session.get("name"), role=session.get("role"))

    # API Request — requires authentication
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.event_id, e.event_name, e.event_date, e.multiplier, e.notes,
               u.name AS created_by_name
        FROM events e
        JOIN users u ON e.created_by = u.user_id
        ORDER BY e.event_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    today_str = _today()
    events = [
        {
            "event_id": r["event_id"],
            "event_name": r["event_name"],
            "event_date": r["event_date"],
            "multiplier": r["multiplier"],
            "notes": r["notes"],
            "created_by_name": r["created_by_name"],
            "is_past": r["event_date"] < today_str,
            "is_today": r["event_date"] == today_str,
        }
        for r in rows
    ]
    return jsonify({"events": events}), 200


@forecast_bp.route("/events/<int:event_id>", methods=["DELETE"])
@owner_required
def delete_event(event_id):
    """DELETE /events/<id> — owner only."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, event_name FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Event not found"}), 404
    cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()
    return jsonify({
        "success": True,
        "message": f"Event '{row['event_name']}' (ID {event_id}) deleted"
    }), 200


# ─── DEMAND ADJUSTMENTS ───────────────────────────────────────────────────────

@forecast_bp.route("/adjustments", methods=["POST"])
@owner_required
def save_adjustment():
    """
    POST /adjustments
    Body (JSON): { item_id, forecast_date, adjusted_qty, notes }
    Upsert — replaces any existing adjustment for the same item + date.
    The adjusted_qty is a manually decided quantity, NOT an ML-generated prediction.
    """
    data = request.get_json(silent=True) or request.form
    if not data:
        return jsonify({"error": "Invalid payload"}), 400

    try:
        item_id = int(data.get("item_id"))
    except (ValueError, TypeError):
        return jsonify({"error": "Please select a valid food item"}), 400

    try:
        adjusted_qty = float(data.get("adjusted_qty"))
        if adjusted_qty < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Adjusted quantity must be a non-negative number"}), 400

    forecast_date_raw = (data.get("forecast_date") or "").strip()
    parsed_date, err = _parse_date(forecast_date_raw, "forecast_date")
    if err:
        return jsonify({"error": err}), 400
    if parsed_date is None:
        return jsonify({"error": "Forecast date is required (YYYY-MM-DD)"}), 400

    notes = (data.get("notes") or "").strip() or None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT item_name, unit FROM items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return jsonify({"error": "Selected food item does not exist"}), 404

    # Upsert: remove existing adjustment for same item + date before inserting
    cursor.execute(
        "DELETE FROM demand_adjustments WHERE item_id = ? AND forecast_date = ?",
        (item_id, parsed_date.isoformat())
    )
    cursor.execute(
        "INSERT INTO demand_adjustments (item_id, forecast_date, adjusted_qty, notes, adjusted_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (item_id, parsed_date.isoformat(), adjusted_qty, notes, session["user_id"])
    )
    adj_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": (
            f"Manual demand adjustment for '{item['item_name']}' "
            f"on {parsed_date.isoformat()} saved"
        ),
        "adjustment": {
            "adj_id": adj_id,
            "item_id": item_id,
            "item_name": item["item_name"],
            "unit": item["unit"],
            "forecast_date": parsed_date.isoformat(),
            "adjusted_qty": adjusted_qty,
            "notes": notes
        }
    }), 201


@forecast_bp.route("/adjustments", methods=["GET"])
@login_required
def get_adjustments():
    """GET /adjustments — optional filters: ?forecast_date=YYYY-MM-DD or ?item_id=N"""
    filter_date = request.args.get("forecast_date", "").strip()
    filter_item = request.args.get("item_id", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT a.adj_id, a.item_id, a.forecast_date, a.adjusted_qty, a.notes,
               i.item_name, i.unit, u.name AS adjusted_by_name, a.created_at
        FROM demand_adjustments a
        JOIN items i ON a.item_id = i.item_id
        JOIN users u ON a.adjusted_by = u.user_id
        WHERE 1=1
    """
    params = []
    if filter_date:
        query += " AND a.forecast_date = ?"
        params.append(filter_date)
    if filter_item:
        try:
            query += " AND a.item_id = ?"
            params.append(int(filter_item))
        except ValueError:
            pass

    query += " ORDER BY a.forecast_date DESC, a.item_id ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "adjustments": [
            {
                "adj_id": r["adj_id"],
                "item_id": r["item_id"],
                "item_name": r["item_name"],
                "unit": r["unit"],
                "forecast_date": r["forecast_date"],
                "adjusted_qty": round(float(r["adjusted_qty"]), 2),
                "notes": r["notes"],
                "adjusted_by_name": r["adjusted_by_name"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]
    }), 200


@forecast_bp.route("/adjustments/<int:adj_id>", methods=["DELETE"])
@owner_required
def delete_adjustment(adj_id):
    """DELETE /adjustments/<id> — owner only."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT adj_id FROM demand_adjustments WHERE adj_id = ?", (adj_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Adjustment record not found"}), 404
    cursor.execute("DELETE FROM demand_adjustments WHERE adj_id = ?", (adj_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Adjustment ID {adj_id} deleted"}), 200


# ─── DASHBOARD SUMMARY ────────────────────────────────────────────────────────

@forecast_bp.route("/forecast/summary", methods=["GET"])
@login_required
def forecast_summary():
    """
    GET /forecast/summary
    Quick-glance stats for the dashboard Sprint 4 cards.
    Returns total sales records, upcoming events count, next event, and active adjustments.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS cnt FROM sales_record")
    total_sales = cursor.fetchone()["cnt"]

    today_str = _today()
    in_30 = (date.today() + timedelta(days=30)).isoformat()

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM events WHERE event_date BETWEEN ? AND ?",
        (today_str, in_30)
    )
    upcoming_events = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT event_name, event_date, multiplier FROM events
        WHERE event_date >= ?
        ORDER BY event_date ASC LIMIT 1
    """, (today_str,))
    next_event_row = cursor.fetchone()
    next_event = dict(next_event_row) if next_event_row else None

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM demand_adjustments WHERE forecast_date >= ?",
        (today_str,)
    )
    active_adjustments = cursor.fetchone()["cnt"]

    conn.close()

    return jsonify({
        "total_sales_records": total_sales,
        "upcoming_events_30d": upcoming_events,
        "next_event": next_event,
        "active_adjustments": active_adjustments
    }), 200
