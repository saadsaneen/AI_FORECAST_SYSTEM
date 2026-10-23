# AI Food Demand Forecasting System

The AI Food Demand Forecasting System supports daily operations at Rahath Foods. It provides sales and waste recording, weather and event context, manual demand adjustments, and ML-based demand forecasts with kitchen preparation estimates.

## Main Features

- User registration, login, sessions, and role-based access for owners and kitchen staff.
- Owner food menu management.
- Sales entry and filtered sales history with per-item quantity totals.
- Waste logging and history.
- Weather information through Open-Meteo and event management with demand multipliers.
- Owner-managed manual demand adjustments.
- ML demand predictions for five food items using saved scikit-learn models.
- Kitchen preparation summary with estimated main raw material requirements.

Sales reports can be viewed as filtered history and totals. CSV/PDF report export is not implemented. Generated prediction history is not stored.

## Technology and Dependencies

- Python and Flask for the web application and API.
- SQLite for application data.
- HTML, Tailwind CSS, and JavaScript for the interface.
- scikit-learn, joblib, pandas, and NumPy for model loading and inference.
- Open-Meteo for weather data; no API key is required.

Dependencies are listed in `requirements.txt`:

- Flask 3.0 or later
- Werkzeug 3.0 or later
- joblib 1.3 or later
- scikit-learn 1.3 or later
- pandas 2.0 or later
- NumPy 1.24 or later

## Project Structure

```text
AI_FORECAST_SYSTEM/
├── app.py                         # Flask application and page routes
├── auth.py                        # Registration, login, logout, and session checks
├── config.py                      # Restaurant and weather configuration
├── database.py                    # SQLite connection, schema, and seed data
├── forecast.py                    # Events, adjustments, summary, and prediction API
├── items.py                       # Food menu API
├── ml_engine.py                   # Loads models and calculates predictions
├── sales.py                       # Sales entry and history API
├── waste.py                       # Waste logging API
├── weather.py                     # Open-Meteo weather API
├── import_historical_data.py      # Historical sales CSV import
├── view_db.py                     # Database viewing utility
├── historical_sales.csv           # Historical sales import data
├── requirements.txt               # Python dependencies
├── test_sprint1.py                # Authentication and menu tests
├── test_sprint2.py                # Sales and CSV import tests
├── test_sprint3.py                # Waste logging tests
├── test_sprint4.py                # Weather, events, adjustments, and summary tests
├── test_sprint5.py                # ML prediction and integration tests
├── datasets/
│   ├── sales_dataset.csv           # Model sales data
│   └── waste_dataset.csv           # Waste data
├── models/
│   ├── rahath_model1_calendar.joblib
│   └── rahath_model2_previous_sales.joblib
├── static/js/app.js               # Shared client-side behavior
└── templates/                     # Flask HTML pages
```

`database.db` is created or used in the current working directory. SQLite database files are local runtime data and are excluded from version control.

## Windows Installation

Open PowerShell in the project directory. Create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, follow your organization's execution policy or activate the environment using another supported shell. Keep the virtual environment active when running the application or tests.

## Database Setup and Application Run

Run commands from the project directory because the application uses the relative path `database.db`.

```powershell
python database.py
python app.py
```

`python database.py` initializes the schema and seeds default data. `python app.py` also calls `init_db()` before starting Flask, so the first command is optional. The development server listens at `http://127.0.0.1:5050`.

The default development owner account is:

- Username: `owner`
- Password: `owner123`

These credentials and the fallback Flask secret key are for local development only. Set a private `SECRET_KEY` environment variable and do not deploy the default credentials or Flask debug server.

## Weather Configuration

`config.py` reads these optional environment variables:

- `RESTAURANT_LAT` (default: `9.9695`)
- `RESTAURANT_LON` (default: `76.2984`)
- `RESTAURANT_NAME` (default: `Rahath Foods`)
- `RESTAURANT_CITY` (default: `Nettoor, Ernakulam, Kerala`)

The default coordinates approximate Nettoor, Ernakulam. Set the latitude and longitude to the restaurant's location for more accurate weather. Weather responses are disabled when either coordinate is set to `0`.

## Running Tests

Run each suite separately from the project directory:

```powershell
python -m unittest test_sprint1 -v
python -m unittest test_sprint2 -v
python -m unittest test_sprint3 -v
python -m unittest test_sprint4 -v
python -m unittest test_sprint5 -v
```

The suites initialize and use test databases. Sprint 1, 2, 3, and 5 use suite-specific paths with production-database guards. Sprint 4 uses the relative file `test_sprint4.db` and deletes/recreates it; keep the working directory at the project root and do not make that file a link to `database.db`.

## Testing Results and Sprint 6 Status

The reported result is 55 passing tests across five suites: Sprint 1 (7), Sprint 2 (5), Sprint 3 (11), Sprint 4 (19), and Sprint 5 (13). Sprint 6 documentation should be kept aligned with future test runs and report implementation.

Sales history and filtered quantity totals are available. CSV/PDF report generation and export are not implemented. Generated prediction history is not implemented. These remain limitations rather than completed Sprint 6 features.

## Known Model Compatibility Limitation

The saved models were trained with scikit-learn 1.6.1. Loading them with scikit-learn 1.9.1 produced an `InconsistentVersionWarning`. The dependency currently allows a range of scikit-learn versions. Use the validated training/runtime version or retrain and verify the models before changing versions.
