"""Pre-kickoff capture and post-week review of My Team lineup decision snapshots (evidence collection only).

Capture appends the forward-validation snapshots My Team already builds to the append-only ``pre_decision_snapshots``
store. A snapshot is written only while its player's schedule-verified kickoff is still ahead, so post-kickoff knowledge
is never recorded as a pre-kickoff decision. Identical evidence is an idempotent no-op, and stored rows are never updated.

The review is read-only. It compares stored decisions with Sleeper's league-scored player points only after the automated
nflverse schedule records the game's result. It never grades a decision or changes a recommendation, confidence, lock,
threshold, projection, or transaction.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from services.game_lock import SCHEDULE_SOURCE_PREFIX, utc_datetime
from services.lineup_projection import SNAPSHOT_DECISION_TYPE
from services.pre_decision_snapshots import SnapshotPersistenceError, SnapshotValidationError, persist_snapshot
from services.team_codes import canonical_team

CAPTURE_CONTRACT_ID = "lineup.forward_validation.capture.v1"
REVIEW_CONTRACT_ID = "lineup.forward_validation.review.v1"
ACTUALS_SOURCE = "Sleeper league matchups (players_points, league-scored by Sleeper)"
EVIDENCE_ONLY = ("Evidence collection only: capture never changes recommendations, confidence, ranking, locks, or transactions, "
                 "and never submits a lineup.")
REVIEW_LIMITATIONS = (
    "Informational only: no decision is graded, and no recommendation, confidence, threshold, projection, or transaction changes.",
    "Actual points count only after the automated nflverse schedule records the game's result; earlier Sleeper zeros are placeholders.",
    "Sleeper stat corrections after the game are not tracked, so actual points can still change; their finality is unverified.",
    "The legacy Weekly Score (v1: season projection ÷ 17, in weekly value points) is shown beside actual points but never differenced.",
    "Weekly Score v2 (shadow) is the exact league-scored projection, so its difference is the projection difference; a partial-scoring range is never "
    "differenced, and snapshots captured before v2 show it as not captured.",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _player_id(snapshot: Mapping[str, Any]) -> str | None:
    return str(snapshot.get("decision_subject") or "").removeprefix("sleeper:") or None


def _entry(snapshot: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    output = snapshot.get("decision_output") or {}
    return {"player": output.get("player"), "player_id": _player_id(snapshot), "snapshot_id": snapshot.get("snapshot_id"),
            "decision": output.get("decision"), "slot": output.get("recommended_slot"), **extra}


def pre_kickoff_rejection(snapshot: Mapping[str, Any], *, write_time: datetime) -> str | None:
    """Why a snapshot cannot be stored as pre-kickoff evidence at ``write_time``; None when it can."""
    if snapshot.get("decision_type") != SNAPSHOT_DECISION_TYPE:
        return "SNAPSHOT_DECISION_TYPE_UNSUPPORTED"
    lock = (snapshot.get("decision_output") or {}).get("lock") or {}
    if lock.get("state") != "OPEN" or lock.get("decision_authority") is not True:
        return "KICKOFF_LOCK_NOT_VERIFIED_OPEN"
    kickoff, evaluated = utc_datetime(lock.get("kickoff_utc")), utc_datetime(snapshot.get("captured_at"))
    if kickoff is None:
        return "KICKOFF_UNVERIFIED"
    if evaluated is None or evaluated >= kickoff:
        return "DECISION_EVALUATED_AT_OR_AFTER_KICKOFF"
    if write_time >= kickoff:
        return "KICKOFF_PASSED_BEFORE_CAPTURE"
    return None


def _capture_counts(result: Mapping[str, Any]) -> dict[str, int]:
    return {key: len(result[key]) for key in ("captured", "duplicates", "rejected", "failed", "not_eligible")}


def capture_lineup_snapshots(connect: Callable[[], Any], lineup_decision: Mapping[str, Any], *, clock: Callable[[], datetime] | None = None) -> dict[str, Any]:
    """Append each eligible pre-kickoff decision snapshot. Duplicates are no-ops; a failed write never alters stored rows."""
    clock = clock or _now
    validation = lineup_decision.get("forward_validation") or {}
    result = {
        "contract_id": CAPTURE_CONTRACT_ID, "state": "UNAVAILABLE", "reason": None, "season": lineup_decision.get("season"), "week": lineup_decision.get("week"),
        "decision_type": SNAPSHOT_DECISION_TYPE, "store": "pre_decision_snapshots", "attempted_at": clock().isoformat(),
        "captured": [], "duplicates": [], "rejected": [], "failed": [], "not_eligible": list(validation.get("skipped") or []),
        "decision_effect": "NONE", "authority": EVIDENCE_ONLY,
    }
    snapshots = list(validation.get("snapshots") or [])
    if lineup_decision.get("mode") != "LIVE":
        result.update(state="NOT_APPLICABLE", reason="Season Sandbox decisions are never captured as forward-validation evidence.")
    elif not snapshots:
        result["reason"] = "No decision has a schedule-verified kickoff still ahead."
    else:
        try:
            conn = connect()
        except Exception as error:
            result["failed"] = [_entry(snapshot, reason="DATABASE_CONNECTION_FAILED") for snapshot in snapshots]
            result.update(state="FAILED", reason=f"Database connection failed ({type(error).__name__}); nothing was written.")
            return {**result, "counts": _capture_counts(result)}
        try:
            for snapshot in snapshots:
                rejection = pre_kickoff_rejection(snapshot, write_time=clock())
                if rejection:
                    result["rejected"].append(_entry(snapshot, reason=rejection))
                    continue
                try:
                    stored = persist_snapshot(conn, snapshot)
                except SnapshotValidationError as error:
                    result["rejected"].append(_entry(snapshot, reason=f"SNAPSHOT_INVALID: {error}"))
                    continue
                except SnapshotPersistenceError as error:
                    result["failed"].append(_entry(snapshot, reason=f"DATABASE_WRITE_FAILED: {type(error.__cause__).__name__}"))
                    continue
                if stored:
                    result["captured"].append(_entry(snapshot, captured_at=snapshot.get("captured_at")))
                else:
                    result["duplicates"].append(_entry(snapshot, reason="IDENTICAL_EVIDENCE_ALREADY_STORED"))
        finally:
            try:
                conn.close()
            except Exception:
                pass
        if result["failed"]:
            written = bool(result["captured"] or result["duplicates"])
            result.update(state="PARTIAL" if written else "FAILED",
                          reason="Some snapshots could not be written; each failed write was rolled back and stored snapshots are unchanged.")
        elif result["captured"]:
            result.update(state="CAPTURED", reason="New pre-kickoff decision evidence was appended.")
        elif result["duplicates"]:
            result.update(state="NO_NEW_EVIDENCE", reason="Identical decision evidence is already stored; nothing was overwritten.")
        else:
            result["reason"] = "No snapshot passed the pre-kickoff check at write time."
    return {**result, "counts": _capture_counts(result)}


def read_lineup_snapshots(cur: Any, *, season: int, week: int) -> list[dict[str, Any]]:
    """Stored My Team lineup decision snapshots for one week (read-only)."""
    cur.execute(
        "SELECT snapshot_payload FROM pre_decision_snapshots WHERE season = %s AND week = %s AND decision_type = %s "
        "ORDER BY decision_subject, captured_at, snapshot_id",
        (season, week, SNAPSHOT_DECISION_TYPE),
    )
    return [row[0] if isinstance(row[0], Mapping) else json.loads(row[0]) for row in cur.fetchall() or []]


def read_week_game_results(cur: Any, *, season: int, week: int) -> list[dict[str, Any]]:
    """This week's stored schedule rows with each game's published result (read-only)."""
    keys = ("home_team", "away_team", "game_time_utc", "result", "source", "source_recorded_at", "retrieved_at")
    cur.execute(f"SELECT {', '.join(keys)} FROM nfl_schedule WHERE season = %s AND week = %s", (season, week))
    return [dict(zip(keys, row)) for row in cur.fetchall() or []]


def sleeper_actual_points(matchups: Any, *, retrieved_at: Any = None) -> dict[str, Any]:
    """League-scored points per player from Sleeper's weekly matchups; missing or contradictory values are never zero."""
    stamp = utc_datetime(retrieved_at)
    base = {"source": ACTUALS_SOURCE, "retrieved_at": stamp.isoformat() if stamp else None, "players": {}, "blockers": []}
    if not isinstance(matchups, list) or not matchups:
        return {**base, "state": "UNAVAILABLE", "blockers": ["SLEEPER_MATCHUPS_UNAVAILABLE"]}
    players, conflicts = {}, set()
    for entry in matchups:
        points = entry.get("players_points") if isinstance(entry, Mapping) else None
        for raw_id, raw_points in (points.items() if isinstance(points, Mapping) else ()):
            player_id, value = str(raw_id), _finite(raw_points)
            if value is None:
                continue
            known = players.setdefault(player_id, {"state": "AVAILABLE", "points": value, "roster_id": entry.get("roster_id")})
            if known["points"] != value:
                conflicts.add(player_id)
    for player_id in conflicts:
        players[player_id] = {"state": "CONTRADICTORY", "points": None, "roster_id": None}
    return {**base, "state": "AVAILABLE" if players else "UNAVAILABLE", "players": players,
            "blockers": [] if players else ["SLEEPER_PLAYER_POINTS_UNAVAILABLE"]}


