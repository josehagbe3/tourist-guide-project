import os
import requests

EXCHANGERATE_API_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"


def fetch_exchangerate(base_currency: str) -> dict:
    """Raw ExchangeRate-API response — raises on any failure."""
    api_key = os.getenv("EXCHANGERATE_API_KEY")
    if not api_key:
        raise RuntimeError("EXCHANGERATE_API_KEY not set")
    resp = requests.get(
        EXCHANGERATE_API_URL.format(key=api_key, base=base_currency),
        timeout=5
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise ValueError(f"API error: {data.get('error-type', 'unknown')}")
    return data
