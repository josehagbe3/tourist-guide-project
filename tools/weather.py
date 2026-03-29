import os
import requests

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
WTTR_URL        = "https://wttr.in/{city}?format=j1"


def fetch_openweather(city: str) -> dict:
    """Raw OpenWeatherMap response — raises on any failure."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY not set")
    resp = requests.get(
        OPENWEATHER_URL,
        params={"q": city, "appid": api_key, "units": "metric"},
        timeout=5
    )
    resp.raise_for_status()
    return resp.json()


def fetch_wttr(city: str) -> dict:
    """Raw wttr.in response — raises on any failure."""
    resp = requests.get(
        WTTR_URL.format(city=requests.utils.quote(city)),
        timeout=6
    )
    resp.raise_for_status()
    return resp.json()
