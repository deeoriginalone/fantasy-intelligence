"""Import nflverse weekly player-stat opportunity evidence without silently falling back."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from imports.import_nflverse_weekly_stats import NFLVERSE_RELEASE_TIMESTAMP_URL, NFLVERSE_RELEASE_URL, load_weekly_stats
from services.player_opportunity_calculation import calculate_player_opportunity
from services.player_opportunity_publication import publish_player_opportunity

OPPORTUNITY_REQUIRED_COLUMNS = {"player_id", "team", "opponent_team", "season", "week", "targets", "carries"}


def build_evidence(path: str | Path, *, season: int, threshold_environment=None) -> dict:
    rows, checksum = load_weekly_stats(path)
    if not rows or not OPPORTUNITY_REQUIRED_COLUMNS.issubset(rows[0]):
        missing = sorted(OPPORTUNITY_REQUIRED_COLUMNS.difference(rows[0] if rows else set()))
        raise ValueError(f"NFLVERSE_OPPORTUNITY_SCHEMA_UNVERIFIED: {missing}")
    filtered = [row for row in rows if str(row.get("season")) == str(season)]
    path_text = str(path)
    verified_source_url = NFLVERSE_RELEASE_URL.format(season=season)
    is_verified_remote = path_text == verified_source_url
    is_remote = path_text.startswith(("http://", "https://"))
    source = "automated:nflverse" if is_verified_remote else (f"remote:unverified:{path_text}" if is_remote else f"fixture:{Path(path).name}")
    source_recorded_at = urlopen(NFLVERSE_RELEASE_TIMESTAMP_URL, timeout=30).read().decode("utf-8").strip() if is_verified_remote else None
    evidence = calculate_player_opportunity(
        filtered, season=season, threshold_environment=threshold_environment,
        source=source, version=f"stats_player_week_{season}", checksum=checksum,
        source_recorded_at=source_recorded_at, retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    evidence["provenance"]["source_location"] = path_text
    evidence["provenance"]["source_authority"] = "automated:nflverse" if is_verified_remote else "UNVERIFIED"
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    evidence = build_evidence(args.csv_path, season=args.season)
    if args.publish:
        import psycopg2
        with psycopg2.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5433"), dbname=os.getenv("DB_NAME", "fantasy_intelligence"), user=os.getenv("DB_USER", "fantasy"), password=os.getenv("DB_PASSWORD")) as connection:
            publish_player_opportunity(connection, evidence)
    print(json.dumps(evidence, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
