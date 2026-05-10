# 🏆 Vava Bot4Bots Cup — Fully Automated via OpenCode

**You don't do anything.** The bot runs on a Digital Ocean box and handles every phase. You interact with it through Discord. OpenCode helps you set it up once, then it runs forever.

---

## ONE-TIME SETUP (5 minutes)

### 1. Create a Discord Bot

Go to https://discord.com/developers/applications:
1. **New Application** → "Vava Bot4Bots Cup"
2. **Bot** tab → **Add Bot** → copy the token
3. Enable **Message Content Intent** and **Server Members Intent**
4. **OAuth2 → URL Generator** → check `bot` + `applications.commands`
5. Bot permissions: Send Messages, Embed Links, Read Message History, Use Slash Commands, Mention Everyone
6. Copy the invite URL, invite the bot to your server

### 2. Get Your Announce Channel ID

Enable Discord Developer Mode (Settings → Advanced → Developer Mode). Right-click the channel where you want bot announcements → Copy ID.

### 3. Get a DeepSeek API Key (optional, for AI hype)

Get your key from https://platform.deepseek.com/api_keys

### 4. Tell OpenCode to Deploy

```
"I want to deploy the vava bot4bots cup bot to my Digital Ocean box"
```

OpenCode will:
1. Create `bot/.env` with your token, channel ID, and API key
2. SSH into your DO box
3. Clone the repo / upload files
4. Run `docker compose up -d`
5. Verify the bot is online

Alternatively, on the DO box manually:

```bash
cd /opt/vavabot4botscup
# Edit bot/.env with your values
docker compose up -d
```

---

## HOW THE BOT WORKS

### Phase 1 — Registration (Admin starts it)

Once the bot is online, an admin runs:

```
/cup_setup  announce_channel:#tournament-announcements  num_teams:8  start_date:2026-05-24
```

This sets everything up and opens registration. Players register with:

```
/cup_register
```

The bot walks them through a multi-step modal flow:
1. Enter Riot ID
2. Select rank (dropdown)
3. Select preferred roles (dropdown, up to 2)
4. Select region (dropdown)

Players can update their profile anytime with `/cup_my_profile`.

### Phase 2 — Close Registration & Form Teams (Admin)

After 2 weeks (or whenever enough players register), admin runs:

```
/cup_close_registration
```

The bot:
- Runs the snake draft algorithm
- Balances teams by rank
- Assigns captains
- Posts all team rosters to the announce channel
- Saves everything to `data/teams.json`

### Phase 3 — Generate Bracket (Admin)

```
/cup_start_bracket
```

The bot:
- Generates a 8-team single elimination bracket
- Schedules quarterfinals over a weekend
- Semifinals the next Saturday
- Grand Final + 3rd Place on Sunday
- Posts the full bracket to the announce channel

### Phase 4 — Tournament Is Live

The bot now operates autonomously:

- **Auto-reminders**: Every hour, checks for matches happening in 24h and 1h. Posts reminders in the announce channel.
- **AI Hype** (if DeepSeek enabled): 24h-before announcements include AI-generated hype lines.
- **Match reporting**: Team captains use `/cup_report <match_id> <our_score> <their_score>`. The bot validates scores, records results, and auto-advances winners through the bracket.
- **Live standings**: `/cup_standings` shows W-L records and map differentials.
- **Bracket view**: `/cup_bracket` shows the full bracket with status icons.
- **Result announcements**: When a match is reported, the bot posts the result in the announce channel with AI-generated commentary.

---

## BOT COMMANDS REFERENCE

### Anyone Can Use

| Command | What It Does |
|---------|-------------|
| `/cup_register` | Sign up for the tournament |
| `/cup_my_profile` | View/update your registration |
| `/cup_rules` | Tournament rules summary |
| `/cup_players` | See how many have registered |
| `/cup_teams` | View team rosters |
| `/cup_bracket` | View tournament bracket |
| `/cup_schedule` | Upcoming matches |
| `/cup_standings` | Current standings |
| `/cup_hype <match_id>` | AI-generated hype for a match |
| `/cup_help` | Show all commands |

