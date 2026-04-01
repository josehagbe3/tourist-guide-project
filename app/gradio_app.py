import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gradio as gr
from core.agent import plan_trip

SUPPORTED_CITIES = ["Kigali", "Paris", "New York", "Nairobi", "Kampala", "London"]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* { box-sizing: border-box; }

body {
    background: #060d1a !important;
    font-family: 'Inter', sans-serif !important;
}

.gradio-container {
    background: #060d1a !important;
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 0 24px 48px !important;
}

/* ── Header ─────────────────────────────────── */
#header {
    text-align: center;
    padding: 48px 0 36px;
}
#header .badge {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    color: #a78bfa;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 4px 14px;
    border-radius: 999px;
    margin-bottom: 18px;
}
#header h1 {
    margin: 0 0 10px;
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
#header p {
    margin: 0;
    color: #475569;
    font-size: 15px;
    letter-spacing: 0.02em;
}
#header .dots { color: #334155; }

/* ── Cards / panels ─────────────────────────── */
.card {
    background: linear-gradient(145deg, #0f1f35 0%, #0d1b2e 100%) !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 20px !important;
    padding: 24px !important;
    box-shadow: 0 4px 32px rgba(0,0,0,0.4) !important;
}

/* ── Section headings ───────────────────────── */
.sec-head {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e3a5f;
}

/* ── Labels ─────────────────────────────────── */
.gradio-container label > span {
    color: #64748b !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ── Inputs ─────────────────────────────────── */
.gradio-container input,
.gradio-container .wrap {
    background: #060d1a !important;
    border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important;
    border-radius: 12px !important;
    transition: border-color 0.2s !important;
}
.gradio-container input:focus,
.gradio-container .wrap:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
}

/* ── Textareas ──────────────────────────────── */
.gradio-container textarea {
    background: #060d1a !important;
    border: 1px solid #1e3a5f !important;
    color: #cbd5e1 !important;
    border-radius: 12px !important;
    font-size: 13.5px !important;
    line-height: 1.85 !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s !important;
}
.gradio-container textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.10) !important;
}

/* ── Plan button ────────────────────────────── */
#plan-btn {
    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%) !important;
    border: none !important;
    border-radius: 14px !important;
    color: white !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    margin-top: 20px !important;
    padding: 14px !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
    transition: all 0.2s !important;
}
#plan-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 28px rgba(99,102,241,0.5) !important;
}
#plan-btn:active { transform: translateY(0) !important; }

/* ── Itinerary textarea special styling ─────── */
#itinerary-box textarea {
    background: linear-gradient(180deg, #060d1a 0%, #07111f 100%) !important;
    border: 1px solid #1e3a5f !important;
    border-left: 3px solid #3b82f6 !important;
    font-size: 14px !important;
    line-height: 2 !important;
    color: #e2e8f0 !important;
    padding: 16px 20px !important;
}

/* ── Weather / Currency textarea ────────────── */
#weather-box textarea, #currency-box textarea {
    font-size: 13px !important;
    line-height: 2 !important;
    color: #94a3b8 !important;
}

/* ── Status textarea ────────────────────────── */
#status-box textarea {
    font-size: 12.5px !important;
    color: #64748b !important;
    line-height: 1.9 !important;
}

