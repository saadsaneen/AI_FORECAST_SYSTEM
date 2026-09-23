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

### Test 1: User Registration

1. Navigate to `/register`.
2. Create a new test account using the registration form.
3. Submit the form.
4. **Expected Result:** The account is created successfully and the user is redirected to the login page.

### Test 2: Login Behavior

1. Navigate to `/login`.
2. Enter the credentials of a registered test account.
3. **Expected Result:** Valid credentials allow the user to log in and access the dashboard.
4. Try an incorrect password.
5. **Expected Result:** A generic `Invalid username or password` message is displayed.

### Test 3: Session Persistence & Logout

1. Log in using a registered test account.
2. Refresh the dashboard.
3. **Expected Result:** The logged-in session remains active.
4. Click **Logout**.
5. **Expected Result:** The user is redirected to the login page.
6. Try accessing `/dashboard` after logout.
7. **Expected Result:** Unauthenticated users are redirected to the login page.

### Test 4: Food Menu Access

1. Log in to the application.
2. Navigate to the dashboard.
3. Open the **Food Menu** section.
4. **Expected Result:** Existing food items are displayed and authorized users can add or delete menu items.


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
