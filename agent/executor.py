from app.services.weather_service import WeatherService
from app.services.currency_service import CurrencyService
from app.services.attraction_service import AttractionService
from app.services.cost_of_living import estimate_daily_budget
from tools.itinerary import compose_itinerary

_weather     = WeatherService()
_currency    = CurrencyService()
_attractions = AttractionService()


def execute_plan(plan: dict, data: dict) -> dict:
    results = {"data": {}, "errors": []}
    city     = plan["city"]
    num_days = plan.get("num_days", 1)

    for step in plan["steps"]:

        if step == "weather":
            res = _weather.get_weather(city)

        elif step == "attractions":
            res = _attractions.get_attractions(city)

        elif step == "currency":
            res = _currency.convert(
                amount=plan.get("budget") or data.get("budget"),
                from_currency=plan.get("from_currency") or data.get("from_currency") or data.get("currency"),
                to_currency=plan.get("to_currency") or data.get("to_currency") or "USD"
            )
            # Budget validation — convert result to USD and compare to minimum
            if res.get("status") == "success":
                converted = res["converted_amount"]
                to_cur    = res["to_currency"]

                # Normalise to USD for comparison
                if to_cur == "USD":
                    budget_usd = converted
                else:
                    usd_res = _currency.convert(converted, to_cur, "USD")
                    budget_usd = usd_res.get("converted_amount", 0) if usd_res.get("status") == "success" else 0

                cost_est      = estimate_daily_budget(city)
                min_daily_usd = cost_est["daily_usd"]
                min_total_usd = min_daily_usd * num_days

                if budget_usd < min_total_usd:
                    min_in_orig = _currency.convert(min_total_usd, "USD", res["from_currency"])
                    min_orig_str = (
                        f"{min_in_orig['converted_amount']:,.0f} {res['from_currency']}"
                        if min_in_orig.get("status") == "success"
                        else f"≈ ${min_total_usd:,.0f} USD"
                    )
                    src  = cost_est["source"]
                    conf = cost_est["confidence"]
                    score_note = (
                        f" (Teleport cost score: {cost_est['teleport_score']}/10)"
                        if src == "teleport" else ""
                    )
                    return {
                        "status": "budget_too_low",
                        "error": (
                            f"Budget too low for {city} ({num_days} day{'s' if num_days > 1 else ''}).\n"
                            f"Minimum required: {min_orig_str} "
                            f"(${min_daily_usd}/day × {num_days} day{'s' if num_days > 1 else ''} "
                            f"covering accommodation, meals, transport & tourism){score_note}.\n"
                            f"Your budget: {res['original_amount']:,.0f} {res['from_currency']} "
                            f"≈ ${budget_usd:,.0f} USD.\n"
                            f"Cost estimate source: {src} · confidence: {conf}."
                        ),
                        "min_daily_usd": min_daily_usd,
                        "min_total_usd": min_total_usd,
                        "cost_source": src,
                        "confidence": conf,
                    }

        elif step == "itinerary":
            weather      = results["data"].get("weather", {}).get("weather")
            attractions  = results["data"].get("attractions", {}).get("attractions", [])
            budget_info  = results["data"].get("currency")
            res = compose_itinerary(
                city=city,
                weather=weather,
                attractions=attractions,
                budget_info=budget_info,
                num_days=plan.get("num_days", 1)
            )

        else:
            continue

        if res.get("status") == "success":
            results["data"][step] = res
        else:
            results["errors"].append({"tool": step, "error": res.get("error", "Unknown error")})

    return results
