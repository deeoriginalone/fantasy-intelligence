"""W6 waiver role and opportunity evidence: what a player's completed-game workload shows, and nothing more.

waiver.opportunity_observation.v1 normalizes one player's completed game from the stored, source-faithful nflverse rows that the
explicit refresh (refresh_opportunity_evidence.py) publishes: offensive snap share from snap_counts (snap_share_evidence, the PFR
player ID joined to GSIS through the nflverse players release) and targets and carries from stats_player_week
(player_opportunity_evidence, published by GSIS ID). Players are linked by the waiver route's existing exact GSIS identity; names are
never matched. waiver.opportunity_trend.v1 compares a player only with himself across his latest supported completed games, and
waiver.role_persistence.v1 says whether an observed change held across those games.

Pure and read-only: no network or database access and no writes. Informational only (INFORMATIONAL_ONLY): it never changes a waiver
move, its order, drop safety, rest-of-season materiality, replacement context, FAAB evidence or decision confidence, and it never
produces a score, forecast, bid or breakout label. Direction is only the sign of change across games; no magnitude threshold exists,
so a direction never means a significant change. Observed persistence looks backward. Future duration stays UNVERIFIED because no
forward-looking contract (injury return timing, depth chart authority, team statement) exists.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from math import isfinite
from numbers import Number
from typing import Any, Mapping, Sequence

from services.game_lock import SCHEDULE_SOURCE_PREFIX, utc_datetime
from services.lineup_forward_validation import game_finality
from services.team_codes import canonical_team

OBSERVATION_CONTRACT_ID = "waiver.opportunity_observation.v1"
TREND_CONTRACT_ID = "waiver.opportunity_trend.v1"
PERSISTENCE_CONTRACT_ID = "waiver.role_persistence.v1"
RECOMMENDATION_IMPACT = "INFORMATIONAL_ONLY"
EVIDENCE_LEVEL = "PRELIMINARY"
WINDOW_GAMES = 3
REFRESH_COMMAND = "python refresh_opportunity_evidence.py"
ATTRIBUTION = "nflverse data (CC BY 4.0)"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
SUPPORTED_POSITIONS = ("QB", "RB", "WR", "TE")
POSITION_METRICS = {"QB": ("snap_share", "carries"), "RB": ("snap_share", "carries", "targets"), "WR": ("snap_share", "targets"),
                    "TE": ("snap_share", "targets")}
METRIC_SOURCE = {"snap_share": "snap_counts", "targets": "stats_player_week", "carries": "stats_player_week"}
METRIC_LABELS = {"snap_share": "snap share", "targets": "targets", "carries": "carries"}
SOURCE_LABELS = {"snap_counts": "nflverse snap_counts (offensive snap share)", "stats_player_week": "nflverse stats_player_week (targets, carries)"}
SOURCE_THRESHOLDS = {"snap_counts": "snap_share.evidence.v1", "stats_player_week": "opportunity.evidence.v1"}
CURRENT_FRESHNESS = ("FRESH", "AGING")
FRESHNESS_ORDER = {"FRESH": 0, "AGING": 1, "STALE": 2, "EXPIRED": 3, "UNAVAILABLE": 4, "BLOCKED": 5}
IDENTITY_CONFLICT_STATES = ("AMBIGUOUS", "CONTRADICTORY", "CONFLICTING", "BLOCKED")
DIRECTION_STATES = ("DIRECTION_UP", "DIRECTION_DOWN", "FLAT", "MIXED", "CURRENT_ROLE_ONLY", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE",
                    "CONTRADICTORY")
DIRECTION_LABELS = {"DIRECTION_UP": "DIRECTION UP", "DIRECTION_DOWN": "DIRECTION DOWN", "FLAT": "FLAT", "MIXED": "MIXED",
                    "CURRENT_ROLE_ONLY": "CURRENT ROLE ONLY", "INSUFFICIENT_EVIDENCE": "INSUFFICIENT EVIDENCE", "NOT_APPLICABLE": "NOT APPLICABLE",
                    "CONTRADICTORY": "CONTRADICTORY"}
# TEMPORARY_ROLE_RISK is reserved: neither stored source verifies a teammate's absence or return, so it is never produced.
PERSISTENCE_STATES = ("PERSISTED_ACROSS_OBSERVED_GAMES", "TEMPORARY_ROLE_RISK", "DURATION_UNVERIFIED", "NOT_APPLICABLE", "CONTRADICTORY")
SAMPLE_STATES = {0: "NO_EVIDENCE", 1: "CURRENT_ROLE_ONLY", 2: "LIMITED_HISTORY", 3: "MULTI_GAME_HISTORY"}
SERIES_WORDS = {"UP": "up", "DOWN": "down", "FLAT": "unchanged", "MIXED": "up and down"}
RESULT_STATES = ("CURRENT", "HISTORICAL_ONLY", "NO_EVIDENCE", "IDENTITY_UNRESOLVED", "CONTRADICTORY", "BLOCKED", "NOT_APPLICABLE")
DURATION_REASON = ("No supported forward-looking evidence establishes how long this role will last; completed-game workload does not show why the role "
                   "changed.")
DIRECTION_RULE = ("Direction compares a player only with himself across his latest supported completed games (up to 3): up when a metric never "
                  "falls and rises at least once, down when it never rises and falls at least once, mixed when it does both or metrics disagree, "
                  "flat when nothing changes. It is the sign of change, not its size, and it never ranks players or changes a move.")
METRIC_DEFINITIONS = {
    "snap_share": {
        "name": "Offensive snap share", "unit": "ratio 0-1 of the team's offensive snaps in one completed game (shown as a percent)",
        "purpose": "How much of the offense the player was on the field for; participation, not player value.",
        "source": "nflverse snap_counts offense_pct (Pro Football Reference), stored in snap_share_evidence; the offense_snaps count is kept in lineage",
        "valid_range": "finite, 0 to 1 inclusive, offensive participation domain only",
        "directionality": "higher = more of the offense on the field; it does not mean a better player",
        "freshness": "snap_share.evidence.v1 (SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS) on retrieved_at",
        "missing": "no snap row = participation unknown, never 0; a stored 0 (for example a special-teams-only game) stays 0",
        "decision_use": RECOMMENDATION_IMPACT, "owner": "services.waiver_role_evidence", "tests": "tests/test_waiver_role_evidence.py",
    },
    "targets": {
        "name": "Targets", "unit": "count per completed game", "purpose": "How many passes were thrown to the player.",
        "source": "nflverse stats_player_week targets, stored in player_opportunity_evidence",
        "valid_range": "finite whole number, 0 or more", "directionality": "higher = more passes thrown to the player",
        "freshness": "opportunity.evidence.v1 (OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS) on retrieved_at",
        "missing": "no stats row = unavailable for that game (the source lists only players credited with a statistic), never 0; a stored 0 stays 0",
        "decision_use": RECOMMENDATION_IMPACT, "owner": "services.waiver_role_evidence", "tests": "tests/test_waiver_role_evidence.py",
    },
    "carries": {
        "name": "Carries", "unit": "rushing attempts per completed game as published by nflverse (designed runs are not separated)",
        "purpose": "How many times the player ran the ball.", "source": "nflverse stats_player_week carries, stored in player_opportunity_evidence",
        "valid_range": "finite whole number, 0 or more", "directionality": "higher = more rushing attempts",
        "freshness": "opportunity.evidence.v1 (OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS) on retrieved_at",
        "missing": "no stats row = unavailable for that game, never 0; a stored 0 stays 0",
        "decision_use": RECOMMENDATION_IMPACT, "owner": "services.waiver_role_evidence", "tests": "tests/test_waiver_role_evidence.py",
    },
}
UNSUPPORTED_METRICS = {
    "route_participation": "routes and route participation (not in either stored source)",
    "target_share": "target share (the stored share divides by targets on the team's published QB/RB/WR/TE rows, not a provider team total)",
    "carry_share": "rush share (the stored share divides by carries on the team's published QB/RB/WR/TE rows, not a provider team total)",
    "red_zone": "red-zone, goal-line and end-zone opportunities (not in either stored source)",
    "air_yards": "air yards (in the source artifact but not stored)",
    "pass_attempts": "pass attempts and dropbacks (pass attempts are in the source artifact but not stored)",
}
POSITION_UNSUPPORTED = {"QB": ("pass_attempts",), "RB": ("carry_share", "target_share", "route_participation", "red_zone"),
                        "WR": ("target_share", "route_participation", "air_yards", "red_zone"), "TE": ("target_share", "route_participation", "red_zone")}
NOT_APPLICABLE_REASONS = {"K": "No individual offensive-role contract exists for kickers.",
                          "DEF": "Team defenses have no individual offensive-role evidence."}
STATS_COMPARE = ("team", "targets", "carries", "fantasy_points_ppr")
SNAP_COMPARE = ("team", "snap_share", "participation_domain", "source_snap_count")


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _plain(value: Any) -> Any:
    return float(value) if isinstance(value, Number) and not isinstance(value, bool) else value


def _count(value: Any) -> tuple[str, int | None]:
    """A source count is a finite whole number of zero or more; anything else is INVALID and never becomes zero."""
    if value is None:
        return "UNAVAILABLE", None
    if isinstance(value, bool) or not isinstance(value, Number):
        return "INVALID", None
    number = float(value)
    if not isfinite(number) or number < 0 or not number.is_integer():
        return "INVALID", None
    return "AVAILABLE", int(number)


def _share(value: Any) -> tuple[str, float | None]:
    """A share is the provider's 0-1 ratio, used as stored (never rescaled from a percent)."""
    if value is None:
        return "UNAVAILABLE", None
    if isinstance(value, bool) or not isinstance(value, Number):
        return "INVALID", None
    number = float(value)
    if not isfinite(number) or not 0 <= number <= 1:
        return "INVALID", None
    return "AVAILABLE", number


