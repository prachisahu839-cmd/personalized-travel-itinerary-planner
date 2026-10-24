"""
Personalized Travel Itinerary Planner
Skill Wallet Capstone Project 4

Streamlit app with:
- Gemini/Groq API support and a deterministic demo mode
- Destination recommendations
- Day-wise itinerary generation with proximity-aware clustering heuristics
- Activity swapping and single-day regeneration
- Session-backed trip history and PDF export

Note: without a maps/geocoding provider, geographic clustering uses destination-specific
neighborhood/area hints and deterministic demo data; it is a planning heuristic, not live routing.
"""
from __future__ import annotations

import json
import os
import random
import re
import textwrap
from datetime import date, timedelta
from io import BytesIO
from typing import Any

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether
)

APP_TITLE = "Personalized Travel Itinerary Planner"
CURRENCY_BY_COUNTRY = {
    "India": ("INR", 83.0), "Japan": ("JPY", 150.0), "United Kingdom": ("GBP", 0.79),
    "United States": ("USD", 1.0), "Thailand": ("THB", 36.0), "Indonesia": ("IDR", 15700.0),
    "France": ("EUR", 0.92), "Italy": ("EUR", 0.92), "Spain": ("EUR", 0.92),
    "Portugal": ("EUR", 0.92), "United Arab Emirates": ("AED", 3.67),
    "Nepal": ("NPR", 133.0), "Singapore": ("SGD", 1.35), "Australia": ("AUD", 1.52),
    "Vietnam": ("VND", 25000.0), "Mexico": ("MXN", 17.2), "Turkey": ("TRY", 34.0),
}
DESTINATIONS = [
    {"city":"Goa", "country":"India", "vibes":["Beach","Relaxed","Food","Nightlife"], "tags":["Beach reset","Seafood","Sunsets"], "budget":"Budget", "season":"Oct–Mar", "areas":["North Goa","Panaji","South Goa"], "currency":"INR"},
    {"city":"Jaipur", "country":"India", "vibes":["Cultural","History","Food"], "tags":["Royal heritage","Markets","Architecture"], "budget":"Budget", "season":"Oct–Mar", "areas":["Pink City","Amer","Central Jaipur"], "currency":"INR"},
    {"city":"Manali", "country":"India", "vibes":["Mountains","Adventure","Relaxed"], "tags":["Mountain air","Trails","Cafés"], "budget":"Moderate", "season":"Mar–Jun / Dec–Feb", "areas":["Old Manali","Mall Road","Solang"], "currency":"INR"},
    {"city":"Rishikesh", "country":"India", "vibes":["Mountains","Adventure","Relaxed"], "tags":["River views","Yoga","Rafting"], "budget":"Budget", "season":"Sep–Nov / Mar–May", "areas":["Tapovan","Ram Jhula","Laxman Jhula"], "currency":"INR"},
    {"city":"Varanasi", "country":"India", "vibes":["Cultural","History","Food"], "tags":["River rituals","Old lanes","Spiritual"], "budget":"Budget", "season":"Nov–Mar", "areas":["Ghats","Old City","Sarnath"], "currency":"INR"},
    {"city":"Mumbai", "country":"India", "vibes":["Urban","Food","Nightlife","History"], "tags":["Street food","Coastal city","Arts"], "budget":"Moderate", "season":"Nov–Feb", "areas":["Colaba","Fort","Bandra"], "currency":"INR"},
    {"city":"Udaipur", "country":"India", "vibes":["Cultural","Relaxed","Food"], "tags":["Lake views","Palaces","Romantic"], "budget":"Moderate", "season":"Oct–Mar", "areas":["Lake Pichola","Old City","Fateh Sagar"], "currency":"INR"},
    {"city":"Bangkok", "country":"Thailand", "vibes":["Urban","Food","Nightlife","Cultural"], "tags":["Night markets","Temples","Street eats"], "budget":"Budget", "season":"Nov–Feb", "areas":["Old Town","Siam","Riverside"], "currency":"THB"},
    {"city":"Kyoto", "country":"Japan", "vibes":["Cultural","History","Relaxed"], "tags":["Temples","Gardens","Tea culture"], "budget":"Luxury", "season":"Mar–May / Oct–Nov", "areas":["Higashiyama","Arashiyama","Downtown"], "currency":"JPY"},
    {"city":"Lisbon", "country":"Portugal", "vibes":["Urban","Food","History","Relaxed"], "tags":["Tram rides","Tile art","Ocean air"], "budget":"Moderate", "season":"Apr–Jun / Sep–Oct", "areas":["Baixa","Belém","Alfama"], "currency":"EUR"},
    {"city":"Bali", "country":"Indonesia", "vibes":["Beach","Mountains","Relaxed","Adventure"], "tags":["Rice terraces","Beaches","Wellness"], "budget":"Moderate", "season":"Apr–Oct", "areas":["Ubud","Canggu","Uluwatu"], "currency":"IDR"},
    {"city":"Istanbul", "country":"Turkey", "vibes":["Cultural","History","Food","Urban"], "tags":["Grand bazaars","Waterfront","Cuisine"], "budget":"Moderate", "season":"Apr–May / Sep–Nov", "areas":["Sultanahmet","Karaköy","Kadıköy"], "currency":"TRY"},
    {"city":"New York", "country":"United States", "vibes":["Urban","Food","History","Nightlife"], "tags":["Museums","Broadway","Neighborhoods"], "budget":"Luxury", "season":"Apr–Jun / Sep–Oct", "areas":["Midtown","Lower Manhattan","Brooklyn"], "currency":"USD"},
    {"city":"Dubai", "country":"United Arab Emirates", "vibes":["Urban","Luxury","Food","Nightlife"], "tags":["Skyline","Desert","Shopping"], "budget":"Luxury", "season":"Nov–Mar", "areas":["Downtown","Marina","Old Dubai"], "currency":"AED"},
]
ACTIVITY_BANK = {
    "Sightseeing": [
        ("Explore the historic district", "History", "Old Town", 12, 2.0),
        ("Visit a landmark viewpoint", "Urban", "Central District", 18, 1.5),
        ("Guided heritage walk", "History", "Old Town", 22, 2.0),
        ("Visit a local art gallery", "Cultural", "Arts Quarter", 14, 1.5),
        ("Explore a botanical garden", "Relaxed", "Garden District", 10, 1.5),
        ("Scenic waterfront promenade", "Beach", "Waterfront", 0, 1.5),
        ("Visit a temple or cultural site", "Cultural", "Heritage Quarter", 8, 1.5),
        ("Explore a neighborhood market", "Food", "Market Quarter", 5, 1.5),
    ],
    "Lunch": [
        ("Local family-run restaurant", "Food", "Market Quarter", 14, 1.0),
        ("Vegetarian café and seasonal bowl", "Food", "Arts Quarter", 12, 1.0),
        ("Street-food tasting walk", "Food", "Old Town", 10, 1.2),
        ("Casual regional cuisine spot", "Food", "Central District", 16, 1.0),
    ],
    "Leisure": [
        ("Relax in a city park", "Relaxed", "Garden District", 0, 1.5),
        ("Browse independent shops", "Urban", "Market Quarter", 15, 1.5),
        ("Easy scenic trail or promenade", "Adventure", "Waterfront", 5, 2.0),
        ("Coffee break at a local café", "Food", "Arts Quarter", 8, 1.0),
        ("Hands-on local craft workshop", "Cultural", "Arts Quarter", 28, 2.0),
        ("Beach or lakeside downtime", "Beach", "Waterfront", 0, 2.0),
    ],
    "Dinner": [
        ("Regional dinner with local specialties", "Food", "Old Town", 24, 1.5),
        ("Sunset dining with a view", "Relaxed", "Waterfront", 32, 1.5),
        ("Lively food hall and evening stroll", "Nightlife", "Market Quarter", 20, 2.0),
        ("Live music venue (cover estimate)", "Nightlife", "Arts Quarter", 30, 2.0),
        ("Chef-led tasting menu", "Food", "Central District", 65, 2.0),
    ],
    "Adventure": [
        ("Guided outdoor adventure session", "Adventure", "Outskirts", 38, 3.0),
        ("Scenic hike with a local guide", "Adventure", "Outskirts", 25, 3.0),
        ("Kayak or water activity", "Beach", "Waterfront", 35, 2.0),
    ],
    "History": [
        ("Museum visit with audio guide", "History", "Museum Quarter", 16, 2.0),
        ("Architecture and history walking tour", "History", "Old Town", 24, 2.0),
    ],
}
SLOT_TIMES = [
    ("09:00", "Morning sightseeing", "Sightseeing"),
    ("12:30", "Lunch recommendation", "Lunch"),
    ("15:00", "Afternoon leisure", "Leisure"),
    ("19:00", "Evening dining & entertainment", "Dinner"),
]

