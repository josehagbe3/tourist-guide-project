# TouristGuide Agent — Technical Report

## 1. Problem and User Scenario

### What the system does
TouristGuide is a tool-calling AI agent that plans day trips by orchestrating four external tools: a weather service, a tourist attractions database, a currency converter, and an itinerary composer. It produces a grounded, weather-aware travel plan — not a guess from memory.

### Who it serves
A traveller who wants a practical, same-day itinerary for an unfamiliar city. They may have a budget in a local currency and want costs shown in a different currency. They expect the agent to flag bad weather and adapt the plan accordingly.

### Why tool access is necessary
- Weather changes daily — a model trained months ago cannot know today's conditions.
- Currency rates fluctuate — hardcoded rates would mislead users on costs.
- Attraction data must be verifiable — hallucinated landmarks break trust immediately.

### What goes wrong without tools
Without tools, the model would invent plausible-sounding but potentially wrong weather, stale exchange rates, and non-existent or closed attractions. A user who plans around hallucinated data wastes time and money.

---

## 2. Agent Design

### Architecture

```
User input (structured dict or natural language string)
        │
        ▼
┌── Planner ────────────────────────────────────────────┐
│  Extracts: city, budget, from_currency, to_currency   │
│  Uses Claude Haiku (LLM path) or rule-based fallback  │
│  Detects missing fields → asks clarification          │
│  Decides which tools to call                          │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌── Executor ───────────────────────────────────────────┐
│  Calls tools in sequence, deterministically           │
│  Each tool result stored or error recorded            │
│  Tools: weather → attractions → currency → itinerary  │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌── Validator ──────────────────────────────────────────┐
│  Checks if at least one tool succeeded                │
│  Passes errors through to responder (no silent fail)  │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌── Responder ──────────────────────────────────────────┐
│  Uses Claude Haiku (LLM path) or structured fallback  │
│  Generates itinerary from tool outputs only           │
│  Never invents data not present in tool results       │
└───────────────────────────────────────────────────────┘
```

### Tools

| Tool | Function | Input | Output |
|------|----------|-------|--------|
| Weather | `get_weather(city)` | city name | condition, temperature, humidity, wind_kph, precipitation_mm |
| Attractions | `get_attractions(city)` | city name | list of notable places |
| Currency | `convert_currency(amount, from, to)` | amount + currency codes | converted amount + rate |
| Itinerary | `compose_itinerary(city, weather, attractions, budget)` | tool outputs | time-based schedule |

**Weather tool** — priority cascade: (1) OpenWeatherMap API when `OPENWEATHER_API_KEY` is set; (2) wttr.in free API (no key, global coverage); (3) curated mock data for 6 cities (Kigali, Paris, New York, Nairobi, Kampala, London). Returns `condition`, `temperature`, `humidity`, `wind_kph`, and `precipitation_mm`. The `source` field (`openweathermap` / `wttr.in` / `mock`) is always declared in the response.

**Currency tool** — fetches live exchange rates from open.er-api.com (free, no API key required) with support for any ISO 4217 currency pair. Falls back to a hardcoded rate table (USD, EUR, GBP, RWF, UGX, KES, JPY) only if the live API is unreachable. The `source` field (`live` / `fallback`) is declared in every response.

**Itinerary tool** — deterministic scheduler. Reads weather condition and marks the plan as outdoor-friendly or not. Produces a 5-slot day schedule. Adds a weather advisory if conditions are poor or temperature is extreme.

### Orchestration logic
The planner decides which tools to call:
- `weather` and `attractions` — always called if city is provided.
- `currency` — only if budget **and** from_currency are both present.
- `itinerary` — always last; consumes outputs of the other three.

The executor runs tools in order. Each failure is recorded in an `errors` list but does not stop execution — remaining tools are still attempted. The responder receives whatever data was collected.

### Error handling

| Scenario | Behaviour |
|----------|-----------|
| Missing city | `needs_clarification` — agent asks for city |
| Budget without currency | `needs_clarification` — agent asks for currency |
| Unsupported city (weather/attractions) | Tool returns `status: error`; other tools still run |
| Invalid currency code | Currency tool returns `status: error`; itinerary built without budget info |
| All tools fail | Validator flags it; responder returns a graceful "no data" message |
| API timeout / network error | Weather falls back to mock data automatically |

---

## 3. Threat Model

| Threat | Mitigation |
|--------|------------|
| Prompt injection via city name | City is passed as a query parameter to the API, never evaluated as code |
| API key exposure | Key loaded from environment variable via `python-dotenv`; never hardcoded |
| Hallucinated attractions or weather | Responder only uses `tool_outputs` dict — never the raw user string |
| Malformed tool output trusted blindly | Validator checks `status` field before passing data to responder |
| Stale mock data misleading users | Source field (`live` vs `mock`) is explicit in every weather response |
| Unsupported currency silently converting wrong | Currency tool validates both `from_currency` and `to_currency` before any calculation |
| Outdoor itinerary in bad weather | Itinerary tool checks `condition` field and sets `outdoor_friendly: False` when rainy/stormy; weather advisory added |

---

## 4. Evaluation Transcripts

### Transcript 1 — Full happy path
**Input:** `city=Kigali, budget=150000, from_currency=UGX, to_currency=USD`
**Tools called:** weather, attractions, currency, itinerary
**Status:** `success`
**Output:** Sunny 26°C day, 3 attractions, 150000 UGX ≈ 40.0 USD, 5-slot schedule

### Transcript 2 — Clarification: missing city
**Input:** `budget=50`
**Status:** `needs_clarification`
**Output:** "Which city would you like to visit?"

### Transcript 3 — Clarification: budget without currency
**Input:** `city=Paris, budget=200`
**Status:** `needs_clarification`
**Output:** "What currency is your budget in?"

### Transcript 4 — Tool failure: unsupported city
**Input:** `city=Nairobi` (no attractions data)
**Tools called:** weather (mock success), attractions (error), itinerary (error — no attractions)
**Status:** `partial_success`
**Output:** Weather retrieved, graceful note that attractions are unavailable

### Transcript 5 — Tool failure: invalid currency
**Input:** `city=Paris, budget=100, from_currency=XYZ, to_currency=USD`
**Tools called:** weather (success), attractions (success), currency (error), itinerary (success without budget)
**Status:** `partial_success`
**Output:** Full itinerary, note that currency conversion failed

### Transcript 6 — New York, EUR budget
**Input:** `city=New York, budget=80, from_currency=EUR, to_currency=USD`
**Tools called:** weather, attractions, currency, itinerary
**Status:** `success`
**Output:** Rainy 22°C day → itinerary marked `outdoor_friendly: False`, weather advisory added

### System limitations
- Attractions database covers 3 cities only (Kigali, Paris, New York). Any other city returns a tool error.
- Mock weather covers 6 cities; live API covers any city with a valid OpenWeatherMap key.
- Currency table is static — does not reflect real-time fluctuations.
- Itinerary schedule is fixed at 5 slots; does not yet adapt to `num_days > 1`.

---

## 5. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional — mock fallbacks exist)
export OPENWEATHER_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here   # enables LLM planner + responder

# Run Gradio UI
python app/gradio_app.py

# Or run FastAPI
uvicorn app.main:app --reload
```

### API example
```bash
curl -X POST http://localhost:8000/plan-trip \
  -H "Content-Type: application/json" \
  -d '{"city": "Kigali", "budget": 150000, "from_currency": "UGX", "to_currency": "USD"}'
```