def game_finality(schedule_rows: Sequence[Mapping[str, Any]] | None, team: Any) -> dict[str, Any]:
    """FINAL only when the automated nflverse schedule has published this team's game result for the week."""
    code = canonical_team(team)
    if code is None:
        return {"state": "UNVERIFIED", "reason": "PLAYER_TEAM_UNRESOLVED"}
    games = [row for row in schedule_rows or [] if code in {canonical_team(row.get("home_team")), canonical_team(row.get("away_team"))}]
    if len(games) != 1:
        return {"state": "UNVERIFIED", "reason": "SCHEDULE_GAME_NOT_FOUND" if not games else "SCHEDULE_GAME_CONFLICT"}
    game = games[0]
    if not str(game.get("source") or "").lower().startswith(SCHEDULE_SOURCE_PREFIX):
        return {"state": "UNVERIFIED", "reason": "SCHEDULE_SOURCE_NOT_AUTOMATED"}
    if game.get("result") in (None, ""):
        return {"state": "NOT_FINAL", "reason": "GAME_RESULT_NOT_PUBLISHED"}
    retrieved = utc_datetime(game.get("retrieved_at"))
    return {"state": "FINAL", "reason": None, "result": str(game.get("result")), "schedule_source": game.get("source"),
            "schedule_retrieved_at": retrieved.isoformat() if retrieved else None}


