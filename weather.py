"""
Sprint 4 — Weather Integration Blueprint
==========================================
Uses the Open-Meteo API (free, no API key required) to fetch current weather
and today's/tomorrow's weather forecast for the restaurant location.

Routes:
  GET /weather/current   — current conditions + today's summary
  GET /weather/forecast  — 3-day weather outlook

Configuration:
  Restaurant coordinates are read from config.py (RESTAURANT_LAT, RESTAURANT_LON).
  If coordinates are not set (both are 0), returns a "not configured" response
  instead of fake data.
"""

from flask import Blueprint, jsonify
from datetime import date, timedelta
import urllib.request
import urllib.error
import json

from auth import login_required
from config import (
    RESTAURANT_LAT, RESTAURANT_LON, RESTAURANT_NAME,
    RESTAURANT_CITY, WEATHER_API_BASE, WEATHER_TIMEOUT_SECONDS,
    coordinates_configured
)

weather_bp = Blueprint("weather", __name__)


# WMO Weather Interpretation Codes → Human-readable description + emoji
# Reference: https://open-meteo.com/en/docs
WMO_CODES = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Moderate Drizzle", "🌦️"),
    55: ("Heavy Drizzle", "🌧️"),
    61: ("Slight Rain", "🌧️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    71: ("Light Snow", "🌨️"),
    73: ("Moderate Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    80: ("Rain Showers", "🌦️"),
    81: ("Moderate Showers", "🌧️"),
    82: ("Heavy Showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm + Hail", "⛈️"),
    99: ("Thunderstorm + Heavy Hail", "⛈️"),
}

def _wmo_label(code):
    if code is None:
        return "Unknown", "🌡️"
    return WMO_CODES.get(int(code), ("Unknown", "🌡️"))


def _fetch_weather(days=3):
    """
    Call Open-Meteo API and return parsed JSON or raise an exception.
    Fetches: current temperature, apparent temperature, rain, weather code,
             and hourly rain probability for the next `days` days.
    """
    params = (
        f"?latitude={RESTAURANT_LAT}"
        f"&longitude={RESTAURANT_LON}"
        f"&current=temperature_2m,apparent_temperature,weather_code,precipitation"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        f"precipitation_sum,precipitation_probability_max"
        f"&timezone=Asia%2FKolkata"
        f"&forecast_days={days}"
    )
    url = WEATHER_API_BASE + params
    req = urllib.request.Request(url, headers={"User-Agent": "RahathFoods-ForecastApp/1.0"})
    with urllib.request.urlopen(req, timeout=WEATHER_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _demand_impact(weather_code, precip_prob):
    """
    Return a simple demand impact note based on weather conditions.
    This is a qualitative label — NOT a machine-learning prediction.
    """
    if weather_code in (65, 80, 81, 82, 95, 96, 99):
        return "⬇️ Heavy rain may reduce customer footfall"
    if weather_code in (61, 63):
        return "↕️ Moderate rain — slight impact on footfall"
    if weather_code in (51, 53, 55):
        return "↕️ Light drizzle — minor impact expected"
    if weather_code == 0 and (precip_prob or 0) < 20:
        return "⬆️ Clear sunny weather — typical or higher footfall"
    if weather_code in (1, 2):
        return "➡️ Mild weather — normal demand expected"
    return "➡️ No significant weather impact predicted"


@weather_bp.route("/weather/current", methods=["GET"])
@login_required
def current_weather():
    """
    GET /weather/current
    Returns real-time weather for the restaurant location using Open-Meteo API.
    If coordinates are not configured, returns a clear configuration notice.
    """
    if not coordinates_configured():
        return jsonify({
            "configured": False,
            "message": (
                f"Restaurant location not configured. "
                f"Please set RESTAURANT_LAT and RESTAURANT_LON in config.py "
                f"or as environment variables."
            )
        }), 200

    try:
        data = _fetch_weather(days=2)
    except urllib.error.URLError as e:
        return jsonify({
            "configured": True,
            "error": "Could not connect to weather service. Check internet connection.",
            "detail": str(e.reason) if hasattr(e, "reason") else str(e)
        }), 503
    except Exception as e:
        return jsonify({
            "configured": True,
            "error": "Weather data temporarily unavailable. Please try again later.",
            "detail": str(e)
        }), 503

    current = data.get("current", {})
    daily = data.get("daily", {})

    code = current.get("weather_code")
    label, emoji = _wmo_label(code)
    temp = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    precipitation = current.get("precipitation", 0)

    # Today's daily summary (index 0)
    today_code = (daily.get("weather_code") or [None])[0]
    today_label, today_emoji = _wmo_label(today_code)
    today_max = (daily.get("temperature_2m_max") or [None])[0]
    today_min = (daily.get("temperature_2m_min") or [None])[0]
    today_precip = (daily.get("precipitation_sum") or [0])[0]
    today_precip_prob = (daily.get("precipitation_probability_max") or [0])[0]

    demand_note = _demand_impact(today_code, today_precip_prob)

    return jsonify({
        "configured": True,
        "location": {
            "name": RESTAURANT_NAME,
            "city": RESTAURANT_CITY,
            "lat": RESTAURANT_LAT,
            "lon": RESTAURANT_LON
        },
        "current": {
            "temperature_c": temp,
            "feels_like_c": feels_like,
            "precipitation_mm": precipitation,
            "weather_code": code,
            "description": label,
            "emoji": emoji
        },
        "today_summary": {
            "description": today_label,
            "emoji": today_emoji,
            "max_temp_c": today_max,
            "min_temp_c": today_min,
            "total_precipitation_mm": today_precip,
            "rain_probability_pct": today_precip_prob
        },
        "demand_impact_note": demand_note
    }), 200


@weather_bp.route("/weather/forecast", methods=["GET"])
@login_required
def weather_forecast():
    """
    GET /weather/forecast
    Returns 3-day daily weather outlook for the restaurant location.
    """
    if not coordinates_configured():
        return jsonify({
            "configured": False,
            "message": "Restaurant location not configured. Edit config.py to enable weather forecasts."
        }), 200

    try:
        data = _fetch_weather(days=3)
    except urllib.error.URLError:
        return jsonify({
            "configured": True,
            "error": "Weather service unreachable. Check internet connection."
        }), 503
    except Exception as e:
        return jsonify({
            "configured": True,
            "error": "Weather forecast temporarily unavailable."
        }), 503

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    maxes = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    precips = daily.get("precipitation_sum", [])
    probs = daily.get("precipitation_probability_max", [])

    days_out = []
    for i, d in enumerate(dates):
        code = codes[i] if i < len(codes) else None
        label, emoji = _wmo_label(code)
        prob = probs[i] if i < len(probs) else 0
        days_out.append({
            "date": d,
            "weather_code": code,
            "description": label,
            "emoji": emoji,
            "max_temp_c": maxes[i] if i < len(maxes) else None,
            "min_temp_c": mins[i] if i < len(mins) else None,
            "precipitation_mm": precips[i] if i < len(precips) else None,
            "rain_probability_pct": prob,
            "demand_impact_note": _demand_impact(code, prob)
        })

    return jsonify({
        "configured": True,
        "location": {
            "name": RESTAURANT_NAME,
            "city": RESTAURANT_CITY
        },
        "days": days_out
    }), 200
