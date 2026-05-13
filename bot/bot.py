#!/usr/bin/env python3
"""
Vava Bot4Bots Cup — All-in-One Discord Bot
===========================================
Runs the entire tournament from Discord. No manual steps.
Handles: registration, team formation, bracket, scheduling, results, standings.
Optional DeepSeek integration for intelligent hype/commentary.
"""
import asyncio
import datetime
import json
import logging
import os
import random
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Optional

# --- Logging ---
LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S",
                    stream=sys.stdout, force=True)
log = logging.getLogger("vavabot")

import discord
from discord import app_commands, ui
from discord.ext import tasks

from aiohttp import web

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PLAYERS_FILE = DATA_DIR / "players.json"
TEAMS_FILE = DATA_DIR / "teams.json"
MATCHES_FILE = DATA_DIR / "matches.json"
CONFIG_FILE = DATA_DIR / "config.json"

# --- Constants ---
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

ROLES = ["Duelist", "Initiator", "Controller", "Sentinel", "Smokes", "Flex"]
RANKS = list(RANK_VALUES.keys())

COMPETITIVE_MAPS = [
    "Ascent", "Bind", "Haven", "Split", "Lotus",
    "Pearl", "Fracture", "Abyss", "Sunset",
]

# --- DeepSeek Client ---
DEEPSEEK_API_KEY = ""
DEEPSEEK_ENABLED = False
BOT_OWNER_ID = ""


