import os
import requests

OPENTRIPMAP_GEONAME_URL = "https://api.opentripmap.com/0.1/en/places/geoname"
OPENTRIPMAP_RADIUS_URL  = "https://api.opentripmap.com/0.1/en/places/radius"
NOMINATIM_URL           = "https://nominatim.openstreetmap.org/search"
OVERPASS_SERVERS        = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


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
    return names[:5]


def _geocode(city: str) -> tuple[float, float]:
    """
    Resolve a city name to (lat, lon) using Nominatim.
    Tries multiple strategies to handle accented names, alternate spellings, etc.
    Raises ValueError if nothing is found.
    """
    headers = {"User-Agent": "TouristGuideAgent/1.0", "Accept-Language": "en"}

    # Strategy 1: plain city name search
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": city, "format": "json", "limit": 3,
                "featuretype": "city", "addressdetails": 0},
        headers=headers, timeout=6,
    )
    resp.raise_for_status()
    results = resp.json()

    # Strategy 2: if no results, relax the featuretype filter
    if not results:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": city, "format": "json", "limit": 3, "addressdetails": 0},
            headers=headers, timeout=6,
        )
        resp.raise_for_status()
        results = resp.json()

    # Strategy 3: try as a settlement (handles villages/towns spelled differently)
    if not results:
        resp = requests.get(
            NOMINATIM_URL,
            params={"city": city, "format": "json", "limit": 3, "addressdetails": 0},
            headers=headers, timeout=6,
        )
        resp.raise_for_status()
        results = resp.json()

    if not results:
        raise ValueError(f"City not found via geocoding: {city}")

    return float(results[0]["lat"]), float(results[0]["lon"])


def _overpass_query(lat: float, lon: float, radius: int) -> list[str]:
    """
    Query Overpass for tourism-related named places within radius metres.
    Tries each server in OVERPASS_SERVERS until one responds.
    Uses a broad set of tags so cities with sparse tourism= tagging still return results.
    """
    query = f"""
    [out:json][timeout:15];
    (
      node["tourism"~"attraction|museum|gallery|viewpoint|artwork|zoo|theme_park"](around:{radius},{lat},{lon});
      node["historic"~"monument|memorial|castle|ruins|archaeological_site|building"](around:{radius},{lat},{lon});
      node["leisure"~"park|nature_reserve|garden"](around:{radius},{lat},{lon});
      node["amenity"~"place_of_worship|theatre|arts_centre|marketplace"](around:{radius},{lat},{lon});
      way["tourism"~"attraction|museum|gallery|viewpoint"](around:{radius},{lat},{lon});
      way["historic"~"monument|memorial|castle|ruins|archaeological_site"](around:{radius},{lat},{lon});
    );
    out tags 20;
    """
    last_error = None
    for server in OVERPASS_SERVERS:
        try:
            resp = requests.post(server, data={"data": query}, timeout=15)
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
            seen = set()
            names = []
            for e in elements:
                name = e.get("tags", {}).get("name", "").strip()
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
            return names
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"All Overpass servers failed: {last_error}")


def fetch_overpass(city: str) -> list[str]:
    """
    Fetch attractions via Nominatim geocoding + Overpass query.
    Tries a 15 km radius first; expands to 30 km if too few results.
    Raises on total failure.
    """
    lat, lon = _geocode(city)

    names = _overpass_query(lat, lon, radius=15000)

    # Expand radius if fewer than 3 results
    if len(names) < 3:
        names = _overpass_query(lat, lon, radius=30000)

    if not names:
        raise ValueError(f"No named attractions found near {city}")

    return names[:5]
