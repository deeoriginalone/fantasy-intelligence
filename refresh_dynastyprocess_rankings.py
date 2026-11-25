#!/usr/bin/env python3
"""Refresh the shared DynastyProcess consensus-ranking cache that Waivers and My Team read, independently of page views.

Fresh current-week FantasyPros PPR positional consensus (ECR) orders Waivers, and it counts only while its upstream scrape_date is
within 48 hours (rest of season: seven days). DynastyProcess publishes the weekly file about twice a day, but the cache used to be
renewed only when My Team was opened or Refresh Waiver Intelligence was pressed, so it could age past that limit while newer rankings
sat upstream. This command closes that gap without changing any ranking rule:

1. reads the NFL season and week from Sleeper's NFL state, the input My Team and Waivers already give the ranking service;
2. reacquires the latest commit-pinned DynastyProcess release and atomically replaces instance/dynastyprocess-rankings.json through
   services.dynastyprocess_rankings.refresh_rankings(force=True), as the Waivers refresh button does; forcing skips only the six-hour
   on-use guard, which page views keep;
3. reads the published cache back with read_cached_rankings, as GET /waivers does, and evaluates it with Sleeper's current player
   catalog against that week.

Freshness stays governed by each artifact's scrape_date (day precision, midnight UTC): reacquiring an old file renews only the
retrieval time. A failed acquisition keeps the previous release, source dates and last successful retrieval and records the failure.
Viewing /waivers never runs this command; scheduler/dynastyprocess-rankings-refresh.timer does, and it stays usable by hand.

Usage: python refresh_dynastyprocess_rankings.py
Status (exit code): success (0) a new upstream commit is published and fresh current-week ranks exist for the verified week at every
supported position; no_source_update (0) the same, with the upstream commit unchanged; partial (2) the cache is published, but
current-week ranks are stale, unavailable for the verified week, missing a position, or could not be checked against Sleeper's player
catalog; failed (1) the NFL week could not be read or verified, the release could not be acquired or published, or its current-week
source date is in the future.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import dynastyprocess_rankings as rankings

# The routes read current_app.instance_path + "/dynastyprocess-rankings.json"; app.py's instance directory is this repository's instance/.
CACHE_PATH = ROOT / "instance" / "dynastyprocess-rankings.json"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
HORIZONS = (("current_week", "this_week"), ("rest_of_season", "rest_of_season"))
EXIT_CODES = {"success": 0, "no_source_update": 0, "partial": 2}
# Nothing current was acquired, published or verifiable for the week; any other blocker leaves a published but unusable source.
FAILED_BLOCKERS = {"NFL_STATE_UNAVAILABLE", "SOURCE_ACQUISITION_FAILED", "CACHE_PUBLICATION_FAILED", "NFL_WEEK_UNVERIFIED",
                   "CURRENT_WEEK_SOURCE_FUTURE_DATED"}
# The ranking service's rejection when Sleeper's state is not a regular-season week of the source's season.
WEEK_UNVERIFIED_REASON = "Season or NFL week is unverified"
AUTHORITY = ("Ranking evidence refresh only: no freshness limit, week, scoring or identity rule, waiver decision, confidence or FAAB "
             "value changes, and nothing is submitted to Sleeper.")


def _horizon_view(published: Mapping[str, Any], previous: Mapping[str, Any], horizon: str) -> dict[str, Any]:
    data = (published.get("horizons") or {}).get(horizon) or {}
    before = (previous.get("horizons") or {}).get(horizon) or {}
    ranks = data.get("ranks") or {}
    counts = {position: 0 for position in POSITIONS}
    for row in ranks.values():
        if row.get("position") in counts:
            counts[row["position"]] += 1
    return {"state": data.get("state") or "UNAVAILABLE", "source_date": data.get("latest_source_date"),
            "previous_source_date": before.get("latest_source_date"), "freshness_state": data.get("freshness_state") or "UNAVAILABLE",
            "source_age_seconds": data.get("latest_source_age_seconds"), "threshold_seconds": data.get("max_age_seconds"),
            "published_rank_count": len(ranks), "supported_source_row_count": (data.get("reconciliation") or {}).get("supported_scope_rows", 0),
            "position_counts": counts, "rejections": dict(sorted((data.get("rejections") or {}).items())),
            "source_url": data.get("source_url"), "checksum": data.get("checksum"),
            "artifact_changed": None if not data.get("checksum") else data.get("checksum") != before.get("checksum")}


def _current_week_blockers(view: dict[str, Any]) -> list[str]:
    """Why the published current-week source cannot order Waivers now; empty when it can at every supported position."""
    blockers = ["NFL_WEEK_UNVERIFIED"] if WEEK_UNVERIFIED_REASON in view["rejections"] else []
    freshness = view["freshness_state"]
    if freshness == "FUTURE_DATED":
        blockers.append("CURRENT_WEEK_SOURCE_FUTURE_DATED")
    elif freshness == "STALE":
        blockers.append("CURRENT_WEEK_SOURCE_STALE")
    elif freshness != "FRESH":
        blockers.append("CURRENT_WEEK_SOURCE_UNAVAILABLE")
    elif view["state"] != "AVAILABLE" or not view["published_rank_count"]:
        blockers.append("CURRENT_WEEK_RANKS_UNAVAILABLE")
    elif missing := [position for position, count in view["position_counts"].items() if not count]:
        blockers.append("CURRENT_WEEK_POSITION_COVERAGE_INCOMPLETE")
        view["missing_positions"] = missing
    return blockers


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    blockers = result["blockers"] = list(dict.fromkeys(result["blockers"]))
    if FAILED_BLOCKERS & set(blockers):
        status = "failed"
    elif blockers:
        status = "partial"
    elif result.get("source_changed") is False:
        status = "no_source_update"
    else:
        status = "success"
    result.update(status=status, exit_code=EXIT_CODES.get(status, 1), run_finished_at=datetime.now(timezone.utc).isoformat())
    return result


def refresh_dynastyprocess_rankings(cache_path: Path | str = CACHE_PATH, *, now: datetime | None = None,
                                    read_nfl_state: Callable[[], Any] | None = None,
                                    read_catalog: Callable[[], Any] | None = None) -> dict[str, Any]:
    from services.sleeper_service import get_all_players, get_nfl_state
    now = now or datetime.now(timezone.utc)
    result: dict[str, Any] = {
        "status": "failed", "exit_code": 1, "run_started_at": now.isoformat(), "run_finished_at": None, "season": None, "season_type": None,
        "week": None, "scope": None, "source": rankings.SOURCE, "source_repository": None, "source_commit": None, "previous_source_commit": None,
        "source_changed": None, "last_attempt": None, "last_successful_refresh": None, "refresh_error": None, "current_week": None,
        "rest_of_season": None, "blockers": [], "warnings": [], "authority": AUTHORITY}
    try:
        state = dict((read_nfl_state or get_nfl_state)() or {})
        season, week, season_type = int(state["season"]), int(state["week"]), str(state["season_type"])
        if not state.get("season_start_date"):
            raise ValueError("season_start_date missing")
    except Exception as exc:
        # Only the error type is reported: a request error message can carry URLs or other request details.
        result["blockers"].append("NFL_STATE_UNAVAILABLE")
        result["error"] = f"Sleeper NFL state could not be read ({type(exc).__name__}); the ranking cache was not changed."
        return _finish(result)
    # The same scope refresh_rankings stores, so a new NFL week is always evaluated against its own week.
    result.update(season=season, season_type=season_type, week=week, scope=":".join(str(state.get(key)) for key in ("season", "season_type", "week")))
    previous = rankings.read_cached_rankings(cache_path, state, now=now)
    result["previous_source_commit"] = previous.get("version")
    try:
        catalog = (read_catalog or get_all_players)()
        if not isinstance(catalog, Mapping) or not catalog:
            raise ValueError("empty player catalog")
    except Exception as exc:
        # Without the catalog, team defenses and owner-approved identities cannot be verified, exactly as on the page.
        catalog = None
        result["blockers"].append("SLEEPER_CATALOG_UNAVAILABLE")
        result["sleeper_catalog_error"] = type(exc).__name__
    refreshed = rankings.refresh_rankings(cache_path, state, now=now, sleeper_catalog=catalog, force=True)
    published = rankings.read_cached_rankings(cache_path, state, now=now, sleeper_catalog=catalog)
    stamp = now.isoformat()
    result.update(source_commit=published.get("version"), last_attempt=published.get("last_attempt"),
                  last_successful_refresh=published.get("last_successful_refresh"),
                  refresh_error=refreshed.get("refresh_error") or published.get("refresh_error"))
    if published.get("last_attempt") != stamp:
        result["blockers"].append("CACHE_PUBLICATION_FAILED")
    elif published.get("refresh_error") or published.get("last_successful_refresh") != stamp:
        result["blockers"].append("SOURCE_ACQUISITION_FAILED")
    else:
        result["source_changed"] = published.get("version") != result["previous_source_commit"]
    for name, horizon in HORIZONS:
        result[name] = _horizon_view(published, previous, horizon)
    repository = re.match(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/", result["current_week"]["source_url"] or result["rest_of_season"]["source_url"] or "")
    result["source_repository"] = repository.group(1) if repository else None
    result["blockers"].extend(_current_week_blockers(result["current_week"]))
    ros = result["rest_of_season"]
    if ros["freshness_state"] != "FRESH":
        result["warnings"].append(f"REST_OF_SEASON_SOURCE_{ros['freshness_state']}")
    elif ros["state"] != "AVAILABLE":
        result["warnings"].append("REST_OF_SEASON_RANKS_UNAVAILABLE")
    return _finish(result)


def _emit(result: Mapping[str, Any]) -> int:
    print(json.dumps(result, indent=2, default=str))
    return int(result.get("exit_code", 1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reacquire the DynastyProcess consensus rankings that Waivers and My Team read (current week "
                                                 "and rest of season) and report whether current-week ranks are usable.")
    parser.parse_args(argv)
    return _emit(refresh_dynastyprocess_rankings(CACHE_PATH))


if __name__ == "__main__":
    raise SystemExit(main())