/* ── Divider ────────────────────────────────── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e3a5f, transparent);
    margin: 20px 0;
}
"""

HEADER = """
<div id="header">
  <div class="badge">AI Travel Agent</div>
  <h1>TouristGuide Agent</h1>
  <p>
    Real-time weather &nbsp;<span class="dots">·</span>&nbsp;
    Live currency conversion &nbsp;<span class="dots">·</span>&nbsp;
    Verified attractions &nbsp;<span class="dots">·</span>&nbsp;
    AI-powered itineraries
  </p>
</div>
"""


def _fmt_itinerary(raw: str) -> str:
    """Add visual separators and spacing to the itinerary text."""
    if not raw:
        return ""
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        # Day headers
        if stripped.startswith("Day ") and stripped.endswith(":"):
            lines.append("")
            lines.append(f"{'─' * 38}")
            lines.append(f"  {stripped}")
            lines.append(f"{'─' * 38}")
        # Trip header (first line)
        elif stripped.startswith("Trip to") or stripped.startswith("Trip from"):
            lines.append(f"  ✈  {stripped}")
        # Weather advisory
        elif stripped.startswith("⚠️"):
            lines.append("")
            lines.append(f"  {stripped}")
            lines.append("")
        # Time slots
        elif stripped and stripped[0].isdigit() and "AM" in stripped or "PM" in stripped:
            lines.append(f"    {stripped}")
        # Summary line (Days 4-7...)
        elif stripped.startswith("..."):
            lines.append("")
            lines.append(f"  {stripped}")
        elif stripped:
            lines.append(f"  {stripped}")
        else:
            lines.append("")
    return "\n".join(lines)


def run_agent(from_city, city, num_days, budget, from_currency, to_currency):
    num_days = max(1, int(num_days or 1))
    data = {"city": city.strip(), "num_days": num_days}
    if from_city and from_city.strip():
        data["from_city"] = from_city.strip()
    if budget:
        fc = from_currency.strip().upper() if from_currency else "USD"
        tc = to_currency.strip().upper() if to_currency else "USD"
        if not fc:
            return "⚠️  Please enter a budget currency (e.g. USD, EUR, XOF).", "", "", ""
        data["budget"] = budget
        data["from_currency"] = fc
        data["to_currency"] = tc

    result = plan_trip(data)
    status = result.get("status", "unknown")

    if status == "needs_clarification":
        return (
            f"⚠️  Please provide more details:\n\n  {result['message']}",
            "", "",
            f"  ℹ  Missing: {', '.join(result['missing_fields'])}"
        )
    if status == "budget_too_low":
        return f"❌  Budget too low\n\n{result.get('error', '')}", "", "", "  Status: budget too low"
    if status == "error":
        return f"❌  {result.get('error', 'Unknown error')}", "", "", "  Status: error"

    itinerary    = _fmt_itinerary(result.get("itinerary", ""))
    errors       = result.get("errors", [])
    tool_outputs = result.get("tool_outputs", {})

    # ── Weather ───────────────────────────────────────────────
    weather         = tool_outputs.get("weather", {}).get("weather", {})
    weather_src     = tool_outputs.get("weather", {}).get("source", "")
    weather_city    = tool_outputs.get("weather", {}).get("city", city.strip())
    weather_country = tool_outputs.get("weather", {}).get("country", "")
    city_label      = f"{weather_city}, {weather_country}" if weather_country else weather_city

    if weather:
        precip = weather.get("precipitation_mm")
        rows = [
            ("📍", "City",          city_label),
            ("🌡", "Temperature",   f"{weather.get('temperature')}°C"),
            ("🌤", "Condition",     weather.get("condition", "—")),
            ("💧", "Humidity",      f"{weather.get('humidity')}%"),
            ("💨", "Wind",          f"{weather.get('wind_kph')} km/h"),
        ]
        if precip is not None:
            rows.append(("🌧", "Precipitation", f"{precip} mm"))
        rows.append(("🔗", "Source", weather_src))
        weather_text = "\n".join(f"  {icon}  {label:<14}: {value}" for icon, label, value in rows)
    else:
        weather_text = "  ⚠️  Live weather data unavailable for this city."

    # ── Currency ──────────────────────────────────────────────
    currency = tool_outputs.get("currency")
    if currency:
        orig   = currency["original_amount"]
        orig_c = currency["from_currency"]
        conv   = currency["converted_amount"]
        conv_c = currency["to_currency"]
        rate   = currency["rate"]
        src    = currency["source"]
        warn   = currency.get("warnings")

        itin       = tool_outputs.get("itinerary", {})
        per_day    = itin.get("budget", {}).get("per_day", "") if itin else ""

        src_label = "ExchangeRate-API (live)" if src == "exchangerate-api" else f"{src} (offline)"
        rows = [
            ("💵", "Amount",        f"{orig:,.2f} {orig_c}"),
            ("💱", "Converted",     f"{conv:,.2f} {conv_c}"),
            ("📈", "Exchange rate", f"1 {orig_c} = {rate} {conv_c}"),
            ("🔗", "Source",        src_label),
        ]
        if per_day:
            rows.append(("📅", "Per day", per_day))
        currency_text = "\n".join(f"  {icon}  {label:<14}: {value}" for icon, label, value in rows)
        if warn:
            currency_text += f"\n\n  ⚠️  {'; '.join(warn)}"
    else:
        currency_text = (
            "  —  No budget entered.\n      Add an amount to see conversion."
            if not budget else "  ⚠️  Currency conversion unavailable."
        )

    # ── Status ────────────────────────────────────────────────
    tools_used      = list(tool_outputs.keys())
    ok              = not errors
    attractions_src = tool_outputs.get("attractions", {}).get("source", "")
    status_lines    = [
        f"  {'✅' if ok else '⚠️'}  {status.replace('_', ' ').title()}",
        f"  🛠  Tools used    : {', '.join(tools_used)}",
    ]
    if attractions_src:
        status_lines.append(f"  📍  Attractions  : source = {attractions_src}")
    if errors:
        status_lines.append(f"  ⚠️  Unavailable  : {', '.join(e['tool'] for e in errors)}")

    return itinerary, weather_text, currency_text, "\n".join(status_lines)


with gr.Blocks(title="TouristGuide Agent", css=CSS) as demo:

    gr.HTML(HEADER)

    with gr.Row(equal_height=False):

        # ── Left: inputs ──────────────────────────────────────
        with gr.Column(scale=1, elem_classes="card"):

            gr.HTML('<div class="sec-head" style="color:#60a5fa;">🗺️ &nbsp; Destination</div>')
            from_city_input = gr.Textbox(
                label="Departure city (optional)",
                placeholder="e.g. London, Kampala"
            )
            city_input = gr.Textbox(
                label="Destination city",
                placeholder=f"e.g. {', '.join(SUPPORTED_CITIES)}"
            )
            num_days_input = gr.Number(
                label="Number of days", value=1, minimum=1, precision=0
            )

            gr.HTML('<div class="divider"></div>')
            gr.HTML('<div class="sec-head" style="color:#a78bfa;">💰 &nbsp; Budget (required)</div>')
            budget_input = gr.Number(
                label="Total amount  (travel + accommodation + food + tourism)",
                precision=2
            )
            with gr.Row():
                from_currency = gr.Textbox(
                    label="Budget currency", value="USD",
                    placeholder="USD, EUR, XOF…"
                )
                to_currency = gr.Textbox(
                    label="Show costs in", value="USD",
                    placeholder="USD, EUR, RWF…"
                )

            submit_btn = gr.Button("✈️  Plan My Trip", variant="primary",
                                   elem_id="plan-btn", size="lg")

        # ── Right: outputs ─────────────────────────────────────
        with gr.Column(scale=2, elem_classes="card"):

            with gr.Row():
                with gr.Column():
                    gr.HTML('<div class="sec-head" style="color:#38bdf8;">🌤️ &nbsp; Current Weather</div>')
                    weather_output = gr.Textbox(
                        label="", show_label=False, lines=8,
                        placeholder="  Weather conditions will appear here…",
                        elem_id="weather-box",
                    )
                with gr.Column():
                    gr.HTML('<div class="sec-head" style="color:#34d399;">💱 &nbsp; Currency Conversion</div>')
                    currency_output = gr.Textbox(
                        label="", show_label=False, lines=8,
                        placeholder="  Enter a budget amount to see the conversion…",
                        elem_id="currency-box",
                    )

            gr.HTML('<div class="divider"></div>')
            gr.HTML('<div class="sec-head" style="color:#60a5fa;">📋 &nbsp; Your Itinerary</div>')
            itinerary_output = gr.Textbox(
                label="", show_label=False, lines=18,
                placeholder="  Your personalised itinerary will appear here…",
                elem_id="itinerary-box",
            )

            gr.HTML('<div class="divider"></div>')
            gr.HTML('<div class="sec-head" style="color:#475569;">⚙️ &nbsp; Agent Status</div>')
            status_output = gr.Textbox(
                label="", show_label=False, lines=4,
                elem_id="status-box",
            )

    submit_btn.click(
        fn=run_agent,
        inputs=[from_city_input, city_input, num_days_input, budget_input,
                from_currency, to_currency],
        outputs=[itinerary_output, weather_output, currency_output, status_output],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Base(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.violet,
        neutral_hue=gr.themes.colors.slate,
        font=gr.themes.GoogleFont("Inter"),
    ))