def init_deepseek():
    global DEEPSEEK_API_KEY, DEEPSEEK_ENABLED, BOT_OWNER_ID
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    BOT_OWNER_ID = os.environ.get("BOT_OWNER_ID", "")
    token_file = PROJECT_ROOT / "bot" / ".env"
    if token_file.exists():
        with open(token_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    DEEPSEEK_API_KEY = line.split("=", 1)[1].strip('"').strip("'")
                elif line.startswith("BOT_OWNER_ID="):
                    BOT_OWNER_ID = line.split("=", 1)[1].strip('"').strip("'")
    DEEPSEEK_ENABLED = bool(DEEPSEEK_API_KEY)
    if DEEPSEEK_ENABLED:
        log.info("DeepSeek AI features enabled")
    if BOT_OWNER_ID:
        log.info("Bot owner set: %s", BOT_OWNER_ID)





def owner_only():
    """Decorator check: only the bot owner can use this command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not BOT_OWNER_ID:
            return True  # No owner set, allow anyone with admin
        if str(interaction.user.id) != BOT_OWNER_ID:
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)


async def deepseek_generate(prompt: str, max_tokens: int = 200) -> Optional[str]:
    """Generate text using DeepSeek API."""
    if not DEEPSEEK_ENABLED:
        return None
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.8,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning("DeepSeek API error: %s", e)
    return None


# --- JSON Helpers ---
def load_json(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            raw = f.read().strip()
            if raw:
                return json.loads(raw)
    return default if default is not None else {}


def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_config():
    cfg = load_json(CONFIG_FILE, {})
    cfg.setdefault("phase", "setup")  # setup | registration | teams | bracket | tournament | done
    cfg.setdefault("announce_channel_id", int(os.environ.get("ANNOUNCE_CHANNEL_ID", "0")))
    cfg.setdefault("num_teams", 0)
    cfg.setdefault("start_date", None)
    cfg.setdefault("registration_deadline", None)
    cfg.setdefault("tournament_started_at", None)
    return cfg


def save_config(cfg):
    save_json(CONFIG_FILE, cfg)


# --- Registration Modal ---
class RegistrationModal(ui.Modal, title="Vava Bot4Bots Cup — Registration"):
    riot_id = ui.TextInput(
        label="Riot ID (Name#TAG)",
        placeholder="PlayerName#1234",
        required=True,
        max_length=40,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Save player
        players = load_json(PLAYERS_FILE, [])
        discord_id = str(interaction.user.id)
        riot_id = self.riot_id.value.strip()

        if any(p["discord_id"] == discord_id for p in players):
            await interaction.response.send_message("You've already registered!", ephemeral=True)
            return

        if any(p["riot_id"].lower() == riot_id.lower() for p in players):
            await interaction.response.send_message("This Riot ID is already registered.", ephemeral=True)
            return

        players.append({
            "discord_id": discord_id,
            "discord_username": str(interaction.user),
            "discord_display": interaction.user.display_name,
            "riot_id": riot_id,
            "rank": "Unranked",
            "roles": [],
            "registered_at": datetime.datetime.now().isoformat(),
        })
        save_json(PLAYERS_FILE, players)

        view = RankSelectView(discord_id)
        await interaction.response.send_message(
            f"✅ **Riot ID saved: {riot_id}**\n\nNow pick your rank:",
            view=view,
            ephemeral=True,
        )


# --- Rank Select View ---
class RankSelectView(ui.View):
    def __init__(self, player_discord_id: str):
        super().__init__(timeout=300)
        self.player_discord_id = player_discord_id
        self.add_item(RankDropdown(player_discord_id))


class RankDropdown(ui.Select):
    def __init__(self, player_discord_id: str):
        self.player_discord_id = player_discord_id
        options = []
        for rank_group in ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal"]:
            for tier in [1, 2, 3]:
                label = f"{rank_group} {tier}"
                options.append(discord.SelectOption(label=label, value=label))
        options.append(discord.SelectOption(label="Radiant", value="Radiant"))

        super().__init__(
            placeholder="Select your Valorant rank...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        players = load_json(PLAYERS_FILE, [])
        for p in players:
            if p["discord_id"] == self.player_discord_id:
                p["rank"] = self.values[0]
                save_json(PLAYERS_FILE, players)
                break

        view = RoleSelectView(self.player_discord_id)
        await interaction.response.send_message(
            f"Rank set to **{self.values[0]}**! Now pick your preferred roles (up to 2):",
            view=view,
            ephemeral=True,
        )


class RoleSelectView(ui.View):
    def __init__(self, player_discord_id: str):
        super().__init__(timeout=300)
        self.player_discord_id = player_discord_id

        options = [discord.SelectOption(label=role, value=role) for role in ROLES]
        dropdown = RoleDropdown(player_discord_id)
        dropdown.options = options
        dropdown.max_values = 2
        self.add_item(dropdown)


class RoleDropdown(ui.Select):
    def __init__(self, player_discord_id: str):
        self.player_discord_id = player_discord_id
        super().__init__(
            placeholder="Select up to 2 preferred roles...",
            options=[discord.SelectOption(label=role, value=role) for role in ROLES],
            min_values=1,
            max_values=2,
        )

    async def callback(self, interaction: discord.Interaction):
        players = load_json(PLAYERS_FILE, [])
        player = None
        for p in players:
            if p["discord_id"] == self.player_discord_id:
                p["roles"] = self.values
                player = p
                save_json(PLAYERS_FILE, players)
                break

        if player:
            log.info("REGISTRATION_COMPLETE: %s — %s — %s — [%s]",
                     player['discord_display'], player['rank'], player['riot_id'],
                     ', '.join(player.get('roles', [])))
            await interaction.response.send_message(
                f"✅ **Registration complete!**\n"
                f"Riot ID: {player['riot_id']}\n"
                f"Rank: {player['rank']}\n"
                f"Roles: {', '.join(player['roles'])}\n\n"
                f"You're in the pool for Vava Bot4Bots Cup! Teams will be formed when registration closes.",
                ephemeral=True,
            )


# --- Tournament Logic (imported from scripts) ---

def organize_teams(num_teams=None):
    """Balanced snake draft. Auto-calculates team count if not provided. Returns (teams, substitutes)."""
    players = load_json(PLAYERS_FILE, [])
    if not players:
        return None

    if num_teams is None:
        num_teams = max(4, len(players) // 5)
        # Round down to nearest power of 2 for clean bracket
        pow2 = 4
        while pow2 * 2 <= num_teams:
            pow2 *= 2
        num_teams = max(4, pow2)

    sorted_players = sorted(players, key=lambda p: RANK_VALUES.get(p.get("rank", ""), 0), reverse=True)
    players_per_team = max(1, len(sorted_players) // num_teams)

    names = TEAM_NAMES[:num_teams]
    random.shuffle(names)

    teams = []
    for i in range(num_teams):
        teams.append({
            "id": f"team_{i+1}",
            "name": names[i],
            "seed": i + 1,
            "players": [],
        })

    idx = 0
    for round_num in range(players_per_team):
        if round_num % 2 == 0:
            for team in teams:
                if idx < len(sorted_players):
                    team["players"].append(sorted_players[idx])
                    idx += 1
        else:
            for team in reversed(teams):
                if idx < len(sorted_players):
                    team["players"].append(sorted_players[idx])
                    idx += 1

    for team in teams:
        if team["players"]:
            team["captain_discord_id"] = team["players"][0]["discord_id"]
            ranks = [RANK_VALUES.get(p.get("rank", ""), 0) for p in team["players"]]
            team["average_rank"] = round(sum(ranks) / len(ranks), 1) if ranks else 0

    subs = sorted_players[idx:] if idx < len(sorted_players) else []
    return teams, subs


def generate_bracket(teams, start_date_str=None):
    """Generate single-elimination bracket. Handles 4, 8, or 16 teams (padded from real count)."""
    teams_sorted = sorted(teams, key=lambda t: t["seed"])
    real_team_count = len(teams_sorted)

    bracket_size = 4
    while bracket_size < real_team_count:
        bracket_size *= 2
    bracket_size = min(bracket_size, 16)

    while len(teams_sorted) < bracket_size:
        teams_sorted.append({"id": f"bye_{len(teams_sorted)+1}", "name": "BYE", "seed": len(teams_sorted)+1})

    if not start_date_str:
        start_date = datetime.date.today() + datetime.timedelta(days=14)
    else:
        start_date = datetime.date.fromisoformat(start_date_str)

    sat = start_date
    while sat.weekday() != 5:
        sat += datetime.timedelta(days=1)
    sun = sat + datetime.timedelta(days=1)

    round_names = {
        4: ["Semifinal", "Grand Final"],
        8: ["Quarterfinal", "Semifinal", "Grand Final"],
        16: ["Round of 16", "Quarterfinal", "Semifinal", "Grand Final"],
    }
    names = round_names.get(bracket_size, round_names[8])

    matches = []
    mid = 1
    prev_match_ids = []

    remaining_slots = bracket_size
    round_slots = bracket_size // 2
    week_offset = 0

    for round_idx, round_name in enumerate(names):
        is_last_round = (round_idx == len(names) - 1)
        slot_dates = []

        for day_offset in range(round_slots):
            day = (sat if week_offset == 0 else sun) if is_last_round else (
                sat if round_slots <= 2 else
                (sat if day_offset < round_slots // 2 else sun)
            )
            slot_dates.append(day)
            day = day + datetime.timedelta(days=1)

        for i in range(round_slots):
            if round_idx == 0:
                t1_idx = i
                t2_idx = remaining_slots - 1 - i
                t1 = teams_sorted[t1_idx]
                t2 = teams_sorted[t2_idx]
            else:
                w1_idx = i * 2
                w2_idx = i * 2 + 1
                t1 = {"id": f"winner_of_{prev_match_ids[w1_idx]}", "name": f"Winner M#{prev_match_ids[w1_idx]}"}
                t2 = {"id": f"winner_of_{prev_match_ids[w2_idx]}", "name": f"Winner M#{prev_match_ids[w2_idx]}"}

            is_bye = t1.get("name") == "BYE" or t2.get("name") == "BYE"
            winner_id = None
            if is_bye:
                if t2.get("name") == "BYE":
                    winner_id = t1["id"]
                else:
                    winner_id = t2["id"]

            date_idx = min(i, len(slot_dates) - 1)
            match_date = sat + datetime.timedelta(days=week_offset * 7 + date_idx)
            if len(slot_dates) > 1 and date_idx > 0:
                match_date = sun if is_last_round else match_date

            matches.append({
                "id": mid,
                "round": round_name,
                "team1": {"id": t1["id"], "name": t1["name"]},
                "team2": {"id": t2["id"], "name": t2["name"]},
                "scheduled_date": match_date.isoformat(),
                "scheduled_time": "18:00",
                "status": "bye" if is_bye else "scheduled",
                "winner_id": winner_id,
                "score": None,
            })
            prev_match_ids.append(mid)
            mid += 1

        remaining_slots = round_slots
        round_slots = round_slots // 2
        week_offset += 1
        prev_match_ids = prev_match_ids[remaining_slots:]
        if round_slots == 0:
            break

    # Add 3rd place match (skip for 4-team bracket)
    if bracket_size > 4 and len(matches) >= 4:
        semis_ids = [m["id"] for m in matches if m["round"] == "Semifinal"]
        if len(semis_ids) >= 2:
            matches.append({
                "id": mid,
                "round": "3rd Place",
                "team1": {"id": f"loser_of_{semis_ids[0]}", "name": f"Loser SF"},
                "team2": {"id": f"loser_of_{semis_ids[1]}", "name": f"Loser SF"},
                "scheduled_date": (sat + datetime.timedelta(days=week_offset * 7)).isoformat(),
                "scheduled_time": "15:00",
                "status": "pending", "winner_id": None, "score": None,
            })

    return {
        "matches": matches,
        "generated_at": datetime.datetime.now().isoformat(),
        "start_date": start_date.isoformat(),
        "format": "single_elimination",
        "num_teams": real_team_count,
    }


def resolve_winners(matches_data):
    """Propagate winners from completed matches to pending matches."""
    matches = matches_data.get("matches", [])
    updated = False
    winner_map = {}
    loser_map = {}

    for m in matches:
        if m["status"] in ("completed", "bye") and m.get("winner_id"):
            winner_map[m["id"]] = m["winner_id"]
            if m["winner_id"] == m["team1"]["id"]:
                loser_map[m["id"]] = m["team2"]["id"]
            else:
                loser_map[m["id"]] = m["team1"]["id"]

    for m in matches:
        if m["status"] not in ("pending",):
            continue

        for key in ["team1", "team2"]:
            tid = m[key]["id"]
            if tid.startswith("winner_of_"):
                src_id = int(tid.split("_")[-1])
                if src_id in winner_map:
                    src_match = next((sm for sm in matches if sm["id"] == src_id), None)
                    if src_match:
                        wid = winner_map[src_id]
                        wname = src_match["team1"]["name"] if wid == src_match["team1"]["id"] else src_match["team2"]["name"]
                        m[key] = {"id": wid, "name": wname}
                        updated = True
            elif tid.startswith("loser_of_"):
                src_id = int(tid.split("_")[-1])
                if src_id in loser_map:
                    src_match = next((sm for sm in matches if sm["id"] == src_id), None)
                    if src_match:
                        lid = loser_map[src_id]
                        lname = src_match["team1"]["name"] if lid == src_match["team1"]["id"] else src_match["team2"]["name"]
                        m[key] = {"id": lid, "name": lname}
                        updated = True

    if updated:
        save_json(MATCHES_FILE, matches_data)


def compute_standings():
    teams_data = load_json(TEAMS_FILE, {})
    matches_data = load_json(MATCHES_FILE, {})

    teams = {
        t["id"]: {"name": t["name"], "seed": t["seed"], "wins": 0, "losses": 0, "maps_won": 0, "maps_lost": 0}
        for t in teams_data.get("teams", [])
    }

    for m in matches_data.get("matches", []):
        if m["status"] != "completed" or not m.get("score"):
            continue
        t1_id, t2_id = m["team1"]["id"], m["team2"]["id"]
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

    return sorted(teams.values(), key=lambda t: (-t["wins"], t["losses"]))


# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


# --- Events ---
@bot.event
async def on_ready():
    await tree.sync()
    cfg = load_config()
    log.info("Bot online as %s — %d guild(s), phase=%s, ai=%s",
             bot.user, len(bot.guilds), cfg['phase'], 'ON' if DEEPSEEK_ENABLED else 'OFF')
    match_reminders.start()


@tree.error
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    log.error("COMMAND_ERROR: %s by %s — %s",
              interaction.command.name if interaction.command else "?",
              interaction.user.display_name, error)
    if not interaction.response.is_done():
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)


@tasks.loop(minutes=60)
async def match_reminders():
    """Auto-announce matches happening in the next 24 hours."""
    cfg = load_config()
    channel_id = cfg.get("announce_channel_id", 0)
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    matches_data = load_json(MATCHES_FILE, {})
    if not matches_data:
        return

    now = datetime.datetime.now()
    window_end = now + datetime.timedelta(hours=24)

    for m in matches_data.get("matches", []):
        if m["status"] not in ("scheduled",):
            continue
        try:
            md = datetime.date.fromisoformat(m["scheduled_date"])
            mt = m.get("scheduled_time", "18:00")
            if len(mt) <= 5:
                mt += ":00"
            match_dt = datetime.datetime.combine(md, datetime.time.fromisoformat(mt))
        except (ValueError, TypeError):
            continue

        time_left = match_dt - now

        # Announce 24h before AND 1h before
        should_announce = False
        announce_type = ""

        if datetime.timedelta(hours=23, minutes=30) < time_left <= datetime.timedelta(hours=24, minutes=30):
            should_announce = True
            announce_type = "24h"
        elif datetime.timedelta(minutes=30) < time_left <= datetime.timedelta(minutes=90):
            should_announce = True
            announce_type = "1h"

        if should_announce and match_dt > now:
            hype_line = ""
            if DEEPSEEK_ENABLED and announce_type == "24h":
                ai_text = await deepseek_generate(
                    f"Write one hype sentence (under 150 chars) for a Valorant match between '{m['team1']['name']}' and '{m['team2']['name']}' "
                    f"in the Vava Bot4Bots Cup tournament. It's the {m['round']}. Make it fun and energetic."
                )
                if ai_text:
                    hype_line = f"\n> *{ai_text}*"

            embed = discord.Embed(
                title=f"⚔️ {m['round']} — {m['team1']['name']} vs {m['team2']['name']}",
                description=f"Match #{m['id']} kicks off in **{'24 hours' if announce_type == '24h' else '1 hour'}**!" + hype_line,
                color=0xff4655,
            )
            embed.add_field(name="Date", value=m["scheduled_date"], inline=True)
            embed.add_field(name="Time", value=m.get("scheduled_time", "TBD"), inline=True)
            embed.add_field(name="Format", value="Best of 3 — Map veto 30 min before match", inline=False)
            embed.set_footer(text="Captains: report results with /cup_report")
            await channel.send(embed=embed)


# --- Slash Commands ---

@tree.command(name="cup_setup", description="(Admin) Configure the tournament")
@owner_only()
@app_commands.describe(
    announce_channel="Channel for bot announcements",
    start_date="Tournament start date, e.g. 2026-05-24",
)
async def cup_setup(
    interaction: discord.Interaction,
    announce_channel: discord.TextChannel,
    start_date: str = "",
):
    cfg = load_config()
    cfg["announce_channel_id"] = announce_channel.id
    if start_date:
        cfg["start_date"] = start_date
    if cfg["phase"] == "setup":
        cfg["phase"] = "registration"
    save_config(cfg)

    # Announce registration is open
    embed = discord.Embed(
        title="🏆 Vava Bot4Bots Cup — Registration OPEN!",
        description="Sign up now to compete in the tournament!",
        color=0xff4655,
    )
    embed.add_field(name="How to Register", value="Type `/cup_register` in this server", inline=False)
    embed.add_field(name="Format", value="Single Elimination | Best-of-3 | Teams balanced by rank", inline=False)
    if cfg.get("start_date"):
        embed.add_field(name="Start Date", value=cfg["start_date"], inline=True)
    embed.set_footer(text="Registration open for 2 weeks — tell your friends!")

    await announce_channel.send(embed=embed)

    await interaction.response.send_message(
        f"✅ **Tournament configured!**\n"
        f"Announce channel: {announce_channel.mention}\n"
        f"Start date: {cfg.get('start_date', 'TBD')}\n"
        f"Phase: **registration**\n\n"
        f"Registration announcement posted. Players register with `/cup_register`!",
        ephemeral=True,
    )


@tree.command(name="cup_register", description="Register for Vava Bot4Bots Cup")
async def cup_register(interaction: discord.Interaction):
    cfg = load_config()
    if cfg["phase"] not in ("registration",):
        await interaction.response.send_message("Registration is not currently open.", ephemeral=True)
        return

    # Check if already registered
    players = load_json(PLAYERS_FILE, [])
    if any(p["discord_id"] == str(interaction.user.id) for p in players):
        # Show profile update flow
        view = RankSelectView(str(interaction.user.id))
        await interaction.response.send_message(
            "You're registered! Update your rank:",
            view=view,
            ephemeral=True,
        )
        return

    # New registration — start with modal
    modal = RegistrationModal()
    await interaction.response.send_modal(modal)


@tree.command(name="cup_my_profile", description="View or update your registration details")
async def cup_my_profile(interaction: discord.Interaction):
    players = load_json(PLAYERS_FILE, [])
    player = next((p for p in players if p["discord_id"] == str(interaction.user.id)), None)

    if not player:
        await interaction.response.send_message("You're not registered yet. Use `/cup_register`!", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Your Registration — Vava Bot4Bots Cup",
        color=0xff4655,
    )
    embed.add_field(name="Riot ID", value=player["riot_id"], inline=True)
    embed.add_field(name="Rank", value=player.get("rank", "Not set"), inline=True)
    embed.add_field(name="Roles", value=", ".join(player.get("roles", [])) or "Not set", inline=True)

    view = RankSelectView(str(interaction.user.id))
    await interaction.response.send_message(
        embed=embed,
        content="To update your details, pick an option below:",
        view=view,
        ephemeral=True,
    )


@tree.command(name="cup_players", description="See registered players")
async def cup_players(interaction: discord.Interaction):
    players = load_json(PLAYERS_FILE, [])
    count = len(players)

    if count == 0:
        await interaction.response.send_message("No players registered yet.", ephemeral=True)
        return

    rank_counts = {}
    for p in players:
        r = p.get("rank", "Unranked")
        rank_counts[r] = rank_counts.get(r, 0) + 1

    max_count = max(rank_counts.values()) if rank_counts else 1
    rank_bars = []
    for rank in RANKS:
        count = rank_counts.get(rank, 0)
        if count > 0:
            bar_len = max(1, int(count / max_count * 15))
            bar = "█" * bar_len
            rank_bars.append(f"`{rank:<14}` {bar} {count}")

    player_list = []
    for p in sorted(players, key=lambda x: x.get("discord_display", "").lower()):
        roles = ", ".join(p.get("roles", [])) or "—"
        player_list.append(f"• **{p['discord_display']}** — {p.get('rank', '?')} — {p['riot_id']} — [{roles}]")

    await interaction.response.send_message(
        f"👥 **Registered Players: {count}**\n"
        f"Enough for **{count // 5}** full team(s)\n\n"
        f"**Rank Distribution:**\n" + "\n".join(rank_bars),
        ephemeral=True,
    )

    chunks = [player_list[i:i+25] for i in range(0, len(player_list), 25)]
    for chunk in chunks:
        await interaction.followup.send("\n".join(chunk), ephemeral=True)


@tree.command(name="cup_rules", description="View tournament rules")
async def cup_rules(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Vava Bot4Bots Cup — Rules",
        description=(
            "**Format:** Single Elimination | Best-of-3\n"
            "**Team Size:** 5 players + up to 2 substitutes\n"
            "**Entry Fee:** $10 AUD per player\n"
            "**Prize Pool:** 1st — 70% | 2nd — 30%\n\n"
            "**Map Selection:** Ban/pick — 3 bans each, picks, remaining decider\n"
            "**Win Condition:** First to 13 rounds per map. First to 2 maps wins.\n"
            "**Overtime:** Enabled (competitive rules)\n\n"
            "**Pauses:** 2 tech pauses (5 min), 1 tactical per half\n"
            "**Agents:** All agents allowed, no bans\n\n"
            "**Code of Conduct:** No toxicity, cheating, or exploits.\n"
            "Penalties: Warning → Map Forfeit → Tournament DQ"
        ),
        color=0xff4655,
    )
    embed.set_footer(text="Vava Bot4Bots Cup — Fair play first")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="cup_close_registration", description="(Admin) Close registration and form teams")
@owner_only()
async def cup_close_registration(interaction: discord.Interaction):
    cfg = load_config()
    if cfg["phase"] != "registration":
        await interaction.response.send_message(f"Current phase is '{cfg['phase']}', not 'registration'.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    players = load_json(PLAYERS_FILE, [])
    if len(players) < 20:  # At least 4 teams of 5
        await interaction.followup.send(
            f"Only {len(players)} players registered. Need at least 20 for 4 teams. Keep registration open.",
            ephemeral=True,
        )
        return

    result = organize_teams()  # Auto-calculates team count
    if result is None:
        await interaction.followup.send("Failed to form teams.", ephemeral=True)
        return

    teams, subs = result
    log.info("TEAMS_FORMED: %d teams, %d players, avg rank spread=%.1f",
             len(teams), len(players),
             max(t['average_rank'] for t in teams) - min(t['average_rank'] for t in teams))
    save_json(TEAMS_FILE, {
        "teams": teams,
        "substitutes": subs,
        "generated_at": datetime.datetime.now().isoformat(),
    })

    cfg["phase"] = "teams"
    cfg["registration_deadline"] = datetime.datetime.now().isoformat()
    save_config(cfg)

    # Announce teams in channel
    channel_id = cfg.get("announce_channel_id", 0)
    channel = bot.get_channel(channel_id) if channel_id else None

    embeds = []
    for team in teams:
        lines = []
        for i, p in enumerate(team["players"], 1):
            cap_mark = "👑 " if p["discord_id"] == team.get("captain_discord_id") else ""
            roles = ", ".join(p.get("roles", [])) or "any"
            lines.append(f"{cap_mark}{i}. **{p['discord_display']}** — {p['rank']} — [{roles}]")

        embed = discord.Embed(
            title=f"#{team['seed']} {team['name']}",
            description="\n".join(lines),
            color=0xff4655,
        )
        embed.add_field(name="Avg Rank", value=str(team["average_rank"]), inline=True)
        embed.add_field(name="Captain", value=f"<@{team['captain_discord_id']}>", inline=True)
        embeds.append(embed)

    if subs:
        sub_list = "\n".join(f"• **{p['discord_display']}** ({p['rank']})" for p in subs)
        embeds[-1].add_field(name="🔁 Substitute Pool", value=sub_list[:1024], inline=False)

    if channel:
        await channel.send("# 🏆 Teams Have Been Formed!")
        for embed in embeds:
            await channel.send(embed=embed)
        await channel.send(
            "Captains: you're marked with 👑. Next step: bracket generation with `/cup_start_bracket`."
        )

    await interaction.followup.send(
        f"✅ **{len(teams)} teams formed!** Balanced by rank. {len(players)} players assigned. Announced in {channel.mention if channel else '#channel'}.\n\n"
        f"Use `/cup_start_bracket` to generate the bracket.",
        ephemeral=True,
    )


@tree.command(name="cup_start_bracket", description="(Admin) Generate bracket and start the tournament")
@owner_only()
async def cup_start_bracket(interaction: discord.Interaction):
    cfg = load_config()
    if cfg["phase"] not in ("teams",):
        await interaction.response.send_message(f"Current phase is '{cfg['phase']}'. Form teams first.", ephemeral=True)
        return

    teams_data = load_json(TEAMS_FILE, {})
    teams = teams_data.get("teams", [])
    if not teams:
        await interaction.response.send_message("No teams found. Form teams first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    bracket = generate_bracket(teams, cfg.get("start_date"))
    log.info("BRACKET_GENERATED: %d teams, %d matches, start=%s",
             bracket['num_teams'], len(bracket['matches']), bracket['start_date'])
    save_json(MATCHES_FILE, bracket)

    cfg["phase"] = "bracket"
    cfg["tournament_started_at"] = datetime.datetime.now().isoformat()
    save_config(cfg)

    channel_id = cfg.get("announce_channel_id", 0)
    channel = bot.get_channel(channel_id) if channel_id else None

    if channel:
        await channel.send("# ⚔️ The Bracket Is Set! Vava Bot4Bots Cup Begins!")

        for m in bracket["matches"]:
            if m["status"] == "bye":
                continue
            embed = discord.Embed(
                title=f"{m['round']} — Match #{m['id']}",
                description=f"**{m['team1']['name']}** 🆚 **{m['team2']['name']}**",
                color=0xff4655,
            )
            embed.add_field(name="Date", value=m["scheduled_date"], inline=True)
            embed.add_field(name="Time", value=m.get("scheduled_time", "TBD"), inline=True)
            embed.add_field(name="Format", value="Best of 3 — Map veto required 30 min before", inline=False)
            embed.set_footer(text="Captains: report results with /cup_report")
            await channel.send(embed=embed)

    await interaction.followup.send(
        f"✅ Bracket generated! {len(bracket['matches'])} matches scheduled. Starting {bracket['start_date']}.",
        ephemeral=True,
    )


@tree.command(name="cup_teams", description="View all teams and rosters")
async def cup_teams(interaction: discord.Interaction):
    teams_data = load_json(TEAMS_FILE, {})
    teams = teams_data.get("teams", [])

    if not teams:
        await interaction.response.send_message("Teams haven't been formed yet.", ephemeral=True)
        return

    embeds = []
    for team in teams:
        lines = []
        for i, p in enumerate(team.get("players", []), 1):
            cap_mark = "👑 " if p["discord_id"] == team.get("captain_discord_id") else ""
            roles = ", ".join(p.get("roles", [])) or "any"
            lines.append(f"{cap_mark}{i}. **{p['discord_display']}** — {p['rank']} — {p['riot_id']} — [{roles}]")

        embed = discord.Embed(
            title=f"#{team['seed']} {team['name']}",
            description="\n".join(lines) if lines else "No players",
            color=0xff4655,
        )
        embed.add_field(name="Avg Rank", value=str(team.get("average_rank", "N/A")), inline=True)
        embed.add_field(name="Captain", value=f"<@{team.get('captain_discord_id', 'N/A')}>", inline=True)
        embeds.append(embed)

    if teams_data.get("substitutes"):
        subs = teams_data["substitutes"]
        sub_list = "\n".join(f"• **{p['discord_display']}** ({p['rank']}) — {p['riot_id']}" for p in subs)
        embeds[-1].add_field(name="🔁 Substitute Pool", value=sub_list[:1024], inline=False)

    # Send all embeds (Discord allows up to 10 embeds per message, so split if > 10)
    await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)

    for i in range(10, len(embeds), 10):
        await interaction.followup.send(embeds=embeds[i:i+10], ephemeral=True)


@tree.command(name="cup_bracket", description="View the tournament bracket")
async def cup_bracket(interaction: discord.Interaction):
    matches_data = load_json(MATCHES_FILE, {})
    matches = matches_data.get("matches", [])

    if not matches:
        await interaction.response.send_message("Bracket hasn't been generated yet.", ephemeral=True)
        return

    rounds = {}
    for m in matches:
        rounds.setdefault(m["round"], []).append(m)

    # Display in match order
    seen = []
    for m in matches:
        if m["round"] not in seen:
            seen.append(m["round"])

    embeds = []
    for round_name in seen:
        if round_name not in rounds:
            continue
        embed = discord.Embed(title=f"▸ {round_name}", color=0xff4655)
        for m in rounds[round_name]:
            icons = {"scheduled": "⏳", "in_progress": "🔴", "completed": "✅", "pending": "⏸️", "bye": "↪️"}
            icon = icons.get(m["status"], "❓")
            score_str = f" ({m['score'][0]}-{m['score'][1]})" if m.get("score") else ""
            embed.add_field(
                name=f"{icon} {m['team1']['name']} vs {m['team2']['name']}{score_str}",
                value=f"Match #{m['id']} | {m['scheduled_date']} @ {m.get('scheduled_time', 'TBD')}",
                inline=False,
            )
        embeds.append(embed)

    embeds[-1].set_footer(text=f"Format: {matches_data.get('format', '?')} | {matches_data.get('num_teams', '?')} teams")
    await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)


@tree.command(name="cup_schedule", description="View upcoming matches")
async def cup_schedule(interaction: discord.Interaction):
    matches_data = load_json(MATCHES_FILE, {})
    matches = matches_data.get("matches", [])

    upcoming = [m for m in matches if m["status"] in ("scheduled", "pending")]
    upcoming.sort(key=lambda m: m["scheduled_date"])

    if not upcoming:
        await interaction.response.send_message("No upcoming matches.", ephemeral=True)
        return

    embed = discord.Embed(title="📅 Upcoming Matches", color=0xff4655)
    for m in upcoming[:25]:
        icons = {"scheduled": "⏳", "pending": "⏸️"}
        icon = icons.get(m["status"], "❓")
        embed.add_field(
            name=f"{icon} Match #{m['id']} — {m['round']}",
            value=f"**{m['team1']['name']}** vs **{m['team2']['name']}**\n{m['scheduled_date']} @ {m.get('scheduled_time', 'TBD')}",
            inline=False,
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="cup_vote_time", description="(Captains) Vote for a match time that works for your team")
@app_commands.describe(
    match_id="Match number",
    time_slot="Preferred time, e.g. 20:00 or 21:30",
)
async def cup_vote_time(interaction: discord.Interaction, match_id: int, time_slot: str):
    teams_data = load_json(TEAMS_FILE, {})
    matches_data = load_json(MATCHES_FILE, {})

    match = next((m for m in matches_data.get("matches", []) if m["id"] == match_id), None)
    if not match:
        await interaction.response.send_message(f"Match #{match_id} not found.", ephemeral=True)
        return

    # Find what team this captain belongs to in this match
    captain_team_id = None
    for team in teams_data.get("teams", []):
        if team["id"] in (match["team1"].get("id", ""), match["team2"].get("id", "")):
            if team.get("captain_discord_id") == str(interaction.user.id):
                captain_team_id = team["id"]
                break

    if not captain_team_id:
        await interaction.response.send_message("Only team captains in this match can vote.", ephemeral=True)
        return

    # Validate time format
    if not re.match(r'^\d{1,2}:\d{2}$', time_slot):
        await interaction.response.send_message("Invalid time. Use format like 20:00 or 21:30.", ephemeral=True)
        return

    # Store vote
    if "time_votes" not in match:
        match["time_votes"] = {}

    match["time_votes"][captain_team_id] = {
        "time": time_slot,
        "captain": str(interaction.user.display_name),
    }
    save_json(MATCHES_FILE, matches_data)

    votes = match["time_votes"]
    other_team = match["team1"]["id"] if captain_team_id == match["team2"]["id"] else match["team2"]["id"]

    if other_team in votes and votes[other_team]["time"] == time_slot:
        match["scheduled_time"] = time_slot
        match["time_votes"] = {}
        save_json(MATCHES_FILE, matches_data)
        # Announce in channel
        cfg = load_config()
        channel_id = cfg.get("announce_channel_id", 0)
        channel = bot.get_channel(channel_id) if channel_id else None
        if channel:
            await channel.send(
                f"⏰ **Match #{match_id} time locked:** {match['scheduled_date']} @ **{time_slot}**\n"
                f"{match['team1']['name']} vs {match['team2']['name']} — both captains agreed!"
            )
        await interaction.response.send_message(
            f"✅ Both captains voted for **{time_slot}**! Match time locked.",
            ephemeral=True,
        )
    else:
        vote_lines = []
        for t, v in votes.items():
            vote_lines.append(f'{v["captain"]} → {v["time"]}')
        await interaction.response.send_message(
            f"🗳️ Voted for **{time_slot}**. Waiting for the other captain.\n"
            f"Current votes: {', '.join(vote_lines)}",
            ephemeral=True,
        )


@tree.command(name="cup_report", description="Report a match result (team captains)")
@app_commands.describe(
    match_id="Match number",
    our_score="Your team's map wins (2, 1, or 0)",
    their_score="Opponent's map wins (2, 1, or 0)",
)
async def cup_report(interaction: discord.Interaction, match_id: int, our_score: int, their_score: int):
    teams_data = load_json(TEAMS_FILE, {})
    matches_data = load_json(MATCHES_FILE, {})

    if not teams_data or not matches_data:
        await interaction.response.send_message("Tournament data not ready.", ephemeral=True)
        return

    match = next((m for m in matches_data.get("matches", []) if m["id"] == match_id), None)
    if not match:
        await interaction.response.send_message(f"Match #{match_id} not found.", ephemeral=True)
        return

    if match["status"] in ("completed", "bye"):
        await interaction.response.send_message(f"Match #{match_id} is already {match['status']}.", ephemeral=True)
        return

    # Validate captain
    reporter_team_id = None
    reporter_team_name = None
    for team in teams_data.get("teams", []):
        if team["id"] in (match["team1"]["id"], match["team2"]["id"]):
            if team.get("captain_discord_id") == str(interaction.user.id):
                reporter_team_id = team["id"]
                reporter_team_name = team["name"]
                break

    if not reporter_team_id:
        await interaction.response.send_message("Only team captains can report results.", ephemeral=True)
        return

    # Determine opponent
    if match["team1"]["id"] == reporter_team_id:
        opponent_name = match["team2"]["name"]
        opponent_id = match["team2"]["id"]
    else:
        opponent_name = match["team1"]["name"]
        opponent_id = match["team1"]["id"]

    # Validate Bo3 score
    if (our_score, their_score) not in ((2, 0), (2, 1), (1, 2), (0, 2)):
        await interaction.response.send_message("Invalid Bo3 score. Must be 2-0, 2-1, 1-2, or 0-2.", ephemeral=True)
        return

    winner_id = reporter_team_id if our_score > their_score else opponent_id
    winner_name = reporter_team_name if our_score > their_score else opponent_name

    match["status"] = "completed"
    match["winner_id"] = winner_id
    if match["team1"]["id"] == reporter_team_id:
        match["score"] = [our_score, their_score]
    else:
        match["score"] = [their_score, our_score]

    resolve_winners(matches_data)
    save_json(MATCHES_FILE, matches_data)
    log.info("MATCH_REPORTED: #%d %s %d-%d %s (%s) — winner: %s",
             match_id, reporter_team_name, our_score, their_score, opponent_name,
             match['round'], winner_name)

    # Announce result
    cfg = load_config()
    channel_id = cfg.get("announce_channel_id", 0)
    channel = bot.get_channel(channel_id) if channel_id else None

    # AI commentary
    ai_commentary = ""
    if DEEPSEEK_ENABLED and channel:
        ai_text = await deepseek_generate(
            f"A Valorant match just finished: {reporter_team_name} {our_score}-{their_score} {opponent_name} "
            f"in the Vava Bot4Bots Cup ({match['round']}). Write a short (under 200 chars) fun post-match commentary. "
            f"Be hyped for the winner but respectful."
        )
        if ai_text:
            ai_commentary = f"\n> *{ai_text}*"

    if channel:
        await channel.send(
            f"# 🏁 Match #{match_id} Result\n"
            f"**{reporter_team_name}** {our_score} — {their_score} **{opponent_name}**\n"
            f"Winner: **{winner_name}** 🎉" + ai_commentary
        )

    await interaction.response.send_message(
        f"✅ Match #{match_id} reported: **{reporter_team_name}** {our_score}-{their_score} **{opponent_name}**",
    )


@tree.command(name="cup_standings", description="View current standings")
async def cup_standings(interaction: discord.Interaction):
    standings = compute_standings()
    if not standings:
        await interaction.response.send_message("No match data yet.", ephemeral=True)
        return

    lines = [
        "```",
        " POS  TEAM                         W  L   MAPS",
        " ─────────────────────────────────────────────────",
    ]
    for i, t in enumerate(standings, 1):
        maps_str = f"{t['maps_won']}-{t['maps_lost']}"
        lines.append(f" {i:>3}. {t['name']:<28} {t['wins']:>2} {t['losses']:>2}  {maps_str:>5}")
    lines.append("```")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="cup_announce", description="(Admin) Announce a round to the configured channel")
@owner_only()
@app_commands.describe(round_name="Round to announce (all, quarterfinal, semifinal, final, 3rd)")
async def cup_announce(interaction: discord.Interaction, round_name: str):
    cfg = load_config()
    channel_id = cfg.get("announce_channel_id", 0)
    channel = bot.get_channel(channel_id) if channel_id else None
    if not channel:
        await interaction.response.send_message("No announce channel configured. Use `/cup_setup`.", ephemeral=True)
        return

    matches_data = load_json(MATCHES_FILE, {})
    if not matches_data:
        await interaction.response.send_message("No matches. Generate bracket first.", ephemeral=True)
        return

    rn = round_name.lower().replace(" ", "")
    to_announce = []
    for m in matches_data.get("matches", []):
        mrn = m["round"].lower().replace(" ", "")
        if rn == "all" or mrn == rn:
            if m["status"] in ("scheduled",):
                to_announce.append(m)

    if not to_announce:
        await interaction.response.send_message(f"No scheduled matches for '{round_name}'.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    for m in to_announce:
        embed = discord.Embed(
            title=f"⚔️ {m['round']} — Match #{m['id']}",
            description=f"**{m['team1']['name']}** vs **{m['team2']['name']}**",
            color=0xff4655,
        )
        embed.add_field(name="Date", value=m["scheduled_date"], inline=True)
        embed.add_field(name="Time", value=m.get("scheduled_time", "TBD"), inline=True)
        embed.add_field(name="Format", value="Best of 3", inline=False)
        embed.set_footer(text="Captains: report with /cup_report")
        await channel.send(embed=embed)

    await interaction.followup.send(f"✅ Announced {len(to_announce)} match(es).", ephemeral=True)


@tree.command(name="cup_hype", description="Generate AI hype for an upcoming match")
@app_commands.describe(match_id="Match number to hype up")
async def cup_hype(interaction: discord.Interaction, match_id: int):
    if not DEEPSEEK_ENABLED:
        await interaction.response.send_message("AI features are not enabled. Ask admin to configure DeepSeek API key.", ephemeral=True)
        return

    matches_data = load_json(MATCHES_FILE, {})
    match = next((m for m in matches_data.get("matches", []) if m["id"] == match_id), None)
    if not match:
        await interaction.response.send_message(f"Match #{match_id} not found.", ephemeral=True)
        return

    await interaction.response.defer()

    prompt = (
        f"Write a hype match preview (2-3 sentences, under 400 chars) for a Valorant tournament match:\n"
        f"Teams: {match['team1']['name']} vs {match['team2']['name']}\n"
        f"Round: {match['round']}\n"
        f"Tournament: Vava Bot4Bots Cup\n"
        f"Make it exciting, Valorant-themed, and respectful."
    )

    hype = await deepseek_generate(prompt, max_tokens=300)
    if not hype:
        await interaction.followup.send("Failed to generate hype. Try again.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🔥 {match['round']}: {match['team1']['name']} vs {match['team2']['name']}",
        description=f"*{hype}*",
        color=0xff4655,
    )
    embed.add_field(name="Date", value=match["scheduled_date"], inline=True)
    embed.add_field(name="Time", value=match.get("scheduled_time", "TBD"), inline=True)
    await interaction.followup.send(embed=embed)


@tree.command(name="cup_phase", description="(Admin) View or advance tournament phase")
@owner_only()
async def cup_phase(interaction: discord.Interaction, action: str = "status"):
    cfg = load_config()

    if action.lower() == "next":
        phases = ["setup", "registration", "teams", "bracket", "tournament", "done"]
        current = phases.index(cfg["phase"]) if cfg["phase"] in phases else 0
        if current < len(phases) - 1:
            cfg["phase"] = phases[current + 1]
            save_config(cfg)
            await interaction.response.send_message(f"Phase advanced to **{cfg['phase']}**", ephemeral=True)
        else:
            await interaction.response.send_message(f"Already at final phase: **{cfg['phase']}**", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"**Current phase:** `{cfg['phase']}`\n"
            f"**Announce channel:** <#{cfg.get('announce_channel_id', 0)}>\n"
            f"**Start date:** {cfg.get('start_date', 'TBD')}\n"
            f"**DeepSeek AI:** {'Enabled' if DEEPSEEK_ENABLED else 'Disabled'}\n\n"
            f"Use `/cup_phase next` to advance.",
            ephemeral=True,
        )


@tree.command(name="cup_reset", description="(Owner) Reset the entire tournament — wipes all data")
@owner_only()
async def cup_reset(interaction: discord.Interaction):
    save_json(PLAYERS_FILE, [])
    save_json(TEAMS_FILE, {})
    save_json(MATCHES_FILE, {})
    save_json(CONFIG_FILE, {
        "phase": "setup",
        "announce_channel_id": 0,
        "start_date": None,
        "registration_deadline": None,
        "tournament_started_at": None,
    })
    await interaction.response.send_message(
        "🗑️ **Tournament reset.** All players, teams, matches, and config wiped. Fresh start.\n"
        "Run `/cup_setup` to configure.",
        ephemeral=True,
    )



@tree.command(name="cup_help", description="Show all commands")
async def cup_help(interaction: discord.Interaction):
    embed = discord.Embed(title="🏆 Vava Bot4Bots Cup — Commands", color=0xff4655)
    embed.add_field(name="👤 Player Commands", value=
        "`/cup_register` — Sign up for the tournament\n"
        "`/cup_my_profile` — View/update your registration\n"
        "`/cup_rules` — Tournament rules\n"
        "`/cup_players` — Registered player count\n"
        "`/cup_teams` — Team rosters\n"
        "`/cup_bracket` — Tournament bracket\n"
        "`/cup_schedule` — Upcoming matches\n"
        "`/cup_standings` — Current standings\n"
        "`/cup_hype` — AI-generated match hype",
        inline=False,
    )
    embed.add_field(name="👑 Captain Commands", value=
        "`/cup_vote_time` — Vote for match time\n"
        "`/cup_report` — Report match result",
        inline=False,
    )
    embed.add_field(name="🔧 Admin Commands", value=
        "`/cup_setup` — Configure tournament\n"
        "`/cup_close_registration` — Close reg & form teams\n"
        "`/cup_start_bracket` — Generate bracket\n"
        "`/cup_announce` — Announce matches to channel\n"
        "`/cup_phase` — View/advance phase\n"
        "`/cup_reset` — Wipe everything, fresh start",
        inline=False,
    )
    embed.set_footer(text="Vava Bot4Bots Cup — Fully automated by opencode")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Entry Point ---
def get_token():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if token:
        return token
    token_file = PROJECT_ROOT / "bot" / ".env"
    if token_file.exists():
        with open(token_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip('"').strip("'")
    return None


PORTAL_URL = os.environ.get("PORTAL_URL", "")
PORTAL_DIR = PROJECT_ROOT / "portal" / "build"


def setup_web_app():
    app = web.Application()
    routes = web.RouteTableDef()

    @routes.get("/api/players")
    async def api_players(request):
        return web.json_response(load_json(PLAYERS_FILE, []))

    @routes.get("/api/teams")
    async def api_teams(request):
        return web.json_response(load_json(TEAMS_FILE, {}))

    @routes.get("/api/matches")
    async def api_matches(request):
        data = load_json(MATCHES_FILE, {})
        return web.json_response(data.get("matches", []))

    @routes.get("/api/standings")
    async def api_standings(request):
        return web.json_response(compute_standings())

    @routes.get("/api/config")
    async def api_config(request):
        cfg = load_config()
        return web.json_response({"phase": cfg.get("phase", ""), "start_date": cfg.get("start_date")})

    app.add_routes(routes)

    if PORTAL_DIR.exists():
        app.router.add_static("/", PORTAL_DIR, show_index=False)

        @routes.get("/")
        async def index_route(request):
            return web.FileResponse(PORTAL_DIR / "index.html")

        @web.middleware
        async def spa_fallback(request, handler):
            try:
                return await handler(request)
            except web.HTTPException as ex:
                if ex.status in (403, 404) and not request.path.startswith("/api/") and not request.path.startswith("/_app/"):
                    return web.FileResponse(PORTAL_DIR / "index.html")
                raise

        app.middlewares.append(spa_fallback)

    return app


async def start_web():
    web_app = setup_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log.info("Portal serving at http://0.0.0.0:8080")


@tree.command(name="cup_portal", description="Get the tournament portal URL")
async def cup_portal(interaction: discord.Interaction):
    url = PORTAL_URL or "http://170.64.204.139:8080"
    embed = discord.Embed(
        title="🌐 Vava Bot4Bots Cup — Tournament Portal",
        description=f"View brackets, standings, teams, and players at:\n\n**[{url}]({url})**",
        color=0xff4655,
    )
    embed.set_thumbnail(url=f"{url}/logo-square.png")
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    init_deepseek()

    token = get_token()
    if not token:
        log.critical("DISCORD_BOT_TOKEN not set. Create a bot at https://discord.com/developers/applications")
        sys.exit(1)

    PORTAL_URL = os.environ.get("PORTAL_URL", "http://170.64.204.139:8080")

    async def main():
        await start_web()
        await bot.start(token)

    asyncio.run(main())
