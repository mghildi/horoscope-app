import os
import json
import re
import pandas as pd
import streamlit as st
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("DEEPINFRA_API_KEY")
DATA_DIR = "public"  # Folder with leaderboard-*.json

# UI Setup
st.set_page_config(page_title="Cricket Horoscope Leaderboard", layout="centered")
st.title("🌟 Horoscope Leaderboard by Match 🌟")

# Step 1: List available files
files = [f for f in os.listdir(DATA_DIR) if f.startswith("leaderboard-") and f.endswith(".json")]
if not files:
    st.error("No leaderboard files found in /public folder.")
    st.stop()

# Step 2: Create dropdown to select match
match_options = []
match_id_to_file = {}

for file in files:
    match_id = file.split("-")[1].replace(".json", "")
    with open(os.path.join(DATA_DIR, file), "r", encoding="utf-8") as f:
        data = json.load(f)
        if data:
            teams = f"{data[0]['Team']} vs {next((x['Team'] for x in data if x['Team'] != data[0]['Team']), '')}"
            label = f"{teams} ({match_id})"
            match_options.append(label)
            match_id_to_file[label] = file

selected = st.selectbox("Select a match to view", match_options)

# Step 3: Load selected match's data
with open(os.path.join(DATA_DIR, match_id_to_file[selected]), "r", encoding="utf-8") as f:
    df = pd.DataFrame(json.load(f))

# Step 4: Call DeepInfra to rank zodiac signs
if not API_KEY:
    st.error("Please set DEEPINFRA_API_KEY in your environment.")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
CHAT_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
SYSTEM_PROMPT = (
    "You are a JSON generator. Always respond with exactly one JSON object matching the asked schema. No extra text."
)

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

def parse_first_json(text: str):
    cleaned = text.strip().replace("Infinity", "null")
    if cleaned.startswith('```') and cleaned.endswith('```'):
        cleaned = cleaned.strip('`')
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in: {cleaned}")
    return json.loads(match.group(0))

# Step 5: Rank zodiac signs
zodiac_map = dict(zip(df['Player'], df['Zodiac']))
unique_signs = sorted(set(zodiac_map.values()))

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

# Step 6: Assign prediction scale and display sorted leaderboard
df["PredictionScale"] = df["Zodiac"].map(rating_map).fillna(0).astype(int)
res_sorted = df.sort_values("PredictionScale", ascending=False, na_position="last")

st.subheader(f"🏏 Horoscope Leaderboard: {selected}")
st.table(res_sorted)
