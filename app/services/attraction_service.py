from tools.attractions import fetch_opentripmap, fetch_overpass


class AttractionService:

    LOCAL_DATA = {
        # Africa
        "kigali":        ["Kigali Genocide Memorial", "Kimironko Market", "Mount Kigali",
                          "Inema Arts Center", "Nyamirambo Women's Center"],
        "nairobi":       ["Nairobi National Park", "Giraffe Centre", "Karen Blixen Museum",
                          "Bomas of Kenya", "David Sheldrick Wildlife Trust"],
        "kampala":       ["Kasubi Tombs", "Uganda Museum", "Namugongo Martyrs Shrine",
                          "Kabaka's Palace", "Owino Market"],
        "cotonou":       ["Dantokpa Market", "Place de l'Etoile Rouge", "Fondation Zinsou",
                          "Musée da Silva", "Fidjrossè Beach"],
        "abidjan":       ["Musée des Civilisations de Côte d'Ivoire", "Cathédrale Saint-Paul",
                          "Parc du Banco", "Marché de Cocody", "Plateau District"],
        "bamako":        ["Monument du Cinquantenaire", "Musée National du Mali", "Marché Artisanal",
                          "Tour de l'Afrique", "Grand Marché de Bamako"],
        "antananarivo":  ["Rova of Antananarivo", "Musée de la Photo", "Lac Anosy",
                          "Marché d'Analakely", "Palais de la Reine"],
        "lagos":         ["Lekki Conservation Centre", "Nike Art Gallery", "Badagry Slave Route",
                          "Eko Atlantic City", "National Museum Lagos"],
        "accra":         ["Kwame Nkrumah Memorial Park", "Cape Coast Castle", "Makola Market",
                          "Labadi Beach", "National Museum of Ghana"],
        "dakar":         ["Gorée Island", "African Renaissance Monument", "IFAN Museum",
                          "Lac Rose", "Dakar Grand Mosque"],
        "cairo":         ["Great Pyramid of Giza", "Egyptian Museum", "Khan el-Khalili",
                          "Sphinx of Giza", "Citadel of Saladin"],
        "casablanca":    ["Hassan II Mosque", "Corniche Ain Diab", "Old Medina",
                          "Quartier Habous", "Mohammed V Square"],
        "marrakech":     ["Djemaa el-Fna", "Majorelle Garden", "Bahia Palace",
                          "Medina of Marrakech", "Saadian Tombs"],
        "cape town":     ["Table Mountain", "Robben Island", "Cape of Good Hope",
                          "V&A Waterfront", "Bo-Kaap"],
        "johannesburg":  ["Apartheid Museum", "Soweto", "Gold Reef City",
                          "Constitution Hill", "Cradle of Humankind"],
        "addis ababa":   ["National Museum of Ethiopia", "Holy Trinity Cathedral",
                          "Mercato", "Entoto Natural Park", "Ethiopian National Theatre"],
        "dar es salaam": ["Kariakoo Market", "Village Museum", "National Museum of Tanzania",
                          "Coco Beach", "Askari Monument"],
        "tunis":         ["Medina of Tunis", "Bardo National Museum", "Carthage Ruins",
                          "Sidi Bou Said", "Zitouna Mosque"],

        # Europe
        "paris":         ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral",
                          "Palace of Versailles", "Musée d'Orsay"],
        "london":        ["British Museum", "Tower of London", "Hyde Park",
                          "Buckingham Palace", "Tate Modern"],
        "rome":          ["Colosseum", "Vatican Museums", "Trevi Fountain",
                          "Roman Forum", "Pantheon"],
        "berlin":        ["Brandenburg Gate", "Berlin Wall Memorial", "Pergamon Museum",
                          "Reichstag Building", "Museum Island"],
        "madrid":        ["Prado Museum", "Retiro Park", "Royal Palace of Madrid",
                          "Reina Sofía Museum", "Puerta del Sol"],
        "barcelona":     ["Sagrada Família", "Park Güell", "Las Ramblas",
                          "Camp Nou", "Gothic Quarter"],
        "amsterdam":     ["Rijksmuseum", "Anne Frank House", "Van Gogh Museum",
                          "Vondelpark", "Canal Ring"],
        "vienna":        ["Schönbrunn Palace", "Kunsthistorisches Museum", "St. Stephen's Cathedral",
                          "Belvedere Palace", "Vienna State Opera"],
        "prague":        ["Prague Castle", "Charles Bridge", "Old Town Square",
                          "Wenceslas Square", "Josefov Jewish Quarter"],
        "lisbon":        ["Belém Tower", "Jerónimos Monastery", "Alfama District",
                          "São Jorge Castle", "LX Factory"],
        "athens":        ["Acropolis", "Parthenon", "National Archaeological Museum",
                          "Plaka District", "Temple of Hephaestus"],
        "istanbul":      ["Hagia Sophia", "Topkapi Palace", "Grand Bazaar",
                          "Blue Mosque", "Bosphorus Strait"],

        # Americas
        "new york":      ["Statue of Liberty", "Central Park", "Metropolitan Museum of Art",
                          "Times Square", "Brooklyn Bridge"],
        "los angeles":   ["Griffith Observatory", "Getty Center", "Santa Monica Pier",
                          "Hollywood Walk of Fame", "The Broad Museum"],
        "miami":         ["South Beach", "Wynwood Walls", "Vizcaya Museum & Gardens",
                          "Everglades National Park", "Little Havana"],
        "toronto":       ["CN Tower", "Royal Ontario Museum", "Distillery District",
                          "Kensington Market", "Casa Loma"],
        "mexico city":   ["Teotihuacán", "National Museum of Anthropology", "Zócalo",
                          "Chapultepec Castle", "Frida Kahlo Museum"],
        "buenos aires":  ["Recoleta Cemetery", "La Boca", "Teatro Colón",
                          "San Telmo Market", "Plaza de Mayo"],
        "rio de janeiro":["Christ the Redeemer", "Sugarloaf Mountain", "Copacabana Beach",
                          "Ipanema Beach", "Tijuca Forest"],
        "bogota":        ["Gold Museum", "Monserrate", "La Candelaria",
                          "Botero Museum", "Usaquén"],
        "lima":          ["Larco Museum", "Historic Centre of Lima", "Miraflores Boardwalk",
                          "Huaca Pucllana", "Barranco District"],

        # Asia & Middle East
        "tokyo":         ["Senso-ji Temple", "Shibuya Crossing", "Meiji Shrine",
                          "Shinjuku Gyoen", "teamLab Borderless"],
        "dubai":         ["Burj Khalifa", "Dubai Mall", "Palm Jumeirah",
                          "Dubai Museum", "Gold Souk"],
        "singapore":     ["Gardens by the Bay", "Marina Bay Sands", "Sentosa Island",
                          "Chinatown", "Singapore Botanic Gardens"],
        "bangkok":       ["Grand Palace", "Wat Phra Kaew", "Wat Arun",
                          "Chatuchak Weekend Market", "Lumphini Park"],
        "beijing":       ["Great Wall of China", "Forbidden City", "Temple of Heaven",
                          "Summer Palace", "Tiananmen Square"],
        "shanghai":      ["The Bund", "Yu Garden", "Shanghai Museum",
                          "Nanjing Road", "Zhujiajiao Water Town"],
        "hong kong":     ["Victoria Peak", "Tian Tan Buddha", "Temple Street Night Market",
                          "Star Ferry", "Wong Tai Sin Temple"],
        "mumbai":        ["Gateway of India", "Elephanta Caves", "Chhatrapati Shivaji Museum",
                          "Marine Drive", "Dharavi"],
        "delhi":         ["Red Fort", "Qutb Minar", "India Gate",
                          "Humayun's Tomb", "Lotus Temple"],
        "seoul":         ["Gyeongbokgung Palace", "N Seoul Tower", "Bukchon Hanok Village",
                          "Myeongdong", "DMZ Tour"],
        "kuala lumpur":  ["Petronas Twin Towers", "Batu Caves", "Central Market",
                          "KL Bird Park", "Merdeka Square"],
        "bali":          ["Uluwatu Temple", "Tegallalang Rice Terraces", "Sacred Monkey Forest",
                          "Tanah Lot", "Ubud Palace"],

        # Oceania
        "sydney":        ["Sydney Opera House", "Harbour Bridge", "Bondi Beach",
                          "Royal Botanic Garden", "Darling Harbour"],
        "melbourne":     ["Federation Square", "Royal Botanic Gardens", "Queen Victoria Market",
                          "National Gallery of Victoria", "Great Ocean Road"],
        "auckland":      ["Sky Tower", "Auckland War Memorial Museum", "Waitemata Harbour",
                          "Rangitoto Island", "Viaduct Harbour"],
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

        # 3. Fallback: OpenStreetMap Overpass (also resolves country)
        try:
            from tools.attractions import _geocode
            _, _, country_code = _geocode(city)
            attractions = fetch_overpass(city)
            result = {"city": city, "attractions": attractions,
                      "source": "openstreetmap", "status": "success"}
            if country_code:
                result["country_code"] = country_code
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
