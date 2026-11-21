#!/usr/bin/env python3
"""Refresh the nflverse role evidence that the Waivers page reads (W6): targets and carries, and offensive snap share.

Reuses the existing importers' builders and atomic publishers: stats_player_week through imports/import_nflverse_opportunity.py into
player_opportunity_evidence, and snap_counts with the nflverse players PFR-to-GSIS crosswalk through imports/import_nflverse_snap_counts.py
into snap_share_evidence. Only completed weeks are published: the boundary is the latest week whose every game has a result in the
automated nflverse schedule already stored in nfl_schedule. Each source replaces its weeks in one transaction; a source that fails keeps
its previously stored rows and their original retrieval time, so a failed refresh never makes old evidence current. Requests to nflverse
are read-only, and viewing /waivers never runs this command.

Usage: python refresh_opportunity_evidence.py [--season YEAR] [--dry-run]
Exit status: 0 both sources published, 2 one source failed, 1 nothing published.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.waiver_role_evidence import completed_week_boundary

SCHEDULE_KEYS = ("week", "home_team", "away_team", "result", "source")


def read_completed_week(connection: Any, season: int) -> int:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT " + ", ".join(SCHEDULE_KEYS) + " FROM nfl_schedule WHERE season = %s", (season,))
        rows = [dict(zip(SCHEDULE_KEYS, row)) for row in cursor.fetchall() or []]
    finally:
        cursor.close()
    return completed_week_boundary(rows)


def _opportunity_step(season: int, through_week: int, environ: Mapping[str, str]) -> tuple[dict, Callable, Callable]:
    from imports.import_nflverse_opportunity import build_evidence
    from imports.import_nflverse_weekly_stats import NFLVERSE_RELEASE_URL
    from services.player_opportunity_publication import _publication_blocker, publish_player_opportunity
    evidence = build_evidence(NFLVERSE_RELEASE_URL.format(season=season), season=season, through_week=through_week, threshold_environment=environ)
    return evidence, _publication_blocker, publish_player_opportunity


def _snap_step(season: int, through_week: int, environ: Mapping[str, str]) -> tuple[dict, Callable, Callable]:
    from imports.import_nflverse_snap_counts import (NFLVERSE_PLAYERS_RELEASE_URL, SNAP_COUNTS_RELEASE_URL, build_pfr_to_gsis_crosswalk,
                                                     build_snap_share_evidence)
    from services.snap_share_publication import _blocker, publish_snap_share
    crosswalk, lineage = build_pfr_to_gsis_crosswalk(NFLVERSE_PLAYERS_RELEASE_URL, include_lineage=True)
    evidence = build_snap_share_evidence(SNAP_COUNTS_RELEASE_URL.format(season=season), season=season, identity_crosswalk=crosswalk,
                                         identity_crosswalk_lineage=lineage, through_week=through_week, threshold_environment=environ)
    return evidence, _blocker, publish_snap_share


STEPS = (("stats_player_week", _opportunity_step), ("snap_counts", _snap_step))


def refresh_opportunity_evidence(connection: Any, *, season: int, dry_run: bool = False, environ: Mapping[str, str] | None = None,
                                 steps=STEPS, completed_week: Callable[[Any, int], int] = read_completed_week) -> dict[str, Any]:
    result: dict[str, Any] = {"season": season, "status": "failed", "through_week": None, "dry_run": dry_run, "sources": {}, "error": None}
    try:
        through_week = completed_week(connection, season)
    except Exception as exc:
        result["error"] = f"Schedule: {type(exc).__name__}: {exc}"
        return result
    if not through_week:
        result["error"] = f"No {season} week is complete in the automated nflverse schedule, so nothing is published."
        return result
    result["through_week"] = through_week
    for key, step in steps:
        try:
            evidence, blocker_of, publish = step(season, through_week, environ if environ is not None else os.environ)
            weeks = sorted({int(week) for week in evidence.get("weeks") or []})
            entry = {"weeks": weeks, "rows": len(evidence.get("rows") or []), "publication_blocker": blocker_of(evidence),
                     "source_recorded_at": (evidence.get("provenance") or {}).get("source_recorded_at"),
                     "retrieved_at": (evidence.get("provenance") or {}).get("retrieved_at"), "reconciliation": {
                         name: value for name, value in (evidence.get("reconciliation") or {}).items() if not isinstance(value, (list, dict))}}
            if weeks and max(weeks) > through_week:
                raise ValueError(f"evidence includes Week {max(weeks)}, after the completed Week {through_week}")
            if dry_run:
                entry["state"] = "DRY_RUN"
            else:
                entry.update(state="PUBLISHED", published_rows=publish(connection, evidence))
        except Exception as exc:
            entry = {"state": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        result["sources"][key] = entry
    succeeded = [entry for entry in result["sources"].values() if entry["state"] in ("PUBLISHED", "DRY_RUN")]
    result["status"] = "success" if len(succeeded) == len(steps) else "partial" if succeeded else "failed"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh nflverse role evidence (targets, carries, offensive snap share) for completed weeks.")
    parser.add_argument("--season", type=int, default=None, help="Season to refresh (default: Sleeper's current NFL season).")
    parser.add_argument("--dry-run", action="store_true", help="Retrieve and validate without writing to the database.")
    args = parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv()
    season = args.season
    if season is None:
        from services.sleeper_service import get_nfl_state
        try:
            season = int((get_nfl_state() or {}).get("season"))
        except Exception as exc:
            print(json.dumps({"status": "failed", "error": f"Season could not be read from Sleeper ({type(exc).__name__}); pass --season."}))
            return 1
    import psycopg2
    from config import Config
    connection = psycopg2.connect(**Config.db_kwargs())
    if args.dry_run:
        connection.set_session(readonly=True)
    try:
        result = refresh_opportunity_evidence(connection, season=season, dry_run=args.dry_run)
    finally:
        connection.close()
    print(json.dumps(result, indent=2, default=str))
    return {"success": 0, "partial": 2}.get(result["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