### Captains Only

| Command | What It Does |
|---------|-------------|
| `/cup_report <match_id> <our_score> <their_score>` | Report match result (e.g. `/cup_report 1 2 0`) |

### Admins Only

| Command | What It Does |
|---------|-------------|
| `/cup_setup` | Configure tournament (channel, teams, dates) |
| `/cup_close_registration` | Close registration & form teams |
| `/cup_start_bracket` | Generate bracket & start tournament |
| `/cup_announce <round>` | Manually announce matches |
| `/cup_phase` | View current phase |
| `/cup_phase next` | Advance to next phase |

---

## ADMIN TOURNAMENT FLOW

```
1. /cup_setup announce_channel:#valorant-news num_teams:8 start_date:2026-05-24
   → Registration is now OPEN. Bot announces in channel.

2. (Wait 2 weeks for sign-ups. Check progress with /cup_players.)

3. /cup_close_registration
   → Teams are formed. Balanced by rank. Rosters posted in channel.

4. /cup_start_bracket
   → Bracket generated. Schedule posted in channel.

5. (Tournament runs. Auto-reminders. Captains report results.)

6. (When all matches are done, bot auto-advances winner through bracket.)

7. /cup_phase next  (to mark tournament as "done")
```

---

## AI FEATURES (DeepSeek)

If you provide a DeepSeek API key in `bot/.env`, the bot gains:

- **Hype match previews**: AI-generated hype lines in 24h match reminders
- **Post-match commentary**: AI-generated commentary when results are reported
- **`/cup_hype <match_id>`**: Anyone can trigger AI hype for any match

Example hype output:
> *"The Neon Blades' lightning fast executes meet the Void Walkers' unbreakable defense in this semifinal clash. Expect map control mind games and a possible third map decider!"*

Without the API key, the bot works fine — just without the AI text.

---

## DEPLOYING TO DIGITAL OCEAN

### With Docker (recommended)

```bash
# On your DO box
git clone <this-repo> /opt/vavabot4botscup
cd /opt/vavabot4botscup

# Create bot/.env with your values
cat > bot/.env << 'EOF'
DISCORD_BOT_TOKEN=your_token
ANNOUNCE_CHANNEL_ID=123456789
DEEPSEEK_API_KEY=sk-your-key
EOF

# Start
docker compose up -d

# Check logs
docker compose logs -f
```

### Without Docker

```bash
cd /opt/vavabot4botscup
pip install -r bot/requirements.txt
python bot/bot.py
```

Use `tmux` or a systemd service to keep it running:

```bash
tmux new -s botscup
python bot/bot.py
# Ctrl+B, D to detach
```

---

## FILE STRUCTURE

```
vavabot4botscup/
├── bot/
│   ├── bot.py              # THE BOT — everything is here
│   ├── requirements.txt    # discord.py + aiohttp
│   └── .env                # YOUR CONFIG (create this)
├── data/                   # All state (auto-managed by bot)
│   ├── config.json         # Tournament config
│   ├── players.json        # Registrations
│   ├── teams.json          # Teams
│   └── matches.json        # Bracket + schedule + results
├── scripts/                # Standalone scripts (optional alternative)
│   ├── form_server.py      # Web form alternative
│   ├── organize_teams.py   # Standalone team balancer
│   ├── generate_bracket.py # Standalone bracket gen
│   └── stats.py            # Standalone stats
├── assets/
│   └── logo.svg            # Championship logo
├── RULES.md                # Full tournament rules
├── Dockerfile              # Docker build
├── docker-compose.yml      # Docker compose config
└── INSTRUCTIONS.md         # This file
```

---

## VERIFYING IT WORKS

After deploying, check Discord:
1. Bot appears online in your server
2. Type `/cup_help` — you see all commands
3. Admin runs `/cup_setup` to configure
4. Players run `/cup_register`

---

> **Vava Bot4Bots Cup** — Set it up once. The bot runs the tournament. You just watch.
