# Food Demand Forecasting System - Sprint 1

A single-restaurant food demand forecasting system built with Flask, SQLite, and Tailwind CSS.

## 📁 Project Folder Structure

```
AI_FORECAST_SYSTEM/
├── app.py                  # Main Flask application entry point & page routes
├── database.py             # SQLite helper functions & DB init / auto-seeding
├── auth.py                 # Blueprint for registration, login, logout, & session check
├── items.py                # Blueprint for Food Menu CRUD management
├── requirements.txt        # Python dependency list (Flask, Werkzeug)
├── test_sprint1.py         # Automated test suite for Sprint 1 functionality & security
├── README.md               # Folder structure, setup, and manual testing guide
├── static/
│   └── js/
│       └── app.js          # Client-side API fetch wrapper, session management, alert UI
└── templates/
    ├── login.html          # Login page UI
    ├── register.html       # Staff registration page UI
    ├── dashboard.html      # User dashboard page UI
    └── food-menu.html      # Owner-only food menu management page UI
```

---

## 🛠️ Step-by-Step Setup & Running Locally

### 1. Prerequisites
- Python 3.8+ installed on your system.

### 2. Install Dependencies
Open a terminal in the project directory (`c:\Users\Saad Saneen\Documents\AI_FORECAST_SYSTEM`) and run:
```bash
pip install -r requirements.txt
```

### 3. Run the Automated Tests (Optional but Recommended)
To run the security and functional test suite:
```bash
python -m unittest test_sprint1.py
```
*(All 7 tests should pass cleanly).*

### 4. Start the Application
Run the main Flask application:
```bash
python app.py
```
Output will show:
```
Starting Flask web server for Food Demand Forecasting System (Sprint 1) on port 5050...
 * Running on http://127.0.0.1:5050
```
Open your browser and navigate to `http://127.0.0.1:5050`.

---

## 🧪 Manual Testing Instructions

### Test 1: Registering a Staff User (Privilege Escalation Security Test)
1. Navigate to `http://127.0.0.1:5050/register`.
2. Notice the UI contains **only** `Username` and `Password` fields (no role selector).
3. Enter username: `kitchen_staff_1` and password: `staffpassword123`.
4. Click **Create Account**. You will see a green success alert and get redirected to `/login`.
5. *(Optional inspection)* Open `database.db` with SQLite viewer or query python:
   `SELECT name, role FROM users WHERE name='kitchen_staff_1';`
   - **Expected Result**: Row is created with `role = 'staff'`.
   - Even if an attacker uses Postman/cURL to send `{"name": "hacker", "password": "pass", "role": "owner"}`, the server ignores the payload and hardcodes `role = 'staff'`.

### Test 2: Login Behavior (Correct vs Incorrect Credentials)
1. Navigate to `http://127.0.0.1:5050/login`.
2. Try invalid password: Username `owner`, Password `wrongpassword`.
   - **Expected Result**: Red alert box displays generic error: `Invalid username or password` (HTTP 401).
3. Try nonexistent user: Username `fakeuser`, Password `any`.
   - **Expected Result**: Red alert box displays identical generic error: `Invalid username or password` (HTTP 401).
4. Login with correct owner credentials: Username `owner`, Password `owner123`.
   - **Expected Result**: Login succeeds and redirects to `/dashboard`.

### Test 3: Session Persistence & Unauthenticated Access Block
1. While logged in as `owner`, refresh the page (`F5`).
   - **Expected Result**: Dashboard remains visible and displays `Welcome back, owner!`.
2. Click **Logout** button in top navbar.
   - **Expected Result**: Redirected back to `/login`.
3. Manually type `http://127.0.0.1:5050/dashboard` in browser address bar.
   - **Expected Result**: Server detects unauthenticated state and redirects to `/login`.

### Test 4: Role-Based Navigation & Page Access (Owner vs Staff)
1. **Login as Owner (`owner` / `owner123`)**:
   - On `/dashboard`, notice the **Manage Food Menu** card with button `Open Food Menu`.
   - Click `Open Food Menu` or navigate to `/food-menu`.
   - **Expected Result**: Page loads cleanly displaying existing menu items (*Porotta*, *Pathiri*, *Chappathi*, *Biriyani*). You can add new items or delete items.
2. **Login as Staff (`kitchen_staff_1` / `staffpassword123`)**:
   - On `/dashboard`, notice the badge says `🍳 Kitchen Staff` and the **Manage Food Menu** section is **hidden**.
   - Manually type `http://127.0.0.1:5050/food-menu` in address bar.
   - **Expected Result**: Server redirects staff user back to `/dashboard`.


### Test 5: API Security Enforcement (403 Forbidden on direct API calls)
1. Log in as staff user (`kitchen_staff_1`).
2. Open Browser Developer Tools (`F12`) -> Console tab.
3. Attempt to add a food item directly via API by pasting:
   ```js
   fetch('/items', {
     method: 'POST',
     headers: {'Content-Type': 'application/json'},
     body: JSON.stringify({item_name: 'Hacked Item', unit: 'pieces'})
   }).then(r => r.json()).then(console.log);
   ```
   - **Expected Result**: Console logs `{error: "Access denied: Owner privilege required"}` with HTTP status `403 Forbidden`.
4. Attempt to delete item ID 1 directly via API:
   ```js
   fetch('/items/1', { method: 'DELETE' }).then(r => r.json()).then(console.log);
   ```
   - **Expected Result**: Response is blocked with HTTP status `403 Forbidden`.
