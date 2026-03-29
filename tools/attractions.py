import os
import requests

OPENTRIPMAP_GEONAME_URL = "https://api.opentripmap.com/0.1/en/places/geoname"
OPENTRIPMAP_RADIUS_URL  = "https://api.opentripmap.com/0.1/en/places/radius"
NOMINATIM_URL           = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL            = "https://overpass-api.de/api/interpreter"


def fetch_opentripmap(city: str) -> list[str]:
    """Raw OpenTripMap attractions — raises on any failure."""
    api_key = os.getenv("OPENTRIPMAP_API_KEY")
    if not api_key:
        raise RuntimeError("OPENTRIPMAP_API_KEY not set")

    geo = requests.get(
        OPENTRIPMAP_GEONAME_URL,
        params={"name": city, "apikey": api_key},
        timeout=6,
    )
    geo.raise_for_status()
    geo_data = geo.json()
    if geo_data.get("status") == "NOT_FOUND" or "lat" not in geo_data:
        raise ValueError(f"City not found: {city}")

    lat, lon = geo_data["lat"], geo_data["lon"]
    resp = requests.get(
        OPENTRIPMAP_RADIUS_URL,
        params={
            "radius": 10000, "lon": lon, "lat": lat,
            "kinds": "cultural,historic,architecture,museums,natural",
            "rate": 2, "format": "json", "limit": 10,
            "apikey": api_key,
        },
        timeout=6,
    )
    resp.raise_for_status()
    places = resp.json()
    if not isinstance(places, list):
        raise ValueError("Unexpected response format")

    names = list({p["name"].strip() for p in places if p.get("name", "").strip()})
    if not names:
        raise ValueError("No named attractions returned")
    return names[:3]


def fetch_overpass(city: str) -> list[str]:
    """Raw Overpass/Nominatim attractions — raises on any failure."""
    geo = requests.get(
        NOMINATIM_URL,
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "TouristGuideAgent/1.0"},
        timeout=6,
    )
    geo.raise_for_status()
    results = geo.json()
    if not results:
        raise ValueError(f"City not found: {city}")

    lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
    query = f"""
    [out:json][timeout:10];
    node["tourism"="attraction"](around:10000,{lat},{lon});
    out 15;
    """
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=12)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])

    names = [
        e["tags"]["name"]
        for e in elements
        if e.get("tags", {}).get("name", "").strip()
    ]
    if not names:
        raise ValueError("No named attractions found")
    return names[:3]
