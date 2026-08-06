"""
aura/tools/weather.py
---------------------
Weather lookup tool using Open-Meteo API.
Supports aliases for location parameters and flexible input handling.
"""

import json
import logging
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


@tool
def fetch_weather(location: str = "", city: str = "") -> str:
    """
    Fetch current weather report for a given city or location string.
    Parameters can be passed as location or city.
    """
    target_loc = (location or city or "").strip()

    if not target_loc or target_loc.lower() in ("current", "current location", "here", "current_location", ""):
        target_loc = "Hyderabad"  # Default city fallback if unspecified

    try:
        # 1. Geocode location name
        clean_search = target_loc.split(",")[0].strip() if "," in target_loc else target_loc
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_search)}&count=1&language=en&format=json"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0 (Aura-Assistant)"})
        with urllib.request.urlopen(req) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
            results = geo_data.get("results")
            if not results:
                return f"Could not find weather coordinates for location '{target_loc}'."
            
        loc_info = results[0]
        lat, lon = loc_info.get("latitude"), loc_info.get("longitude")
        loc_name = f"{loc_info.get('name')}, {loc_info.get('country', '')}"

        # 2. Fetch forecast
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
        req_w = urllib.request.Request(weather_url, headers={"User-Agent": "Mozilla/5.0 (Aura-Assistant)"})
        with urllib.request.urlopen(req_w) as resp_w:
            w_data = json.loads(resp_w.read().decode("utf-8"))
            cur = w_data.get("current", {})
            units = w_data.get("current_units", {})
            desc = _WMO_CODES.get(cur.get("weather_code", -1), "Unknown")

            return (
                f"Current Weather Report for {loc_name}:\n"
                f"- Condition: {desc}\n"
                f"- Temperature: {cur.get('temperature_2m')}{units.get('temperature_2m', '°C')} "
                f"(Feels like {cur.get('apparent_temperature')}{units.get('apparent_temperature', '°C')})\n"
                f"- Humidity: {cur.get('relative_humidity_2m')}{units.get('relative_humidity_2m', '%')}\n"
                f"- Precipitation: {cur.get('precipitation')}{units.get('precipitation', 'mm')}\n"
                f"- Wind Speed: {cur.get('wind_speed_10m')} {units.get('wind_speed_10m', 'km/h')}"
            )
    except Exception as e:
        logger.error("Weather tool error for %s: %s", target_loc, e)
        return f"Error fetching weather for '{target_loc}': {e}"


# Register both 'fetch_weather' and 'weather' aliases in registry
TOOL_REGISTRY["fetch_weather"] = fetch_weather
TOOL_REGISTRY["weather"] = fetch_weather
LANGCHAIN_TOOLS.append(fetch_weather)
