"""Pure current-week player-opportunity usage calculation for full PPR.

Computes only metrics verifiably derivable from the same nflverse weekly
stats artifact already used by services.defense_matchup_calculation
(stats_player_week_{season}.csv.gz): target share, carry share, and touch
share via team-level target/carry aggregation. Snap share, route
participation, red-zone usage, and role classification require separate
nflverse datasets (snap counts, participation, play-by-play) that are not
part of this artifact, so this module never estimates or invents them.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math
from typing import Any, Mapping, Sequence

from services.defense_matchup_calculation import full_ppr_points
from services.integrity.integrity_service import opportunity_evidence_threshold
from services.opportunity_evidence import build_nflverse_usage_evidence

CONTRACT_SCHEMA_VERSION = "nflverse-opportunity-publication-contracts.v1"
PRODUCTION_CALCULATION_VERSION = "full-ppr.v1"
SUPPORTED_PRODUCTION_POSITIONS = {"QB", "RB", "WR", "TE"}
UNSUPPORTED_PRODUCTION_POSITIONS = {"K", "DEF", "DST"}
UNAVAILABLE_METRICS = ("snap_share", "route_participation", "red_zone_share", "role_classification")
UNAVAILABLE_METRIC_BLOCKER = "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE"
THRESHOLD_OWNER = "services.integrity.integrity_service.opportunity_evidence_threshold"
PRODUCTION_INPUT_GROUPS = (
    ("passing_interceptions", "interceptions"),
    ("two_point_conversions", "passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions"),
    ("fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost"),
)
PRODUCTION_FIELDS = (
    "passing_yards", "passing_tds", "passing_interceptions",
    "rushing_yards", "rushing_tds", "receptions", "receiving_yards", "receiving_tds",
)
POSITION_PRODUCTION_FIELDS = {
    "QB": ("passing_yards", "passing_tds", "passing_interceptions"),
    "RB": ("rushing_yards", "rushing_tds", "receptions", "receiving_yards", "receiving_tds"),
    "WR": ("receptions", "receiving_yards", "receiving_tds"),
    "TE": ("receptions", "receiving_yards", "receiving_tds"),
}


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _production_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _opportunity_freshness(retrieved_at: Any, now: Any, threshold_seconds: int | None) -> tuple[str, str | None, int | None]:
    if not retrieved_at:
        return "UNAVAILABLE", "OPPORTUNITY_RETRIEVAL_TIME_UNAVAILABLE", None
    if threshold_seconds is None:
        return "UNAVAILABLE", "OPPORTUNITY_FRESHNESS_THRESHOLD_UNVERIFIED", None
    stamp = _timestamp(retrieved_at)
    if stamp is None:
        return "UNAVAILABLE", "OPPORTUNITY_RETRIEVAL_TIME_UNAVAILABLE", None
    evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
    age = max(0, int((evaluation_time - stamp).total_seconds()))
    if age <= threshold_seconds * .8:
        return "FRESH", None, age
    if age <= threshold_seconds:
        return "AGING", None, age
    return "STALE", "OPPORTUNITY_DATA_STALE", age


def _production_input_blockers(row: Mapping[str, Any]) -> list[str]:
    required = POSITION_PRODUCTION_FIELDS.get(_production_position(row), ())
    blockers = [f"PLAYER_WEEK_PRODUCTION_INPUT_UNAVAILABLE:{field}" for field in required if _production_number(_production_value(row, field)) is None]
    for group in PRODUCTION_INPUT_GROUPS:
        if not any(field in row for field in group):
            blockers.append(f"PLAYER_WEEK_PRODUCTION_INPUT_UNAVAILABLE:{group[0]}")
    return blockers


def _production_position(row: Mapping[str, Any]) -> str:
    return str(row.get("position") or row.get("position_group") or "").upper().replace("DST", "DEF")


def _production_value(row: Mapping[str, Any], field: str) -> Any:
    if field == "passing_interceptions":
        return row.get("passing_interceptions", row.get("interceptions"))
    return row.get(field)


def calculate_player_opportunity(
    weekly_stats: Sequence[Mapping[str, Any]],
    *,
    season: int,
    threshold_environment: Mapping[str, str] | None = None,
    source: str = "automated:nflverse",
    version: str | None = None,
    checksum: str | None = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    now: Any = None,
) -> dict[str, Any]:
    """Publish fail-closed target/carry/touch-share opportunity evidence per player-week."""
    threshold = opportunity_evidence_threshold(threshold_environment)
    freshness_state, freshness_blocker, age = _opportunity_freshness(retrieved_at, now, threshold.get("seconds"))

    input_row_count = len(weekly_stats)
    unresolved: list[dict[str, Any]] = []
    unsupported_positions: list[dict[str, Any]] = []
    production_blockers: list[dict[str, Any]] = []
    eligible_rows: list[dict[str, Any]] = []
    for row in weekly_stats:
        player_id = str(row.get("player_id") or "").strip()
        team = str(row.get("team") or "").strip()
        if not player_id or not team:
            unresolved.append({"row": dict(row), "reason": "OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"})
            continue
        position = _production_position(row)
        if position not in SUPPORTED_PRODUCTION_POSITIONS:
            reason = "PLAYER_WEEK_PRODUCTION_POSITION_UNSUPPORTED" if position in UNSUPPORTED_PRODUCTION_POSITIONS else "PLAYER_WEEK_PRODUCTION_POSITION_UNAVAILABLE"
            unsupported_positions.append({"player_id": player_id, "week": row.get("week"), "position": position or None, "reason": reason})
            continue
        input_blockers = _production_input_blockers(row)
        if input_blockers:
            production_blockers.append({"player_id": player_id, "week": row.get("week"), "blockers": input_blockers})
            continue
        production_points = full_ppr_points(row)
        if not math.isfinite(production_points):
            production_blockers.append({"player_id": player_id, "week": row.get("week"), "blockers": ["PLAYER_WEEK_PRODUCTION_NONFINITE"]})
            continue
        week = row.get("week")
        game_id = row.get("game_id") or f"{row.get('season')}:{week}:{team}:{row.get('opponent_team')}"
        eligible_rows.append({
            "player_id": player_id, "team": team, "week": week, "game_id": game_id,
            "position": position, "opponent_team": row.get("opponent_team"),
            "targets": _float(row.get("targets")), "carries": _float(row.get("carries")),
            **{field: _production_number(_production_value(row, field)) for field in PRODUCTION_FIELDS},
            "fantasy_points_ppr": production_points,
        })

    # Group by player-week identity to detect duplicate rows and contradictory team
    # assignment before any team total is computed; conflicted rows never contribute.
    groups: dict[tuple[str, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible_rows:
        groups[(row["player_id"], row["week"])].append(row)

    clean_rows: list[dict[str, Any]] = []
    duplicate_player_weeks: list[dict[str, Any]] = []
    contradictory_player_weeks: list[dict[str, Any]] = []
    for (player_id, week), group_rows in groups.items():
        if len(group_rows) == 1:
            clean_rows.append(group_rows[0])
            continue
        teams = sorted({row["team"] for row in group_rows})
        if len(teams) > 1:
            contradictory_player_weeks.append({"player_id": player_id, "week": week, "teams": teams, "row_count": len(group_rows)})
        else:
            duplicate_player_weeks.append({"player_id": player_id, "week": week, "team": teams[0], "row_count": len(group_rows)})

    duplicate_row_count = sum(item["row_count"] for item in duplicate_player_weeks)
    contradictory_row_count = sum(item["row_count"] for item in contradictory_player_weeks)

    team_targets: dict[tuple[str, Any], float] = defaultdict(float)
    team_carries: dict[tuple[str, Any], float] = defaultdict(float)
    for row in clean_rows:
        key = (row["team"], row["game_id"])
        team_targets[key] += row["targets"]
        team_carries[key] += row["carries"]

    published = []
    for row in clean_rows:
        player_id = row["player_id"]
        key = (row["team"], row["game_id"])
        total_targets = team_targets[key]
        total_carries = team_carries[key]
        total_touches = row["targets"] + row["carries"]
        total_team_touches = total_targets + total_carries
        target_share = round(row["targets"] / total_targets, 4) if total_targets > 0 else None
        carry_share = round(row["carries"] / total_carries, 4) if total_carries > 0 else None
        touch_share = round(total_touches / total_team_touches, 4) if total_team_touches > 0 else None
        evidence = build_nflverse_usage_evidence(
            {"targets": row["targets"], "target_share": target_share, "carries": row["carries"], "carry_share": carry_share, "touch_share": touch_share},
            player_id=player_id, season=season, week=row["week"],
            source=source, source_recorded_at=source_recorded_at, retrieved_at=retrieved_at,
            freshness_state=freshness_state,
            blocker=freshness_blocker,
        )
        evidence["age"] = age
        evidence["team"] = row["team"]
        evidence["position"] = row["position"]
        evidence["opponent_team"] = row["opponent_team"]
        evidence["fantasy_points_ppr"] = row["fantasy_points_ppr"]
        evidence["rush_attempts"] = row["carries"]
        evidence["pass_attempts"] = _float(row.get("attempts")) if "attempts" in row else None
        evidence["games_sample"] = 1
        evidence["sample_start_week"] = row["week"]
        evidence["sample_end_week"] = row["week"]
        evidence["target_volume"] = row["targets"]
        evidence["carry_volume"] = row["carries"]
        evidence["scoring_format"] = "FULL_PPR"
        evidence["calculation_version"] = PRODUCTION_CALCULATION_VERSION
        evidence["unavailable_metrics"] = list(UNAVAILABLE_METRICS)
        evidence["unavailable_metric_blocker"] = UNAVAILABLE_METRIC_BLOCKER
        evidence.update({field: row[field] for field in PRODUCTION_FIELDS})
        published.append(evidence)

    published_row_count = len(published)
    unresolved_identity_count = len(unresolved)
    excluded_row_count = unresolved_identity_count + duplicate_row_count + contradictory_row_count + len(unsupported_positions) + len(production_blockers)
    reconciliation = {
        "input_row_count": input_row_count,
        "eligible_input_count": len(eligible_rows),
        "published_row_count": published_row_count,
        "excluded_row_count": excluded_row_count,
        "unresolved_identity_count": unresolved_identity_count,
        "duplicate_player_week_count": len(duplicate_player_weeks),
        "contradictory_player_week_count": len(contradictory_player_weeks),
        "duplicate_player_weeks": duplicate_player_weeks,
        "contradictory_player_weeks": contradictory_player_weeks,
        "reconciled": (published_row_count + excluded_row_count) == input_row_count,
    }

    threshold_contract = {
        "identifier": threshold.get("id"),
        "value": threshold.get("seconds"),
        "state": "VERIFIED" if threshold.get("seconds") is not None else "UNAVAILABLE",
        "source": "OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS",
        "owner": THRESHOLD_OWNER,
        "schema_version": CONTRACT_SCHEMA_VERSION,
    }
    publication_contracts = {"threshold": threshold_contract}
    production_evidence = {
        f"{row['player_id']}:{row['week']}": {field: row.get(field) for field in PRODUCTION_FIELDS}
        for row in published
    }
    return {
        "season": season,
        "weeks": sorted({row["week"] for row in published}),
        "rows": published,
        "unresolved_identities": unresolved,
        "unsupported_positions": unsupported_positions,
        "production_blockers": production_blockers,
        "reconciliation": reconciliation,
        "unavailable_metrics": list(UNAVAILABLE_METRICS),
        "unavailable_metric_blocker": UNAVAILABLE_METRIC_BLOCKER,
        "production_contract": {
            "supported_positions": sorted(SUPPORTED_PRODUCTION_POSITIONS),
            "unsupported_positions": sorted(UNSUPPORTED_PRODUCTION_POSITIONS),
            "scoring_format": "FULL_PPR",
            "calculation_version": PRODUCTION_CALCULATION_VERSION,
        },
        "freshness_state": freshness_state,
        "blocker": freshness_blocker,
        "publication_contracts": publication_contracts,
        "provenance": {
            "source": source, "version": version, "checksum": checksum,
            "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at,
            "attribution": "NFLverse data, licensed under CC BY 4.0.",
            "publication_contracts": publication_contracts,
            "reconciliation": reconciliation,
            "production_evidence": production_evidence,
        },
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "decision_effect": "NONE",
    }
