#!/usr/bin/env python3
"""
WC2026 Live Score Updater
Fetches completed match results from ESPN API and writes results.json.
Runs via GitHub Actions every 3 hours -- no API key required.
"""

import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/FIFA.World/scoreboard"
RESULTS_FILE = Path("results.json")

WC_START = datetime(2026, 6, 11)
WC_END   = datetime(2026, 7, 19)

TEAM_NAME_MAP = {
    "United States":          "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Korea Republic":         "South Korea",
    "Cape Verde":             "Cape Verde",
}


def normalize(name):
    return TEAM_NAME_MAP.get(name, name)


def fetch_matches_for_date(date_str):
    try:
        resp = requests.get(ESPN_URL, params={"dates": date_str, "limit": 50}, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Could not fetch {date_str}: {e}")
        return []

    matches = []
    for event in resp.json().get("events", []):
        comp = event["competitions"][0]
        if comp["status"]["type"]["name"] != "STATUS_FINAL":
            continue
        home = next((c for c in comp["competitors"] if c["homeAway"] == "home"), None)
        away = next((c for c in comp["competitors"] if c["homeAway"] == "away"), None)
        if not (home and away):
            continue
        matches.append({
            "key":        f"{normalize(home['team']['displayName'])} vs {normalize(away['team']['displayName'])}",
            "home_score": int(home["score"]),
            "away_score": int(away["score"]),
        })
    return matches


def main():
    existing = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else {}
    today = datetime.utcnow()
    changed = False

    for delta in range(4, -1, -1):
        date = today - timedelta(days=delta)
        if date < WC_START or date > WC_END:
            continue
        date_str = date.strftime("%Y%m%d")
        print(f"Checking {date_str}...")
        for m in fetch_matches_for_date(date_str):
            new_val = {"home": m["home_score"], "away": m["away_score"]}
            if existing.get(m["key"]) != new_val:
                print(f"  OK {m['key']} -> {m['home_score']}-{m['away_score']}")
                existing[m["key"]] = new_val
                changed = True

    if changed:
        RESULTS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
        print(f"Saved {len(existing)} result(s) to {RESULTS_FILE}")
    else:
        print("No new results.")


if __name__ == "__main__":
    main()
