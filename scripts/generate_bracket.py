#!/usr/bin/env python3
"""
Vava Bot4Bots Cup — Bracket & Match Generator
Generates single-elimination brackets and match schedules.
Run: python scripts/generate_bracket.py
"""
import json
import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

TEAMS_FILE = DATA_DIR / "teams.json"
MATCHES_FILE = DATA_DIR / "matches.json"
RESULTS_FILE = DATA_DIR / "results.json"


def load_teams():
    with open(TEAMS_FILE) as f:
        return json.load(f)


def save_matches(matches):
    with open(MATCHES_FILE, "w") as f:
        json.dump(matches, f, indent=2)


def generate_bracket(start_date=None):
    """
    Generate a single-elimination bracket from the teams.
    Seeding: Team 1 vs Team 8, Team 2 vs Team 7, etc.
    """
    data = load_teams()
    teams = data["teams"]

    if len(teams) < 4:
        print("[!] Need at least 4 teams for a bracket.")
        return None

    # Sort teams by seed
    teams_sorted = sorted(teams, key=lambda t: t["seed"])

    num_teams = len(teams_sorted)
    round_names = {
        8: ["Quarterfinal", "Semifinal", "Grand Final"],
        4: ["Semifinal", "Grand Final"],
        2: ["Grand Final"],
    }

    # Default to 8-team bracket, pad with virtual BYEs if fewer
    while len(teams_sorted) < 8:
        teams_sorted.append({"id": f"bye_{len(teams_sorted)+1}", "name": "BYE", "seed": len(teams_sorted)+1})

    # Standard bracket: 1v8, 4v5 on top half, 2v7, 3v6 on bottom half
    pairing_order = [
        (0, 7),  # 1v8
        (3, 4),  # 4v5
        (1, 6),  # 2v7
        (2, 5),  # 3v6
    ]

    if not start_date:
        start_date = datetime.date.today() + datetime.timedelta(days=14)

    sat = start_date
    while sat.weekday() != 5:  # next Saturday
        sat += datetime.timedelta(days=1)

    sun = sat + datetime.timedelta(days=1)
    next_sat = sat + datetime.timedelta(days=7)
    next_sun = sun + datetime.timedelta(days=7)

    # Quarterfinals: Saturday + Sunday of Week 1
    qf_slots = [
        sat,
        sat,
        sun,
        sun,
    ]

    # Semifinals: Saturday of Week 2
    sf_slots = [next_sat, next_sat]

    # Grand Final + 3rd Place: Sunday of Week 2
    final_slots = [next_sun, next_sun]

    matches = []
    match_id = 1

    # Quarterfinals
    for i, (t1_idx, t2_idx) in enumerate(pairing_order[:4]):
        team1 = teams_sorted[t1_idx]
        team2 = teams_sorted[t2_idx]
        is_bye = team1["name"] == "BYE" or team2["name"] == "BYE"

        match = {
            "id": match_id,
            "round": "Quarterfinal",
            "team1": {"id": team1["id"], "name": team1["name"]},
            "team2": {"id": team2["id"], "name": team2["name"]},
            "scheduled_date": qf_slots[i].isoformat(),
            "scheduled_time": "18:00",
            "status": "bye" if is_bye else "scheduled",
            "winner_id": team1["id"] if team2["name"] == "BYE" else (team2["id"] if team1["name"] == "BYE" else None),
            "score": None,
        }
        matches.append(match)
        match_id += 1

    # Semifinals (placeholders for winners of QF 1v4 and QF 2v3)
    matches.append({
        "id": match_id,
        "round": "Semifinal",
        "team1": {"id": "winner_of_1", "name": "Winner QF 1"},
        "team2": {"id": "winner_of_4", "name": "Winner QF 4"},
        "scheduled_date": sf_slots[0].isoformat(),
        "scheduled_time": "18:00",
        "status": "pending",
        "winner_id": None,
        "score": None,
    })
    match_id += 1

    matches.append({
        "id": match_id,
        "round": "Semifinal",
        "team1": {"id": "winner_of_2", "name": "Winner QF 2"},
        "team2": {"id": "winner_of_3", "name": "Winner QF 3"},
        "scheduled_date": sf_slots[1].isoformat(),
        "scheduled_time": "18:00",
        "status": "pending",
        "winner_id": None,
        "score": None,
    })
    match_id += 1

    # Grand Final
    matches.append({
        "id": match_id,
        "round": "Grand Final",
        "team1": {"id": "winner_of_5", "name": "Winner SF 1"},
        "team2": {"id": "winner_of_6", "name": "Winner SF 2"},
        "scheduled_date": final_slots[0].isoformat(),
        "scheduled_time": "18:00",
        "status": "pending",
        "winner_id": None,
        "score": None,
    })
    match_id += 1

    # 3rd Place Match
    matches.append({
        "id": match_id,
        "round": "3rd Place",
        "team1": {"id": "loser_of_5", "name": "Loser SF 1"},
        "team2": {"id": "loser_of_6", "name": "Loser SF 2"},
        "scheduled_date": final_slots[1].isoformat(),
        "scheduled_time": "16:00",
        "status": "pending",
        "winner_id": None,
        "score": None,
    })

    # Remove BYE matches that auto-advance
    # For each BYE match, advance the non-BYE team to the next stage
    result = {
        "matches": matches,
        "generated_at": datetime.datetime.now().isoformat(),
        "start_date": start_date.isoformat(),
        "format": "single_elimination",
        "num_teams": num_teams,
    }

    save_matches(result)

    return matches


def print_bracket(matches):
    print("\n" + "=" * 70)
    print("  VAVA BOT4BOTS CUP — TOURNAMENT BRACKET")
    print("=" * 70)

    rounds = {}
    for m in matches:
        r = m["round"]
        if r not in rounds:
            rounds[r] = []
        rounds[r].append(m)

    for round_name, round_matches in rounds.items():
        print(f"\n  ▸ {round_name.upper()}")
        print(f"  {'─' * 50}")
        for m in round_matches:
            status_map = {"scheduled": "⏳", "in_progress": "🔴 LIVE", "completed": "✅", "pending": "⏸️", "bye": "↪️ BYE"}
            status_icon = status_map.get(m["status"], "❓")
            score = f" ({m['score'][0]}-{m['score'][1]})" if m.get("score") else ""
            print(f"  Match #{m['id']}  {status_icon}")
            print(f"    {m['team1']['name']}  vs  {m['team2']['name']}{score}")
            print(f"    {m['scheduled_date']} @ {m.get('scheduled_time', 'TBD')}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    if not TEAMS_FILE.exists():
        print("[!] No teams.json found. Run organize_teams.py first.")
        sys.exit(1)

    start_date = None
    if len(sys.argv) > 1:
        start_date = datetime.date.fromisoformat(sys.argv[1])

    matches = generate_bracket(start_date=start_date)
    if matches:
        print_bracket(matches)
        print(f"\n[+] Bracket saved to {MATCHES_FILE}")
