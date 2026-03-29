import os

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


SYSTEM_PROMPT = """You are a friendly travel guide assistant. Generate a concise, engaging travel itinerary based ONLY on the tool data provided.

Rules:
- Do NOT invent attractions, weather, or prices not present in the data
- Do NOT repeat the weather summary, budget, or attractions list — those are shown separately
- If weather is rainy or bad, mention to prefer indoor activities
- Cover every day in the schedule with specific times and activities
- Use a friendly, helpful tone
- Structure: one-line intro, day-by-day schedule, one closing tip
"""


def _build_prompt(city: str, results: dict) -> str:
    data = results["data"]
    errors = results.get("errors", [])
    country = data.get("weather", {}).get("country", "")
    destination = f"{city}, {country}" if country else city
    lines = [f"City: {destination}"]

    if "weather" in data:
        w = data["weather"]["weather"]
        lines.append(f"Weather: {w['condition']}, {w['temperature']}°C")

    if "attractions" in data:
        lines.append(f"Attractions: {', '.join(data['attractions']['attractions'])}")

    # Budget shown via itinerary block (includes per-day breakdown); skip standalone currency line
    if "currency" in data and "itinerary" not in data:
        c = data["currency"]
        lines.append(
            f"Budget: {c['original_amount']} {c['from_currency']} "
            f"= {c['converted_amount']} {c['to_currency']}"
        )

    if "itinerary" in data:
        itin = data["itinerary"]
        num_days = itin.get("num_days", 1)
        lines.append(f"Trip duration: {num_days} day(s)")
        lines.append(f"Outdoor friendly: {itin['outdoor_friendly']}")
        if itin.get("weather_advisory"):
            lines.append(f"Weather advisory: {itin['weather_advisory']}")
        if itin.get("budget"):
            b = itin["budget"]
            lines.append(f"Budget: {b['total_original']} = {b['total_converted']} ({b['per_day']}/day)")
        all_days = itin.get("days", [])
        for day in all_days[:3]:
            lines.append(f"Day {day['day']}:")
            for s in day["schedule"]:
                lines.append(f"  {s['time']}: {s['activity']} ({s.get('note', '')})")
        if len(all_days) > 3:
            lines.append(f"  (Days 4–{len(all_days)}: continue the same rotation of attractions)")

    if errors:
        error_notes = [f"{e['tool']}: {e['error']}" for e in errors]
        lines.append(f"Note — some data unavailable: {'; '.join(error_notes)}")

    return "\n".join(lines)


def _build_fallback_response(city: str, results: dict, from_city: str = None) -> str:
    """Schedule-only itinerary — weather/currency/attractions shown in their own boxes."""
    data = results["data"]
    errors = results.get("errors", [])
    country = data.get("weather", {}).get("country", "")
    destination = f"{city}, {country}" if country else city
    header = f"Trip from {from_city} to {destination}" if from_city else f"Trip to {destination}"
    lines = [header]

    if "itinerary" in data:
        itin = data["itinerary"]
        if itin.get("weather_advisory"):
            lines.append(f"⚠️  {itin['weather_advisory']}")
        all_days = itin.get("days", [])
        for day in all_days[:3]:
            lines.append(f"\nDay {day['day']}:")
            for s in day["schedule"]:
                lines.append(f"  {s['time']} — {s['activity']}")
        if len(all_days) > 3:
            lines.append(f"\n  … Days 4–{len(all_days)} follow the same daily pattern.")
    elif errors:
        unavailable = [e["tool"] for e in errors if e["tool"] != "all"]
        if unavailable:
            lines.append(f"⚠️  Could not build itinerary — missing data: {', '.join(unavailable)}")

    return "\n".join(lines)


def build_response(city: str, results: dict, from_city: str = None) -> dict:
    errors = results.get("errors", [])

    if _ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            prompt = _build_prompt(city, results)
            if from_city:
                prompt = f"Departure city: {from_city}\n" + prompt
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            itinerary_text = response.content[0].text.strip()
        except Exception:
            itinerary_text = _build_fallback_response(city, results, from_city)
    else:
        itinerary_text = _build_fallback_response(city, results, from_city)

    return {
        "city": city,
        "itinerary": itinerary_text,
        "tool_outputs": results["data"],
        "errors": errors,
        "status": "success" if not errors else "partial_success"
    }
