import os
from flask import Flask, render_template, redirect, url_for, session
from database import init_db
from auth import auth_bp
from items import items_bp
from sales import sales_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key-food-forecast-sprint1")
app.config["SESSION_COOKIE_NAME"] = "food_demand_session_sprint1"

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(items_bp)
app.register_blueprint(sales_bp)

# Page Routes
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard_page"))
    return redirect(url_for("login_page"))

@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")

@app.route("/register")
def register_page():
    if "user_id" in session:
        return redirect(url_for("dashboard_page"))
    return render_template("register.html")

@app.route("/dashboard")
def dashboard_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", name=session.get("name"), role=session.get("role"))

@app.route("/food-menu")
def food_menu_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    # SERVER-SIDE ROLE ACCESS CONTROL FOR PAGES
    if session.get("role") != "owner":
        return redirect(url_for("dashboard_page"))
    return render_template("food-menu.html", name=session.get("name"), role=session.get("role"))

@app.route("/sales-entry")
def sales_entry_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("sales-entry.html", name=session.get("name"), role=session.get("role"))

@app.route("/sales-history")
def sales_history_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("sales-history.html", name=session.get("name"), role=session.get("role"))

if __name__ == "__main__":
    init_db()
    print("Starting Flask web server for Food Demand Forecasting System (Sprint 2) on port 5050...")
    app.run(host="127.0.0.1", port=5050, debug=True)

