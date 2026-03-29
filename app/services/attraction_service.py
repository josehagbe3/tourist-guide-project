from tools.attractions import fetch_opentripmap, fetch_overpass


class AttractionService:

    LOCAL_DATA = {
        "kigali":   ["Kigali Genocide Memorial", "Kimironko Market", "Mount Kigali"],
        "paris":    ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral"],
        "new york": ["Statue of Liberty", "Central Park", "Metropolitan Museum of Art"],
        "nairobi":  ["Nairobi National Park", "Giraffe Centre", "Karen Blixen Museum"],
        "kampala":  ["Kasubi Tombs", "Uganda Museum", "Namugongo Martyrs Shrine"],
        "london":   ["British Museum", "Tower of London", "Hyde Park"],
        "tokyo":    ["Senso-ji Temple", "Shibuya Crossing", "Meiji Shrine"],
        "dubai":    ["Burj Khalifa", "Dubai Mall", "Palm Jumeirah"],
        "cairo":    ["Great Pyramid of Giza", "Egyptian Museum", "Khan el-Khalili"],
        "cotonou":  ["Dantokpa Market", "Place de l'Etoile Rouge", "Fondation Zinsou"],
    }

    def get_attractions(self, city: str) -> dict:
        if not city:
            return {"error": "City required", "status": "error"}

        normalized = city.strip().lower()
        warnings   = []

        # 1. Local curated DB — instant, no API key
        if normalized in self.LOCAL_DATA:
            return {
                "city": city,
                "attractions": self.LOCAL_DATA[normalized],
                "source": "local",
                "status": "success"
            }

        # 2. Primary: OpenTripMap
        try:
            attractions = fetch_opentripmap(city)
            return {"city": city, "attractions": attractions,
                    "source": "opentripmap", "status": "success"}
        except RuntimeError as e:
            warnings.append(str(e))
        except Exception as e:
            warnings.append(f"OpenTripMap: {e}")

        # 3. Fallback: OpenStreetMap Overpass
        try:
            attractions = fetch_overpass(city)
            result = {"city": city, "attractions": attractions,
                      "source": "openstreetmap", "status": "success"}
            if warnings:
                result["warnings"] = warnings
            return result
        except Exception as e:
            warnings.append(f"Overpass: {e}")

        return {
            "error": f"No attraction data available for '{city}'. Set OPENTRIPMAP_API_KEY for best results.",
            "details": warnings,
            "status": "error"
        }
