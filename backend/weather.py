from __future__ import annotations

import json
from typing import Dict
from urllib.parse import urlencode
from urllib.request import urlopen

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def build_weather_request(latitude: float, longitude: float) -> Dict:
    return {
        "provider": "open-meteo",
        "method": "GET",
        "url": OPEN_METEO_FORECAST_URL,
        "params": {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,relative_humidity_2m,weather_code",
            "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Seoul",
            "forecast_days": 1,
        },
    }


def fetch_today_weather(latitude: float, longitude: float) -> Dict:
    request_spec = build_weather_request(latitude=latitude, longitude=longitude)
    query = urlencode(request_spec["params"])
    url = f"{OPEN_METEO_FORECAST_URL}?{query}"

    with urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    return {
        "provider": "open-meteo",
        "temperature_2m": current.get("temperature_2m"),
        "precipitation": current.get("precipitation"),
        "relative_humidity_2m": current.get("relative_humidity_2m"),
        "weather_code": current.get("weather_code"),
        "precipitation_probability_max": (daily.get("precipitation_probability_max") or [None])[0],
        "temperature_2m_max": (daily.get("temperature_2m_max") or [None])[0],
        "temperature_2m_min": (daily.get("temperature_2m_min") or [None])[0],
    }
