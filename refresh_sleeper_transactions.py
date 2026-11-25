#!/usr/bin/env python3
"""Refresh this league's Sleeper transaction history for the Waivers FAAB market evidence.

Read-only Sleeper requests (the league, then GET /league/{league_id}/transactions/{week} once per week of the season through the
league's current week). Each week that is retrieved is stored in sleeper_api_snapshots (resource type 'transactions'); a week
that fails is reported by number and its previously stored snapshot is kept. The run is recorded in sleeper_sync_runs.
Viewing /waivers never runs this; it only reads what this command stored. scheduler/sleeper-transactions-refresh.timer runs this
same command after each weekly waiver run; running it by hand is unchanged.

After storing, the command re-reads the stored weeks and reports W5's own verdict on each (build_faab_market_evidence, the
evaluation /waivers uses): a stored week counts as history only if a later week's transaction already existed when it was
retrieved, so the open week, a week retrieved before it closed and a missing week never count, while a week retrieved as an empty
list after it closed is verified empty. The verdict is only reported: sleeper_sync_runs keeps the retrieval outcome that W5 reads.

Usage: python refresh_sleeper_transactions.py [--league-id ID] [--season YEAR] [--dry-run]
Prints one JSON result. Status and exit code:
  success 0             every week was stored and every closed week is verified, at least one of them newly
  no_new_closed_week 0  every week was stored and every closed week is verified, none newly (or no week has closed yet)
  partial 2             a week failed, or a closed week is missing, was retrieved before it closed, is invalid or is contradictory
  failed 1              no usable refresh: no league id, the league or every week unavailable, or a database error (the error says what was stored)
--dry-run retrieves and reports each week without connecting to the database (success, partial or failed for retrieval only).
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

from services.sleeper_service import get_league, get_transactions
from services.sleeper_snapshots import read_transaction_history, refresh_transaction_history
from services.waiver_market_evidence import build_faab_market_evidence

EXIT_CODES = {"success": 0, "no_new_closed_week": 0, "partial": 2}
# Claim counts only: the run reports what is stored, never a bid figure.
SAMPLE_COUNTS = ("waiver_claims", "completed", "failed", "pending", "missing_bids", "zero_bid_completed", "contested", "uncontested", "free_agent_adds")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _instant(value: Any) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: Any) -> str | None:
    instant = _instant(value)
    return instant.astimezone(timezone.utc).isoformat() if instant else None


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _league_season(league: Any) -> int | None:
    try:
        return int(league.get("season"))
    except (AttributeError, TypeError, ValueError):
        return None


def closure_verdict(league: Mapping[str, Any], history: Mapping[str, Any], *, league_id: str, season: int) -> dict[str, Any]:
    """W5's own verdict on the stored weeks, exactly as /waivers evaluates them; closure and coverage need no users, rosters or catalog."""
    market = build_faab_market_evidence(league_id=league_id, season=season, league=league, users=None, rosters=None, history=history, catalog=None)
    completeness = market.get("completeness") or {}
    summary = market.get("season_summary")
    return {
        "market_state": market.get("state"), "completeness": completeness.get("state"), "through_week": market.get("through_week"),
        "expected_weeks": completeness.get("expected_weeks"), "weeks": {int(week): state for week, state in (completeness.get("weeks") or {}).items()},
        "verified_weeks": completeness.get("verified_weeks") or [], "open_at_retrieval_weeks": completeness.get("open_at_retrieval_weeks") or [],
        "missing_weeks": completeness.get("missing_weeks") or [], "invalid_weeks": completeness.get("invalid_weeks") or [],
        "empty_verified_weeks": completeness.get("empty_verified_weeks") or [],
        "conflicting_transaction_ids": completeness.get("conflicting_transaction_ids") or [], "duplicates_removed": completeness.get("duplicates_removed"),
        "coverage": completeness.get("text") or market.get("reason"), "sample": {key: summary.get(key) for key in SAMPLE_COUNTS} if isinstance(summary, dict) else None,
    }


def _read(connection: Any, league_id: str, season: int) -> dict[str, Any]:
    cursor = connection.cursor()
    try:
        return read_transaction_history(cursor, league_id, season)
    finally:
        cursor.close()


