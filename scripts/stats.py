#!/usr/bin/env python3
"""
Vava Bot4Bots Cup — Stats Engine
Calculates standings, win/loss records, and player statistics.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

TEAMS_FILE = DATA_DIR / "teams.json"
MATCHES_FILE = DATA_DIR / "matches.json"
RESULTS_FILE = DATA_DIR / "results.json"
STATS_FILE = DATA_DIR / "stats.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def compute_standings():
    """Compute team standings based on match results."""
    if not TEAMS_FILE.exists():
        return None

    teams_data = load_json(TEAMS_FILE)
    teams = {t["id"]: {"name": t["name"], "seed": t["seed"], "wins": 0, "losses": 0, "maps_won": 0, "maps_lost": 0}
             for t in teams_data["teams"]}

    if not MATCHES_FILE.exists():
        return list(teams.values())

    matches_data = load_json(MATCHES_FILE)
    matches = matches_data.get("matches", [])

    for m in matches:
        if m["status"] != "completed" or not m.get("score"):
            continue

        t1_id = m["team1"]["id"]
        t2_id = m["team2"]["id"]
        score = m["score"]

        if not isinstance(score, list) or len(score) != 2:
            continue

        t1_maps, t2_maps = score[0], score[1]

        if t1_id in teams:
            teams[t1_id]["maps_won"] += t1_maps
            teams[t1_id]["maps_lost"] += t2_maps
            if t1_maps > t2_maps:
                teams[t1_id]["wins"] += 1
            else:
                teams[t1_id]["losses"] += 1

        if t2_id in teams:
            teams[t2_id]["maps_won"] += t2_maps
            teams[t2_id]["maps_lost"] += t1_maps
            if t2_maps > t1_maps:
                teams[t2_id]["wins"] += 1
            else:
                teams[t2_id]["losses"] += 1

    standings = sorted(teams.values(), key=lambda t: (-t["wins"], t["losses"]))
    return standings


def format_standings(standings):
    if not standings:
        return "No standings available yet."

    lines = [
        "```",
        "  POS  TEAM                         W  L   MAPS",
        "  ─────────────────────────────────────────────────",
    ]
    for i, t in enumerate(standings, 1):
        maps_str = f"{t['maps_won']}-{t['maps_lost']}"
        lines.append(f"  {i:>3}. {t['name']:<28} {t['wins']:>2} {t['losses']:>2}  {maps_str:>5}")
    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    standings = compute_standings()
    print(format_standings(standings))
