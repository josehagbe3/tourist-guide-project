import json
import os

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

SYSTEM_PROMPT = """You are a travel planning assistant. Your job is to extract structured travel intent from the user's message.

Return ONLY a valid JSON object with these fields:
{
  "city": "<city name or null>",
  "budget": <numeric amount or null>,
  "from_currency": "<source currency code or null>",
  "to_currency": "<target currency code or null>",
  "num_days": <integer or null>,
  "date": "<date string or null>"
}

Rules:
- Extract city names exactly as written (capitalise first letter)
- Budget must be a number, strip currency symbols
- Currency codes must be standard 3-letter ISO 4217 codes — accept ANY valid world currency
  (e.g. USD, EUR, GBP, JPY, NGN, XOF, XAF, RWF, UGX, KES, BRL, INR, AED, ZAR, MAD, GHS …)
- Infer the currency from context when possible (e.g. "francs" → XOF or XAF, "naira" → NGN,
  "rupees" → INR, "pounds" → GBP, "shillings" → KES or UGX depending on city)
- If the user says "show costs in X" or "convert to X", set to_currency to X
- If no currency is mentioned for from_currency, leave it null
- num_days: 1 for "day trip" or "one-day", etc.
- Return null for any field you cannot determine
"""


def _extract_intent_with_llm(user_message: str) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    raw = response.content[0].text.strip()
    return json.loads(raw)


def _normalize_currency(code) -> str | None:
    """Uppercase and strip whitespace from any currency code."""
    if not code:
        return None
    return str(code).strip().upper()


def _extract_intent_rule_based(data: dict) -> dict:
    """Fallback rule-based extraction when LLM is unavailable."""
    return {
        "city": data.get("city"),
        "budget": data.get("budget"),
        "from_currency": _normalize_currency(data.get("from_currency") or data.get("currency")),
        "to_currency": _normalize_currency(data.get("to_currency")),
        "num_days": data.get("num_days", 1),
        "date": data.get("date")
    }


def create_plan(data: dict) -> dict:
    """
    Parse user intent and produce a plan dict.

    Accepts either:
    - {"message": "<natural language request>"} for LLM parsing
    - structured dict with city/budget/currency keys for direct use
    """
    # LLM path: parse natural language
    if "message" in data and _ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
        try:
            intent = _extract_intent_with_llm(data["message"])
        except Exception as e:
            return {"status": "error", "error": f"LLM parsing failed: {e}"}
    else:
        intent = _extract_intent_rule_based(data)

    city = intent.get("city")
    budget = intent.get("budget")
    from_currency = intent.get("from_currency")
    to_currency = intent.get("to_currency")

    # Normalize city name — title-case each word
    if city:
        city = city.strip().title()

    # Determine missing required fields
    missing = []
    if not city:
        missing.append("city")
    if budget is None:
        missing.append("budget")
    if budget is not None and not from_currency:
        missing.append("from_currency")
    if budget is None and from_currency:
        missing.append("budget")

    if missing:
        field_hints = {
            "city": "Which city would you like to visit?",
            "from_currency": "What currency is your budget in?",
            "budget": "What is your total budget for the trip (covering travel, accommodation, food and tourism)?",
            "num_days": "How many days is your trip?"
        }
        questions = " ".join(field_hints[f] for f in missing if f in field_hints)
        return {
            "status": "needs_clarification",
            "needs_clarification": True,
            "missing_fields": missing,
            "clarification_message": questions
        }

    # Validate num_days
    num_days = max(1, int(intent.get("num_days") or data.get("num_days") or 1))

    # Budget and currency always required now
    steps = ["weather", "attractions", "currency", "itinerary"]

    return {
        "status": "success",
        "city": city,
        "from_city": data.get("from_city", "").strip().title() or None,
        "budget": budget,
        "from_currency": from_currency,
        "to_currency": to_currency or "USD",
        "num_days": num_days,
        "date": intent.get("date"),
        "steps": steps,
    }
