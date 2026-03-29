import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gradio as gr
from core.agent import plan_trip

SUPPORTED_CITIES = ["Kigali", "Paris", "New York", "Nairobi", "Kampala", "London"]
SUPPORTED_CURRENCIES = ["USD", "EUR", "RWF", "UGX", "KES", "GBP", "JPY"]

CSS = """
body { background: #0f172a !important; }

.gradio-container {
    background: #0f172a !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* Header */
#header {
    text-align: center;
    padding: 32px 0 24px;
}

/* Panels */
.panel {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 16px !important;
    padding: 20px !important;
}

/* All labels */
.gradio-container label > span {
    color: #94a3b8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* Inputs */
.gradio-container input,
.gradio-container .wrap {
    background: #0f172a !important;
    border-color: #334155 !important;
    color: #f1f5f9 !important;
    border-radius: 10px !important;
}

/* Textareas */
.gradio-container textarea {
    background: #0f172a !important;
    border-color: #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
}

/* Plan button */
#plan-btn {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    margin-top: 16px !important;
    transition: opacity 0.2s !important;
}
#plan-btn:hover { opacity: 0.88 !important; }

/* Section titles */
.section-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #334155;
}

/* Examples table */
.gradio-container .examples table {
    background: #1e293b !important;
    border-radius: 10px !important;
}
.gradio-container .examples td, .gradio-container .examples th {
    color: #94a3b8 !important;
    border-color: #334155 !important;
}
"""

HEADER = """
<div id="header">
  <div style="font-size:48px; margin-bottom:8px;">✈️</div>
  <h1 style="margin:0; font-size:28px; font-weight:800; letter-spacing:-0.5px;
             background:linear-gradient(90deg,#60a5fa,#a78bfa);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
    TouristGuide Agent
  </h1>
  <p style="margin:8px 0 0; color:#64748b; font-size:14px;">
    AI-powered travel planning &nbsp;·&nbsp; Real weather &nbsp;·&nbsp; Live currency conversion
  </p>
</div>
"""


def run_agent(from_city, city, num_days, budget, from_currency, to_currency):
    num_days = max(1, int(num_days or 1))
    data = {"city": city.strip(), "num_days": num_days}
    if from_city and from_city.strip():
        data["from_city"] = from_city.strip()
    if budget:
        data["budget"] = budget
        data["from_currency"] = from_currency
        data["to_currency"] = to_currency

    result = plan_trip(data)
    status = result.get("status", "unknown")


    if status == "needs_clarification":
        return (
            f"⚠️  Please provide more details:\n{result['message']}",
            "", "",
            f"Missing fields: {', '.join(result['missing_fields'])}"
        )
    if status == "error":
        return f"❌  {result.get('error', 'Unknown error')}", "", "", "Status: error"

    itinerary   = result.get("itinerary", "")
    errors      = result.get("errors", [])
    tool_outputs = result.get("tool_outputs", {})

    # ── Weather box ───────────────────────────────────────────
    weather      = tool_outputs.get("weather", {}).get("weather", {})
    weather_src  = tool_outputs.get("weather", {}).get("source", "")
    weather_city = tool_outputs.get("weather", {}).get("city", city.strip())
    weather_country = tool_outputs.get("weather", {}).get("country", "")
    city_label   = f"{weather_city}, {weather_country}" if weather_country else weather_city

    if weather:
        precip = weather.get("precipitation_mm")
        weather_lines = [
            f"  📍  City          : {city_label}",
            f"  🌡  Temperature   : {weather.get('temperature')}°C",
            f"  🌤  Condition     : {weather.get('condition')}",
            f"  💧  Humidity      : {weather.get('humidity')}%",
            f"  💨  Wind          : {weather.get('wind_kph')} km/h",
        ]
        if precip is not None:
            weather_lines.append(f"  🌧  Precipitation : {precip} mm")
        weather_lines.append(f"  🔗  Source        : {weather_src}")
        weather_text = "\n".join(weather_lines)
    else:
        weather_text = "⚠️  Live weather data unavailable for this city."

    # ── Currency box ──────────────────────────────────────────
    currency = tool_outputs.get("currency")
    if currency:
        orig    = currency["original_amount"]
        orig_c  = currency["from_currency"]
        conv    = currency["converted_amount"]
        conv_c  = currency["to_currency"]
        rate    = currency["rate"]
        src     = currency["source"]
        warn    = currency.get("warnings")

        # Per-day breakdown if itinerary was built
        itin = tool_outputs.get("itinerary", {})
        per_day_line = ""
        if itin.get("budget"):
            per_day_line = f"\n  📅  Per day       : {itin['budget']['per_day']}"

        currency_lines = [
            f"  💵  Amount        : {orig:,.2f} {orig_c}",
            f"  💱  Converted     : {conv:,.2f} {conv_c}",
            f"  📈  Exchange rate : 1 {orig_c} = {rate} {conv_c}",
            f"  🔗  Source        : ExchangeRate-API (live)" if src == "exchangerate-api"
                else f"  🔗  Source        : {src} (offline table — set EXCHANGERATE_API_KEY)",
        ]
        if per_day_line:
            currency_lines.append(per_day_line)
        if warn:
            currency_lines.append(f"  ⚠️  Warning       : {'; '.join(warn)}")

        currency_text = "\n".join(currency_lines)
    else:
        currency_text = "—  No budget entered. Add an amount above to see currency conversion." \
            if not budget else "⚠️  Currency conversion unavailable."

    # ── Status box ────────────────────────────────────────────
    tools_used = list(tool_outputs.keys())
    status_lines = [
        f"{'✅' if not errors else '⚠️'} {status.replace('_', ' ').title()}",
        f"🛠  Tools used : {', '.join(tools_used)}",
    ]
    attractions_src = tool_outputs.get("attractions", {}).get("source", "")
    if attractions_src:
        status_lines.append(f"📍  Attractions: source = {attractions_src}")
    if errors:
        status_lines.append(f"⚠️  Unavailable: {', '.join(e['tool'] for e in errors)}")

    return itinerary, weather_text, currency_text, "\n".join(status_lines)