def _whole(value: Any) -> int | None:
    if isinstance(value, str) and re.fullmatch(r"\s*\d+\s*", value):
        return int(value)
    state, number = _count(value)
    return number if state == "AVAILABLE" else None


def _time_text(value: Any) -> str | None:
    stamp = utc_datetime(value)
    return stamp.strftime("%Y-%m-%d %H:%M UTC") if stamp else None


def _weeks_text(weeks: Sequence[int]) -> str:
    weeks = list(weeks)
    if not weeks:
        return "no weeks"
    return f"Week {weeks[0]}" if len(weeks) == 1 else "Weeks " + ", ".join(str(week) for week in weeks)


def _span_text(first: int, last: int) -> str:
    return f"Week {first}" if first == last else f"Weeks {first}–{last}"


def _ranges_text(weeks: Sequence[int]) -> str:
    """Consecutive weeks collapse into ranges: Weeks 4–9, 11."""
    runs: list[list[int]] = []
    for week in sorted(weeks):
        if runs and week == runs[-1][-1] + 1:
            runs[-1].append(week)
        else:
            runs.append([week])
    parts = [str(run[0]) if len(run) == 1 else f"{run[0]}–{run[-1]}" for run in runs]
    return ("Week " if len(weeks) == 1 else "Weeks ") + ", ".join(parts)


def completed_week_boundary(schedule_rows: Sequence[Mapping[str, Any]] | None, *, through_week: int | None = None) -> int:
    """Latest week W such that every scheduled game in Weeks 1..W has a result published by the automated schedule (0 if none)."""
    by_week: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in schedule_rows or []:
        week = _int((row or {}).get("week"))
        if week and week >= 1:
            by_week[week].append(row)
    boundary = 0
    for week in range(1, (max(by_week) if by_week else 0) + 1):
        if through_week is not None and week > through_week:
            break
        games = by_week.get(week) or []
        if not games or not all(str(game.get("source") or "").lower().startswith(SCHEDULE_SOURCE_PREFIX) and game.get("result") not in (None, "")
                                for game in games):
            break
        boundary = week
    return boundary


