from tools.currency import fetch_exchangerate


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

        from_currency = from_currency.strip().upper()
        to_currency   = to_currency.strip().upper()
        warnings      = []

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
