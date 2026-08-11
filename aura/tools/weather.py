"""
aura/tools/weather.py
---------------------
Weather lookup tool using OpenStreetMap Nominatim & Open-Meteo APIs.
Supports single or multiple locations, states, towns, and villages.
"""

import json
import logging
import re
import urllib.request
import urllib.parse
from langchain_core.tools import tool
from aura.tools.base import TOOL_REGISTRY, LANGCHAIN_TOOLS

logger = logging.getLogger(__name__)

_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm"
}


def _geocode_location(loc_name: str) -> tuple[float | None, float | None, str]:
    """
    Geocode location string using OpenStreetMap Nominatim first (high precision for towns/villages/states),
    falling back to Open-Meteo Geocoding API.
    Returns (latitude, longitude, display_name).
    """
    clean_search = loc_name.strip()
    
    # 1. Try OpenStreetMap Nominatim API first
    try:
        nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(clean_search)}&format=json&limit=1"
        req_nom = urllib.request.Request(nom_url, headers={"User-Agent": "Aura-Assistant/1.0 (Contact: support@aura.ai)"})
        with urllib.request.urlopen(req_nom, timeout=5) as resp_nom:
            nom_data = json.loads(resp_nom.read().decode("utf-8"))
            if nom_data:
                first = nom_data[0]
                lat = float(first.get("lat"))
                lon = float(first.get("lon"))
                disp = first.get("display_name", clean_search)
                parts = [p.strip() for p in disp.split(",")]
                # Build concise display name (e.g. "Maredumilli, Andhra Pradesh, India")
                if len(parts) >= 3:
                    short_name = f"{parts[0]}, {parts[-2]} {parts[-1]}".strip()
                else:
                    short_name = disp
                return lat, lon, short_name
    except Exception as e:
        logger.warning("Nominatim geocoding error for %s: %s", clean_search, e)

    # 2. Fallback to Open-Meteo Geocoding API
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_search)}&count=5&language=en&format=json"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0 (Aura-Assistant)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results", [])
            
            if results:
                best = results[0]
                lat, lon = best.get("latitude"), best.get("longitude")
                display_name = f"{best.get('name')}, {best.get('admin1', '')} {best.get('country', '')}".strip()
                return lat, lon, display_name
    except Exception as e:
        logger.warning("Open-Meteo geocoding error for %s: %s", clean_search, e)

    return None, None, clean_search


def _get_single_weather(loc_name: str) -> str:
    """Fetch current weather for a single location."""
    lat, lon, display_name = _geocode_location(loc_name)
    if lat is None or lon is None:
        return f"Could not find coordinates for location '{loc_name}'."

    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "Mozilla/5.0 (Aura-Assistant)"})
        with urllib.request.urlopen(req_w, timeout=5) as resp_w:
            w_data = json.loads(resp_w.read().decode("utf-8"))
            cur = w_data.get("current", {})
            units = w_data.get("current_units", {})
            desc = _WMO_CODES.get(cur.get("weather_code", -1), "Clear / Partly Cloudy")

            return (
                f"Weather for {display_name}:\n"
                f"- Condition: {desc}\n"
                f"- Temperature: {cur.get('temperature_2m')}{units.get('temperature_2m', '°C')} "
                f"(Feels like {cur.get('apparent_temperature')}{units.get('apparent_temperature', '°C')})\n"
                f"- Humidity: {cur.get('relative_humidity_2m')}{units.get('relative_humidity_2m', '%')}\n"
                f"- Precipitation: {cur.get('precipitation')}{units.get('precipitation', 'mm')}\n"
                f"- Wind Speed: {cur.get('wind_speed_10m')} {units.get('wind_speed_10m', 'km/h')}"
            )
    except Exception as e:
        logger.error("Weather forecast error for %s: %s", loc_name, e)
        return f"Error fetching weather forecast for '{loc_name}': {e}"


@tool
def fetch_weather(location: str = "", city: str = "") -> str:
    """
    Fetch current weather report for one or multiple cities/locations.
    Supports single locations ('Tokyo'), multiple locations ('Goa and Maredumilli'), states, and villages.
    """
    raw_loc = (location or city or "").strip()

    if not raw_loc or raw_loc.lower() in ("current", "current location", "here", "current_location", ""):
        raw_loc = "Hyderabad"  # Default fallback location

    # Parse potential multiple locations separated by 'and', '&', or commas
    locations = []
    split_parts = re.split(r"\s+(?:and|&)\s+", raw_loc, flags=re.IGNORECASE)
    for part in split_parts:
        part = part.strip()
        if part:
            locations.append(part)

    if not locations:
        locations = [raw_loc]

    reports = []
    for loc in locations:
        reports.append(_get_single_weather(loc))

    return "\n\n".join(reports)


# Register both 'fetch_weather' and 'weather' aliases in registry
TOOL_REGISTRY["fetch_weather"] = fetch_weather
TOOL_REGISTRY["weather"] = fetch_weather
LANGCHAIN_TOOLS.append(fetch_weather)
