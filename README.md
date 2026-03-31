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

**Weather tool** — priority cascade: (1) OpenWeatherMap API when `OPENWEATHER_API_KEY` is set; (2) wttr.in free API (no key, global coverage). Returns `condition`, `temperature`, `humidity`, `wind_kph`, `feels_like`, and `precipitation_mm`. The `source` field (`openweathermap` / `wttr.in`) is always declared in the response.

**Currency tool** — fetches live exchange rates from ExchangeRate-API when `EXCHANGERATE_API_KEY` is set. Falls back to a hardcoded offline table (USD, EUR, GBP, RWF, UGX, KES, JPY) if the key is missing or the API is unreachable. The `source` field (`exchangerate-api` / `fallback`) is declared in every response.

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
| API timeout / network error | Weather falls back to wttr.in; attractions fall back to OpenStreetMap Overpass |

---

## 3. Threat Model

| Threat | Mitigation |
|--------|------------|
| Prompt injection via city name | City is passed as a query parameter to the API, never evaluated as code |
| API key exposure | Key loaded from environment variable via `python-dotenv`; never hardcoded |
| Hallucinated attractions or weather | Responder only uses `tool_outputs` dict — never the raw user string |
| Malformed tool output trusted blindly | Validator checks `status` field before passing data to responder |
| Stale data misleading users | `source` field is explicit in every tool response (`openweathermap` / `wttr.in`, `exchangerate-api` / `fallback`, etc.) |
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

### Transcript 4 — Tool failure: unknown city (no API key)
**Input:** `city=Accra` (not in local DB, no OPENTRIPMAP_API_KEY set)
**Tools called:** weather (wttr.in success), attractions (OpenStreetMap Overpass fallback), itinerary (success)
**Status:** `success`
**Output:** Live weather, real attractions from OpenStreetMap, full itinerary

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
- Attractions for cities outside the local database (10 cities) require `OPENTRIPMAP_API_KEY`; free fallback via OpenStreetMap Overpass is used otherwise.
- Currency conversion is live via ExchangeRate-API when `EXCHANGERATE_API_KEY` is set; falls back to a 7-currency offline table.
- Weather is live via OpenWeatherMap when `OPENWEATHER_API_KEY` is set; falls back to wttr.in (free, global).
- Itinerary detail shown for up to 3 days; longer trips summarise remaining days.

---

## 5. Setup & Running

### Requirements

- Python 3.10 or higher
- Internet connection (for live weather, attractions, and currency APIs)

### Step-by-step (Linux / macOS)

```bash
# 1. Get the project
git clone <repo-url>
cd TouristGuide_Agent

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys (optional — free fallbacks work without keys)
cp .env.example .env
# Edit .env and fill in any keys you have:
#   OPENWEATHER_API_KEY   → openweathermap.org/api       (free tier)
#   OPENTRIPMAP_API_KEY   → opentripmap.com/product      (free tier)
#   EXCHANGERATE_API_KEY  → exchangerate-api.com          (free tier)
#   ANTHROPIC_API_KEY     → console.anthropic.com         (enables AI responses)

# 5. Run the Gradio UI
python app/gradio_app.py
```
Open **http://127.0.0.1:7860** in your browser.

### Windows

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app/gradio_app.py
```

### Running the REST API (optional)

```bash
uvicorn app.main:app --reload --port 8000
```
Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI.

### API example
```bash
curl -X POST http://localhost:8000/plan-trip \
  -H "Content-Type: application/json" \
  -d '{"city": "Kigali", "budget": 150000, "from_currency": "UGX", "to_currency": "USD"}'
```

### What works without any API keys

| Feature | Without keys | With keys |
|---------|-------------|-----------|
| Weather | wttr.in (free, global) | OpenWeatherMap (more accurate) |
| Attractions | OpenStreetMap Overpass (free) | OpenTripMap (richer data) |
| Currency | Offline 7-currency table | ExchangeRate-API (live, all currencies) |
| AI responses | Structured fallback | Claude Haiku (natural language) |



