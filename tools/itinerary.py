def _build_day(day: int, attractions_slice: list, outdoor_ok: bool) -> dict:
    """Build a single day's schedule from up to 3 attractions."""
    schedule = []

    if len(attractions_slice) >= 1:
        schedule.append({
            "time": "9:00 AM",
            "activity": f"Visit {attractions_slice[0]}",
            "type": "outdoor" if outdoor_ok else "indoor",
            "note": "Morning highlight"
        })

    if len(attractions_slice) >= 2:
        schedule.append({
            "time": "11:00 AM",
            "activity": f"Explore {attractions_slice[1]}",
            "type": "outdoor" if outdoor_ok else "indoor",
            "note": "Allow 1-2 hours" if outdoor_ok else "Indoor alternative recommended"
        })

    schedule.append({
        "time": "1:00 PM",
        "activity": "Lunch at a local restaurant",
        "type": "indoor",
        "note": "Try local cuisine"
    })

    if len(attractions_slice) >= 3:
        schedule.append({
            "time": "3:00 PM",
            "activity": f"Afternoon at {attractions_slice[2]}",
            "type": "outdoor" if outdoor_ok else "indoor",
            "note": "Main afternoon highlight"
        })

    schedule.append({
        "time": "6:00 PM",
        "activity": "Evening walk and dinner",
        "type": "outdoor" if outdoor_ok else "indoor",
        "note": "Wrap up the day"
    })

    return {"day": day, "schedule": schedule}


def compose_itinerary(
    city: str,
    weather: dict,
    attractions: list,
    budget_info: dict = None,
    num_days: int = 1
) -> dict:
    """
    Compose a structured itinerary from tool outputs.

    Parameters:
        city:        destination city
        weather:     result from get_weather (condition, temperature)
        attractions: list of attraction names from get_attractions
        budget_info: optional result from convert_currency
        num_days:    number of days (default 1)
    """
    if not city:
        return {"error": "City is required", "status": "error"}

    if not attractions:
        return {"error": "No attractions to build itinerary", "status": "error"}

    num_days = max(1, int(num_days or 1))

    condition = weather.get("condition", "Unknown") if weather else "Unknown"
    temperature = weather.get("temperature") if weather else None
    _bad = {"rain", "rainy", "drizzle", "storm", "stormy", "thunderstorm",
            "heavy rain", "snow", "blizzard", "sleet", "hail", "shower", "showers"}
    outdoor_ok = not any(b in condition.lower() for b in _bad)

    # Distribute attractions across days (cycle if more days than attractions)
    days = []
    for day in range(1, num_days + 1):
        # Rotate through attractions: day 1 → [0,1,2], day 2 → [1,2,0], etc.
        offset = (day - 1) * 2 % len(attractions)
        rotated = attractions[offset:] + attractions[:offset]
        days.append(_build_day(day, rotated[:3], outdoor_ok))

    weather_note = None
    if not outdoor_ok:
        weather_note = f"Weather advisory: {condition} conditions. Prefer indoor venues."
    elif temperature is not None and temperature >= 30:
        weather_note = f"It's {temperature}°C — stay hydrated and use sun protection."

    result = {
        "city": city,
        "num_days": num_days,
        "weather_summary": f"{condition}, {temperature}°C" if temperature is not None else condition,
        "outdoor_friendly": outdoor_ok,
        "days": days,
        "status": "success"
    }

    if weather_note:
        result["weather_advisory"] = weather_note

    if budget_info:
        daily = round(budget_info["converted_amount"] / num_days, 2)
        result["budget"] = {
            "total_original": f"{budget_info['original_amount']} {budget_info['from_currency']}",
            "total_converted": f"{budget_info['converted_amount']} {budget_info['to_currency']}",
            "per_day": f"{daily} {budget_info['to_currency']}"
        }

    return result
