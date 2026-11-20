#!/usr/bin/env python3
"""Refresh this league's Sleeper transaction history for the Waivers FAAB market evidence.

Read-only Sleeper requests (the league, then GET /league/{league_id}/transactions/{week} once per week of the season through the
league's current week). Each week that is retrieved is stored in sleeper_api_snapshots (resource type 'transactions'); a week
that fails is reported by number and its previously stored snapshot is kept. The run is recorded in sleeper_sync_runs.
Viewing /waivers never runs this; it only reads what this command stored.

Usage: python refresh_sleeper_transactions.py [--league-id ID] [--season YEAR] [--dry-run]
Exit status: 0 every week stored, 2 some weeks failed, 1 nothing stored.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.sleeper_service import get_league, get_transactions
from services.sleeper_snapshots import refresh_transaction_history


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh Sleeper transaction history for the Waivers FAAB market evidence (read-only Sleeper requests).")
    parser.add_argument("--league-id", default=os.getenv("SLEEPER_LEAGUE_ID", "").strip(), help="Sleeper league id (default: SLEEPER_LEAGUE_ID).")
    parser.add_argument("--season", type=int, default=None, help="Season to refresh; must match the league's season (default: the league's season).")
    parser.add_argument("--dry-run", action="store_true", help="Retrieve and report without writing to the database.")
    args = parser.parse_args(argv)
    connection = None
    if not args.dry_run:
        import psycopg2
        from config import Config
        connection = psycopg2.connect(**Config.db_kwargs())
    try:
        result = refresh_transaction_history(connection, league_id=args.league_id, season=args.season, get_league=get_league,
                                             get_transactions=get_transactions, dry_run=args.dry_run)
    finally:
        if connection is not None:
            connection.close()
    print(json.dumps(result, indent=2, default=str))
    return {"success": 0, "partial": 2}.get(result["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