st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
:root { --ink:#173b35; --leaf:#2f6b57; --mint:#eaf3ed; --sand:#f8f4eb; --coral:#d97d62; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:linear-gradient(180deg,#fbfaf6 0%,#f4f7f2 100%); color:var(--ink); }
h1,h2,h3 { color:var(--ink); font-family:'Playfair Display',serif; }
[data-testid="stSidebar"] { background:#edf4ee; border-right:1px solid #dce8dd; }
div[data-testid="stMetric"] { background:white; padding:15px 17px; border:1px solid #e3ebe3; border-radius:16px; }
div.stButton > button, div[data-testid="stFormSubmitButton"] button { border-radius:12px; border:0; background:#2f6b57; color:white; font-weight:700; min-height:2.7rem; }
div.stButton > button:hover, div[data-testid="stFormSubmitButton"] button:hover { background:#214f41; color:white; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; }
.hero { background:linear-gradient(120deg,#163f36,#367762); color:white; padding:30px 32px; border-radius:22px; margin:0 0 20px 0; }
.hero h1 { color:white; margin:0; font-size:2.45rem; }
.hero p { color:#e1eee6; margin:.45rem 0 0 0; font-size:1rem; }
.eyebrow { text-transform:uppercase; letter-spacing:.14em; font-size:.72rem; font-weight:700; color:#d9e9de; }
.tag { display:inline-block; background:#e8f2e9; color:#2b614e; border-radius:99px; padding:4px 10px; margin:3px 4px 3px 0; font-size:.78rem; font-weight:600; }
.small-muted { color:#65776e; font-size:.88rem; }
.trip-card { background:white; border:1px solid #e0e9df; padding:17px; border-radius:16px; margin-bottom:10px; }
hr { border-color:#e1e9e1; }
</style>
""", unsafe_allow_html=True)

def init_state():
    defaults = {"trip_history": [], "current_trip": None, "last_recommendations": [], "api_provider": "Demo mode"}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

def money(amount: float, currency: str) -> str:
    symbols = {"INR":"₹", "USD":"$", "EUR":"€", "GBP":"£", "JPY":"¥", "THB":"฿", "IDR":"Rp ", "AED":"AED ", "TRY":"₺", "AUD":"A$"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.0f}"

def fx_to_usd(amount: float, currency: str) -> float:
    # Rates are approximate display estimates, not live financial data.
    rates = {"INR":83.0, "USD":1.0, "EUR":0.92, "GBP":0.79, "JPY":150.0, "THB":36.0,
             "IDR":15700.0, "AED":3.67, "TRY":34.0, "AUD":1.52, "NPR":133.0, "MXN":17.2, "VND":25000.0}
    return amount / rates.get(currency, 1.0)

def destination_record(city: str) -> dict[str, Any]:
    for d in DESTINATIONS:
        if d["city"].lower() == city.lower():
            return d
    return {"city":city, "country":"Local destination", "vibes":["Urban","Cultural"], "tags":["Local discoveries","Flexible plan"], "budget":"Moderate", "season":"Check local season", "areas":["Historic Center","Central District","Waterfront"], "currency":"USD"}

def current_rate_currency(country: str) -> tuple[str, float]:
    return CURRENCY_BY_COUNTRY.get(country, ("USD", 1.0))

def season_for_month(month: int) -> str:
    if month in (12, 1, 2): return "winter"
    if month in (3, 4, 5): return "spring"
    if month in (6, 7, 8): return "summer"
    return "autumn"

def recommend_destinations(vibe: str, budget: str, travel_date: date, interests: list[str]) -> list[dict[str, Any]]:
    season = season_for_month(travel_date.month)
    scored = []
    for d in DESTINATIONS:
        score = 0
        if vibe == "Surprise me" or vibe in d["vibes"]: score += 4
        if d["budget"] == budget: score += 2
        elif budget == "Budget" and d["budget"] == "Moderate": score += 1
        score += min(3, len(set(interests) & set(d["vibes"]))) * 1.2
        # Broad seasonal heuristic; display season notes instead of claiming forecast accuracy.
        if season in ("winter", "autumn") and any(x in d["season"] for x in ("Oct", "Nov", "Dec", "Jan", "Feb")): score += 1.3
        if season == "spring" and any(x in d["season"] for x in ("Mar", "Apr", "May")): score += 1.3
        if season == "summer" and any(x in d["season"] for x in ("Jun", "Jul", "Aug")): score += 1.0
        scored.append((score, d))
    scored.sort(key=lambda x: (-x[0], x[1]["city"]))
    return [dict(d, match_score=round(score, 1)) for score, d in scored[:3]]

def choose_activity(slot_type: str, interests: list[str], vibe: str, budget: str, used_areas: set[str], rng: random.Random) -> dict[str, Any]:
    options = list(ACTIVITY_BANK.get(slot_type, ACTIVITY_BANK["Sightseeing"]))
    def score(item):
        name, category, area, cost, hours = item
        s = 3 if category in interests else 0
        if vibe.lower() in category.lower(): s += 1
        if budget == "Budget": s += 1 if cost <= 15 else -2
        elif budget == "Luxury": s += 1 if cost >= 25 else 0
        if area in used_areas: s += 0.8  # weak clustering preference: nearby area reused
        return s + rng.random() * 1.5
    chosen = max(options, key=score)
    name, category, area, cost, hours = chosen
    return {"name":name, "category":category, "area":area, "cost":float(cost), "duration_hours":hours,
            "notes": f"{area} area · estimated {hours:g} hr", "source":"Illustrative planning estimate"}

def generate_demo_itinerary(trip: dict[str, Any], only_day: int | None = None) -> dict[str, Any]:
    rng = random.Random(f'{trip["destination"]}-{trip["start_date"]}-{trip["budget"]}-{trip["interests"]}')
    dest = destination_record(trip["destination"])
    currency = trip["currency"]
    all_days = trip.get("days", [])
    if only_day is None:
        all_days = []
        day_indices = range(1, trip["duration"] + 1)
    else:
        # Replace the selected day rather than appending a duplicate.
        all_days = [d for d in all_days if d.get("day") != only_day]
        day_indices = [only_day]
    interest_list = trip["interests"] or ["Cultural", "Food"]
    for day_no in day_indices:
        used_areas: set[str] = set()
        activities = []
        for time_label, slot_label, slot_type in SLOT_TIMES:
            if slot_type == "Sightseeing" and "Adventure" in interest_list and rng.random() < 0.35:
                item = choose_activity("Adventure", interest_list, trip["vibe"], trip["budget"], used_areas, rng)
            elif slot_type == "Sightseeing" and "History" in interest_list and rng.random() < 0.45:
                item = choose_activity("History", interest_list, trip["vibe"], trip["budget"], used_areas, rng)
            else:
                item = choose_activity(slot_type, interest_list, trip["vibe"], trip["budget"], used_areas, rng)
            # Assign day-specific neighborhood clusters, minimizing cross-town jumps by reusing areas.
            if not used_areas:
                preferred = dest.get("areas", ["Central District"])[(day_no - 1) % len(dest.get("areas", ["Central District"]))]
                if item["area"] not in used_areas:
                    item["cluster"] = preferred
            else:
                item["cluster"] = sorted(used_areas)[0]
            used_areas.add(item["area"])
            activities.append({"time":time_label, "slot":slot_label, **item})
        all_days.append({"day":day_no, "date":(trip["start_date"] + timedelta(days=day_no-1)).isoformat(),
                         "theme": f'{dest["city"]}: {["Discover","Explore","Unwind","Go deeper","Local favorites"][((day_no-1)%5)]}',
                         "cluster": ", ".join(dest.get("areas", ["Central District"])[:2]),
                         "activities":activities})
    all_days.sort(key=lambda x: x["day"])
    trip["days"] = all_days
    trip["itinerary_mode"] = "Demo itinerary"
    return trip

def build_ai_prompt(trip: dict[str, Any]) -> str:
    return f"""You are a practical travel planner. Return ONLY valid JSON, no markdown.
Create a realistic, cautious {trip['duration']}-day itinerary for {trip['destination']}.
Dates: {trip['start_date']} onward. Budget: {trip['budget']}. Party: {trip['party']}.
Pace: {trip['pace']}. Vibe: {trip['vibe']}. Interests: {', '.join(trip['interests'])}.
Currency: {trip['currency']}. Each day must have exactly four activities at 09:00, 12:30, 15:00, 19:00.
Group nearby places into the same day and avoid backtracking. Don't claim live availability, exact routing, or verified prices.
Output schema:
{{"days":[{{"day":1,"date":"YYYY-MM-DD","theme":"...","cluster":"neighborhood/area","activities":[
{{"time":"09:00","slot":"Morning sightseeing","name":"...","category":"...","area":"...","cost":12,"duration_hours":2,"notes":"..."}},
{{"time":"12:30","slot":"Lunch recommendation","name":"...","category":"Food","area":"...","cost":15,"duration_hours":1,"notes":"..."}},
{{"time":"15:00","slot":"Afternoon leisure","name":"...","category":"...","area":"...","cost":5,"duration_hours":1.5,"notes":"..."}},
{{"time":"19:00","slot":"Evening dining & entertainment","name":"...","category":"...","area":"...","cost":25,"duration_hours":1.5,"notes":"..."}}
]}}]}}"""

def call_ai(trip: dict[str, Any], provider: str, api_key: str, only_day: int | None = None) -> dict[str, Any]:
    prompt = build_ai_prompt(trip)
    if only_day is not None:
        prompt += f"\nReturn only day {only_day} in the same schema."
    if provider == "Gemini":
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        raw = response.text or ""
    elif provider == "Groq":
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":"Return valid JSON only."},{"role":"user","content":prompt}],
            temperature=0.5,
        )
        raw = response.choices[0].message.content or ""
    else:
        raise ValueError("Choose Gemini, Groq, or Demo mode.")
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    data = json.loads(raw)
    days = data.get("days", [])
    if only_day is not None:
        if not days: raise ValueError("AI returned no itinerary day.")
        new_day = days[0]
        new_day["day"] = only_day
        existing = [d for d in trip.get("days", []) if d["day"] != only_day]
        existing.append(new_day)
        trip["days"] = sorted(existing, key=lambda d:d["day"])
    else:
        trip["days"] = days
    trip["itinerary_mode"] = f"{provider} generated"
    return trip

def generate_trip(trip: dict[str, Any], provider: str, api_key: str, only_day: int | None = None) -> dict[str, Any]:
    if provider == "Demo mode" or not api_key:
        return generate_demo_itinerary(trip, only_day)
    try:
        return call_ai(trip, provider, api_key, only_day)
    except Exception as exc:
        st.warning(f"AI generation was unavailable ({type(exc).__name__}). Using demo mode for this request.")
        return generate_demo_itinerary(trip, only_day)

def total_cost(trip: dict[str, Any]) -> float:
    return sum(float(a.get("cost", 0) or 0) for day in trip.get("days", []) for a in day.get("activities", []))

def export_pdf(trip: dict[str, Any]) -> bytes:
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, rightMargin=17*mm, leftMargin=17*mm, topMargin=17*mm, bottomMargin=17*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=colors.HexColor("#214f41"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Sub", parent=styles["Normal"], fontSize=10, leading=15, textColor=colors.HexColor("#5b6f65"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="DayHead", parent=styles["Heading2"], textColor=colors.HexColor("#214f41"), spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8.5, leading=11))
    story = [
        Spacer(1, 22*mm), Paragraph("YOUR JOURNEY, THOUGHTFULLY PLANNED", styles["Sub"]), Spacer(1, 6*mm),
        Paragraph(trip["destination"], styles["CoverTitle"]),
        Paragraph(f'{trip["duration"]} days · {trip["start_date"].strftime("%d %b %Y")} · {trip["budget"]} budget', styles["Sub"]),
        Spacer(1, 8*mm),
        Paragraph(f'<b>Travel style:</b> {trip["vibe"]} · {trip["party"]} · {trip["pace"]}', styles["Normal"]),
        Paragraph(f'<b>Interests:</b> {", ".join(trip["interests"]) or "Open to suggestions"}', styles["Normal"]),
        Paragraph(f'<b>Estimated activity total:</b> {money(total_cost(trip), trip["currency"])} (approx. ${fx_to_usd(total_cost(trip), trip["currency"]):,.0f} USD)', styles["Normal"]),
        Spacer(1, 7*mm),
        Paragraph("Planning note: prices, schedules and recommendations are estimates. Verify opening hours, transit, local guidance and reservations before travel.", styles["Small"]),
        PageBreak()
    ]
    running = 0.0
    for day in trip.get("days", []):
        story.append(Paragraph(f'Day {day["day"]} — {day.get("theme","Explore")}', styles["DayHead"]))
        story.append(Paragraph(f'{day.get("date","")} · Suggested area cluster: {day.get("cluster","")}', styles["Small"]))
        rows = [["Time", "Plan", "Area", f"Est. ({trip['currency']})"]]
        for act in day.get("activities", []):
            cost = float(act.get("cost",0) or 0); running += cost
            rows.append([act.get("time",""), f'{act.get("slot","")}<br/><b>{act.get("name","")}</b><br/>{act.get("notes","")}', act.get("area", ""), money(cost, trip["currency"])])
        table = Table(rows, colWidths=[19*mm, 91*mm, 36*mm, 27*mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#214f41")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
            ("LEADING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#dce7de")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f7f2")]),
            ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        story.extend([table, Spacer(1, 3*mm), Paragraph(f'Running activity estimate: {money(running, trip["currency"])}', styles["Small"]), Spacer(1, 4*mm)])
    story += [PageBreak(), Paragraph("Before You Go", styles["DayHead"]),
              Paragraph("Emergency & travel checklist", styles["Heading3"])]
    checklist = [
        "Save the local emergency number and your accommodation address.",
        "Share your itinerary with a trusted contact.",
        "Confirm travel insurance, medication and essential documents.",
        "Check official travel advisories and local transport updates.",
        "Keep copies of passport/ID and bookings in a secure offline location.",
        "Confirm venue opening hours, accessibility and reservation requirements.",
        "Record accommodation, local host and nearest hospital contacts.",
        "Carry a backup payment method and a small amount of local cash.",
    ]
    for item in checklist:
        story.append(Paragraph("☐ " + item, styles["Normal"])); story.append(Spacer(1, 2*mm))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Emergency contacts (fill before departure)", styles["Heading3"]))
    contact_rows = [["Contact", "Name / Number"], ["Local emergency services", "____________________________"], ["Accommodation", "____________________________"], ["Travel insurance", "____________________________"], ["Trusted contact", "____________________________"]]
    ct = Table(contact_rows, colWidths=[55*mm, 110*mm])
    ct.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e8f2e9")),("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#d5e1d7")),("PADDING",(0,0),(-1,-1),7)]))
    story.append(ct)
    doc.build(story)
    return buff.getvalue()

def safe_trip_name(trip: dict[str, Any]) -> str:
    return f'{trip["destination"]} · {trip["start_date"].strftime("%d %b %Y")}'

def render_activity(activity: dict[str, Any], currency: str):
    with st.container(border=True):
        c1, c2 = st.columns([4,1])
        c1.markdown(f'**{activity.get("time","")} · {activity.get("slot","")}**')
        c1.markdown(f'### {activity.get("name","Activity")}')
        c1.caption(f'{activity.get("area","")} · {activity.get("duration_hours",1)} hr · {activity.get("notes","")}')
        c2.metric("Estimate", money(float(activity.get("cost",0) or 0), currency))
        c2.caption(f'≈ ${fx_to_usd(float(activity.get("cost",0) or 0), currency):,.0f} USD')

# Sidebar configuration
with st.sidebar:
    st.markdown("## 🧭 Trip Studio")
    st.caption("Skill Wallet · Capstone Project 4")
    provider = st.selectbox("AI provider", ["Demo mode", "Gemini", "Groq"], help="Demo mode works without credentials.")
    api_key = ""
    if provider != "Demo mode":
        api_key = st.text_input(f"{provider} API key", type="password", help="Used only for this session; do not commit it to Git.")
        st.caption("For deployment, configure secrets in Streamlit Community Cloud.")
    st.session_state.api_provider = provider
    st.divider()
    st.markdown("**Your trip preferences**")
    with st.form("trip_preferences"):
        destination_input = st.text_input("Destination (optional)", placeholder="e.g. Kyoto, Goa, Lisbon")
        vibe = st.selectbox("Travel mood / vibe", ["Beach", "Mountains", "Cultural", "Urban", "Surprise me"])
        duration = st.slider("Trip duration (days)", 1, 14, 3)
        start_date = st.date_input("Start date", value=date.today() + timedelta(days=14), min_value=date.today())
        budget = st.select_slider("Budget level", options=["Budget", "Moderate", "Luxury"], value="Moderate")
        party = st.selectbox("Travel party", ["Solo", "Couple", "Family", "Friends"])
        pace = st.select_slider("Pace", options=["Relaxed", "Moderate", "Fast-Paced"], value="Moderate")
        interests = st.multiselect("Interests", ["Food", "Adventure", "History", "Nightlife", "Nature", "Shopping", "Art & culture", "Wellness"], default=["Food","History"])
        submitted = st.form_submit_button("✨ Create my trip", use_container_width=True)
    st.caption("Demo costs are illustrative, not live quotes. Currency conversion is approximate.")

if "start_date" not in st.session_state:
    st.session_state.start_date = date.today() + timedelta(days=14)

# Header
st.markdown(f"""
<div class="hero">
  <div class="eyebrow">Wander well · Travel better</div>
  <h1>Personalized Travel Itinerary Planner</h1>
  <p>Less scrolling. More discovering. A thoughtful trip plan shaped around your budget, pace and kind of adventure.</p>
</div>
""", unsafe_allow_html=True)

if submitted:
    chosen_destination = destination_input.strip()
    if not chosen_destination:
        recs = recommend_destinations(vibe, budget, start_date, interests)
        chosen_destination = recs[0]["city"]
        st.session_state.last_recommendations = recs
    record = destination_record(chosen_destination)
    currency, _ = current_rate_currency(record["country"])
    if record.get("currency"): currency = record["currency"]
    # Convert UI interests into recommendation taxonomy.
    mapped = list(interests)
    if "Art & culture" in mapped: mapped.append("Cultural")
    if "Nature" in mapped: mapped.extend(["Mountains","Beach","Adventure"])
    trip = {
        "id": f'{chosen_destination.lower().replace(" ","-")}-{start_date.isoformat()}',
        "destination": chosen_destination, "vibe":vibe, "duration":duration, "start_date":start_date,
        "budget":budget, "party":party, "pace":pace, "interests":mapped, "currency":currency,
        "created_at":date.today().isoformat(), "days":[]
    }
    with st.spinner("Designing your trip…"):
        trip = generate_trip(trip, provider, api_key)
    st.session_state.current_trip = trip
    st.session_state.trip_history.insert(0, trip.copy())
    st.success(f"Your {duration}-day plan for {chosen_destination} is ready.")

trip = st.session_state.current_trip
tabs = st.tabs(["🌍 Destination Recommender", "🗓️ Day-by-Day Itinerary", "✨ Customize & Swap", "🧳 Saved Trips & PDF"])

with tabs[0]:
    st.subheader("Find a destination that feels like you")
    st.write("No fixed destination? Match a travel mood with a budget and broad seasonal preferences.")
    col1, col2, col3 = st.columns(3)
    with col1:
        rec_vibe = st.selectbox("Mood", ["Surprise me","Beach","Mountains","Cultural","Urban"], key="rec_vibe")
    with col2:
        rec_budget = st.selectbox("Budget", ["Budget","Moderate","Luxury"], index=1, key="rec_budget")
    with col3:
        rec_date = st.date_input("Approximate travel date", value=date.today()+timedelta(days=30), min_value=date.today(), key="rec_date")
    rec_interests = st.multiselect("What would you love?", ["Food","Adventure","History","Nightlife","Relaxed","Cultural"], default=["Food","Cultural"], key="rec_interests")
    if st.button("Find my top 3 destinations", key="recommend"):
        st.session_state.last_recommendations = recommend_destinations(rec_vibe, rec_budget, rec_date, rec_interests)
    recs = st.session_state.last_recommendations
    if recs:
        cols = st.columns(3)
        for col, d in zip(cols, recs):
            with col:
                st.markdown('<div class="trip-card">', unsafe_allow_html=True)
                st.markdown(f"### {d['city']}, {d['country']}")
                st.markdown("".join(f'<span class="tag">{t}</span>' for t in d["tags"]), unsafe_allow_html=True)
                st.write(f"**Best-season note:** {d['season']}")
                st.write(f"**Budget fit:** {d['budget']}")
                st.caption(f"Preference match score: {d['match_score']}/10 (heuristic)")
                if st.button(f"Plan {d['city']} →", key=f'plan_{d["city"]}'):
                    st.session_state["prefill_destination"] = d["city"]
                    st.info(f'Select “{d["city"]}” in the Destination field in the sidebar and press Create my trip.')
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Choose your mood and select **Find my top 3 destinations** to see personalized matches.")
    st.caption("Season notes are broad planning guidance, not a live weather forecast. Check a forecast closer to departure.")

with tabs[1]:
    st.subheader("Your day-by-day plan")
    if not trip:
        st.info("Create a trip using the form in the sidebar to see your itinerary here.")
    else:
        total = total_cost(trip)
        activity_count = sum(len(d.get("activities",[])) for d in trip.get("days",[]))
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Destination", trip["destination"])
        m2.metric("Duration", f'{trip["duration"]} days')
        m3.metric("Activity estimates", money(total, trip["currency"]))
        m4.metric("Approx. USD", f'${fx_to_usd(total,trip["currency"]):,.0f}')
        st.caption(f'{trip.get("itinerary_mode","Demo itinerary")} · {activity_count} planned slots · Activity estimates only; exclude flights, accommodation and some transport.')
        running = 0.0
        for day in trip.get("days", []):
            with st.expander(f'Day {day["day"]} · {day.get("date","")} — {day.get("theme","Explore")}', expanded=(day["day"]==1)):
                st.caption(f'Area cluster: {day.get("cluster","")} · Sequence is designed to reduce unnecessary travel; verify routes with a maps app.')
                for activity in sorted(day.get("activities",[]), key=lambda a:a.get("time","")):
                    render_activity(activity, trip["currency"])
                    running += float(activity.get("cost",0) or 0)
                st.markdown(f"**Cumulative activity estimate through Day {day['day']}: {money(running, trip['currency'])}**")
        st.progress(min(total / max({"Budget":120,"Moderate":250,"Luxury":500}.__getitem__(trip["budget"])*trip["duration"], 1), 1.0), text="Indicative activity budget usage (rough guide)")

with tabs[2]:
    st.subheader("Make the plan feel more like you")
    if not trip:
        st.info("Create a trip first to customize activities.")
    else:
        day_options = [d["day"] for d in trip.get("days",[])]
        if day_options:
            selected_day = st.selectbox("Choose a day", day_options, format_func=lambda d:f"Day {d}")
            selected_day_obj = next(d for d in trip["days"] if d["day"] == selected_day)
            act_options = list(range(len(selected_day_obj.get("activities",[]))))
            selected_idx = st.selectbox("Activity slot", act_options, format_func=lambda i:f'{selected_day_obj["activities"][i].get("time","")} · {selected_day_obj["activities"][i].get("slot","")}')
            selected_activity = selected_day_obj["activities"][selected_idx]
            st.markdown(f"**Current activity:** {selected_activity['name']}")
            st.caption(f'{selected_activity.get("area","")} · {money(float(selected_activity.get("cost",0) or 0),trip["currency"])}')
            request = st.text_input("What would you prefer instead?", placeholder="e.g. Swap museum for outdoor market")
            swap_type = st.selectbox("Quick swap", ["Keep current slot type","Vegetarian lunch spot","Outdoor market","More affordable option","More nature","More history","Less walking"])
            c1,c2 = st.columns(2)
            with c1:
                if st.button("🔄 Swap this activity", use_container_width=True):
                    old = selected_activity
                    request_lower = (request + " " + swap_type).lower()
                    if "vegetarian" in request_lower or "lunch" in request_lower:
                        new = {"name":"Vegetarian café with local seasonal dishes","category":"Food","area":old.get("area","Central District"),"cost":12.0,"duration_hours":1.0,"notes":"Vegetarian-friendly suggestion; verify menu and opening hours","source":"Demo swap"}
                    elif "market" in request_lower or "outdoor" in request_lower:
                        new = {"name":"Browse an outdoor market and local stalls","category":"Cultural","area":old.get("area","Market Quarter"),"cost":8.0,"duration_hours":1.5,"notes":"Market schedule varies by day and season","source":"Demo swap"}
                    elif "affordable" in request_lower or "budget" in request_lower:
                        new = {"name":"Self-guided neighborhood walk","category":"Relaxed","area":old.get("area","Old Town"),"cost":0.0,"duration_hours":1.0,"notes":"Low-cost flexible alternative","source":"Demo swap"}
                    elif "nature" in request_lower:
                        new = {"name":"Botanical garden or scenic greenway","category":"Nature","area":old.get("area","Garden District"),"cost":6.0,"duration_hours":1.5,"notes":"Check local weather and opening times","source":"Demo swap"}
                    elif "history" in request_lower:
                        new = {"name":"Local heritage walk with a guide","category":"History","area":old.get("area","Old Town"),"cost":18.0,"duration_hours":2.0,"notes":"Confirm tour schedule before visiting","source":"Demo swap"}
                    elif request.strip():
                        new = {"name":request.strip(),"category":"Custom","area":old.get("area","Central District"),"cost":float(old.get("cost",0)),"duration_hours":float(old.get("duration_hours",1)),"notes":"User-requested activity; verify location, price and availability","source":"User edit"}
                    else:
                        new = {"name":"Discover a local independent café","category":"Food","area":old.get("area","Arts Quarter"),"cost":10.0,"duration_hours":1.0,"notes":"Flexible replacement suggestion","source":"Demo swap"}
                    selected_day_obj["activities"][selected_idx] = {**old, **new}
                    st.session_state.current_trip = trip
                    st.success("Activity updated. Other days remain unchanged.")
                    st.rerun()
            with c2:
                if st.button("✨ Regenerate this day", use_container_width=True):
                    with st.spinner("Refreshing this day only…"):
                        updated = generate_trip(trip, provider, api_key, only_day=selected_day)
                    st.session_state.current_trip = updated
                    # Update history's latest snapshot.
                    if st.session_state.trip_history:
                        st.session_state.trip_history[0] = updated.copy()
                    st.success(f"Day {selected_day} regenerated. The rest of the itinerary was preserved.")
                    st.rerun()
            st.divider()
            st.markdown("**Current day at a glance**")
            for a in selected_day_obj["activities"]:
                st.write(f'• {a.get("time","")} — {a.get("name","")} ({money(float(a.get("cost",0) or 0),trip["currency"])})')
        else:
            st.warning("No days exist yet. Generate a trip first.")

with tabs[3]:
    st.subheader("Saved trips & offline guide")
    st.write("Trips are saved in the current Streamlit session. This is simulated persistence: history clears when the session resets or the app restarts.")
    if trip:
        left,right = st.columns([3,1])
        with left:
            st.markdown(f"### {safe_trip_name(trip)}")
            st.caption(f'{trip["duration"]} days · {trip["budget"]} · {trip["party"]} · {trip.get("itinerary_mode","Demo")}')
            st.write(f'Estimated activity costs: **{money(total_cost(trip), trip["currency"])}** (≈ ${fx_to_usd(total_cost(trip),trip["currency"]):,.0f} USD)')
        with right:
            pdf_bytes = export_pdf(trip)
            st.download_button("⬇️ Download itinerary PDF", data=pdf_bytes, file_name=f'{trip["destination"].lower().replace(" ","-")}-itinerary.pdf', mime="application/pdf", use_container_width=True)
        if st.button("💾 Save another snapshot", use_container_width=False):
            st.session_state.trip_history.insert(0, trip.copy())
            st.success("Trip snapshot saved to session history.")
    else:
        st.info("Create a trip to export an itinerary PDF or save it to session history.")
    st.divider()
    st.markdown("### Trip history")
    history = st.session_state.trip_history
    if not history:
        st.caption("No trips saved in this session yet.")
    else:
        for idx, saved in enumerate(history):
            with st.container(border=True):
                c1,c2,c3 = st.columns([4,2,1])
                c1.markdown(f'**{safe_trip_name(saved)}**')
                c1.caption(f'{saved["duration"]} days · {saved["budget"]} · {saved.get("itinerary_mode","Demo")}')
                c2.write(money(total_cost(saved), saved["currency"]))
                if c3.button("Load", key=f"load_{idx}"):
                    st.session_state.current_trip = saved.copy()
                    st.rerun()
        if st.button("Clear session trip history"):
            st.session_state.trip_history = []
            st.success("Session history cleared.")

st.markdown("---")
st.caption("Personalized Travel Itinerary Planner · Skill Wallet Capstone Project 4 · Built with Streamlit, Python and ReportLab")
