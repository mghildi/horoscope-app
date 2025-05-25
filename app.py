# horoscope_app.py

import os
import json
import re
import duckdb
import pandas as pd
import streamlit as st
import requests
from dotenv import load_dotenv

# — Load environment variables —
load_dotenv()
API_KEY = os.getenv("DEEPINFRA_API_KEY")

# — Streamlit UI Setup —
st.set_page_config(page_title="Cricket Horoscope Leaderboard", layout="centered")
st.title("🌟 Cricket Horoscope Ratings for Today 🌟")

# — Check database —
DB_PATH = "squads.db"
if not os.path.exists(DB_PATH):
    st.error("⚠️ 'squads.db' not found. Run the data ingestion script first.")
    st.stop()

# — Load player data from DuckDB —
try:
    
    conn = duckdb.connect("squads.db")
    df = conn.execute("SELECT * FROM players").fetchdf()
except Exception as e:
    st.error(f"Error loading data from DuckDB: {e}")
    st.stop()

if df.empty:
    st.warning("No players found in database.")
    st.stop()

# — Setup API connection —
if not API_KEY:
    st.error("Please set DEEPINFRA_API_KEY in your .env or environment variables.")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
CHAT_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM_PROMPT = (
    "You are a JSON generator. Always respond with exactly one JSON object matching the asked schema. No extra text."
)

# — Helper: Call DeepInfra API to rank zodiac signs —
def call_deepinfra(prompt: str) -> str:
    payload = {
        "model": "openchat/openchat-3.6-8b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 128,
        "temperature": 0.0
    }
    resp = requests.post(CHAT_ENDPOINT, json=payload, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

# — Helper: Extract JSON from response —
def parse_first_json(text: str):
    cleaned = text.strip().replace("Infinity", "null")
    if cleaned.startswith('```') and cleaned.endswith('```'):
        cleaned = cleaned.strip('`')
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in: {cleaned}")
    return json.loads(match.group(0))

# — Build zodiac to player mapping —
zodiac_map = dict(zip(df['player'], df['zodiac']))
signs = [s for s in zodiac_map.values() if s]
unique_signs = sorted(set(signs))

# — Rank signs for today's outlook —
if unique_signs:
    prompt = (
        "Rank these zodiac signs by today's career outlook descending: "
        + ", ".join(unique_signs)
        + ". Respond JSON {\"order\":[" + ",".join(f'\"{s}\"' for s in unique_signs) + "]}."
    )
    try:
        raw = call_deepinfra(prompt)
        parsed = parse_first_json(raw)
        ordered_signs = parsed.get("order", unique_signs)
    except Exception as e:
        st.warning(f"Could not get ranking from DeepInfra: {e}")
        ordered_signs = unique_signs

    rating_map = {sign: 12 - idx for idx, sign in enumerate(ordered_signs)}
else:
    rating_map = {}

# — Build result table —
results = []
for _, row in df.iterrows():
    zodiac = row["zodiac"]
    rating = rating_map.get(zodiac)
    results.append({
        "Player": row["player"],
        "Team": row["team"],
        "Zodiac": zodiac,
        "DOB": row["dob"],
        "Rating": rating
    })

res_df = pd.DataFrame(results)
res_sorted = res_df.sort_values("Rating", ascending=False, na_position="last")

# — Display —
st.subheader("🏏 Today's Horoscope Leaderboard")
st.table(res_sorted)

# # — Optional: Download —
# st.download_button("📥 Download as CSV", data=res_sorted.to_csv(index=False), file_name="horoscope_ratings.csv")
# Save result for React app
res_sorted.to_json("leaderboard.json", orient="records")

