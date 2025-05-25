import os
import requests
import duckdb
from datetime import datetime, date
from dotenv import load_dotenv, find_dotenv

# — Load credentials from .env —
env_path = find_dotenv()
if not env_path:
    raise RuntimeError("⚠️  .env file not found! Please create one with RAPIDAPI_KEY and RAPIDAPI_HOST.")
load_dotenv(env_path)

RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    raise RuntimeError("Please set RAPIDAPI_KEY in your .env")

HEADERS = {
    "x-rapidapi-host": RAPIDAPI_HOST,
    "x-rapidapi-key":  RAPIDAPI_KEY
}

# Zodiac sign date ranges
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


def extract_ipl(matches, only_today=True):
    out = []
    for tm in matches:
        for sm in tm.get("seriesMatches", []):
            wrap = sm.get("seriesAdWrapper") or {}
            if "INDIAN PREMIER LEAGUE" not in wrap.get("seriesName", "").upper():
                continue
            for m in wrap.get("matches", []):
                info = m.get("matchInfo", {})
                ms = info.get("startDate")
                if not ms:
                    continue
                dt = datetime.fromtimestamp(int(ms)/1000)
                if only_today and dt.date() != date.today():
                    continue
                out.append({
                    "matchId": info["matchId"],
                    "teams": f"{info['team1']['teamName']} vs {info['team2']['teamName']}",
                    "start": dt
                })
    return out

import json
def fetch_full_squad(match_id: int):
    url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()

    match_info = data.get("matchInfo", {})
    team1_info = match_info.get("team1", {})
    team2_info = match_info.get("team2", {})

    # FIXED HERE: use "name", not "teamName"
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
        r = requests.get(url, headers=HEADERS, timeout=10)
        
        r.raise_for_status()
        dob = r.json().get("DoBFormat") or r.json().get("DoB") or ""
        
        return dob.split("(")[0].strip()
    except requests.exceptions.HTTPError:
        return ""


def main():
    recent = fetch_type_matches("recent")
    upcoming = fetch_type_matches("upcoming")
    ipl = extract_ipl(recent + upcoming, only_today=True)
    if ipl:
        m = ipl[0]
        print(f"🏏 Today's IPL: {m['teams']} @ {m['start'].time()}")
    else:
        fut = extract_ipl(upcoming, only_today=False)
        if not fut:
            print("❌ No IPL fixtures found.")
            return
        m = fut[0]
        print(f"🏏 Next IPL: {m['teams']} on {m['start'].date()} @ {m['start'].time()}")

    squadA, squadB = fetch_full_squad(m['matchId'])
    players = squadA + squadB

    records = []
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
        records.append((p['name'], p['team'], dob_fmt, zodiac))

    db = 'squads.db'
    conn = duckdb.connect(db)
    conn.execute("DROP TABLE IF EXISTS players;")
    conn.execute("CREATE TABLE IF NOT EXISTS players (player TEXT, team TEXT, dob TEXT, zodiac TEXT);")
    if records:
        conn.executemany("INSERT INTO players VALUES (?, ?, ?, ?)", records)
    conn.close()
    print(f"✅ Created {db} with {len(records)} players.")

if __name__ == '__main__':
    main()
