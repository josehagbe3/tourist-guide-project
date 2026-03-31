"""
Daily travel budget estimation — layered system with confidence scoring.

Pipeline (highest to lowest confidence):
  1. Teleport API   — free, no key, real city cost-of-living score → USD estimate
  2. Local dataset  — curated, verified, fast
  3. Global default — last resort

Cost of living ≠ travel cost: a 1.35× tourism multiplier is applied to
API/local values to account for tourist-grade accommodation and activities.
"""

import requests

TELEPORT_SCORES_URL = "https://api.teleport.org/api/urban_areas/slug:{slug}/scores/"
TELEPORT_SEARCH_URL = "https://api.teleport.org/api/cities/?search={city}&embed=city%3Asearch-results%2Fcity%3Aitem%2Fcity%3Aurban_area"

TOURISM_MULTIPLIER = 1.35   # tourist prices > local cost of living
BASE_DAILY_USD     = 60     # anchor: a "score 5/10" city costs ~$60/day

# Curated fallback — verified, fast, no API needed
DAILY_MINIMUMS_USD = {
    # Africa
    "kigali":        35,  "kampala":      30,  "nairobi":       40,
    "cotonou":       35,  "lagos":        45,  "accra":         40,
    "addis ababa":   30,  "cairo":        35,  "casablanca":    45,
    "dakar":         40,  "dar es salaam":35,  "johannesburg":  55,
    "cape town":     65,  "tunis":        40,
    # Europe
    "paris":        130,  "london":      150,  "berlin":        90,
    "rome":         100,  "madrid":       90,  "amsterdam":    110,
    "vienna":        95,  "prague":       60,  "barcelona":    100,
    "lisbon":        80,  "athens":       70,  "warsaw":        55,
    # Americas
    "new york":     180,  "los angeles": 160,  "miami":        150,
    "toronto":      130,  "mexico city":  55,  "buenos aires":  45,
    "rio de janeiro":60,  "bogota":       40,  "lima":          40,
    # Asia & Middle East
    "tokyo":        110,  "dubai":       130,  "singapore":    120,
    "bangkok":       35,  "bali":         40,  "beijing":       60,
    "shanghai":      70,  "hong kong":   100,  "mumbai":        45,
    "delhi":         35,  "istanbul":     55,  "seoul":         80,
    "kuala lumpur":  40,
    # Oceania
    "sydney":       150,  "melbourne":   140,  "auckland":     130,
}

GLOBAL_DEFAULT_USD = 60


def _city_to_teleport_slug(city: str) -> str | None:
    """Resolve a city name to a Teleport urban area slug via the search endpoint."""
    try:
        resp = requests.get(
            TELEPORT_SEARCH_URL.format(city=requests.utils.quote(city)),
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        results = (
            data.get("_embedded", {})
                .get("city:search-results", [])
        )
        for r in results:
            ua = (
                r.get("_embedded", {})
                 .get("city:item", {})
                 .get("_embedded", {})
                 .get("city:urban_area", {})
            )
            slug = ua.get("slug")
            if slug:
                return slug
    except Exception:
        pass
    return None


def _fetch_teleport_cost_score(slug: str) -> float | None:
    """Return the 'Cost Of Living' score (0–10) for a Teleport urban area slug."""
    try:
        resp = requests.get(TELEPORT_SCORES_URL.format(slug=slug), timeout=5)
        resp.raise_for_status()
        for cat in resp.json().get("categories", []):
            if cat.get("name") == "Cost Of Living":
                return cat["score_out_of_10"]
    except Exception:
        pass
    return None


def _score_to_daily_usd(score: float) -> int:
    """
    Convert Teleport 0–10 cost-of-living score to estimated daily travel USD.
    Score 10 = very cheap (~$25/day), score 0 = very expensive (~$200/day).
    Linear interpolation anchored at score 5 → $60/day.
    """
    # Invert: high score = low cost
    daily = BASE_DAILY_USD + (5 - score) * 28
    daily = max(25, min(200, daily))
    return round(daily * TOURISM_MULTIPLIER)


def estimate_daily_budget(city: str) -> dict:
    """
    Return minimum daily travel budget in USD with source and confidence.
    """
    # 1. Teleport API — real-time city cost score
    slug = _city_to_teleport_slug(city)
    if slug:
        score = _fetch_teleport_cost_score(slug)
        if score is not None:
            daily = _score_to_daily_usd(score)
            return {
                "daily_usd": daily,
                "source": "teleport",
                "confidence": "high",
                "teleport_score": round(score, 1),
            }

    # 2. Curated local dataset
    local = DAILY_MINIMUMS_USD.get(city.strip().lower())
    if local:
        return {
            "daily_usd": round(local * TOURISM_MULTIPLIER),
            "source": "local_db",
            "confidence": "high",
        }

    # 3. Global default
    return {
        "daily_usd": round(GLOBAL_DEFAULT_USD * TOURISM_MULTIPLIER),
        "source": "default",
        "confidence": "low",
    }


def get_minimum_daily_usd(city: str) -> int:
    """Convenience wrapper — returns just the USD amount."""
    return estimate_daily_budget(city)["daily_usd"]
