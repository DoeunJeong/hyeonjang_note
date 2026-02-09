from __future__ import annotations

import json
from typing import Dict, List
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
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation",
            "timezone": "Asia/Seoul",
            "forecast_days": 1,
        },
    }


def _hourly_weather_rows(hourly: Dict, max_slots: int = 20) -> List[Dict]:
    times = hourly.get("time", [])[:max_slots]
    temps = hourly.get("temperature_2m", [])[:max_slots]
    hums = hourly.get("relative_humidity_2m", [])[:max_slots]
    probs = hourly.get("precipitation_probability", [])[:max_slots]
    precips = hourly.get("precipitation", [])[:max_slots]

    rows: List[Dict] = []
    for idx, t in enumerate(times):
        rows.append(
            {
                "time": t,
                "temperature_2m": temps[idx] if idx < len(temps) else None,
                "relative_humidity_2m": hums[idx] if idx < len(hums) else None,
                "precipitation_probability": probs[idx] if idx < len(probs) else None,
                "precipitation": precips[idx] if idx < len(precips) else None,
            }
        )
    return rows


def fetch_today_weather(latitude: float, longitude: float) -> Dict:
    request_spec = build_weather_request(latitude=latitude, longitude=longitude)
    query = urlencode(request_spec["params"])
    url = f"{OPEN_METEO_FORECAST_URL}?{query}"

    with urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    hourly_rows = _hourly_weather_rows(payload.get("hourly", {}))
    return {
        "provider": "open-meteo",
        "location": {"latitude": latitude, "longitude": longitude},
        "hourly_weather": hourly_rows,
    }
