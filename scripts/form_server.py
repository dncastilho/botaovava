#!/usr/bin/env python3
"""
Vava Bot4Bots Cup — Form Server
Tiny Flask server that serves the registration form and saves submissions.
Run: python scripts/form_server.py
"""
import json
import os
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FORM_DIR = PROJECT_ROOT / "form"
ASSETS_DIR = PROJECT_ROOT / "assets"

DATA_DIR.mkdir(exist_ok=True)

PLAYERS_FILE = DATA_DIR / "players.json"

app = Flask(__name__, static_folder=str(FORM_DIR), static_url_path="")


def load_players():
    if PLAYERS_FILE.exists():
        with open(PLAYERS_FILE) as f:
            return json.load(f)
    return []


def save_players(players):
    with open(PLAYERS_FILE, "w") as f:
        json.dump(players, f, indent=2)


@app.route("/")
def index():
    return send_from_directory(str(FORM_DIR), "index.html")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(ASSETS_DIR), filename)


@app.route("/RULES.md")
def rules():
    return send_from_directory(str(PROJECT_ROOT), "RULES.md")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)

    required = ["discord_username", "discord_id", "riot_id", "rank", "region"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    players = load_players()

    if any(p["discord_id"] == data["discord_id"] for p in players):
        return jsonify({"error": "You have already registered."}), 409

    if any(p["riot_id"].lower() == data["riot_id"].lower() for p in players):
        return jsonify({"error": "This Riot ID is already registered."}), 409

    players.append(data)
    save_players(players)

    print(f"[+] Registered: {data['discord_username']} ({data['rank']}) — Total: {len(players)}")
    return jsonify({"ok": True, "total_players": len(players)})


@app.route("/api/players", methods=["GET"])
def get_players():
    return jsonify(load_players())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"  Vava Bot4Bots Cup Form Server starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
