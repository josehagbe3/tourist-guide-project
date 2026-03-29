import requests
from tools.weather import fetch_openweather, fetch_wttr


class WeatherService:

    def get_weather(self, city: str) -> dict:
        if not city:
            return {"error": "City is required", "status": "error"}

        warnings = []

        # Primary: OpenWeatherMap
        try:
            data = fetch_openweather(city)
            weather = {
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"].title(),
                "temperature": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "humidity": data["main"]["humidity"],
                "wind_kph": round(data["wind"]["speed"] * 3.6, 1),
                "precipitation_mm": round(data.get("rain", {}).get("1h", 0.0), 1),
            }
            country = data.get("sys", {}).get("country", "")
            return {"city": city, "country": country, "weather": weather,
                    "source": "openweathermap", "status": "success"}

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {"error": f"City not found: {city}", "status": "error"}
            warnings.append(f"OpenWeatherMap: {e}")
        except RuntimeError as e:
            warnings.append(str(e))
        except Exception as e:
            warnings.append(f"OpenWeatherMap: {e}")

        # Fallback: wttr.in
        try:
            data = fetch_wttr(city)
            current = data["current_condition"][0]
            weather = {
                "condition": current["weatherDesc"][0]["value"],
                "description": current["weatherDesc"][0]["value"],
                "temperature": int(current["temp_C"]),
                "feels_like": int(current["FeelsLikeC"]),
                "humidity": int(current["humidity"]),
                "wind_kph": float(current["windspeedKmph"]),
                "precipitation_mm": float(current.get("precipMM", 0)),
            }
            area = data.get("nearest_area", [{}])[0]
            country = area.get("country", [{}])[0].get("value", "")
            result = {"city": city, "country": country, "weather": weather,
                      "source": "wttr.in", "status": "success"}
            if warnings:
                result["warnings"] = warnings
            return result
        except Exception as e:
            warnings.append(f"wttr.in: {e}")

        return {"error": f"Weather unavailable for '{city}'.", "warnings": warnings, "status": "error"}
