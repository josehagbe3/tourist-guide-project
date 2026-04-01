from tools.currency import fetch_exchangerate


# Map country names (lowercase) → ISO 4217 currency code.
# Covers ~150 countries; used when user enters a country instead of a code.
COUNTRY_TO_CURRENCY = {
    # Africa
    "algeria": "DZD", "angola": "AOA", "benin": "XOF", "botswana": "BWP",
    "burkina faso": "XOF", "burundi": "BIF", "cameroon": "XAF",
    "cape verde": "CVE", "central african republic": "XAF", "chad": "XAF",
    "comoros": "KMF", "congo": "XAF", "democratic republic of congo": "CDF",
    "djibouti": "DJF", "egypt": "EGP", "equatorial guinea": "XAF",
    "eritrea": "ERN", "ethiopia": "ETB", "gabon": "XAF", "gambia": "GMD",
    "ghana": "GHS", "guinea": "GNF", "guinea-bissau": "XOF",
    "ivory coast": "XOF", "cote d'ivoire": "XOF", "kenya": "KES",
    "lesotho": "LSL", "liberia": "LRD", "libya": "LYD",
    "madagascar": "MGA", "malawi": "MWK", "mali": "XOF",
    "mauritania": "MRU", "mauritius": "MUR", "morocco": "MAD",
    "mozambique": "MZN", "namibia": "NAD", "niger": "XOF",
    "nigeria": "NGN", "rwanda": "RWF", "senegal": "XOF",
    "seychelles": "SCR", "sierra leone": "SLL", "somalia": "SOS",
    "south africa": "ZAR", "south sudan": "SSP", "sudan": "SDG",
    "tanzania": "TZS", "togo": "XOF", "tunisia": "TND",
    "uganda": "UGX", "zambia": "ZMW", "zimbabwe": "ZWL",

    # Americas
    "argentina": "ARS", "bahamas": "BSD", "barbados": "BBD",
    "belize": "BZD", "bolivia": "BOB", "brazil": "BRL",
    "canada": "CAD", "chile": "CLP", "colombia": "COP",
    "costa rica": "CRC", "cuba": "CUP", "dominican republic": "DOP",
    "ecuador": "USD", "el salvador": "USD", "guatemala": "GTQ",
    "haiti": "HTG", "honduras": "HNL", "jamaica": "JMD",
    "mexico": "MXN", "nicaragua": "NIO", "panama": "PAB",
    "paraguay": "PYG", "peru": "PEN", "trinidad and tobago": "TTD",
    "united states": "USD", "usa": "USD", "uruguay": "UYU",
    "venezuela": "VES",

    # Asia
    "afghanistan": "AFN", "bangladesh": "BDT", "bhutan": "BTN",
    "brunei": "BND", "cambodia": "KHR", "china": "CNY",
    "hong kong": "HKD", "india": "INR", "indonesia": "IDR",
    "japan": "JPY", "kazakhstan": "KZT", "kyrgyzstan": "KGS",
    "laos": "LAK", "macau": "MOP", "malaysia": "MYR",
    "maldives": "MVR", "mongolia": "MNT", "myanmar": "MMK",
    "nepal": "NPR", "north korea": "KPW", "pakistan": "PKR",
    "philippines": "PHP", "singapore": "SGD", "south korea": "KRW",
    "sri lanka": "LKR", "taiwan": "TWD", "tajikistan": "TJS",
    "thailand": "THB", "timor-leste": "USD", "turkmenistan": "TMT",
    "uzbekistan": "UZS", "vietnam": "VND",

    # Europe
    "albania": "ALL", "andorra": "EUR", "austria": "EUR",
    "belarus": "BYN", "belgium": "EUR", "bosnia": "BAM",
    "bulgaria": "BGN", "croatia": "EUR", "cyprus": "EUR",
    "czech republic": "CZK", "czechia": "CZK", "denmark": "DKK",
    "estonia": "EUR", "finland": "EUR", "france": "EUR",
    "germany": "EUR", "greece": "EUR", "hungary": "HUF",
    "iceland": "ISK", "ireland": "EUR", "italy": "EUR",
    "kosovo": "EUR", "latvia": "EUR", "liechtenstein": "CHF",
    "lithuania": "EUR", "luxembourg": "EUR", "malta": "EUR",
    "moldova": "MDL", "monaco": "EUR", "montenegro": "EUR",
    "netherlands": "EUR", "north macedonia": "MKD", "norway": "NOK",
    "poland": "PLN", "portugal": "EUR", "romania": "RON",
    "russia": "RUB", "san marino": "EUR", "serbia": "RSD",
    "slovakia": "EUR", "slovenia": "EUR", "spain": "EUR",
    "sweden": "SEK", "switzerland": "CHF", "turkey": "TRY",
    "ukraine": "UAH", "united kingdom": "GBP", "uk": "GBP",
    "england": "GBP", "scotland": "GBP", "wales": "GBP",
    "vatican": "EUR",

    # Middle East
    "bahrain": "BHD", "iran": "IRR", "iraq": "IQD",
    "israel": "ILS", "jordan": "JOD", "kuwait": "KWD",
    "lebanon": "LBP", "oman": "OMR", "palestine": "ILS",
    "qatar": "QAR", "saudi arabia": "SAR", "syria": "SYP",
    "united arab emirates": "AED", "uae": "AED", "yemen": "YER",

    # Oceania
    "australia": "AUD", "fiji": "FJD", "new zealand": "NZD",
    "papua new guinea": "PGK", "samoa": "WST", "tonga": "TOP",
}


