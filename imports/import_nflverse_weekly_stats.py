"""Import nflverse weekly player statistics without silently falling back."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from services.defense_matchup_calculation import calculate_defense_matchups
from services.nflverse_ingestion_validator import validate_nflverse_weekly_stats
from services.defense_matchup_publication import publish_defense_matchups

NFLVERSE_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv.gz"
NFLVERSE_RELEASE_TIMESTAMP_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/timestamp.txt"
REQUIRED_WEEKLY_COLUMNS = {"player_id", "position", "position_group", "season", "week", "season_type", "team", "opponent_team", "passing_yards", "passing_tds", "passing_interceptions", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds", "receptions"}


def load_weekly_stats(path: str | Path) -> tuple[list[dict], str]:
    raw = urlopen(str(path), timeout=30).read() if str(path).startswith(("http://", "https://")) else Path(path).read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    if str(path).endswith(".gz"):
        import gzip
        raw = gzip.decompress(raw)
    return list(csv.DictReader(raw.decode("utf-8-sig").splitlines())), checksum


def normalize_nflverse_rows(rows: list[dict], *, season: int) -> list[dict]:
    if not rows or not REQUIRED_WEEKLY_COLUMNS.issubset(rows[0]):
        missing = sorted(REQUIRED_WEEKLY_COLUMNS.difference(rows[0] if rows else set()))
        raise ValueError(f"NFLVERSE_WEEKLY_SCHEMA_UNVERIFIED: {missing}")
    normalized = []
    for row in rows:
        if str(row.get("season")) != str(season):
            continue
        item = dict(row)
        item["defense_team"] = item.get("opponent_team")
        item["game_id"] = f"{item.get('season')}:{item.get('week')}:{item.get('team')}:{item.get('opponent_team')}"
        normalized.append(item)
    return normalized


def build_evidence(path: str | Path, *, season: int, sample_threshold: int | None = None) -> dict:
    rows, checksum = load_weekly_stats(path)
    rows = normalize_nflverse_rows(rows, season=season) if str(path).startswith(("http://", "https://")) else rows
    validation = validate_nflverse_weekly_stats(rows, season=season)
    if not validation["valid"]:
        raise ValueError(", ".join(validation["blockers"]))
    source = NFLVERSE_RELEASE_URL.format(season=season) if str(path).startswith(("http://", "https://")) else f"fixture:{Path(path).name}"
    source_recorded_at = None
    if str(path).startswith(("http://", "https://")):
        source_recorded_at = urlopen(NFLVERSE_RELEASE_TIMESTAMP_URL, timeout=30).read().decode("utf-8").strip()
    return calculate_defense_matchups(rows, season=season, sample_threshold=sample_threshold, source=source, version=f"stats_player_week_{season}", checksum=checksum, source_recorded_at=source_recorded_at, retrieved_at=datetime.now(timezone.utc).isoformat())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--sample-threshold", type=int)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    evidence = build_evidence(args.csv_path, season=args.season, sample_threshold=args.sample_threshold)
    if args.publish:
        import psycopg2
        with psycopg2.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5433"), dbname=os.getenv("DB_NAME", "fantasy_intelligence"), user=os.getenv("DB_USER", "fantasy"), password=os.getenv("DB_PASSWORD")) as connection:
            publish_defense_matchups(connection, evidence)
    print(json.dumps(evidence, default=str, sort_keys=True))


if __name__ == "__main__":
    main()