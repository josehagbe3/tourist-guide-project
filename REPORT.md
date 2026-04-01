# TouristGuide Agent — Technical Report

## 1. Problem and User Scenario

### What the system does
TouristGuide Agent is a tool-calling AI agent that produces real, grounded travel plans by
orchestrating four external tools: weather data, currency conversion, tourist attractions, and
itinerary composition. The agent does not generate travel advice from memory — every fact
in the final response comes from a tool call.

### Who it serves
A traveller who wants a personalised, realistic day-by-day itinerary for any city in the world,
based on live conditions and their actual budget. Example request:

> "Plan a one-day trip in Kampala for someone with a budget of 50 USD, but show the costs in UGX."

### Why tool access is necessary
| Information | Why the model cannot guess |
|---|---|
| Current weather | Changes hourly; outdated advice can ruin a trip |
| Exchange rates | Fluctuate daily; wrong rates mislead budgeting |
| Attractions | Venue-specific; hallucinated names cause confusion |
| Cost of living | City-specific; a flat guess may be wildly incorrect |

### What goes wrong without tools
Without tools the model might suggest outdoor activities during a storm, quote an exchange
rate from training data that is months out of date, or invent attractions that do not exist. The
no-hallucination policy enforced by this system prevents all three.

---

## 2. Agent Design

### Architecture overview

```
User Input
    ↓
PLANNER  (agent/planner.py)
  • Claude Haiku parses natural language → structured intent
  • Rule-based fallback when no API key
  • Validates required fields: city, budget, from_currency
  • Returns clarification request if fields are missing
    ↓
EXECUTOR  (agent/executor.py)
  • Runs tools in sequence: weather → attractions → currency → itinerary
  • Budget validation after currency step (rejects if below city minimum)
  • Each tool failure is recorded; execution continues
    ↓
VALIDATOR  (agent/validator.py)
  • Confirms at least one tool succeeded
  • Flags total failure without crashing
    ↓
RESPONDER  (agent/responder.py)
  • Claude Haiku composes friendly itinerary from tool outputs only
  • Template-based fallback if no API key
  • Never invents data
    ↓
Response: { city, itinerary, tool_outputs, errors, status }
```

### Tools

#### 1. Weather Tool
- **Source**: OpenWeatherMap (live, requires key) → wttr.in (free, no key)
- **Output**: temperature (°C), condition, humidity (%), wind (km/h), precipitation (mm), country
- **Used for**: weather advisory in itinerary, choosing indoor vs outdoor activities

#### 2. Currency Conversion Tool
- **Source**: ExchangeRate-API (live, 160+ currencies) → offline table (50+ currencies)
- **Input**: amount, from_currency, to_currency (ISO 4217 codes)
- **Output**: converted amount, exchange rate, source, warnings
- **Safety**: no `eval()` or dynamic code execution; purely table/API lookup

#### 3. Tourist Attractions Tool
- **Source**: local curated DB (54 cities, 5 verified attractions each) → OpenTripMap API → OpenStreetMap Overpass (3 mirror servers, quality-ranked by wikidata/wikipedia tags)
- **Output**: list of up to 5 named attractions
- **Cache**: geocoding and Overpass results cached in-process (`lru_cache`)

#### 4. Itinerary Composition Tool
- **Input**: city, weather, attractions, budget info, num_days
- **Logic**: weather-aware (flags rain/heat), rotates attractions across days, adds per-day budget breakdown
- **Output**: structured day-by-day schedule with time slots

### Orchestration logic
1. Tools always run in the fixed sequence: weather → attractions → currency → itinerary
2. If budget < minimum daily cost × num_days, execution stops immediately with a clear message
3. Each tool result is stored; later tools consume earlier results (itinerary uses weather + attractions + currency)
4. Partial success is acceptable — if weather fails but attractions and currency succeed, an itinerary is still generated

### Error handling

| Scenario | Behaviour |
|---|---|
| Missing city | Asks: "Which city would you like to visit?" |
| Missing budget | Asks: "What is your total budget?" |
| Budget too low | Returns minimum required with source and confidence |
| Invalid API key | Falls back to free service or offline table |
| Network timeout | Next fallback tried automatically |
| City not in local DB | Overpass (3 servers) tried with expanding radius |
| All tools fail | `partial_success` status with explanation shown to user |
| Unknown currency | Error: "Set EXCHANGERATE_API_KEY for full global support" |

---

## 3. Threat Model

### Risk 1 — Unsafe execution of user input
**Threat**: User injects code or shell commands via city/budget fields.
**Mitigation**: City and currency values are used only as string parameters to HTTP requests. No `eval()`, `exec()`, or shell calls anywhere in the codebase. Pydantic validates types on the FastAPI endpoint.

### Risk 2 — API key exposure
**Threat**: Keys logged, leaked in error messages, or committed to version control.
**Mitigation**: Keys loaded via `python-dotenv` from `.env` (git-ignored). Error messages never include key values. `.env.example` provided with placeholder strings.

### Risk 3 — Trusting malformed tool outputs
**Threat**: An API returns unexpected JSON structure causing a crash or wrong data.
**Mitigation**: Every tool result is checked for `status == "success"` before use. Missing fields default safely (e.g. `res.get("converted_amount", 0)`). Exceptions are caught and added to the `errors` list, not propagated.

### Risk 4 — Stale or unreliable data
**Threat**: Offline fallback rates or local attraction data become outdated.
**Mitigation**: Live API always takes precedence. Offline data is clearly labelled with source and confidence in the response (`"source": "fallback"`, `"confidence": "low"`). Users see warnings when live data is unavailable.