def _actual(actual_points: Mapping[str, Any], player_id: str | None, game: Mapping[str, Any]) -> dict[str, Any]:
    if actual_points.get("state") != "AVAILABLE":
        return {"state": "UNAVAILABLE", "points": None, "reason": (actual_points.get("blockers") or ["SLEEPER_MATCHUPS_UNAVAILABLE"])[0]}
    if game["state"] != "FINAL":
        return {"state": "NOT_FINAL" if game["state"] == "NOT_FINAL" else "UNVERIFIED", "points": None, "reason": game["reason"]}
    entry = (actual_points.get("players") or {}).get(player_id)
    if entry is None:
        return {"state": "UNAVAILABLE", "points": None, "reason": "PLAYER_NOT_IN_SLEEPER_MATCHUPS"}
    if entry.get("state") == "CONTRADICTORY":
        return {"state": "CONTRADICTORY", "points": None, "reason": "SLEEPER_PLAYER_POINTS_CONTRADICTORY"}
    return {"state": "AVAILABLE", "points": entry["points"], "reason": None}


def review_lineup_snapshots(snapshots: Sequence[Mapping[str, Any]] | None, *, actual_points: Mapping[str, Any], schedule_rows: Sequence[Mapping[str, Any]] | None,
                            season: int, week: int) -> dict[str, Any]:
    """Each player's last pre-kickoff decision beside his actual Sleeper points; informational and read-only."""
    by_player, excluded = {}, []
    for snapshot in snapshots or []:
        lock = (snapshot.get("decision_output") or {}).get("lock") or {}
        kickoff, evaluated = utc_datetime(lock.get("kickoff_utc")), utc_datetime(snapshot.get("captured_at"))
        if snapshot.get("decision_type") != SNAPSHOT_DECISION_TYPE or snapshot.get("season") != season or snapshot.get("week") != week:
            excluded.append({"snapshot_id": snapshot.get("snapshot_id"), "reason": "OTHER_DECISION_OR_WEEK"})
        elif kickoff is None or evaluated is None or evaluated >= kickoff:
            excluded.append({"snapshot_id": snapshot.get("snapshot_id"), "reason": "NOT_PROVEN_PRE_KICKOFF"})
        else:
            by_player.setdefault(_player_id(snapshot), []).append((evaluated, snapshot))
    rows = []
    for player_id, items in sorted(by_player.items(), key=lambda item: str(item[0])):
        items.sort(key=lambda item: (item[0], str(item[1].get("snapshot_id"))))
        snapshot = items[-1][1]
        output = snapshot.get("decision_output") or {}
        lock, value = output.get("lock") or {}, output.get("weekly_value") or {}
        weekly = output.get("weekly_score_v2")
        game = game_finality(schedule_rows, output.get("nfl_team") or lock.get("team"))
        actual = _actual(actual_points, player_id, game)
        projection = output.get("league_scored_projection")
        if actual["state"] != "AVAILABLE":
            difference = {"state": "NOT_COMPARED", "reason": f"ACTUAL_POINTS_{actual['state']}", "actual_minus_projection": None}
        elif projection is None:
            difference = {"state": "NOT_COMPARED", "reason": "PROJECTION_RANGE_ONLY" if output.get("league_scored_range") else "PROJECTION_UNAVAILABLE",
                          "actual_minus_projection": None}
        else:
            difference = {"state": "AVAILABLE", "reason": None, "actual_minus_projection": round(actual["points"] - projection, 2),
                          "evidence_level": "PRELIMINARY", "recommendation_impact": "INFORMATIONAL_ONLY"}
        rows.append({
            "player": output.get("player"), "player_id": player_id, "position": output.get("position"), "nfl_team": output.get("nfl_team"),
            "opponent": output.get("opponent"), "decision": output.get("decision"), "recommended_slot": output.get("recommended_slot"),
            "current_slot": output.get("current_slot"), "decision_confidence": (output.get("decision_confidence") or {}).get("state"),
            "snapshot_id": snapshot.get("snapshot_id"), "captured_at": snapshot.get("captured_at"), "first_captured_at": items[0][1].get("captured_at"),
            "snapshot_count": len(items), "kickoff_utc": lock.get("kickoff_utc"),
            "weekly_value": {key: value.get(key) for key in ("value", "state", "evidence_level", "unit")},
            "weekly_score_v2": ({key: weekly.get(key) for key in ("contract_id", "state", "value", "value_range", "unit", "evidence_level", "authority")}
                                if isinstance(weekly, Mapping) else {"contract_id": None, "state": "NOT_CAPTURED", "value": None, "value_range": None}),
            "league_scored_projection": {"value": projection, "range": output.get("league_scored_range"), "evidence_state": output.get("projection_evidence_state"),
                                         "recommendation_impact": (output.get("projection_evidence") or {}).get("recommendation_impact")},
            "game": game, "actual": {**actual, "source": ACTUALS_SOURCE}, "projection_difference": difference,
        })
    counts = Counter(row["actual"]["state"] for row in rows)
    if not rows:
        state = "NO_SNAPSHOTS"
    elif actual_points.get("state") != "AVAILABLE":
        state = "UNAVAILABLE"
    else:
        state = "COMPLETE" if counts["AVAILABLE"] == len(rows) else "PARTIAL" if counts["AVAILABLE"] else "PENDING"
    return {
        "contract_id": REVIEW_CONTRACT_ID, "state": state, "season": season, "week": week, "decision_type": SNAPSHOT_DECISION_TYPE,
        "players": rows, "excluded": excluded, "counts": {"players": len(rows), **dict(sorted(counts.items()))},
        "actuals": {key: actual_points.get(key) for key in ("source", "state", "retrieved_at", "blockers")},
        "decision_effect": "NONE", "limitations": list(REVIEW_LIMITATIONS),
    }