with gr.Blocks(title="TouristGuide Agent") as demo:

    gr.HTML(HEADER)

    with gr.Row(equal_height=False):

        # ── Left: inputs ──────────────────────────────────────
        with gr.Column(scale=1, elem_classes="panel"):
            gr.HTML('<div class="section-title" style="color:#60a5fa;">🗺️ &nbsp;Destination</div>')
            from_city_input = gr.Textbox(
                label="Departure city (optional)",
                placeholder="e.g. London"
            )
            city_input = gr.Textbox(
                label="Destination city",
                placeholder=f"e.g. {', '.join(SUPPORTED_CITIES)}"
            )
            num_days_input = gr.Number(
                label="Number of days", value=1, minimum=1, precision=0
            )

            gr.HTML('<div class="section-title" style="color:#a78bfa; margin-top:20px;">💰 &nbsp;Budget (optional)</div>')
            budget_input = gr.Number(label="Amount", precision=2)
            with gr.Row():
                from_currency = gr.Dropdown(
                    choices=SUPPORTED_CURRENCIES, value="USD", label="Budget currency"
                )
                to_currency = gr.Dropdown(
                    choices=SUPPORTED_CURRENCIES, value="USD", label="Show costs in"
                )

            submit_btn = gr.Button("✈️  Plan My Trip", variant="primary", elem_id="plan-btn", size="lg")

        # ── Right: outputs ─────────────────────────────────────
        with gr.Column(scale=2, elem_classes="panel"):

            # Weather + Currency side by side
            with gr.Row():
                with gr.Column():
                    gr.HTML('<div class="section-title" style="color:#38bdf8;">🌤️ &nbsp;Current Weather</div>')
                    weather_output = gr.Textbox(
                        label="", show_label=False, lines=8,
                        placeholder="Weather conditions will appear here…",
                    )
                with gr.Column():
                    gr.HTML('<div class="section-title" style="color:#34d399;">💱 &nbsp;Currency Conversion</div>')
                    currency_output = gr.Textbox(
                        label="", show_label=False, lines=8,
                        placeholder="Enter a budget amount to see the conversion…",
                    )

            gr.HTML('<div class="section-title" style="color:#60a5fa; margin-top:16px;">📋 &nbsp;Your Itinerary</div>')
            itinerary_output = gr.Textbox(
                label="", show_label=False, lines=14,
                placeholder="Your personalised itinerary will appear here after clicking Plan My Trip…",
            )

            gr.HTML('<div class="section-title" style="color:#64748b; margin-top:12px;">⚙️ &nbsp;Agent Status</div>')
            status_output = gr.Textbox(
                label="", show_label=False, lines=4,
            )

    gr.HTML('<div style="margin-top:20px;"></div>')
    gr.Examples(
        label="Quick examples — click any row to auto-fill",
        examples=[
            ["",        "Kigali",    1, 150000, "UGX", "USD"],
            ["London",  "Paris",     3, 240,    "EUR", "USD"],
            ["",        "New York",  2, 100,    "USD", "USD"],
            ["",        "Cotonou",   1, None,   "USD", "USD"],
            ["",        "Tokyo",     2, 50000,  "JPY", "USD"],
            ["",        "Cairo",     1, 500,    "USD", "USD"],
        ],
        inputs=[from_city_input, city_input, num_days_input, budget_input, from_currency, to_currency],
    )

    submit_btn.click(
        fn=run_agent,
        inputs=[from_city_input, city_input, num_days_input, budget_input, from_currency, to_currency],
        outputs=[itinerary_output, weather_output, currency_output, status_output],
    )

if __name__ == "__main__":
    demo.launch(css=CSS, theme=gr.themes.Base(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.violet,
        neutral_hue=gr.themes.colors.slate,
        font=gr.themes.GoogleFont("Inter"),
    ))
