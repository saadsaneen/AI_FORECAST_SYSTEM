from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from database import get_db_connection

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    """Decorator to require login for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    """Decorator to require owner role for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        if session.get("role") != "owner":
            return jsonify({"error": "Access denied: Owner privilege required"}), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /register
    Accepts JSON: { "name": "...", "password": "..." }
    Hardcodes role="staff" on the server side to prevent privilege escalation.
    """
    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip() if data else ""
    password = data.get("password", "").strip() if data else ""

    if not name or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # SERVER-SIDE PRIVILEGE ESCALATION SECURITY RULE:
    # Role is strictly hardcoded to "staff". Any "role" field sent in the request is completely ignored.
    role = "staff"
    password_hash = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (name, password_hash, role) VALUES (?, ?, ?)",
            (name, password_hash, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username already exists"}), 400
    except Exception as e:
        conn.close()
        return jsonify({"error": "Server error during registration"}), 500

    conn.close()
    return jsonify({"success": True, "message": "Registration successful. Please log in."}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /login
    Accepts JSON: { "name": "...", "password": "..." }
    Returns 401 with generic error message on failure.
    """
    data = request.get_json(silent=True) or request.form
    name = data.get("name", "").strip() if data else ""
    password = data.get("password", "").strip() if data else ""

    if not name or not password:
        return jsonify({"error": "Invalid username or password"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cursor.fetchone()
    conn.close()

    # Generic error message to prevent username enumeration attacks
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Establish session
    session.clear()
    session["user_id"] = user["user_id"]
    session["name"] = user["name"]
    session["role"] = user["role"]

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user["role"]
        }
    }), 200

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """GET/POST /logout - clears the Flask session."""
    session.clear()
    if request.headers.get("Accept", "").find("text/html") != -1 and not request.is_json:
        from flask import redirect, url_for
        return redirect(url_for("login_page"))
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

@auth_bp.route("/session-check", methods=["GET"])
def session_check():
    """GET /session-check - returns current login state and user info."""
    if "user_id" in session:
        return jsonify({
            "logged_in": True,
            "user": {
                "user_id": session.get("user_id"),
                "name": session.get("name"),
                "role": session.get("role")
            }
        }), 200
    return jsonify({"logged_in": False}), 200
