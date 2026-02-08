from typing import Dict


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def build_weather_request(latitude: float, longitude: float) -> Dict:
    """Build request metadata for Open-Meteo.

    실제 HTTP 호출은 API 키/재시도 정책 확정 후 연결합니다.
    """
    return {
        "provider": "open-meteo",
        "method": "GET",
        "url": OPEN_METEO_FORECAST_URL,
        "params": {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation_probability,relative_humidity_2m",
            "timezone": "Asia/Seoul",
        },
        "integration_status": "stubbed_without_http_call",
    }
