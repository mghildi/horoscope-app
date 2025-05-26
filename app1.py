import os
import json
import re
import requests
from datetime import datetime, date
from dotenv import load_dotenv, find_dotenv

# — Load credentials from .env —
# Load credentials from .env if it exists (locally), otherwise rely on GitHub Secrets
env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)
else:
    print("⚠️  .env file not found — assuming GitHub Actions environment variables are already set.")


RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
if not RAPIDAPI_KEY:
    raise RuntimeError("Please set RAPIDAPI_KEY in your .env")
if not DEEPINFRA_API_KEY:
    raise RuntimeError("Please set DEEPINFRA_API_KEY in your .env")

HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key": RAPIDAPI_KEY
}

ZODIAC_DATES = [
    ((1, 20), (2, 18), 'Aquarius'),
    ((2, 19), (3, 20), 'Pisces'),
    ((3, 21), (4, 19), 'Aries'),
    ((4, 20), (5, 20), 'Taurus'),
    ((5, 21), (6, 20), 'Gemini'),
    ((6, 21), (7, 22), 'Cancer'),
    ((7, 23), (8, 22), 'Leo'),
    ((8, 23), (9, 22), 'Virgo'),
    ((9, 23), (10, 22), 'Libra'),
    ((10, 23), (11, 21), 'Scorpio'),
    ((11, 22), (12, 21), 'Sagittarius'),
    ((12, 22), (1, 19), 'Capricorn'),
]

CHAT_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
DEEP_HEADERS = {
    "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
    "Content-Type": "application/json"
}
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
    resp = requests.post(CHAT_ENDPOINT, json=payload, headers=DEEP_HEADERS)
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

def get_zodiac_sign(dt: date) -> str:
    for (m1, d1), (m2, d2), sign in ZODIAC_DATES:
        if m1 > m2:
            if dt >= date(dt.year, m1, d1) or dt <= date(dt.year, m2, d2):
                return sign
        else:
            if date(dt.year, m1, d1) <= dt <= date(dt.year, m2, d2):
                return sign
    return 'Unknown'

def fetch_type_matches(endpoint: str):
    url = f"https://{RAPIDAPI_HOST}/matches/v1/{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json().get("typeMatches", [])
    except requests.exceptions.HTTPError:
        if r.status_code == 429:
            print(f"⚠️  Rate limited on '{endpoint}' feed, skipping.")
            return []
        raise

def extract_today_matches(matches):
    out = []
    for tm in matches:
        for sm in tm.get("seriesMatches", []):
            wrap = sm.get("seriesAdWrapper") or {}
            for m in wrap.get("matches", []):
                info = m.get("matchInfo", {})
                ms = info.get("startDate")
                if not ms:
                    continue
                dt = datetime.fromtimestamp(int(ms)/1000)
                if dt.date() != date.today():
                    continue
                out.append({
                    "matchId": info["matchId"],
                    "teams": f"{info['team1']['teamName']} vs {info['team2']['teamName']}",
                    "start": dt
                })
    return out

def fetch_full_squad(match_id: int):
    url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    match_info = data.get("matchInfo", {})
    team1_info = match_info.get("team1", {})
    team2_info = match_info.get("team2", {})

    team1_name = team1_info.get("name", "Unknown")
    team2_name = team2_info.get("name", "Unknown")

    squad1 = team1_info.get("playerDetails", [])
    squad2 = team2_info.get("playerDetails", [])

    def norm(p, team_name):
        return {
            "id": p.get("id"),
            "name": p.get("name"),
            "role": (p.get("role") or "Player").lower(),
            "team": team_name
        }

    return [norm(p, team1_name) for p in squad1], [norm(p, team2_name) for p in squad2]

def fetch_player_dob(player_id: int) -> str:
    url = f"https://{RAPIDAPI_HOST}/stats/v1/player/{player_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        dob = r.json().get("DoBFormat") or r.json().get("DoB") or ""
        return dob.split("(")[0].strip()
    except requests.exceptions.RequestException:
        return ""

def main():
    recent = fetch_type_matches("recent")
    upcoming = fetch_type_matches("upcoming")
    today_matches = extract_today_matches(recent + upcoming)

    if not today_matches:
        print("❌ No matches found for today.")
        return

    
    os.makedirs("frontend/public", exist_ok=True)

    match_list = []

    for match in today_matches:
        match_id = match["matchId"]
        label = match["teams"]
        print(f"🎯 Processing: {label}")

        squadA, squadB = fetch_full_squad(match_id)
        players = squadA + squadB

        records = []
        zodiac_set = set()

        for p in players:
            if 'coach' in p['role'] or 'mentor' in p['role']:
                continue
            dob_raw = fetch_player_dob(p['id'])
            if not dob_raw:
                continue
            for fmt in ("%B %d, %Y", "%b %d, %Y"):
                try:
                    dt = datetime.strptime(dob_raw, fmt).date()
                    break
                except ValueError:
                    dt = None
            if not dt:
                continue
            dob_fmt = dt.strftime("%d/%m/%y")
            zodiac = get_zodiac_sign(dt)
            zodiac_set.add(zodiac)
            records.append({
                "Player": p['name'],
                "Team": p['team'],
                "DOB": dob_fmt,
                "Zodiac": zodiac
            })

        zodiac_list = sorted(zodiac_set)
        prompt = (
            "Rank these zodiac signs by today's career outlook descending: "
            + ", ".join(zodiac_list)
            + ". Respond JSON {\"order\":[" + ",".join(f'\"{s}\"' for s in zodiac_list) + "]}."
        )

        try:
            raw = call_deepinfra(prompt)
            parsed = parse_first_json(raw)
            ordered_signs = parsed.get("order", zodiac_list)
        except Exception as e:
            print(f"⚠️ Could not fetch DeepInfra prediction: {e}")
            ordered_signs = zodiac_list

        rating_map = {sign: 12 - idx for idx, sign in enumerate(ordered_signs)}

        for r in records:
            r["PredictionScale"] = rating_map.get(r["Zodiac"], 0)

        filename = f"frontend/public/leaderboard-{match_id}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved: {filename}")

        match_list.append({"matchId": match_id, "teams": label})

    with open("frontend/public/matches.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, indent=2)
    print("✅ Saved: frontend/public/matches.json")

if __name__ == "__main__":
    main()
