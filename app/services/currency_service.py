from tools.currency import fetch_exchangerate


class CurrencyService:

    FALLBACK_RATES = {
        "USD": 1.0, "EUR": 0.92, "GBP": 0.79,
        "RWF": 1300.0, "UGX": 3750.0, "KES": 130.0, "JPY": 149.0,
    }

    def convert(self, amount: float, from_currency: str, to_currency: str = "USD") -> dict:
        if amount is None:
            return {"error": "Amount required", "status": "error"}
        if amount < 0:
            return {"error": "Amount must be non-negative", "status": "error"}
        if not from_currency:
            return {"error": "Source currency required", "status": "error"}

        from_currency = from_currency.upper()
        to_currency   = to_currency.upper()
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
        """Returns (rate, source) or (None, error_message).
        Falls back to offline table for known currencies; for unknown ones
        instructs the user to set EXCHANGERATE_API_KEY.
        """
        if from_currency not in self.FALLBACK_RATES or to_currency not in self.FALLBACK_RATES:
            return None, (
                f"Currency pair {from_currency}/{to_currency} requires a live API. "
                "Set EXCHANGERATE_API_KEY for full global currency support."
            )
        rate = self.FALLBACK_RATES[to_currency] / self.FALLBACK_RATES[from_currency]
        return rate, "fallback"