def _result(league_id: str, season: int | None, dry_run: bool) -> dict[str, Any]:
    return {"status": "failed", "exit_code": 1, "league_id": league_id, "season": season, "dry_run": dry_run, "league_leg": None, "start_week": None,
            "requested_weeks": [], "fetched_weeks": [], "stored_weeks": [], "failed_weeks": [], "verified_closed_weeks": None, "newly_verified_weeks": None,
            "no_longer_verified_weeks": None, "open_weeks": None, "open_at_retrieval_weeks": None, "missing_weeks": None, "invalid_weeks": None,
            "empty_verified_weeks": None, "completeness_before": None, "completeness": None, "market_state": None, "through_week": None, "coverage": None,
            "conflicting_transaction_ids": None, "duplicates_removed": None, "sample_before": None, "sample": None, "fetch_status": None, "run_id": None,
            "requests": 0, "run_started_at": _now().isoformat(), "run_finished_at": None, "error": None, "weeks": []}


def _finish(result: dict[str, Any], status: str, error: str | None = None) -> dict[str, Any]:
    result.update(status=status, exit_code=EXIT_CODES.get(status, 1), run_finished_at=_now().isoformat())
    if error:
        result["error"] = error
    return result


def refresh_league_transactions(connection: Any, *, league_id: Any, season: int | None = None, dry_run: bool = False, get_league: Callable = get_league,
                                get_transactions: Callable = get_transactions, now: Callable[[], datetime] = _now) -> dict[str, Any]:
    """Run the existing transaction-history refresh once and report each week's retrieval, storage and W5 closure verdict."""
    league_id = str(league_id or "").strip()
    result = _result(league_id, season, dry_run)
    if not league_id:
        return _finish(result, "failed", "No Sleeper league id is configured (SLEEPER_LEAGUE_ID or --league-id); nothing was fetched or written.")
    try:
        league, league_error = get_league(league_id), None
    except Exception as exc:
        league, league_error = None, exc

    def replay_league(requested_id: Any) -> Any:
        # The refresh validates and records this same response (or failure), so a run makes one league request.
        if league_error is not None:
            raise league_error
        return league

    source: dict[int, dict[str, Any]] = {}

    def observe_week(requested_id: Any, week: int) -> Any:
        try:
            payload = get_transactions(requested_id, week)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            status = status if isinstance(status, int) else None
            source[week] = {"source_state": "HTTP_ERROR" if status else "REQUEST_FAILED", "http_status": status}
            raise
        source[week] = {"source_state": "TRANSACTION_LIST" if isinstance(payload, list) else "NOT_A_TRANSACTION_LIST", "http_status": None}
        return payload

    # Database and driver messages can name the host or user, so a failure reports only its type.
    failure = ("Reading the stored transaction history", "no transaction week was fetched or written.")
    try:
        read_season = season if season is not None else _league_season(league)
        before = _read(connection, league_id, read_season) if not dry_run and read_season is not None else None
        failure = ("The refresh", "no transaction week from this run was stored.")
        refresh = refresh_transaction_history(connection, league_id=league_id, season=season, get_league=replay_league, get_transactions=observe_week,
                                              dry_run=dry_run, now=now)
        outcomes = refresh["weeks"]
        requested = sorted(outcomes)
        result.update(season=refresh["season"], league_leg=refresh["league_leg"], start_week=refresh["start_week"], run_id=refresh["run_id"],
                      fetch_status=refresh["status"], requests=refresh["requests"], error=refresh["error"], requested_weeks=requested,
                      fetched_weeks=[week for week in requested if outcomes[week]["ok"]], failed_weeks=refresh["failed_weeks"])
        after = verdict = verdict_before = None
        if requested and not dry_run:
            failure = ("Re-reading the stored transaction history", "this run's weeks were stored but their closure was not verified.")
            after = _read(connection, league_id, result["season"])
            verdict = closure_verdict(league, after, league_id=league_id, season=result["season"])
            verdict_before = closure_verdict(league, before, league_id=league_id, season=result["season"]) if before is not None else None
    except Exception as exc:
        return _finish(result, "failed", f"{failure[0]} failed ({type(exc).__name__}); {failure[1]}")

    prior = {row["week"]: row for row in (before or {}).get("rows") or []}
    stored = {row["week"]: row for row in (after or {}).get("rows") or []}
    for week in requested:
        outcome, old, new = outcomes[week], prior.get(week), stored.get(week)
        fetched = outcome.get("ok") is True
        written = fetched and new is not None and _instant(new["fetched_at"]) == _instant(outcome.get("requested_at"))
        if dry_run:
            snapshot = "NOT_WRITTEN_DRY_RUN"
        elif fetched:
            snapshot = "STORED" if written else "NOT_CONFIRMED"
        else:
            snapshot = "RETAINED" if new is not None else "MISSING"
        result["weeks"].append({
            "week": week, "fetch_state": "FETCHED" if fetched else "FAILED", **source.get(week, {"source_state": None, "http_status": None}),
            "transaction_count": outcome.get("count"), "snapshot": snapshot, "prior_snapshot": None if dry_run else old is not None,
            "prior_snapshot_retained": None if dry_run or fetched else (old is not None and new is not None and _instant(new["fetched_at"]) == _instant(old["fetched_at"])),
            "payload_changed": _canonical(old["payload"]) != _canonical(new["payload"]) if written and old is not None else None,
            "requested_at": outcome.get("requested_at"), "retrieved_at": _iso(new["fetched_at"]) if new else None,
            "stored_transaction_count": len(new["payload"]) if new and isinstance(new.get("payload"), list) else None,
            "closed_state_before": verdict_before["weeks"].get(week) if verdict_before else None, "closed_state": verdict["weeks"].get(week) if verdict else None,
            "error": outcome.get("error"),
        })
    result["stored_weeks"] = [entry["week"] for entry in result["weeks"] if entry["snapshot"] == "STORED"]
    if verdict:
        verified, verified_before = verdict["verified_weeks"], (verdict_before or {}).get("verified_weeks") or []
        result.update(verified_closed_weeks=verified, newly_verified_weeks=sorted(set(verified) - set(verified_before)),
                      no_longer_verified_weeks=sorted(set(verified_before) - set(verified)),
                      open_weeks=[week for week, state in sorted(verdict["weeks"].items()) if state == "OPEN"],
                      open_at_retrieval_weeks=verdict["open_at_retrieval_weeks"], missing_weeks=verdict["missing_weeks"], invalid_weeks=verdict["invalid_weeks"],
                      empty_verified_weeks=verdict["empty_verified_weeks"], completeness_before=(verdict_before or {}).get("completeness"),
                      completeness=verdict["completeness"], market_state=verdict["market_state"], through_week=verdict["through_week"], coverage=verdict["coverage"],
                      conflicting_transaction_ids=verdict["conflicting_transaction_ids"], duplicates_removed=verdict["duplicates_removed"],
                      sample_before=(verdict_before or {}).get("sample"), sample=verdict["sample"])
    if dry_run:
        status = refresh["status"]
    elif refresh["status"] == "failed" or verdict is None:
        status = "failed"
    elif refresh["status"] != "success" or any(entry["snapshot"] != "STORED" for entry in result["weeks"]):
        status = "partial"
    elif verdict["completeness"] == "COMPLETE":
        status = "success" if result["newly_verified_weeks"] else "no_new_closed_week"
    elif verdict["completeness"] == "UNAVAILABLE" and verdict["expected_weeks"] == []:
        # The season's first transaction week is still open: no week has closed yet.
        status = "no_new_closed_week"
    else:
        status = "partial"
    return _finish(result, status)


