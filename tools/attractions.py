import os
import requests
from functools import lru_cache

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


@lru_cache(maxsize=512)
def _geocode(city: str) -> tuple[float, float, str]:
    """
    Resolve a city name to (lat, lon, country_code) using Nominatim.
    Result is cached so repeated calls for the same city are free.
    Tries multiple strategies to handle accents, alternate spellings, etc.
    Raises ValueError if nothing is found.
    """
    headers = {"User-Agent": "TouristGuideAgent/1.0", "Accept-Language": "en"}

    for params in [
        {"q": city, "format": "json", "limit": 3,
         "featuretype": "city", "addressdetails": 1},
        {"q": city, "format": "json", "limit": 3, "addressdetails": 1},
        {"city": city, "format": "json", "limit": 3, "addressdetails": 1},
    ]:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=6)
        resp.raise_for_status()
        results = resp.json()
        if results:
            r = results[0]
            country_code = r.get("address", {}).get("country_code", "").upper()
            return float(r["lat"]), float(r["lon"]), country_code

    raise ValueError(f"City not found via geocoding: {city}")


def _score_element(tags: dict) -> int:
    """
    Return a quality score for an OSM element.
    Higher = better: prefer entries linked to Wikipedia/Wikidata
    and tourism=attraction over generic amenity tags.
    """
    score = 0
    if tags.get("wikidata"):
        score += 3
    if tags.get("wikipedia"):
        score += 2
    if tags.get("tourism") in ("attraction", "museum", "gallery", "viewpoint"):
        score += 2
    if tags.get("historic") in ("monument", "memorial", "castle", "ruins",
                                 "archaeological_site"):
        score += 1
    return score


def _overpass_query(lat: float, lon: float, radius: int) -> list[str]:
    """
    Query Overpass for tourism-related named places within radius metres.
    Tries each server in OVERPASS_SERVERS until one responds.
    Results are ranked by quality score (wikidata/wikipedia links first).
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

            # Rank by quality, deduplicate by name
            scored = []
            seen = set()
            for e in elements:
                tags = e.get("tags", {})
                name = tags.get("name", "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                scored.append((name, _score_element(tags)))

            scored.sort(key=lambda x: x[1], reverse=True)
            return [name for name, _ in scored]

        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"All Overpass servers failed: {last_error}")


@lru_cache(maxsize=512)
def fetch_overpass(city: str) -> list[str]:
    """
    Fetch attractions via Nominatim geocoding + Overpass query.
    Tries a 15 km radius first; expands to 30 km if too few results.
    Raises on total failure.
    """
    lat, lon, _ = _geocode(city)

    names = _overpass_query(lat, lon, radius=15000)
    if len(names) < 3:
        names = _overpass_query(lat, lon, radius=30000)

    if not names:
        raise ValueError(f"No named attractions found near {city}")

    return names[:5]
