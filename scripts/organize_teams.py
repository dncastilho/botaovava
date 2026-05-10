#!/usr/bin/env python3
"""
Vava Bot4Bots Cup — Team Organization
Balanced team assignment using snake draft based on player ranks.
Run: python scripts/organize_teams.py
"""
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

PLAYERS_FILE = DATA_DIR / "players.json"
TEAMS_FILE = DATA_DIR / "teams.json"

RANK_VALUES = {
    "Iron 1": 1, "Iron 2": 2, "Iron 3": 3,
    "Bronze 1": 4, "Bronze 2": 5, "Bronze 3": 6,
    "Silver 1": 7, "Silver 2": 8, "Silver 3": 9,
    "Gold 1": 10, "Gold 2": 11, "Gold 3": 12,
    "Platinum 1": 13, "Platinum 2": 14, "Platinum 3": 15,
    "Diamond 1": 16, "Diamond 2": 17, "Diamond 3": 18,
    "Ascendant 1": 19, "Ascendant 2": 20, "Ascendant 3": 21,
    "Immortal 1": 22, "Immortal 2": 23, "Immortal 3": 24,
    "Radiant": 25,
}

TEAM_NAMES = [
    "Phoenix Rising", "Shadow Strikers", "Void Walkers",
    "Neon Blades", "Cypher's Watch", "Sage's Guard",
    "Reyna's Wrath", "Omen's Shroud", "Jett Stream",
    "Breach Force", "Killjoy Crew", "Yoru's Gate",
    "Fade Nightmare", "Astra Nova", "Deadlock Squad",
    "Gekko's Pack",
]


def load_players():
    with open(PLAYERS_FILE) as f:
        return json.load(f)


def save_teams(teams):
    with open(TEAMS_FILE, "w") as f:
        json.dump(teams, f, indent=2)


def assign_rank_value(rank):
    return RANK_VALUES.get(rank, 0)


def organize_teams(num_teams=8, shuffle_names=True):
    """
    Organize players into balanced teams using snake draft.

    Args:
        num_teams: Number of teams to form (default 8)
        shuffle_names: If True, randomize which team name goes where

    Returns:
        List of team dicts with players and metadata
    """
    players = load_players()

    if len(players) < num_teams:
        print(f"[!] Only {len(players)} players registered. Need at least {num_teams}.")
        return None

    if len(players) < num_teams * 5:
        print(f"[!] Only {len(players)} players. Need {num_teams * 5} for full teams. Will form with what we have.")
        players_per_team = len(players) // num_teams
    else:
        players_per_team = 5

    players_sorted = sorted(players, key=lambda p: assign_rank_value(p.get("rank", "")), reverse=True)

    names = TEAM_NAMES[:num_teams]
    if shuffle_names:
        random.shuffle(names)

    teams = []
    for i in range(num_teams):
        teams.append({
            "id": f"team_{i+1}",
            "name": names[i],
            "seed": i + 1,
            "players": [],
        })

    # Snake draft: round 0 forward, round 1 backward, round 2 forward, ...
    player_index = 0
    for round_num in range(players_per_team):
        if round_num % 2 == 0:
            # Forward
            for team_idx in range(num_teams):
                if player_index < len(players_sorted):
                    teams[team_idx]["players"].append(players_sorted[player_index])
                    player_index += 1
        else:
            # Backward
            for team_idx in range(num_teams - 1, -1, -1):
                if player_index < len(players_sorted):
                    teams[team_idx]["players"].append(players_sorted[player_index])
                    player_index += 1

    # Assign captains (highest rank on each team)
    for team in teams:
        if team["players"]:
            team["captain_discord_id"] = team["players"][0]["discord_id"]
            team["average_rank"] = round(
                sum(assign_rank_value(p.get("rank", "")) for p in team["players"]) / len(team["players"]), 1
            )

    # Remaining players become substitutes
    subs = players_sorted[player_index:] if player_index < len(players_sorted) else []

    save_teams({"teams": teams, "substitutes": subs, "generated_at": ""})

    return teams, subs


def print_teams(teams, subs):
    print("\n" + "=" * 60)
    print("  VAVA BOT4BOTS CUP — TEAM ROSTERS")
    print("=" * 60)

    for team in teams:
        print(f"\n  [{team['seed']}] {team['name']}")
        print(f"      Avg Rank: {team.get('average_rank', 'N/A')}  |  Captain: <@{team.get('captain_discord_id', 'N/A')}>")
        print(f"      {'─' * 40}")
        for i, p in enumerate(team["players"]):
            roles = ", ".join(p.get("roles", [])) or "any"
            print(f"      {i+1}. {p['discord_username']} — {p['rank']} — {p['riot_id']} — [{roles}]")

    if subs:
        print(f"\n  ◆ SUBSTITUTE POOL ({len(subs)}):")
        for p in subs:
            print(f"    • {p['discord_username']} ({p['rank']}) — {p['riot_id']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import datetime

    if not PLAYERS_FILE.exists():
        print("[!] No players.json found. Run the form server and collect registrations first.")
        sys.exit(1)

    players = load_players()
    print(f"[+] Loaded {len(players)} registered players.")

    num_teams = 8
    if len(sys.argv) > 1:
        num_teams = int(sys.argv[1])

    result = organize_teams(num_teams=num_teams)
    if result is None:
        sys.exit(1)

    teams, subs = result

    # Update timestamp
    teams_data = json.loads(TEAMS_FILE.read_text())
    teams_data["generated_at"] = datetime.datetime.now().isoformat()
    TEAMS_FILE.write_text(json.dumps(teams_data, indent=2))

    print_teams(teams, subs)
    print(f"\n[+] Teams saved to {TEAMS_FILE}")
