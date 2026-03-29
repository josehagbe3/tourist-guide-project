from app.services.weather_service import WeatherService
from app.services.currency_service import CurrencyService
from app.services.attraction_service import AttractionService
from tools.itinerary import compose_itinerary

_weather    = WeatherService()
_currency   = CurrencyService()
_attractions = AttractionService()


def execute_plan(plan: dict, data: dict) -> dict:
    results = {"data": {}, "errors": []}
    city = plan["city"]

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