### Risk 5 — Misleading advice from incomplete results
**Threat**: Agent generates an itinerary when key data (e.g. attractions) is missing, leading to vague or wrong suggestions.
**Mitigation**: Itinerary tool is skipped if attractions are unavailable. The response explicitly lists which tools failed under "Unavailable". The responder never invents attraction names.

### Risk 6 — Budget validation bypass
**Threat**: User submits a trivially small budget and receives a plan for an unaffordable trip.
**Mitigation**: Budget is converted to USD and compared against per-city minimum (Teleport API → curated DB → global default × 1.35 tourism multiplier). Trip is rejected if budget is insufficient, with exact shortfall shown.

---

## 4. Evaluation — Test Transcripts

### Scenario 1 — Multi-Tool Request
**Input**: `city=Kampala, budget=50, from_currency=USD, to_currency=UGX, num_days=1`

```
Status: success
Tools used: weather, attractions, currency, itinerary

Trip to Kampala, Uganda
⚠️  Weather advisory: Patchy rain nearby. Prefer indoor venues.

Day 1:
  9:00 AM  — Visit Kasubi Tombs
  11:00 AM — Explore Uganda Museum
  1:00 PM  — Lunch at a local restaurant
  3:00 PM  — Afternoon at Namugongo Martyrs Shrine
  6:00 PM  — Evening walk and dinner
```
**Observation**: All 4 tools called in sequence. Weather condition correctly triggers indoor advisory. Attractions from local DB. Currency converted live (or via fallback table).

---

### Scenario 2 — Clarification
**Input**: `city=Kigali` (no budget)

```
Status: needs_clarification
Missing: ['budget']
Message: What is your total budget for the trip (covering travel,
         accommodation, food and tourism)?
```
**Observation**: Agent correctly identifies the missing required field and asks a targeted question without crashing.

---

### Scenario 3 — Tool Failure (Invalid City)
**Input**: `city=Xyzabc123, budget=100, from_currency=USD`

```
Status: partial_success
Tools used: currency
Errors: weather, attractions, itinerary

Trip to Xyzabc123
⚠️  Could not build itinerary — missing data: weather, attractions, itinerary
```
**Observation**: Currency still converts correctly. Weather and attractions fail gracefully (city not found). User is informed transparently; no crash.

---

### Scenario 4 — Budget Too Low
**Input**: `city=Paris, budget=10, from_currency=USD, num_days=3`

```
Status: budget_too_low

Budget too low for Paris (3 days).
Minimum required: 528 USD ($176/day × 3 days covering accommodation,
meals, transport & tourism).
Your budget: 10 USD ≈ $10 USD.
Cost estimate source: local_db · confidence: high.
```
**Observation**: System rejects the trip before wasting API calls on itinerary generation. Minimum is sourced from curated local DB with high confidence.

---

### Scenario 5 — Multi-Day Trip with Currency Conversion
**Input**: `city=Tokyo, budget=50000, from_currency=JPY, to_currency=USD, num_days=2`

```
Status: success
Tools used: weather, attractions, currency, itinerary

Weather: Light rain, 14°C, humidity 94%
Currency: 50,000 JPY = 314.45 USD (rate: 0.006289)

Trip to Tokyo, Japan
⚠️  Weather advisory: Light rain conditions. Prefer indoor venues.

Day 1:
  9:00 AM  — Visit Senso-ji Temple
  11:00 AM — Explore Shibuya Crossing
  1:00 PM  — Lunch at a local restaurant
  3:00 PM  — Afternoon at Meiji Shrine
  6:00 PM  — Evening walk and dinner

Day 2:
  9:00 AM  — Visit Meiji Shrine
  11:00 AM — Explore Shinjuku Gyoen
  1:00 PM  — Lunch at a local restaurant
  3:00 PM  — Afternoon at teamLab Borderless
  6:00 PM  — Evening walk and dinner
```
**Observation**: Multi-day schedule correctly rotates attractions. Weather advisory consistent with rain data. JPY→USD conversion accurate.

---

### Scenario 6 — Unlisted City (Overpass Fallback)
**Input**: `city=Lomé, budget=100000, from_currency=XOF, to_currency=USD, num_days=1`

```
Status: partial_success
Tools used: weather, currency
Errors: attractions, itinerary

Trip to Lomé, Togo
⚠️  Could not build itinerary — missing data: attractions, itinerary
```
**Observation**: Lomé is not in the local 54-city DB. Overpass was unavailable at test time (server timeout). Weather and currency succeeded. System reports partial success honestly rather than generating a fake itinerary.

---

### System Limitations
1. **Overpass reliability**: Free OSM servers occasionally timeout (504). Cities outside the 54-city local DB may return no attractions during peak load.
2. **API keys required for best experience**: Without `OPENWEATHER_API_KEY` and `EXCHANGERATE_API_KEY`, the system falls back to free/offline sources with lower accuracy.
3. **LLM itinerary quality**: Without `ANTHROPIC_API_KEY`, itineraries use a deterministic template (fixed time slots, no prose). With the key, Claude Haiku generates richer, more natural text.
4. **Offline rate staleness**: The 50+ currency fallback table was last reviewed early 2025. Rates drift over time — the live API should be used for accurate results.
5. **Attraction depth**: Local DB has 5 attractions per city. For longer trips (5+ days), attractions repeat after rotation.
