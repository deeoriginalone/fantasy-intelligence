#!/usr/bin/env python3
"""Refresh the nflverse role evidence that the Waivers page reads (W6): targets and carries, and offensive snap share.

Reuses the existing importers' builders and atomic publishers: stats_player_week through imports/import_nflverse_opportunity.py into
player_opportunity_evidence, and snap_counts with the nflverse players PFR-to-GSIS crosswalk through imports/import_nflverse_snap_counts.py
into snap_share_evidence. Only completed weeks are published: the boundary is the latest week whose every game has a result in the
automated nflverse schedule already stored in nfl_schedule. Each source replaces its weeks in one transaction; a source that fails keeps
its previously stored rows and their original retrieval time, so a failed refresh never makes old evidence current. Requests to nflverse
are read-only, and viewing /waivers never runs this command.

scheduler/opportunity-evidence-refresh.timer runs this same command every six hours; it stays usable by hand for an immediate refresh.
Every successful run reacquires each provider artifact, so retrieved_at is a real retrieval time, and an artifact identical to the one
already stored (same checksum) is reported as unchanged. After publishing, each source is judged exactly as /waivers judges it
(build_role_index), so a source that does not cover every completed game is never reported current, however recently it was retrieved.

Usage: python refresh_opportunity_evidence.py [--season YEAR] [--dry-run]
Status (exit code): success (0) every source published and current; no_source_update (0) the same, with every provider artifact
unchanged; no_completed_week (0) no week of the season is complete yet, so nothing is fetched or written; partial (2) a source failed
or is not current after the run; failed (1) nothing was published.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.game_lock import SCHEDULE_SOURCE_PREFIX
from services.waiver_role_evidence import build_role_index, completed_week_boundary

SCHEDULE_KEYS = ("week", "home_team", "away_team", "result", "source")
# Each source's table and the automated rows its publisher replaces (the publishers' own DELETE scope).
SOURCE_TABLES = {"stats_player_week": ("player_opportunity_evidence", "source LIKE 'automated:nflverse%%'"),
                 "snap_counts": ("snap_share_evidence", "source = 'automated:nflverse'")}
STORED_FIELDS = ("currency", "completeness", "verified_through_week", "completed_through_week", "stored_through_week", "freshness_state",
                 "retrieved_at", "source_recorded_at", "threshold_id", "blocker", "reason")
ENTRY_ORDER = ("state", "stage", "error", "rows_published", "prior_evidence", "acquired", "stored_before", "stored")
EXIT_CODES = {"success": 0, "no_source_update": 0, "no_completed_week": 0, "partial": 2}


def read_schedule(connection: Any, season: int) -> list[dict]:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT " + ", ".join(SCHEDULE_KEYS) + " FROM nfl_schedule WHERE season = %s", (season,))
        return [dict(zip(SCHEDULE_KEYS, row)) for row in cursor.fetchall() or []]
    finally:
        cursor.close()


def read_completed_week(connection: Any, season: int) -> int:
    return completed_week_boundary(read_schedule(connection, season))


def read_stored_publication(connection: Any, season: int) -> dict[str, dict]:
    """What each source table holds for the season before a run (SELECT only), so the result shows what the run changed or kept."""
    stored = {}
    cursor = connection.cursor()
    try:
        for key, (table, automated) in SOURCE_TABLES.items():
            cursor.execute(f"SELECT count(*), min(week), max(week), min(retrieved_at), max(retrieved_at), max(source_recorded_at), "
                           f"array_agg(DISTINCT checksum) FROM {table} WHERE season = %s AND {automated}", (season,))
            rows, first, last, oldest, newest, recorded, checksums = cursor.fetchone()
            stored[key] = {"rows": rows, "first_week": first, "last_week": last, "oldest_retrieved_at": oldest, "newest_retrieved_at": newest,
                           "source_recorded_at": recorded, "checksums": sorted(value for value in checksums or [] if value)}
    finally:
        cursor.close()
    return stored


def evaluate_sources(connection: Any, season: int, through_week: int, schedule_rows: list[dict], environ: Mapping[str, str]) -> dict[str, dict]:
    """Each source's stored state after a run, judged by the same readers and rules /waivers uses (SELECT only)."""
    from services.player_opportunity_reader import read_opportunity_observations
    from services.snap_share_reader import read_snap_share_observations
    reads = {"opportunity": read_opportunity_observations(connection, player_ids=[], season=season, threshold_environment=environ),
             "snaps": read_snap_share_observations(connection, player_ids=[], season=season, threshold_environment=environ),
             "schedule": schedule_rows}
    index = build_role_index(season=season, week=max(int(through_week), 1), week_verified=True, reads=reads, mode="LIVE")
    if not index.get("sources"):
        return {key: {"currency": index.get("state"), "blocker": next(iter(index.get("blockers") or []), None), "reason": index.get("reason")}
                for key in SOURCE_TABLES}
    return {key: {field: source.get(field) for field in STORED_FIELDS} for key, source in index["sources"].items()}


def _source_update(prior: Mapping[str, Any] | None, checksum: Any) -> str:
    """Whether the provider artifact differs from the one the stored rows came from, by artifact checksum."""
    if prior is None:
        return "UNKNOWN"
    if not prior.get("rows"):
        return "FIRST_PUBLICATION"
    return "UNCHANGED" if checksum and prior.get("checksums") == [checksum] else "UPDATED"


