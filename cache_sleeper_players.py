#!/usr/bin/env python3
"""Cache Sleeper's NFL player catalog for the Sleeper Intelligence layer."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.sleeper_service import get_all_players


def db_connection():
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError("DB_PASSWORD is not set")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "fantasy_intelligence"),
        user=os.getenv("DB_USER", "fantasy"),
        password=password,
    )


def main():
    league_id = os.getenv("SLEEPER_LEAGUE_ID", "1398094330668797952").strip()
    season = int(os.getenv("FANTASY_SEASON", "2026"))
    if not league_id:
        raise RuntimeError("SLEEPER_LEAGUE_ID is not set")

    print("Downloading Sleeper NFL player catalog...")
    players = get_all_players()
    if not isinstance(players, dict) or not players:
        raise RuntimeError("Sleeper returned an empty or invalid player catalog")

    active = sum(
        1 for player in players.values()
        if isinstance(player, dict) and player.get("active") is True
    )
    positions = {}
    for player in players.values():
        if not isinstance(player, dict):
            continue
        position = (player.get("position") or "UNKNOWN").upper()
        positions[position] = positions.get(position, 0) + 1

    conn = db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO sleeper_api_snapshots (
                resource_type, resource_key, season, week, payload, fetched_at
            )
            VALUES ('players', %s, %s, 0, %s::jsonb, NOW())
            ON CONFLICT (resource_type, resource_key, season, week)
            DO UPDATE SET payload = EXCLUDED.payload, fetched_at = NOW()
            """,
            (league_id, season, json.dumps(players)),
        )
        conn.commit()

        cur.execute(
            """
            SELECT jsonb_object_length(payload), fetched_at
            FROM sleeper_api_snapshots
            WHERE resource_type = 'players'
              AND resource_key = %s
              AND season = %s
              AND week = 0
            """,
            (league_id, season),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row or row[0] != len(players):
        raise RuntimeError("Player snapshot verification failed")

    core = {key: positions.get(key, 0) for key in ("QB", "RB", "WR", "TE")}
    print(f"PASS: cached {row[0]} Sleeper NFL players")
    print(f"Active players: {active}")
    print(f"Core position counts: {core}")
    print(f"League key: {league_id}")
    print(f"Fetched at: {row[1]}")
    print("Next: reload /sleeper-intelligence/ (no app restart required)")


if __name__ == "__main__":
    main()