def _source_currency(key: str, read: Mapping[str, Any] | None, by_week: Mapping[int, Sequence[Mapping[str, Any]]], completed: int) -> dict[str, Any]:
    """Whether one stored source covers every completed game through the latest completed week and is within its freshness limit."""
    base = {"source": key, "label": SOURCE_LABELS[key], "metrics": [name for name, source in METRIC_SOURCE.items() if source == key],
            "threshold_id": SOURCE_THRESHOLDS[key], "threshold_seconds": None, "verified_through_week": 0, "completed_through_week": completed,
            "completeness": "UNAVAILABLE", "freshness_state": "UNAVAILABLE", "retrieved_at": None, "source_recorded_at": None, "currency": "UNAVAILABLE",
            "blocker": None, "reason": None}
    if not isinstance(read, Mapping) or read.get("state") != "READ":
        blocker = next(iter((read or {}).get("blockers") or []), None) if isinstance(read, Mapping) else None
        return {**base, "currency": "BLOCKED", "blocker": blocker or f"{key.upper()}_UNREAD", "reason": "Stored rows could not be read for this page view."}
    threshold = read.get("threshold") or {}
    base["threshold_id"] = threshold.get("id") or base["threshold_id"]
    base["threshold_seconds"] = threshold.get("seconds")
    if not threshold.get("seconds"):
        return {**base, "currency": "BLOCKED", "blocker": f"{key.upper()}_FRESHNESS_THRESHOLD_UNVERIFIED",
                "reason": f"The {base['threshold_id']} freshness limit is not configured, so currency cannot be checked."}
    coverage = [entry for entry in read.get("coverage") or [] if isinstance(entry, Mapping) and _int(entry.get("week"))]
    if not coverage:
        return {**base, "blocker": f"{key.upper()}_NO_ROWS", "reason": "No rows are stored for this season."}
    present = {(entry["week"], canonical_team(entry.get("team"))) for entry in coverage}
    verified = 0
    for week in range(1, completed + 1):
        expected = {(week, canonical_team(team)) for game in by_week.get(week) or [] for team in (game.get("home_team"), game.get("away_team"))}
        if not expected or None in {team for _, team in expected} or not expected <= present:
            break
        verified = week
    needed = [entry for entry in coverage if entry["week"] <= verified] or coverage
    freshness = max((str(entry.get("freshness_state") or "UNAVAILABLE") for entry in needed), key=lambda state: FRESHNESS_ORDER.get(state, 5))
    retrieved = [stamp for stamp in (utc_datetime(entry.get("retrieved_at")) for entry in needed) if stamp]
    recorded = [stamp for stamp in (utc_datetime(entry.get("source_recorded_at")) for entry in needed) if stamp]
    completeness = "NOT_STARTED" if not completed else "COMPLETE" if verified == completed else "PARTIAL" if verified else "INCOMPLETE"
    result = {**base, "verified_through_week": verified, "completeness": completeness, "freshness_state": freshness,
              "retrieved_at": min(retrieved).isoformat() if retrieved else None, "source_recorded_at": max(recorded).isoformat() if recorded else None,
              "stored_through_week": max(entry["week"] for entry in coverage)}
    limit_hours = int(threshold["seconds"]) // 3600
    retrieved_text = _time_text(result["retrieved_at"]) or "an unrecorded time"
    if completeness == "NOT_STARTED":
        return {**result, "currency": "UNAVAILABLE", "blocker": "NO_COMPLETED_WEEK", "reason": "No week of this season is complete yet."}
    if completeness != "COMPLETE":
        missing = _span_text(verified + 1, completed)
        return {**result, "currency": "NOT_CURRENT", "blocker": f"{key.upper()}_PIPELINE_INCOMPLETE",
                "reason": (f"Stored through Week {verified}; completed {missing} {'is' if verified + 1 == completed else 'are'} not stored." if verified
                           else f"Stored rows do not cover every completed game of Week 1; completed weeks through Week {completed} cannot be verified.")}
    if freshness not in CURRENT_FRESHNESS:
        return {**result, "currency": "NOT_CURRENT", "blocker": f"{key.upper()}_STALE",
                "reason": f"Retrieved {retrieved_text}, older than the {limit_hours}-hour {base['threshold_id']} limit, so it is not presented as current."}
    return {**result, "currency": "CURRENT", "reason": f"Verified through Week {verified}; retrieved {retrieved_text} ({freshness.lower()}; limit {limit_hours} hours)."}


