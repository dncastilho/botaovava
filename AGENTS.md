# AGENTS.md — Bot Rules

## Git Workflow

Every code change MUST:

1. **Pull first**: `git pull` before making any changes
2. **Commit**: `git add -A && git commit -m "<description>"`
3. **Push**: `git push` to `origin main`

This ensures the DO server and GitHub stay in sync. The bot auto-follows this when `/cup_edit` is used.

## Project Structure

```
/opt/vavabot4botscup/     ← Production on DO server
├── bot/bot.py            ← The Discord bot (all logic)
├── portal/               ← SvelteKit 5 web dashboard
├── data/                 ← JSON state files (gitignored)
└── scripts/              ← Standalone utilities (optional)
```

## Important

- `bot/.env` is gitignored — contains secrets
- `data/*.json` is gitignored — live tournament state
- `portal/build/` is gitignored — built output
- The DO server reboots the bot via systemd on restart
- Bot listens on port 8080 for the web portal
- Only user ID `383966572290506755` can use admin commands