def _rollback(connection: Any) -> None:
    rollback = getattr(connection, "rollback", None)
    if callable(rollback):
        try:
            rollback()
        except Exception:
            pass


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
                                 steps=STEPS, schedule: Callable[[Any, int], list] = read_schedule,
                                 stored: Callable[[Any, int], dict] = read_stored_publication,
                                 evaluate: Callable[..., dict] = evaluate_sources) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    result: dict[str, Any] = {"season": season, "status": "failed", "exit_code": 1, "through_week": None, "dry_run": dry_run,
                              "run_started_at": datetime.now(timezone.utc).isoformat(), "sources": {}, "error": None}
    try:
        schedule_rows = list(schedule(connection, season))
    except Exception as exc:
        result["error"] = f"Schedule: {type(exc).__name__}: {exc}"
        return result
    if not any(str(row.get("source") or "").lower().startswith(SCHEDULE_SOURCE_PREFIX) for row in schedule_rows):
        result["error"] = f"No automated nflverse schedule is stored for {season}, so completed games cannot be verified and nothing is published."
        return result
    through_week = completed_week_boundary(schedule_rows)
    if not through_week:
        result.update(status="no_completed_week", exit_code=0,
                      message=f"No {season} week is complete in the automated nflverse schedule, so nothing is fetched or published.")
        return result
    result["through_week"] = through_week
    try:
        before = stored(connection, season)
    except Exception as exc:
        before = {}
        result["stored_before_error"] = f"{type(exc).__name__}: {exc}"
        _rollback(connection)
    for key, step in steps:
        entry: dict[str, Any] = {"stored_before": before.get(key)}
        stage = "acquisition"
        try:
            evidence, blocker_of, publish = step(season, through_week, environ)
            provenance = evidence.get("provenance") or {}
            weeks = sorted({int(week) for week in evidence.get("weeks") or []})
            entry["acquired"] = {
                "artifact": provenance.get("source_location"), "version": provenance.get("version"), "checksum": provenance.get("checksum"),
                "source_recorded_at": provenance.get("source_recorded_at"), "retrieved_at": provenance.get("retrieved_at"), "weeks": weeks,
                "rows": len(evidence.get("rows") or []), "publication_blocker": blocker_of(evidence),
                "source_update": _source_update(before.get(key), provenance.get("checksum")),
                "reconciliation": {name: value for name, value in (evidence.get("reconciliation") or {}).items() if not isinstance(value, (list, dict))}}
            stage = "validation"
            if weeks and max(weeks) > through_week:
                raise ValueError(f"evidence includes Week {max(weeks)}, after the completed Week {through_week}")
            if dry_run:
                entry.update(state="DRY_RUN", prior_evidence="RETAINED")
            else:
                stage = "publication"
                entry.update(state="PUBLISHED", rows_published=publish(connection, evidence), prior_evidence="REPLACED")
        except Exception as exc:
            # Nothing was written for this source: acquisition and validation precede any write, and each publisher rolls back.
            entry.update(state="FAILED", stage=stage, error=f"{type(exc).__name__}: {exc}", prior_evidence="RETAINED")
        result["sources"][key] = entry
    try:
        after = evaluate(connection, season, through_week, schedule_rows, environ)
    except Exception as exc:
        _rollback(connection)
        after = {key: {"currency": "BLOCKED", "reason": f"Evaluation: {type(exc).__name__}: {exc}"} for key, _ in steps}
    for key, entry in result["sources"].items():
        entry["stored"] = after.get(key) or {"currency": "UNAVAILABLE", "reason": "The stored evidence could not be evaluated."}
        result["sources"][key] = {name: entry[name] for name in ENTRY_ORDER if name in entry}
    entries = list(result["sources"].values())
    if dry_run:
        ready = sum(entry["state"] == "DRY_RUN" for entry in entries)
        status = "success" if entries and ready == len(entries) else "partial" if ready else "failed"
    else:
        published = [entry for entry in entries if entry["state"] == "PUBLISHED"]
        current = [entry for entry in entries if entry["stored"].get("currency") == "CURRENT"]
        if not published:
            status = "failed"
        elif len(published) < len(entries) or len(current) < len(entries):
            # Some evidence was published, but /waivers would not show every source as current.
            status = "partial"
        elif all(entry["acquired"]["source_update"] == "UNCHANGED" for entry in published):
            status = "no_source_update"
        else:
            status = "success"
    result.update(status=status, exit_code=EXIT_CODES.get(status, 1))
    return result


def _emit(result: Mapping[str, Any]) -> int:
    print(json.dumps(result, indent=2, default=str))
    return int(result.get("exit_code", 1))


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
            return _emit({"status": "failed", "exit_code": 1, "error": f"Season could not be read from Sleeper ({type(exc).__name__}); pass --season."})
    import psycopg2
    from config import Config
    try:
        connection = psycopg2.connect(**Config.db_kwargs())
    except Exception as exc:
        # The driver's message can name the host and user, so only the error type is reported.
        return _emit({"season": season, "status": "failed", "exit_code": 1,
                      "error": f"Database connection failed ({type(exc).__name__}); nothing was fetched or written."})
    try:
        if args.dry_run:
            connection.set_session(readonly=True)
        result = refresh_opportunity_evidence(connection, season=season, dry_run=args.dry_run)
    finally:
        connection.close()
    return _emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