def _one(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> tuple[Mapping[str, Any] | None, bool]:
    """One authoritative row per player and week: exact duplicates collapse, differing duplicates are a conflict (never averaged)."""
    if not rows:
        return None, False
    first = rows[0]
    if all(all(_plain(row.get(field)) == _plain(first.get(field)) for field in fields) for row in rows[1:]):
        return first, False
    return None, True


def _metric(name: str, state: str, value: Any = None, *, row: Mapping[str, Any] | None = None, reason: str | None = None,
            snaps: int | None = None) -> dict[str, Any]:
    row = row or {}
    usable = state == "AVAILABLE" and row.get("freshness_state") in CURRENT_FRESHNESS
    return {"name": name, "state": state, "value": value, "reason": reason, "snaps": snaps, "source": METRIC_SOURCE[name],
            "freshness_state": row.get("freshness_state"), "retrieved_at": row.get("retrieved_at"), "usable": usable}


def _snap_metric(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return _metric("snap_share", "UNAVAILABLE", reason="NO_SNAP_ROW")
    if row.get("provenance_blockers"):
        return _metric("snap_share", "BLOCKED", row=row, reason=list(row["provenance_blockers"])[0])
    if row.get("participation_domain") != "OFFENSE":
        return _metric("snap_share", "INVALID", row=row, reason="SNAP_SHARE_NOT_OFFENSIVE")
    state, value = _share(row.get("snap_share"))
    if state != "AVAILABLE":
        return _metric("snap_share", state, row=row, reason=f"SNAP_SHARE_{state}")
    return _metric("snap_share", "AVAILABLE", value, row=row, snaps=_whole(row.get("source_snap_count")))


def _count_metric(name: str, row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return _metric(name, "UNAVAILABLE", reason="NO_STATS_ROW")
    if row.get("provenance_blockers"):
        return _metric(name, "BLOCKED", row=row, reason=list(row["provenance_blockers"])[0])
    state, value = _count(row.get(name))
    return _metric(name, state, value, row=row, reason=None if state == "AVAILABLE" else f"{name.upper()}_{state}")


def _production(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {"state": "UNAVAILABLE", "value": None, "reason": "NO_STATS_ROW", "usable": False}
    if row.get("provenance_blockers") or row.get("scoring_format") != "FULL_PPR":
        return {"state": "UNAVAILABLE", "value": None, "reason": "PRODUCTION_CONTRACT_UNVERIFIED", "usable": False}
    value = row.get("fantasy_points_ppr")
    if value is None or isinstance(value, bool) or not isinstance(value, Number) or not isfinite(float(value)):
        return {"state": "UNAVAILABLE", "value": None, "reason": "PRODUCTION_VALUE_UNAVAILABLE", "usable": False}
    return {"state": "AVAILABLE", "value": float(value), "reason": None, "usable": row.get("freshness_state") in CURRENT_FRESHNESS}


def _observation(season: int, week: int, stats_rows: Sequence[Mapping[str, Any]], snap_rows: Sequence[Mapping[str, Any]], final_state) -> dict[str, Any]:
    """waiver.opportunity_observation.v1: one player's game as the sources recorded it; a missing source row is never a zero."""
    stats, stats_conflict = _one(stats_rows, STATS_COMPARE)
    snap, snap_conflict = _one(snap_rows, SNAP_COMPARE)
    blockers = (["OPPORTUNITY_DUPLICATE_CONFLICT"] if stats_conflict else []) + (["SNAP_SHARE_DUPLICATE_CONFLICT"] if snap_conflict else [])
    rows = [row for row in (stats, snap) if row is not None]
    teams = {canonical_team(row.get("team")) for row in rows}
    if len(teams - {None}) > 1:
        blockers.append("OBSERVATION_TEAM_CONFLICT")
    team = next(iter(teams)) if len(teams) == 1 and None not in teams else None
    if rows and team is None and "OBSERVATION_TEAM_CONFLICT" not in blockers:
        blockers.append("OBSERVATION_TEAM_UNRESOLVED")
    game = final_state(week, team) if team else {"state": "UNVERIFIED", "reason": "PLAYER_TEAM_UNRESOLVED"}
    conflicted = bool(stats_conflict or snap_conflict or "OBSERVATION_TEAM_CONFLICT" in blockers)
    opponent = next((row.get("opponent_team") for row in rows if row.get("opponent_team")), None)
    return {"contract_id": OBSERVATION_CONTRACT_ID, "season": season, "week": week, "team": team, "opponent": canonical_team(opponent) or opponent,
            "game": game, "participation": "CONTRADICTORY" if conflicted else "PLAYED",
            "metrics": {"snap_share": _snap_metric(None if snap_conflict else snap), "targets": _count_metric("targets", None if stats_conflict else stats),
                        "carries": _count_metric("carries", None if stats_conflict else stats)},
            "production": _production(None if stats_conflict else stats), "blockers": blockers}


def build_role_index(*, season: Any, week: Any, week_verified: bool, reads: Mapping[str, Any] | None, bye_rows: Sequence[Mapping[str, Any]] | None = None,
                     mode: str = "LIVE") -> dict[str, Any]:
    """Index stored observations by exact GSIS ID once per page view, with each source's completed-game coverage and freshness."""
    index: dict[str, Any] = {
        "contract_id": TREND_CONTRACT_ID, "observation_contract_id": OBSERVATION_CONTRACT_ID, "persistence_contract_id": PERSISTENCE_CONTRACT_ID,
        "state": "AVAILABLE", "season": season, "week": week, "blockers": [], "reason": None, "players": {}, "sources": {}, "byes": {},
        "completed_through_week": None, "currency": "UNAVAILABLE", "rejected_rows": {}, "refresh_command": REFRESH_COMMAND, "window_games": WINDOW_GAMES,
        "recommendation_impact": RECOMMENDATION_IMPACT, "evidence_level": EVIDENCE_LEVEL, "attribution": ATTRIBUTION, "direction_rule": DIRECTION_RULE,
    }

    def stop(state: str, blocker: str, reason: str) -> dict[str, Any]:
        index.update(state=state, currency=state, blockers=[blocker], reason=reason)
        return index

    if mode != "LIVE":
        return stop("NOT_APPLICABLE", "LIVE_LEAGUE_ONLY", "Role evidence is shown only for the live league.")
    if not week_verified or not _int(season) or not _int(week) or week < 1:
        return stop("BLOCKED", "NFL_WEEK_UNVERIFIED", "The current NFL season and week are not verified, so completed games cannot be identified.")
    if not isinstance(reads, Mapping) or reads.get("state") == "READ_FAILED":
        return stop("BLOCKED", "ROLE_EVIDENCE_UNREAD", "Stored role evidence could not be read for this page view.")
    by_week: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in reads.get("schedule") or []:
        if isinstance(row, Mapping) and _int(row.get("week")):
            by_week[row["week"]].append(row)
    completed = completed_week_boundary([row for rows in by_week.values() for row in rows], through_week=week)
    finality: dict[tuple[int, str], dict[str, Any]] = {}

    def final_state(game_week: int, team: str) -> dict[str, Any]:
        if (game_week, team) not in finality:
            finality[(game_week, team)] = game_finality(by_week.get(game_week) or [], team)
        return finality[(game_week, team)]

    sources = {"snap_counts": _source_currency("snap_counts", reads.get("snaps"), by_week, completed),
               "stats_player_week": _source_currency("stats_player_week", reads.get("opportunity"), by_week, completed)}
    states = {source["currency"] for source in sources.values()}
    index.update(completed_through_week=completed, sources=sources,
                 currency="CURRENT" if states == {"CURRENT"} else "PARTIAL" if "CURRENT" in states else "HISTORICAL" if "NOT_CURRENT" in states
                 else "BLOCKED" if states == {"BLOCKED"} else "UNAVAILABLE")
    index["byes"] = {code: _int(row.get("bye_week")) for row in bye_rows or [] if isinstance(row, Mapping)
                     for code in [canonical_team(row.get("team"))] if code and _int(row.get("bye_week"))}
    grouped: dict[tuple[str, int], dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: {"stats": [], "snap": []})
    rejected: Counter = Counter()
    for kind, read_key in (("stats", "opportunity"), ("snap", "snaps")):
        read = reads.get(read_key)
        for row in (read.get("rows") or []) if isinstance(read, Mapping) and read.get("state") == "READ" else []:
            player_id, row_week = str((row or {}).get("player_id") or "").strip(), _int((row or {}).get("week"))
            if not player_id or row.get("season") != season or not row_week or row_week < 1:
                rejected[f"{kind}:season_or_week_invalid"] += 1
            elif row_week > week:
                rejected[f"{kind}:future_week"] += 1
            else:
                grouped[(player_id, row_week)][kind].append(row)
    players: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (player_id, row_week), parts in grouped.items():
        players[player_id].append(_observation(season, row_week, parts["stats"], parts["snap"], final_state))
    for observations in players.values():
        observations.sort(key=lambda observation: observation["week"])
    index.update(players=dict(players), rejected_rows=dict(rejected))
    return index


def _series_direction(values: Sequence[float]) -> str:
    if len(values) < 2:
        return "SINGLE" if values else "UNAVAILABLE"
    steps = [later - earlier for earlier, later in zip(values, values[1:])]
    if all(step == 0 for step in steps):
        return "FLAT"
    if all(step >= 0 for step in steps):
        return "UP"
    if all(step <= 0 for step in steps):
        return "DOWN"
    return "MIXED"


def _overall_direction(window_size: int, directions: Mapping[str, str]) -> str:
    moving = [direction for direction in directions.values() if direction in ("UP", "DOWN", "FLAT", "MIXED")]
    if not moving:
        return "CURRENT_ROLE_ONLY" if window_size == 1 else "INSUFFICIENT_EVIDENCE"
    if "MIXED" in moving or ("UP" in moving and "DOWN" in moving):
        return "MIXED"
    if "UP" in moving:
        return "DIRECTION_UP"
    return "DIRECTION_DOWN" if "DOWN" in moving else "FLAT"


def _format(metric: str, values: Sequence[float | None]) -> list[str]:
    if metric != "snap_share":
        return ["n/a" if value is None else str(int(value)) for value in values]
    decimals = 0
    present = [value for value in values if value is not None]
    while decimals < 2 and any(a != b and f"{a * 100:.{decimals}f}" == f"{b * 100:.{decimals}f}" for a, b in zip(present, present[1:])):
        decimals += 1
    return ["n/a" if value is None else f"{value * 100:.{decimals}f}%" for value in values]


def _persistence(direction: str, series: Mapping[str, Sequence[tuple[int, float]]], directions: Mapping[str, str], window: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """waiver.role_persistence.v1: whether an observed change held across the supported games. Backward-looking only."""
    base = {"contract_id": PERSISTENCE_CONTRACT_ID, "games": len(window), "weeks": [obs["week"] for obs in window]}

    def unverified(reason: str) -> dict[str, Any]:
        return {**base, "state": "DURATION_UNVERIFIED", "label": "DURATION UNVERIFIED", "reason": reason}

    if direction in ("DIRECTION_UP", "DIRECTION_DOWN"):
        word, sign = ("larger", 1) if direction == "DIRECTION_UP" else ("smaller", -1)
        moving = {metric: [value for _, value in series[metric]] for metric, metric_direction in directions.items()
                  if metric_direction == ("UP" if sign > 0 else "DOWN")}
        if len(window) < 3:
            return unverified(f"The change appears across only {len(window)} supported completed games (one change), so it has not been observed to hold.")
        held = [metric for metric, values in moving.items() if len(values) >= 3 and all(sign * (value - values[0]) > 0 for value in values[1:])]
        if held and len(held) == len(moving):
            first, *later = [obs["week"] for obs in window]
            names = " and ".join(METRIC_LABELS[metric] for metric in held)
            return {**base, "state": "PERSISTED_ACROSS_OBSERVED_GAMES", "label": "PERSISTED ACROSS OBSERVED GAMES",
                    "reason": (f"{'Higher' if sign > 0 else 'Lower'} {names} held in each of the last {len(later)} of {len(window)} supported completed games "
                               f"({_weeks_text(later)} {'above' if sign > 0 else 'below'} Week {first}). This looks back only.")}
        verb = "rose" if sign > 0 else "fell"
        failures = [f"{METRIC_LABELS[metric]} was not recorded in all {len(window)} games" if len(values) < 3 else f"{METRIC_LABELS[metric]} {verb} only in the latest game"
                    for metric, values in moving.items() if metric not in held]
        return unverified(f"The {word} role has not been observed to hold: {'; '.join(failures)}.")
    if direction == "FLAT":
        if len(window) >= 3 and all(len(series[metric]) >= 3 for metric, metric_direction in directions.items() if metric_direction == "FLAT"):
            return {**base, "state": "PERSISTED_ACROSS_OBSERVED_GAMES", "label": "PERSISTED ACROSS OBSERVED GAMES",
                    "reason": f"The observed role level held across {len(window)} supported completed games. This looks back only."}
        return unverified("An unchanged role across fewer than 3 supported completed games is not persistence evidence.")
    if direction == "MIXED":
        return unverified("The supported metrics moved in different directions, so no single role change has been observed to hold.")
    if direction == "CURRENT_ROLE_ONLY":
        return unverified("Only one supported completed game is available.")
    return unverified("No supported metric was recorded in two supported completed games.")


def _result(base: Mapping[str, Any], state: str, direction: str, reason: str, *, persistence: str = "DURATION_UNVERIFIED") -> dict[str, Any]:
    label = {"HISTORICAL_ONLY": "HISTORICAL ONLY", "NO_EVIDENCE": "NO EVIDENCE", "IDENTITY_UNRESOLVED": "UNAVAILABLE", "CONTRADICTORY": "CONTRADICTORY",
             "BLOCKED": "BLOCKED", "NOT_APPLICABLE": "NOT APPLICABLE"}[state]
    persistence_label = persistence.replace("_", " ")
    persistence_reason = {"NOT_APPLICABLE": "Not applicable for this position.", "CONTRADICTORY": "Contradictory evidence is not used."}.get(
        persistence, "No current supported role evidence is available, so persistence cannot be observed.")
    duration_state = "NOT_APPLICABLE" if persistence == "NOT_APPLICABLE" else "UNVERIFIED"
    return {**base, "state": state, "label": label, "direction": direction, "reason": reason, "sample_state": "NO_EVIDENCE", "sample_size": 0,
            "persistence": {"contract_id": PERSISTENCE_CONTRACT_ID, "state": persistence, "label": persistence_label, "reason": persistence_reason, "games": 0,
                            "weeks": []},
            "future_duration": {"state": duration_state, "label": duration_state.replace("_", " "),
                                "reason": "Not applicable for this position." if duration_state == "NOT_APPLICABLE" else DURATION_REASON},
            "text": {"role": f"{label} — {reason}", "persistence": f"{persistence_label} — {persistence_reason}",
                     "duration": "NOT APPLICABLE" if duration_state == "NOT_APPLICABLE" else f"UNVERIFIED — {DURATION_REASON}"}}


def _observation_view(observation: Mapping[str, Any], metrics: Sequence[str]) -> dict[str, Any]:
    parts = []
    for metric in metrics:
        entry = observation["metrics"][metric]
        if entry["state"] == "AVAILABLE":
            value = _format(metric, [entry["value"]])[0]
            parts.append(f"{value} snaps" if metric == "snap_share" else f"{value} {METRIC_LABELS[metric]}")
            if metric == "snap_share" and entry.get("snaps") is not None:
                parts[-1] += f" ({entry['snaps']} offensive snaps)"
        else:
            parts.append(f"{METRIC_LABELS[metric]} n/a")
    production = observation["production"]
    return {"week": observation["week"], "team": observation["team"], "opponent": observation["opponent"], "game_state": observation["game"]["state"],
            "text": " · ".join(parts), "production": production["value"] if production["state"] == "AVAILABLE" else None,
            "retrieved_at": next((entry["retrieved_at"] for entry in observation["metrics"].values() if entry.get("retrieved_at")), None)}


def role_evidence(index: Mapping[str, Any] | None, *, player_id: Any = None, opportunity_player_id: Any = None, identity_state: Any = None,
                  identity_method: Any = None, position: Any = None, team: Any = None, player: Any = None) -> dict[str, Any]:
    """waiver.opportunity_trend.v1 for one player: observed role, its direction, observed persistence and (unverified) future duration."""
    index = index or {}
    position = str(position or "").upper().replace("DST", "DEF")
    gsis = str(opportunity_player_id or "").strip()
    sources = index.get("sources") or {}
    base = {"contract_id": TREND_CONTRACT_ID, "player_id": str(player_id) if player_id is not None else None, "player": player, "position": position,
            "team": canonical_team(team) or team, "opportunity_player_id": gsis or None, "identity_state": identity_state, "identity_method": identity_method,
            "season": index.get("season"), "week": index.get("week"), "completed_through_week": index.get("completed_through_week"),
            "currency": index.get("currency"), "sources": [dict(sources[key]) for key in ("snap_counts", "stats_player_week") if key in sources],
            "metrics": {}, "metric_order": [], "observations": [], "weeks": [], "gaps": [], "notes": [], "unavailable_metrics": [],
            "production": {"state": "UNAVAILABLE", "display": None, "direction": None, "comparison": None},
            "what_changed": [], "blockers": [], "recommendation_impact": RECOMMENDATION_IMPACT, "evidence_level": EVIDENCE_LEVEL,
            "decision_effect": "NONE", "refresh_command": REFRESH_COMMAND, "attribution": ATTRIBUTION}
    if position in NOT_APPLICABLE_REASONS:
        return _result(base, "NOT_APPLICABLE", "NOT_APPLICABLE", NOT_APPLICABLE_REASONS[position], persistence="NOT_APPLICABLE")
    if position not in SUPPORTED_POSITIONS:
        return _result(base, "NOT_APPLICABLE", "NOT_APPLICABLE", "No offensive-role contract exists for this position.", persistence="NOT_APPLICABLE")
    base["unavailable_metrics"] = [UNSUPPORTED_METRICS[key] for key in POSITION_UNSUPPORTED[position]]
    if index.get("state") != "AVAILABLE":
        state = "NOT_APPLICABLE" if index.get("state") == "NOT_APPLICABLE" else "BLOCKED"
        return {**_result(base, state, "NOT_APPLICABLE" if state == "NOT_APPLICABLE" else "INSUFFICIENT_EVIDENCE", index.get("reason") or "Role evidence is unavailable.",
                          persistence="NOT_APPLICABLE" if state == "NOT_APPLICABLE" else "DURATION_UNVERIFIED"),
                "blockers": list(index.get("blockers") or [])}
    if str(identity_state or "").upper() in IDENTITY_CONFLICT_STATES:
        return _result(base, "CONTRADICTORY", "CONTRADICTORY", "The player's GSIS identity is ambiguous or conflicting, so no role evidence is used.",
                       persistence="CONTRADICTORY")
    if identity_state != "RESOLVED" or not gsis:
        return _result(base, "IDENTITY_UNRESOLVED", "INSUFFICIENT_EVIDENCE",
                       "No exact GSIS identity links this player to the nflverse role sources; names are never matched.")
    metrics = POSITION_METRICS[position]
    observations = list((index.get("players") or {}).get(gsis) or [])
    final = [observation for observation in observations if observation["game"]["state"] == "FINAL"]
    not_final = [observation["week"] for observation in observations if observation["game"]["state"] != "FINAL" and observation["participation"] != "CONTRADICTORY"]
    if not_final:
        base["notes"].append(f"{_weeks_text(not_final)}: stored, but the game result is not verified as final, so it is not counted.")
    # A conflicted observation cannot even verify its game, so the conflict check looks at it before the completed-game filter.
    latest_observed = sorted((observation for observation in observations if observation["game"]["state"] == "FINAL" or observation["participation"] == "CONTRADICTORY"),
                             key=lambda observation: observation["week"], reverse=True)[:WINDOW_GAMES]
    conflicted = [observation["week"] for observation in latest_observed if observation["participation"] == "CONTRADICTORY"]
    if conflicted:
        return {**_result(base, "CONTRADICTORY", "CONTRADICTORY", f"The stored rows for {_weeks_text(sorted(conflicted))} disagree (team or duplicate values), "
                          "so no role evidence is used.", persistence="CONTRADICTORY"),
                "blockers": sorted({blocker for observation in latest_observed for blocker in observation["blockers"]})}
    current_metrics = [metric for metric in metrics if (sources.get(METRIC_SOURCE[metric]) or {}).get("currency") == "CURRENT"]
    base["metric_order"] = list(metrics)
    if not current_metrics and all((sources.get(METRIC_SOURCE[metric]) or {}).get("currency") == "BLOCKED" for metric in metrics):
        reason = _source_reasons(base["sources"])
        return {**_result(base, "BLOCKED", "INSUFFICIENT_EVIDENCE", f"Role evidence currency cannot be checked ({reason})."),
                "blockers": sorted({source["blocker"] for source in base["sources"] if source.get("blocker")})}
    if not current_metrics:
        historical = [observation for observation in latest_observed
                      if observation["participation"] == "PLAYED" and any(observation["metrics"][metric]["state"] == "AVAILABLE" for metric in metrics)]
        through = max((source.get("verified_through_week") or 0 for source in sources.values()), default=0)
        source_reason = _source_reasons(base["sources"])
        if not historical:
            return _result(base, "NO_EVIDENCE", "INSUFFICIENT_EVIDENCE", f"No current role evidence is stored ({source_reason}).")
        view = [_observation_view(observation, metrics) for observation in sorted(historical, key=lambda item: item["week"])]
        return {**_result(base, "HISTORICAL_ONLY", "INSUFFICIENT_EVIDENCE",
                          f"Stored role evidence for this player ends at Week {view[-1]['week']} and the stored sources are not verified as current "
                          f"({source_reason}). No current role or trend is claimed; run {REFRESH_COMMAND}."),
                "observations": view, "weeks": [item["week"] for item in view], "historical_through_week": through}
    for metric in metrics:
        if metric not in current_metrics:
            source = sources.get(METRIC_SOURCE[metric]) or {}
            base["notes"].append(f"{METRIC_LABELS[metric].capitalize()} not used: {source.get('label')} is not current ({str(source.get('reason') or 'no reason recorded').rstrip('.')}).")
    supported = [observation for observation in sorted(final, key=lambda item: item["week"], reverse=True)
                 if observation["participation"] == "PLAYED" and any(observation["metrics"][metric]["usable"] for metric in current_metrics)][:WINDOW_GAMES]
    window = sorted(supported, key=lambda observation: observation["week"])
    weeks = [observation["week"] for observation in window]
    through = min(sources[METRIC_SOURCE[metric]]["verified_through_week"] for metric in current_metrics)
    if not window:
        return _result(base, "NO_EVIDENCE", "INSUFFICIENT_EVIDENCE",
                       f"No supported completed-game snap or usage row is stored for this player in {index.get('season')} through Week {through}. "
                       "Missing role evidence does not mean a poor player.")
    gaps = []
    current_team = canonical_team(team)
    byes = index.get("byes") or {}
    for earlier, later in zip(window, window[1:]):
        for gap_week in range(earlier["week"] + 1, later["week"]):
            gaps.append({"week": gap_week, "state": _gap_state(gap_week, earlier.get("team") if earlier.get("team") == later.get("team") else None,
                                                              observations, byes)})
    latest = window[-1]
    trailing = []
    for gap_week in range(latest["week"] + 1, through + 1):
        # After the last supported game the team is known only while Sleeper still lists the same team.
        trailing.append({"week": gap_week, "state": _gap_state(gap_week, latest.get("team") if latest.get("team") == current_team else None, observations, byes)})
    gaps.extend(trailing)
    if current_team and latest["team"] and current_team != latest["team"]:
        base["notes"].append(f"Observed with {latest['team']}; Sleeper now lists {current_team}.")
    missed = [gap["week"] for gap in trailing if gap["state"] != "BYE"]
    if len(missed) >= WINDOW_GAMES:
        # No supported game in the team's latest completed games: the player's observed role is history, not his current role.
        view = [_observation_view(observation, current_metrics) for observation in window]
        return {**_result(base, "HISTORICAL_ONLY", "INSUFFICIENT_EVIDENCE",
                          f"No supported snap or usage row for this player after Week {latest['week']}: {_gaps_text(trailing)} No current role or trend is "
                          f"claimed. Last recorded: {view[-1]['text']} (Week {latest['week']})."),
                "observations": view, "weeks": weeks, "gaps": gaps, "through_week": through, "historical_through_week": latest["week"]}
    series = {metric: [(observation["week"], observation["metrics"][metric]["value"]) for observation in window if observation["metrics"][metric]["usable"]]
              for metric in current_metrics}
    directions = {metric: _series_direction([value for _, value in values]) for metric, values in series.items()}
    direction = _overall_direction(len(window), directions)
    metric_views = {}
    for metric in current_metrics:
        aligned = [observation["metrics"][metric]["value"] if observation["metrics"][metric]["usable"] else None for observation in window]
        display = " → ".join(_format(metric, aligned))
        word = SERIES_WORDS.get(directions[metric])
        metric_views[metric] = {"label": METRIC_LABELS[metric], "values": series[metric], "display": display, "direction": directions[metric],
                                "text": f"{METRIC_LABELS[metric]} {display}{f' ({word})' if word else ''}", "definition": METRIC_DEFINITIONS[metric]}
    persistence = _persistence(direction, series, directions, window)
    production = _production_view(window, direction)
    sample_state = SAMPLE_STATES[min(len(window), 3)]
    sample_text = f"{len(window)} supported completed game{'s' if len(window) != 1 else ''}"
    texts = [metric_views[metric]["text"] for metric in current_metrics]
    if direction == "CURRENT_ROLE_ONLY":
        role_text = f"CURRENT ROLE ONLY — {'; '.join(texts)} ({_weeks_text(weeks)}; one supported completed game, so no trend is shown)."
    else:
        role_text = f"{DIRECTION_LABELS[direction]} — {'; '.join(texts)} ({_weeks_text(weeks)}; {sample_text})."
    gap_text = _gaps_text(gaps)
    if gap_text:
        role_text += f" {gap_text}"
    what_changed = [f"{METRIC_LABELS[metric]} {SERIES_WORDS[directions[metric]]}" for metric in current_metrics if directions[metric] in SERIES_WORDS]
    return {**base, "state": "CURRENT", "label": DIRECTION_LABELS[direction], "direction": direction, "reason": None, "sample_state": sample_state,
            "sample_size": len(window), "weeks": weeks, "through_week": through, "metrics": metric_views, "metric_order": current_metrics,
            "observations": [_observation_view(observation, current_metrics) for observation in window], "gaps": gaps, "persistence": persistence,
            "future_duration": {"state": "UNVERIFIED", "label": "UNVERIFIED", "reason": DURATION_REASON}, "production": production,
            "what_changed": what_changed,
            "text": {"role": role_text, "persistence": f"{persistence['label']} — {persistence['reason']}", "duration": f"UNVERIFIED — {DURATION_REASON}"}}


def _source_reasons(sources: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(f"{source['label']}: {str(source['reason']).rstrip('.')}" for source in sources if source.get("reason"))


def _gap_state(gap_week: int, team: str | None, observations: Sequence[Mapping[str, Any]], byes: Mapping[str, int]) -> str:
    """Why a week between or after supported games is absent: a bye, an excluded stored row, or no stored row (never a zero)."""
    if any(observation["week"] == gap_week for observation in observations):
        return "EXCLUDED"
    if team and byes.get(team) == gap_week:
        return "BYE"
    return "MISSING_SOURCE_ROW"


def _gaps_text(gaps: Sequence[Mapping[str, Any]]) -> str:
    groups: dict[str, list[int]] = defaultdict(list)
    for gap in gaps:
        groups[gap["state"]].append(gap["week"])
    parts = []
    if groups.get("BYE"):
        parts.append(f"{_ranges_text(groups['BYE'])}: bye, not counted")
    if groups.get("MISSING_SOURCE_ROW"):
        parts.append(f"{_ranges_text(groups['MISSING_SOURCE_ROW'])}: no stored snap or stats row (did not play, inactive or not recorded; the source "
                     "does not say which), not counted as zero")
    if groups.get("EXCLUDED"):
        parts.append(f"{_ranges_text(groups['EXCLUDED'])}: stored but not usable (game not final, invalid or not current), not counted")
    return ("; ".join(parts) + ".") if parts else ""


def _production_view(window: Sequence[Mapping[str, Any]], role_direction: str) -> dict[str, Any]:
    """Full-PPR production over the same games, kept separate from role; a comparison sentence is descriptive only."""
    values = [observation["production"]["value"] if observation["production"]["usable"] else None for observation in window]
    present = [value for value in values if value is not None]
    if not present:
        return {"state": "UNAVAILABLE", "display": None, "direction": None, "comparison": None}
    direction = _series_direction(present)
    display = " → ".join("n/a" if value is None else f"{value:.1f}" for value in values)
    comparison = None
    if role_direction == "DIRECTION_UP" and direction in ("FLAT", "DOWN", "MIXED"):
        comparison = "Observed role increased over the supported completed games while Full-PPR production did not increase over the same games."
    elif direction == "UP" and role_direction in ("FLAT", "DIRECTION_DOWN"):
        comparison = "Recent Full-PPR production improved without a corresponding increase in the supported role evidence."
    return {"state": "AVAILABLE", "values": values, "display": display, "direction": direction, "comparison": comparison,
            "text": f"Full-PPR points {display}{f' ({SERIES_WORDS[direction]})' if direction in SERIES_WORDS else ''}"}


def role_coverage_summary(index: Mapping[str, Any] | None, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Full-universe counts by position; the denominator is the current published candidate population, never a constant."""
    index = index or {}
    keys = {"CURRENT": "current", "HISTORICAL_ONLY": "historical_only", "NO_EVIDENCE": "no_evidence", "IDENTITY_UNRESOLVED": "identity_unresolved",
            "CONTRADICTORY": "contradictory", "BLOCKED": "blocked", "NOT_APPLICABLE": "not_applicable"}
    positions = {position: Counter({"population": 0, **{key: 0 for key in keys.values()}}) for position in POSITIONS}
    directions: Counter = Counter()
    for result in results:
        position = result.get("position")
        if position not in positions:
            continue
        positions[position]["population"] += 1
        positions[position][keys.get(result.get("state"), "blocked")] += 1
        if result.get("state") == "CURRENT":
            directions[result.get("direction")] += 1
    totals = Counter()
    for counts in positions.values():
        totals.update(counts)
    sources = index.get("sources") or {}
    current = [source for source in sources.values() if source.get("currency") == "CURRENT"]
    return {"state": index.get("state"), "currency": index.get("currency"), "reason": index.get("reason"),
            "completed_through_week": index.get("completed_through_week"),
            "through_week": min((source["verified_through_week"] for source in current), default=None),
            "sources": [dict(sources[key]) for key in ("snap_counts", "stats_player_week") if key in sources],
            "positions": {position: dict(counts) for position, counts in positions.items()}, "totals": dict(totals), "directions": dict(directions),
            "denominator": totals["population"], "refresh_command": REFRESH_COMMAND, "attribution": ATTRIBUTION, "direction_rule": DIRECTION_RULE,
            "recommendation_impact": RECOMMENDATION_IMPACT}
