from __future__ import annotations

import json
from typing import Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODE_LABELS = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "착빙 안개",
    51: "약한 이슬비",
    53: "보통 이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "보통 비",
    65: "강한 비",
    71: "약한 눈",
    80: "약한 소나기",
    81: "보통 소나기",
    82: "강한 소나기",
    95: "뇌우",
}


def build_weather_request(latitude: float, longitude: float) -> Dict:
    """Open-Meteo forecast API request spec.

    Docs: https://open-meteo.com/en/docs
    """
    return {
        "provider": "open-meteo",
        "method": "GET",
        "url": OPEN_METEO_FORECAST_URL,
        "params": {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weather_code",
            "timezone": "Asia/Seoul",
            "forecast_days": 1,
        },
    }


def _today_hourly_window(hourly: Dict, max_slots: int = 10) -> List[Dict]:
    times = hourly.get("time", [])[:max_slots]
    probs = hourly.get("precipitation_probability", [])[:max_slots]
    precips = hourly.get("precipitation", [])[:max_slots]
    hums = hourly.get("relative_humidity_2m", [])[:max_slots]

    window = []
    for idx, t in enumerate(times):
        window.append(
            {
                "time": t,
                "precipitation_probability": probs[idx] if idx < len(probs) else None,
                "precipitation": precips[idx] if idx < len(precips) else None,
                "relative_humidity_2m": hums[idx] if idx < len(hums) else None,
            }
        )
    return window


def _build_weather_rag_text(current: Dict, daily: Dict, hourly_window: List[Dict]) -> str:
    code = current.get("weather_code")
    label = WEATHER_CODE_LABELS.get(code, f"unknown({code})")
    rain_risk = (daily.get("precipitation_probability_max") or [0])[0] or 0
    total_rain = (daily.get("precipitation_sum") or [0])[0] or 0
    hum = current.get("relative_humidity_2m")

    caution = []
    if rain_risk >= 50 or total_rain >= 3:
        caution.append("강수 리스크 높음: 옥외 노출 작업 최소화")
    if (hum or 0) >= 80:
        caution.append("습도 높음: 건조시간 지연 가능")

    return (
        f"현재날씨={label}, 현재기온={current.get('temperature_2m')}°C, 현재습도={hum}%, "
        f"금일최고/최저={((daily.get('temperature_2m_max') or [None])[0])}/"
        f"{((daily.get('temperature_2m_min') or [None])[0])}°C, "
        f"강수확률최대={rain_risk}%, 예상강수량={total_rain}mm, "
        f"시간대샘플={hourly_window[:3]}, 작업주의={' | '.join(caution) if caution else '특이사항 없음'}"
    )


def fetch_today_weather(latitude: float, longitude: float) -> Dict:
    request_spec = build_weather_request(latitude=latitude, longitude=longitude)
    query = urlencode(request_spec["params"])
    url = f"{OPEN_METEO_FORECAST_URL}?{query}"

    with urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    current = payload.get("current", {})
    hourly = payload.get("hourly", {})
    daily = payload.get("daily", {})

    hourly_window = _today_hourly_window(hourly)
    weather_code = current.get("weather_code")

    return {
        "provider": "open-meteo",
        "location": {"latitude": latitude, "longitude": longitude},
        "current": {
            "temperature_2m": current.get("temperature_2m"),
            "relative_humidity_2m": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed_10m": current.get("wind_speed_10m"),
            "weather_code": weather_code,
            "weather_label": WEATHER_CODE_LABELS.get(weather_code, f"unknown({weather_code})"),
        },
        "daily": {
            "temperature_2m_max": (daily.get("temperature_2m_max") or [None])[0],
            "temperature_2m_min": (daily.get("temperature_2m_min") or [None])[0],
            "precipitation_probability_max": (daily.get("precipitation_probability_max") or [None])[0],
            "precipitation_sum": (daily.get("precipitation_sum") or [None])[0],
            "weather_code": (daily.get("weather_code") or [None])[0],
        },
        "hourly_window": hourly_window,
        "rag_weather_summary": _build_weather_rag_text(current=current, daily=daily, hourly_window=hourly_window),
    }
