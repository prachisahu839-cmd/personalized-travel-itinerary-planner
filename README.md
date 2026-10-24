# Personalized Travel Itinerary Planner
**Skill Wallet Capstone Project 4**

A Streamlit travel-planning application with destination recommendations, day-by-day itinerary generation, activity swaps, session-backed trip history, and offline PDF export.

## Features
- Gemini / Groq API support, plus a no-key demo mode
- Preference form: destination, vibe, dates, duration, budget, party, pace and interests
- Top-three destination recommender using a transparent heuristic
- Four daily time slots and approximate itemized costs
- Day-only regeneration and activity swapping
- Downloadable PDF itinerary with pre-departure checklist and emergency contact fields
- No external database dependency

## Run locally
```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## API keys
Choose Demo mode to run without an API key. For Gemini or Groq, enter your key in the password field in the sidebar. The key is used only for that Streamlit session. For Streamlit Community Cloud, use **App settings → Secrets** and read keys from `st.secrets` before production deployment; never commit keys to GitHub.

Optional secrets format:
```toml
GEMINI_API_KEY = "..."
GROQ_API_KEY = "..."
```

## Important limitations
- Demo destinations, activities and prices are illustrative.
- Exchange rates are approximate display conversions, not live FX.
- Weather-season matching uses broad heuristics, not a forecast.
- Geographic grouping is heuristic and is not live geocoding, distance calculation or route optimization.
- Trip history is stored in Streamlit session state only and clears when the session resets. Add a database only if durable persistence is required.
- AI-generated details, venue status, prices and schedules must be independently verified before travel.

## Deploy to Streamlit Community Cloud
1. Push this repository to GitHub.
2. Create a new app at Streamlit Community Cloud and select `app.py`.
3. Add optional API keys in the app's Secrets settings.
4. Deploy.
