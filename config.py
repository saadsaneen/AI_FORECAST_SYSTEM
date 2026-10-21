"""
Restaurant Configuration — Sprint 4
=====================================
Edit RESTAURANT_LAT and RESTAURANT_LON to set the actual location of Rahath Foods.
The default coordinates approximate Nettoor, Ernakulam, Kerala, India.
Set env vars RESTAURANT_LAT and RESTAURANT_LON to override without editing this file.
"""

import os

# Rahath Foods — Nettoor, Ernakulam, Kerala, India
# Approx coordinates: 9.9695 N, 76.2984 E
# Confirm exact location with Google Maps and update below for precise weather data.
RESTAURANT_LAT = float(os.environ.get("RESTAURANT_LAT", "9.9695"))
RESTAURANT_LON = float(os.environ.get("RESTAURANT_LON", "76.2984"))
RESTAURANT_NAME = os.environ.get("RESTAURANT_NAME", "Rahath Foods")
RESTAURANT_CITY = os.environ.get("RESTAURANT_CITY", "Nettoor, Ernakulam, Kerala")

# Weather API config (Open-Meteo — free, no API key required)
WEATHER_API_BASE = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 8  # Max wait for weather API response

# Coordinates are considered "configured" if they differ from the default placeholder
# If you want to mark as unconfigured, set RESTAURANT_LAT=0 or RESTAURANT_LON=0
def coordinates_configured():
    return RESTAURANT_LAT != 0 and RESTAURANT_LON != 0
