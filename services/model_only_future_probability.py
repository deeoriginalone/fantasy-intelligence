"""Informational model-only future win-probability evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping

from market_intelligence import elo_home

MODEL_VERSION = "model-only-future-probability-v1.0.0"
SOURCE_TYPE = "MODEL_ONLY"
INFORMATIONAL_AUTHORITY = "INFORMATIONAL_ONLY"


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _blocked(blockers: list[str], *, source_recorded_at: Any = None, generated_at: Any = None) -> dict[str, Any]:
    return {
        "available": False,
        "home_win_probability": None,
        "away_win_probability": None,
        "source_type": SOURCE_TYPE,
        "authority_state": "UNAVAILABLE",
        "decision_effect": "NONE",
        "model_version": None,
        "generated_at": generated_at,
        "source_recorded_at": source_recorded_at,
        "freshness_state": "UNAVAILABLE",
        "completeness_state": "INCOMPLETE",
        "blocker_reasons": blockers,
        "lineage": {},
    }


def build_model_only_future_probability(
    *,
    season: int,
    week: int,
    game_id: str,
    home_team: str,
    away_team: str,
    home_elo: Any,
    away_elo: Any,
    source_identifiers: Mapping[str, Any] | None,
    source_recorded_at: Any,
    generated_at: Any,
    model_version: str,
    freshness_threshold_id: str | None,
    freshness_threshold_seconds: Any,
    situational_inputs: Mapping[str, Any] | None = None,
    now: Any = None,
) -> dict[str, Any]:
    """Build non-authoritative probability evidence without changing any consumer."""
    blockers: list[str] = []
    normalized_home = str(home_team or "").strip().upper()
    normalized_away = str(away_team or "").strip().upper()
    normalized_game_id = str(game_id or "").strip()
    normalized_model_version = str(model_version or "").strip()
    normalized_threshold_id = str(freshness_threshold_id or "").strip()
    if not isinstance(season, int) or season <= 0 or not isinstance(week, int) or week <= 0:
        blockers.append("FUTURE_PROBABILITY_SCHEDULE_IDENTITY_UNAVAILABLE")
    if not normalized_game_id or not normalized_home or not normalized_away or normalized_home == normalized_away:
        blockers.append("FUTURE_PROBABILITY_GAME_IDENTITY_UNAVAILABLE")
    if not isinstance(source_identifiers, Mapping) or not source_identifiers or any(value in (None, "") for value in source_identifiers.values()):
        blockers.append("FUTURE_PROBABILITY_SOURCE_ID_UNAVAILABLE")
    recorded = _timestamp(source_recorded_at)
    generated = _timestamp(generated_at)
    if recorded is None:
        blockers.append("FUTURE_PROBABILITY_SOURCE_TIMESTAMP_UNAVAILABLE")
    if generated is None:
        blockers.append("FUTURE_PROBABILITY_GENERATED_TIMESTAMP_UNAVAILABLE")
    if not normalized_model_version:
        blockers.append("FUTURE_PROBABILITY_MODEL_VERSION_UNAVAILABLE")
    try:
        threshold_seconds = int(freshness_threshold_seconds)
    except (TypeError, ValueError):
        threshold_seconds = 0
    if not normalized_threshold_id or threshold_seconds <= 0:
        blockers.append("FUTURE_PROBABILITY_FRESHNESS_THRESHOLD_UNAVAILABLE")
    try:
        if isinstance(home_elo, bool) or isinstance(away_elo, bool):
            raise ValueError
        home_rating = float(home_elo)
        away_rating = float(away_elo)
        if not isfinite(home_rating) or not isfinite(away_rating):
            raise ValueError
    except (TypeError, ValueError):
        blockers.append("FUTURE_PROBABILITY_ELO_EVIDENCE_UNAVAILABLE")
    if situational_inputs is not None and not isinstance(situational_inputs, Mapping):
        blockers.append("FUTURE_PROBABILITY_SITUATIONAL_INPUTS_INVALID")
    freshness_blocker = "FUTURE_PROBABILITY_FRESHNESS_THRESHOLD_UNAVAILABLE"
    structural_blockers = [blocker for blocker in blockers if blocker != freshness_blocker]
    if structural_blockers:
        return _blocked(blockers, source_recorded_at=source_recorded_at, generated_at=generated_at)

    if freshness_blocker in blockers:
        freshness_state = "UNAVAILABLE"
    else:
        evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
        age_seconds = max(0, int((evaluation_time - recorded).total_seconds()))
        if age_seconds <= threshold_seconds * 0.8:
            freshness_state = "FRESH"
        elif age_seconds <= threshold_seconds:
            freshness_state = "AGING"
        else:
            return {
                **_blocked(["FUTURE_PROBABILITY_DATA_STALE"], source_recorded_at=source_recorded_at, generated_at=generated_at),
                "model_version": normalized_model_version,
                "freshness_state": "STALE",
                "completeness_state": "COMPLETE",
            }

    try:
        home_probability = float(elo_home(away_rating, home_rating))
    except (TypeError, ValueError, OverflowError):
        return _blocked(["FUTURE_PROBABILITY_CALCULATION_FAILED"], source_recorded_at=source_recorded_at, generated_at=generated_at)
    away_probability = 1.0 - home_probability
    if not (0.0 <= home_probability <= 1.0 and 0.0 <= away_probability <= 1.0):
        return _blocked(["FUTURE_PROBABILITY_CALCULATION_FAILED"], source_recorded_at=source_recorded_at, generated_at=generated_at)
    return {
        "available": not blockers,
        "home_win_probability": home_probability,
        "away_win_probability": away_probability,
        "source_type": SOURCE_TYPE,
        "authority_state": INFORMATIONAL_AUTHORITY,
        "decision_effect": "NONE",
        "model_version": normalized_model_version,
        "generated_at": generated_at,
        "source_recorded_at": source_recorded_at,
        "freshness_state": freshness_state,
        "completeness_state": "COMPLETE",
        "blocker_reasons": blockers,
        "lineage": {
            "owner": "services.model_only_future_probability",
            "calculation": "market_intelligence.elo_home",
            "season": season,
            "week": week,
            "game_id": normalized_game_id,
            "home_team": normalized_home,
            "away_team": normalized_away,
            "source_identifiers": dict(source_identifiers),
            "freshness_threshold_id": normalized_threshold_id,
            "freshness_threshold_seconds": threshold_seconds,
            "situational_inputs_supplied": situational_inputs is not None,
        },
    }