def resolve_currency(value: str) -> tuple[str, str | None]:
    """
    Resolve a user input to an ISO 4217 currency code.
    Accepts:
      - A country name: "France" → "EUR", "Nigeria" → "NGN"  (checked first)
      - A 3-letter ISO 4217 code: "USD", "eur", "rwf" → returned uppercased
    Returns (code, note) where note is a human-readable clarification or None.
    Raises ValueError if the input cannot be resolved.
    """
    value = value.strip()

    # 1. Try country name lookup first (handles abbreviations like "uae", "usa")
    country = value.lower()
    code = COUNTRY_TO_CURRENCY.get(country)
    if code:
        note = f"'{value}' is a country → using {code}" if len(value) > 4 or value.upper() != code else None
        return code, note

    # 2. Treat as currency code (2–4 uppercase letters)
    if len(value) <= 4 and value.replace("-", "").isalpha():
        return value.upper(), None

    raise ValueError(
        f"'{value}' is not a recognised currency code or country name. "
        "Please enter a 3-letter ISO 4217 code (e.g. USD, EUR, NGN) "
        "or a country name (e.g. France, Nigeria)."
    )


class CurrencyService:

    # Approximate rates relative to 1 USD — used when EXCHANGERATE_API_KEY is not set.
    # Live API always takes precedence when the key is available.
    # Rates last reviewed: early 2025.
    FALLBACK_RATES = {
        # Major / G10
        "USD": 1.0,       "EUR": 0.92,      "GBP": 0.79,
        "JPY": 149.0,     "CHF": 0.90,      "AUD": 1.53,
        "CAD": 1.36,      "NZD": 1.63,      "SEK": 10.42,
        "NOK": 10.55,     "DKK": 6.88,      "SGD": 1.34,
        "HKD": 7.82,      "CNY": 7.24,

        # Americas
        "MXN": 17.15,     "BRL": 4.97,      "ARS": 870.0,
        "CLP": 950.0,     "COP": 3900.0,    "PEN": 3.72,

        # Europe (non-euro)
        "PLN": 3.97,      "CZK": 22.8,      "HUF": 355.0,
        "RON": 4.57,      "TRY": 32.5,

        # Middle East / Asia
        "AED": 3.67,      "SAR": 3.75,      "QAR": 3.64,
        "KWD": 0.307,     "BHD": 0.376,     "OMR": 0.385,
        "INR": 83.5,      "PKR": 278.0,     "BDT": 110.0,
        "LKR": 305.0,     "THB": 35.1,      "MYR": 4.70,
        "IDR": 15700.0,   "PHP": 56.5,      "VND": 24500.0,
        "KRW": 1325.0,    "TWD": 31.8,

        # Africa
        "NGN": 1550.0,    "GHS": 15.5,      "KES": 130.0,
        "UGX": 3750.0,    "TZS": 2530.0,    "RWF": 1300.0,
        "ETB": 56.5,      "XOF": 603.0,     "XAF": 603.0,
        "ZAR": 18.6,      "MAD": 10.0,      "EGP": 30.9,
        "DZD": 134.5,     "TND": 3.10,
    }

    def convert(self, amount: float, from_currency: str, to_currency: str = "USD") -> dict:
        if amount is None:
            return {"error": "Amount required", "status": "error"}
        if amount < 0:
            return {"error": "Amount must be non-negative", "status": "error"}
        if not from_currency:
            return {"error": "Source currency required", "status": "error"}

        warnings = []

        # Resolve country names → currency codes
        try:
            from_currency, from_note = resolve_currency(from_currency)
            if from_note:
                warnings.append(from_note)
        except ValueError as e:
            return {"error": str(e), "status": "error"}

        try:
            to_currency, to_note = resolve_currency(to_currency)
            if to_note:
                warnings.append(to_note)
        except ValueError as e:
            return {"error": str(e), "status": "error"}

        # Primary: ExchangeRate-API
        try:
            data  = fetch_exchangerate(from_currency)
            rates = data.get("conversion_rates", {})
            if to_currency not in rates:
                raise ValueError(f"Currency '{to_currency}' not in API response")
            rate   = rates[to_currency]
            source = "exchangerate-api"
        except RuntimeError as e:
            warnings.append(str(e))
            rate, source = self._fallback_rate(from_currency, to_currency)
            if rate is None:
                return {"error": source, "status": "error"}
        except Exception as e:
            warnings.append(f"ExchangeRate-API: {e}")
            rate, source = self._fallback_rate(from_currency, to_currency)
            if rate is None:
                return {"error": source, "status": "error"}

        result = {
            "original_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "converted_amount": round(amount * rate, 2),
            "rate": round(rate, 6),
            "source": source,
            "status": "success"
        }
        if warnings:
            result["warnings"] = warnings
        return result

    def _fallback_rate(self, from_currency: str, to_currency: str):
        """Returns (rate, source) or (None, error_message)."""
        if from_currency not in self.FALLBACK_RATES or to_currency not in self.FALLBACK_RATES:
            return None, (
                f"Currency pair {from_currency}/{to_currency} requires a live API. "
                "Set EXCHANGERATE_API_KEY for full global currency support."
            )
        rate = self.FALLBACK_RATES[to_currency] / self.FALLBACK_RATES[from_currency]
        return rate, "fallback"