def _emit(result: Mapping[str, Any]) -> int:
    print(json.dumps(result, indent=2, default=str))
    return int(result.get("exit_code", 1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh Sleeper transaction history for the Waivers FAAB market evidence (read-only Sleeper requests).")
    parser.add_argument("--league-id", default=None, help="Sleeper league id (default: SLEEPER_LEAGUE_ID from the environment or the repository .env).")
    parser.add_argument("--season", type=int, default=None, help="Season to refresh; must match the league's season (default: the league's season).")
    parser.add_argument("--dry-run", action="store_true", help="Retrieve and report each week without connecting to or writing the database.")
    args = parser.parse_args(argv)
    from dotenv import load_dotenv
    # Unattended runs read the same repository .env a configured shell would; variables already set still win.
    load_dotenv()
    league_id = (args.league_id if args.league_id is not None else os.getenv("SLEEPER_LEAGUE_ID", "")).strip()
    connection = None
    if not args.dry_run:
        import psycopg2
        from config import Config
        try:
            connection = psycopg2.connect(**Config.db_kwargs())
        except Exception as exc:
            return _emit(_finish(_result(league_id, args.season, False), "failed",
                                 f"Database connection failed ({type(exc).__name__}); nothing was fetched or written."))
    try:
        result = refresh_league_transactions(connection, league_id=league_id, season=args.season, dry_run=args.dry_run)
    finally:
        if connection is not None:
            connection.close()
    return _emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
