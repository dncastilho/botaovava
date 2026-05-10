# 🏆 Vava Bot4Bots Cup

Valorant tournament management bot + web portal. Runs entirely from Discord. Set it up once, the bot handles everything.

---

## Quick Start

```bash
# 1. Create a Discord bot at https://discord.com/developers/applications
# 2. Get your token, channel ID, and (optional) DeepSeek API key
# 3. Deploy

git clone git@github.com:dncastilho/botaovava.git
cd botaovava
cp bot/.env.example bot/.env   # Fill in your tokens
pip install -r bot/requirements.txt
python bot/bot.py
```

Or with Docker:
```bash
docker compose up -d
```

## Features

- **Registration** — Players sign up via Discord modals (Riot ID → Rank → Roles)
- **Team Formation** — Snake draft algorithm balances teams by rank
- **Bracket Generation** — Single elimination, supports 4/8/16 teams
- **Match Scheduling** — Auto-generated weekend schedule
- **Auto-Reminders** — 24h and 1h match reminders with AI hype
- **Result Reporting** — Captains report scores, winners auto-advance
- **Standings** — Live W-L records and map differentials
- **Time Voting** — Captains vote for match times
- **Web Portal** — Bootstrap 5 dashboard at port 8080
- **AI Powered** — DeepSeek integration for match hype and commentary
- **Self-Modifying** — `/cup_edit` lets the owner modify bot code via opencode

## Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/cup_register` | Anyone | Sign up for the tournament |
| `/cup_my_profile` | Anyone | View/update your registration |
| `/cup_rules` | Anyone | Tournament rules |
| `/cup_players` | Anyone | Registered players list |
| `/cup_teams` | Anyone | Team rosters |
| `/cup_bracket` | Anyone | Tournament bracket |
| `/cup_schedule` | Anyone | Upcoming matches |
| `/cup_standings` | Anyone | Current standings |
| `/cup_hype` | Anyone | AI match hype |
| `/cup_portal` | Anyone | Portal URL |
| `/cup_help` | Anyone | All commands |
| `/cup_vote_time` | Captains | Vote for match time |
| `/cup_report` | Captains | Report match result |
| `/cup_setup` | Owner | Configure tournament |
| `/cup_close_registration` | Owner | Form teams |
| `/cup_start_bracket` | Owner | Generate bracket |
| `/cup_announce` | Owner | Announce matches |
| `/cup_phase` | Owner | View/advance phase |
| `/cup_reset` | Owner | Full tournament reset |
| `/cup_edit` | Owner | Modify bot code via opencode |

## Tournament Flow

```
/cup_setup          → Registration opens
(2 weeks sign-ups)
/cup_close_registration  → Teams formed, balanced by rank
/cup_start_bracket       → Bracket generated, schedule posted
(tournament runs — auto-reminders, captains report results)
```

## Tech Stack

- **Bot**: Python, discord.py, aiohttp
- **Portal**: SvelteKit 5, Bootstrap 5
- **AI**: DeepSeek API
- **Data**: JSON files (no database)

## Entry Fee

$10 AUD per player. Prize pool split 70/30 for 1st/2nd place.

## License

MIT
