"""Fail-closed opportunity usage evidence and descriptive change facts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

METRICS = (
    "snap_share",
    "route_participation",
    "target_share",
    "touch_share",
    "rush_share",
    "red_zone_share",
    "goal_line_share",
    "role_stability",
)
TREND_METRICS = (
    "target_share",
    "snap_share",
    "touch_share",
    "route_participation",
    "red_zone_share",
)
MARKET_VALUE_STATES = {
    "VALUE_RISING",
    "VALUE_FALLING",
    "VALUE_STABLE",
    "INSUFFICIENT_MARKET_DATA",
    "UNAVAILABLE",
}
MARKET_SIGNAL_STATES = {
    "UNDERVALUED_SIGNAL",
    "OVERVALUED_SIGNAL",
    "FAIR_VALUE_SIGNAL",
    "INSUFFICIENT_MARKET_DATA",
    "UNAVAILABLE",
}
TRADE_OPPORTUNITY_STATES = {
    "TRADE_OPPORTUNITY_PRESENT",
    "TRADE_OPPORTUNITY_WEAK",
    "TRADE_OPPORTUNITY_NONE",
    "INSUFFICIENT_EVIDENCE",
    "UNAVAILABLE",
}
DECISION_CENTER_PANELS = (
    "MUST_ACT",
    "START_SIT_ALERTS",
    "WAIVER_ALERTS",
    "TRADE_ALERTS",
    "OPPORTUNITY_ALERTS",
    "RISK_ALERTS",
    "NO_ACTION_NEEDED",
)
FRESHNESS_STATES = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
COMPLETENESS_STATES = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}
USAGE_SCHEMA_VERSION = "nflverse-opportunity-evidence.v1"


def build_nflverse_usage_evidence(
    values: Mapping[str, Any] | None,
    *,
    player_id: Any,
    season: Any,
    week: Any,
    source: str | None = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    freshness_state: str = "UNAVAILABLE",
    completeness_state: str = "COMPLETE",
    blocker: str | None = None,
) -> dict[str, Any]:
    """Publish only NFLverse usage fields proven by the weekly artifact."""
    values = dict(values or {})
    target_volume = _nonnegative(values.get("targets"))
    target_share = _share(values.get("target_share"))
    carry_volume = _nonnegative(values.get("carries"))
    carry_share = _share(values.get("carry_share"))
    touch_share = _share(values.get("touch_share"))
    snap_share = _share(values.get("snap_share"))
    route_participation = _share(values.get("route_participation"))
    red_zone_share = _share(values.get("red_zone_share"))
    role_classification = values.get("role_classification") or None
    blockers = []
    if player_id in (None, ""):
        blockers.append("OPPORTUNITY_PLAYER_ID_UNAVAILABLE")
    if season in (None, ""):
        blockers.append("OPPORTUNITY_SEASON_UNAVAILABLE")
    if week in (None, ""):
        blockers.append("OPPORTUNITY_WEEK_UNAVAILABLE")
    if target_volume is None:
        blockers.append("OPPORTUNITY_TARGETS_UNAVAILABLE")
    if target_share is None:
        blockers.append("OPPORTUNITY_TARGET_SHARE_UNAVAILABLE")
    if carry_volume is None:
        blockers.append("OPPORTUNITY_CARRIES_UNAVAILABLE")
    if not source or not retrieved_at:
        blockers.append("OPPORTUNITY_SOURCE_METADATA_UNAVAILABLE")
    if blocker:
        blockers.append(blocker)
    freshness = _state(freshness_state, FRESHNESS_STATES)
    completeness = _state(completeness_state, COMPLETENESS_STATES)
    if freshness not in {"FRESH", "AGING"}:
        blockers.append("OPPORTUNITY_EVIDENCE_NOT_CURRENT")
    if completeness != "COMPLETE":
        blockers.append("OPPORTUNITY_INCOMPLETE")
    blockers = list(dict.fromkeys(blockers))
    return {
        "player_id": player_id,
        "season": season,
        "week": week,
        "target_volume": target_volume,
        "target_share": target_share,
        "carry_volume": carry_volume,
        "carry_share": carry_share,
        "snap_share": snap_share,
        "touch_share": touch_share,
        "route_participation": route_participation,
        "red_zone_share": red_zone_share,
        "role_classification": role_classification,
        "source": source or "UNVERIFIED",
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "freshness_state": freshness,
        "completeness_state": "COMPLETE" if not blockers else "INCOMPLETE",
        "blockers": blockers,
        "lineage": {"source": source, "player_id": player_id, "season": season, "week": week},
        "schema_version": USAGE_SCHEMA_VERSION,
        "authoritative": not blockers,
        "decision_effect": "NONE",
    }


def build_nflverse_usage_what_changed(
    current: Mapping[str, Any] | None,
    previous: Mapping[str, Any] | None,
    rolling_baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare proven target/carry usage without inferring role labels."""
    result = {
        "state": "UNAVAILABLE", "changes": [], "summaries": [],
        "target_volume_change": None, "target_share_change": None,
        "carry_volume_change": None, "workload_change": "UNAVAILABLE",
        "role_change": "UNAVAILABLE", "blocker": "OPPORTUNITY_COMPARISON_UNAVAILABLE",
        "recommendation_impact": "Evidence only; no recommendation or score changes are made.",
        "decision_effect": "NONE",
    }
    if not current or not previous or not rolling_baseline:
        return result
    if not all(item.get("authoritative") for item in (current, previous, rolling_baseline)):
        result["blocker"] = "OPPORTUNITY_PERIOD_UNAVAILABLE"
        return result
    keys = (("target_volume", "Target Volume"), ("target_share", "Target Share"), ("carry_volume", "Carry Volume"))
    changes = []
    for key, label in keys:
        previous_delta = current[key] - previous[key]
        baseline_delta = current[key] - rolling_baseline[key]
        previous_classification = _change_classification(previous_delta)
        baseline_classification = _change_classification(baseline_delta)
        result_key = f"{key}_change"
        result[result_key] = {
            "metric": key, "label": label, "current": current[key],
            "previous": previous[key], "baseline": rolling_baseline[key],
            "previous_delta": round(previous_delta, 4),
            "baseline_delta": round(baseline_delta, 4),
            "previous_classification": previous_classification,
            "baseline_classification": baseline_classification,
        }
        changes.append({"metric": key, "label": label, "direction": previous_classification, "delta": round(previous_delta, 4), "current": current[key], "previous": previous[key], "baseline": rolling_baseline[key]})
        result["summaries"].append(f"{label} {_summary_word(previous_classification)}")
    workload_deltas = [current[key] - previous[key] for key in ("target_volume", "carry_volume", "target_share")]
    average = sum(workload_deltas) / len(workload_deltas)
    result.update(state="AVAILABLE", changes=changes, workload_change="UP" if average > 0 else "DOWN" if average < 0 else "UNCHANGED", blocker=None)
    return result


def _change_classification(delta: float) -> str:
    return "INCREASING" if delta > 0 else "DECREASING" if delta < 0 else "STABLE"


def _summary_word(classification: str) -> str:
    return classification.title()


def build_opportunity_evidence(
    values: Mapping[str, Any] | None,
    *,
    source: str | None = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    age: int | None = None,
    freshness_state: str = "UNAVAILABLE",
    completeness_state: str = "COMPLETE",
    blocker: str | None = None,
    recommendation_impact: str | None = None,
) -> dict[str, Any]:
    """Return usage metrics only when source, freshness, and values are valid."""
    state = _state(freshness_state, FRESHNESS_STATES)
    completeness = _state(completeness_state, COMPLETENESS_STATES)
    normalized = {metric: _number(values.get(metric)) if values else None for metric in METRICS}
    invalid = [metric for metric, value in normalized.items() if value is None]
    if invalid and completeness == "COMPLETE":
        completeness = "INCOMPLETE"
    if not source or not retrieved_at:
        state = "UNAVAILABLE"
        blocker = blocker or "OPPORTUNITY_SOURCE_METADATA_UNAVAILABLE"
    elif invalid:
        state = "BLOCKED"
        blocker = blocker or "OPPORTUNITY_VALUES_UNAVAILABLE"
    elif state not in {"FRESH", "AGING"}:
        blocker = blocker or "OPPORTUNITY_EVIDENCE_NOT_CURRENT"
    authoritative = state in {"FRESH", "AGING"} and completeness == "COMPLETE" and not blocker
    return {
        **normalized,
        "source": source or "UNVERIFIED",
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "age": age,
        "freshness_state": state,
        "completeness_state": completeness,
        "blocker": blocker,
        "recommendation_impact": recommendation_impact or (
            "Informational evidence only; it does not change recommendations."
            if authoritative else
            "Opportunity evidence cannot support a recommendation until refreshed and verified."
        ),
        "authoritative": authoritative,
    }


def build_what_changed(
    current: Mapping[str, Any] | None,
    previous: Mapping[str, Any] | None,
    rolling_baseline: Mapping[str, Any] | None,
    *,
    published_weeks: list[Mapping[str, Any]] | None = None,
    player_id: Any = None,
    season: Any = None,
    requested_week: Any = None,
) -> dict[str, Any]:
    """Describe metric movements without drawing player-level conclusions."""
    if published_weeks is not None:
        return _build_published_what_changed(
            published_weeks,
            player_id=player_id,
            season=season,
            requested_week=requested_week,
        )
    result = {
        "state": "UNAVAILABLE",
        "current_week": dict(current or {}),
        "previous_week": dict(previous or {}),
        "rolling_baseline": dict(rolling_baseline or {}),
        "changes": [],
        "workload_change": "UNAVAILABLE",
        "role_change": "UNAVAILABLE",
        "blocker": "OPPORTUNITY_COMPARISON_UNAVAILABLE",
        "recommendation_impact": "Evidence only; no recommendation or score changes are made.",
    }
    if not current or not previous or not rolling_baseline:
        return result
    if not current.get("authoritative"):
        result["blocker"] = "OPPORTUNITY_CURRENT_EVIDENCE_UNAVAILABLE"
        return result
    if not previous.get("authoritative"):
        result["blocker"] = "OPPORTUNITY_PREVIOUS_EVIDENCE_UNAVAILABLE"
        return result
    if not rolling_baseline.get("authoritative"):
        result["blocker"] = "OPPORTUNITY_BASELINE_UNAVAILABLE"
        return result
    labels = {
        "target_share": "Target Share",
        "snap_share": "Snap Share",
        "red_zone_share": "Red-Zone Usage",
        "route_participation": "Routes Run",
    }
    for metric, label in labels.items():
        current_value = current[metric]
        previous_value = previous[metric]
        delta = current_value - previous_value
        result["changes"].append({
            "metric": metric,
            "label": label,
            "direction": "UP" if delta > 0 else "DOWN" if delta < 0 else "UNCHANGED",
            "delta": round(delta, 4),
            "current": current_value,
            "previous": previous_value,
            "baseline": rolling_baseline[metric],
        })
    workload_deltas = [
        current[metric] - previous[metric]
        for metric in ("snap_share", "touch_share", "target_share", "route_participation")
    ]
    workload_delta = sum(workload_deltas) / len(workload_deltas)
    result["workload_change"] = "UP" if workload_delta > 0 else "DOWN" if workload_delta < 0 else "UNCHANGED"
    role_delta = current["role_stability"] - previous["role_stability"]
    result["role_change"] = "UP" if role_delta > 0 else "DOWN" if role_delta < 0 else "UNCHANGED"
    result["state"] = "AVAILABLE"
    result["blocker"] = None
    return result


PUBLISHED_COMPARISON_METRICS = (
    ("target_volume", "Targets"),
    ("carry_volume", "Carries"),
    ("target_share", "Target Share"),
    ("carry_share", "Carry Share"),
    ("touch_share", "Touch Share"),
)
UNAVAILABLE_PUBLISHED_METRICS = (
    ("snap_share", "Snap Share"),
    ("route_participation", "Routes Run"),
    ("red_zone_share", "Red-Zone Usage"),
    ("role_classification", "Role Classification"),
)
PUBLISHED_REQUIRED_FIELDS = (
    "player_id", "season", "week", "source", "source_authority",
    "source_recorded_at", "retrieved_at", "artifact_id", "version",
    "checksum", "freshness_threshold_id", "freshness_state",
    "completeness_state", "publication_state", "lineage",
)


def _build_published_what_changed(
    published_weeks: list[Mapping[str, Any]],
    *,
    player_id: Any = None,
    season: Any = None,
    requested_week: Any = None,
) -> dict[str, Any]:
    """Compare verified published player-week rows without adding conclusions."""
    result = {
        "schema_version": "what-changed.v2",
        "player_id": player_id,
        "season": season,
        "current_week": requested_week,
        "prior_comparison_week": None,
        "comparison_window_type": "UNAVAILABLE",
        "state": "UNAVAILABLE",
        "current_context": {},
        "prior_context": {},
        "changes": [],
        "summary": [],
        "summaries": [],
        "blockers": [],
        "lineage": {},
        "decision_effect": "INFORMATIONAL_ONLY",
    }
    rows = list(published_weeks or [])
    if not rows:
        result["blockers"] = ["OPPORTUNITY_CURRENT_EVIDENCE_UNAVAILABLE"]
        return result
    if not all(isinstance(row, Mapping) for row in rows):
        result["blockers"] = ["OPPORTUNITY_PUBLISHED_ROW_INVALID"]
        return result

    identity_values = {row.get("player_id") for row in rows}
    if player_id in (None, ""):
        if len(identity_values) != 1 or None in identity_values or "" in identity_values:
            result["blockers"] = ["OPPORTUNITY_PLAYER_IDENTITY_AMBIGUOUS"]
            return result
        player_id = next(iter(identity_values))
    result["player_id"] = player_id
    player_rows = [row for row in rows if row.get("player_id") == player_id]
    if not player_rows:
        result["blockers"] = ["OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"]
        return result

    seasons = {row.get("season") for row in player_rows}
    if season is None:
        if len(seasons) != 1 or None in seasons:
            result["blockers"] = ["OPPORTUNITY_CROSS_SEASON_COMPARISON_UNAUTHORIZED"]
            return result
        season = next(iter(seasons))
    result["season"] = season
    if any(row.get("season") != season for row in player_rows):
        result["blockers"] = ["OPPORTUNITY_CROSS_SEASON_COMPARISON_UNAUTHORIZED"]
        return result

    invalid_rows = [row for row in player_rows if _published_row_blockers(row)]
    if invalid_rows:
        result["blockers"] = list(dict.fromkeys(
            blocker for row in invalid_rows for blocker in _published_row_blockers(row)
        ))
        result["state"] = "BLOCKED"
        return result
    by_week: dict[Any, Mapping[str, Any]] = {}
    duplicate_weeks = set()
    for row in player_rows:
        week = row["week"]
        if week in by_week:
            duplicate_weeks.add(week)
        by_week[week] = row
    if duplicate_weeks:
        result["state"] = "BLOCKED"
        result["blockers"] = ["OPPORTUNITY_DUPLICATE_PLAYER_WEEK"]
        return result

    try:
        current_week = requested_week if requested_week is not None else max(by_week)
        earlier_weeks = [week for week in by_week if week < current_week]
    except TypeError:
        result["state"] = "BLOCKED"
        result["blockers"] = ["OPPORTUNITY_WEEK_UNAVAILABLE"]
        return result
    result["current_week"] = current_week
    current = by_week.get(current_week)
    if current is None:
        result["blockers"] = ["OPPORTUNITY_CURRENT_WEEK_UNAVAILABLE"]
        return result
    if not earlier_weeks:
        result["blockers"] = ["OPPORTUNITY_PRIOR_WEEK_UNAVAILABLE"]
        return result
    prior_week = current_week - 1 if current_week - 1 in by_week else max(earlier_weeks)
    prior = by_week[prior_week]
    result["prior_comparison_week"] = prior_week
    result["comparison_window_type"] = "ADJACENT" if prior_week == current_week - 1 else "NON_ADJACENT"
    result["current_context"] = _published_context(current)
    result["prior_context"] = _published_context(prior)
    result["lineage"] = {
        "current_week": current_week,
        "prior_week": prior_week,
        "current_lineage": current.get("lineage"),
        "prior_lineage": prior.get("lineage"),
    }
    for metric, label in PUBLISHED_COMPARISON_METRICS:
        current_value = current.get(metric)
        prior_value = prior.get(metric)
        comparison = {
            "metric": metric,
            "label": label,
            "current_value": current_value,
            "prior_value": prior_value,
            "absolute_delta": None,
            "direction": "UNAVAILABLE",
            "availability_state": "UNAVAILABLE",
            "current_week": current_week,
            "prior_week": prior_week,
            "blocker": None,
        }
        if current_value is None or prior_value is None:
            comparison["blocker"] = "OPPORTUNITY_METRIC_VALUE_UNAVAILABLE"
        else:
            delta = round(current_value - prior_value, 4)
            comparison.update(
                absolute_delta=delta,
                direction="INCREASED" if delta > 0 else "DECREASED" if delta < 0 else "UNCHANGED",
                availability_state="AVAILABLE",
            )
            result["summary"].append(
                f"{label} {comparison['direction'].lower()} from the verified Week {prior_week} value to the verified Week {current_week} value."
            )
        result["changes"].append(comparison)
    for metric, label in UNAVAILABLE_PUBLISHED_METRICS:
        result["changes"].append({
            "metric": metric,
            "label": label,
            "current_value": None,
            "prior_value": None,
            "absolute_delta": None,
            "direction": "UNAVAILABLE",
            "availability_state": "UNAVAILABLE",
            "current_week": current_week,
            "prior_week": prior_week,
            "blocker": "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE",
        })
    result["summaries"] = list(result["summary"])
    result["state"] = "AVAILABLE"
    return result


def _published_row_blockers(row: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:{field}"
        for field in PUBLISHED_REQUIRED_FIELDS
        if row.get(field) in (None, "", {})
    ]
    if row.get("source_authority") != "automated":
        blockers.append("OPPORTUNITY_SOURCE_AUTHORITY_UNSUPPORTED")
    if not str(row.get("source") or "").startswith("automated:nflverse"):
        blockers.append("OPPORTUNITY_SOURCE_UNSUPPORTED")
    if row.get("freshness_state") not in {"FRESH", "AGING"}:
        blockers.append("OPPORTUNITY_EVIDENCE_NOT_CURRENT")
    if row.get("completeness_state") != "COMPLETE":
        blockers.append("OPPORTUNITY_INCOMPLETE")
    if row.get("publication_state") != "PUBLISHED":
        blockers.append("OPPORTUNITY_PUBLICATION_STATE_INVALID")
    reconciliation = (row.get("lineage") or {}).get("reconciliation")
    if not isinstance(reconciliation, Mapping) or reconciliation.get("reconciled") is not True:
        blockers.append("OPPORTUNITY_RECONCILIATION_UNVERIFIED")
    return list(dict.fromkeys(blockers))


def published_opportunity_row_blockers(row: Mapping[str, Any]) -> list[str]:
    """Expose the publication-row validation used by What Changed readers."""
    return _published_row_blockers(row)


def _published_context(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in (
        "source", "source_authority", "source_recorded_at", "retrieved_at",
        "artifact_id", "version", "checksum", "freshness_threshold_id",
        "freshness_state", "completeness_state", "publication_state",
    )}


def classify_opportunity_trend(
    current: Mapping[str, Any] | None,
    previous: Mapping[str, Any] | None,
    rolling_baseline: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify verified opportunity movement without making a recommendation."""
    result = {
        "state": "UNAVAILABLE",
        "explanations": [],
        "blocker": None,
        "decision_effect": "NONE",
    }
    if not current or not current.get("authoritative"):
        result["blocker"] = "UNAVAILABLE"
        return result
    if not previous or not rolling_baseline:
        result["state"] = "INSUFFICIENT_HISTORY"
        result["blocker"] = "INSUFFICIENT_HISTORY"
        return result
    if not previous.get("authoritative") or not rolling_baseline.get("authoritative"):
        result["blocker"] = "BLOCKED"
        return result
    if any(metric not in current or metric not in previous or metric not in rolling_baseline for metric in TREND_METRICS):
        result["blocker"] = "BLOCKED"
        return result

    comparisons = {
        metric: (current[metric] - previous[metric], current[metric] - rolling_baseline[metric])
        for metric in TREND_METRICS
    }
    if all(previous_delta >= 0 and baseline_delta >= 0 for previous_delta, baseline_delta in comparisons.values()) and any(
        previous_delta > 0 or baseline_delta > 0 for previous_delta, baseline_delta in comparisons.values()
    ):
        result["state"] = "GROWING_OPPORTUNITY"
    elif all(previous_delta <= 0 and baseline_delta <= 0 for previous_delta, baseline_delta in comparisons.values()) and any(
        previous_delta < 0 or baseline_delta < 0 for previous_delta, baseline_delta in comparisons.values()
    ):
        result["state"] = "SHRINKING_OPPORTUNITY"
    else:
        result["state"] = "STABLE_OPPORTUNITY"

    labels = {
        "target_share": "Target Share",
        "snap_share": "Snap Share",
        "touch_share": "Touch Share",
        "route_participation": "Routes Run",
        "red_zone_share": "Red-Zone Usage",
    }
    for metric, (previous_delta, baseline_delta) in comparisons.items():
        if previous_delta > 0 and baseline_delta > 0:
            result["explanations"].append(f"↑ {labels[metric]}")
        elif previous_delta < 0 and baseline_delta < 0:
            result["explanations"].append(f"↓ {labels[metric]}")
    return result


def build_market_value_evidence(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize explicitly supplied market evidence without deriving player value."""
    config = dict(config or {})
    state = str(config.get("market_value_state") or "UNAVAILABLE").upper()
    freshness = _state(config.get("freshness_state"), FRESHNESS_STATES)
    completeness = _state(config.get("completeness_state"), COMPLETENESS_STATES)
    blocker = config.get("blocker")
    if state not in MARKET_VALUE_STATES:
        state = "UNAVAILABLE"
        blocker = blocker or "MARKET_VALUE_STATE_UNKNOWN"
    if not config.get("source") or not config.get("source_recorded_at") or not config.get("retrieved_at"):
        state = "UNAVAILABLE"
        blocker = blocker or "MARKET_VALUE_SOURCE_METADATA_UNAVAILABLE"
    elif freshness not in {"FRESH", "AGING"}:
        state = "UNAVAILABLE"
        blocker = blocker or ("BLOCKED" if freshness == "BLOCKED" else "MARKET_VALUE_FRESHNESS_UNSUPPORTED")
    elif completeness != "COMPLETE":
        state = "INSUFFICIENT_MARKET_DATA"
        blocker = blocker or "INSUFFICIENT_MARKET_DATA"
    authoritative = state in {"VALUE_RISING", "VALUE_FALLING", "VALUE_STABLE"} and not blocker
    return {
        "market_value_state": state,
        "market_value_source": config.get("source") or "UNVERIFIED",
        "source_recorded_at": config.get("source_recorded_at"),
        "retrieved_at": config.get("retrieved_at"),
        "freshness_state": freshness,
        "completeness_state": completeness,
        "blocker": blocker,
        "recommendation_impact": config.get("recommendation_impact") or (
            "Informational evidence only; it does not change recommendations."
            if authoritative else
            "Market value evidence cannot support a recommendation until refreshed and verified."
        ),
        "authoritative": authoritative,
    }


def classify_market_signal(
    opportunity_classification: Mapping[str, Any] | None,
    what_changed: Mapping[str, Any] | None,
    market_value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify supported opportunity/value alignment as evidence only."""
    result = {
        "market_signal_state": "UNAVAILABLE",
        "blocker": None,
        "recommendation_impact": "Informational evidence only; it does not change recommendations.",
        "authoritative": False,
    }
    if not market_value or not market_value.get("authoritative"):
        result["blocker"] = "UNAVAILABLE"
        result["recommendation_impact"] = "Market signal evidence cannot be assessed until refreshed and verified."
        return result
    if not opportunity_classification or not what_changed:
        result["market_signal_state"] = "INSUFFICIENT_MARKET_DATA"
        result["blocker"] = "INSUFFICIENT_MARKET_DATA"
        return result
    if what_changed.get("state") != "AVAILABLE":
        result["market_signal_state"] = "INSUFFICIENT_MARKET_DATA"
        result["blocker"] = "INSUFFICIENT_MARKET_DATA"
        return result
    opportunity_state = opportunity_classification.get("state")
    market_state = market_value.get("market_value_state")
    if opportunity_state not in {"GROWING_OPPORTUNITY", "SHRINKING_OPPORTUNITY", "STABLE_OPPORTUNITY"}:
        result["blocker"] = "BLOCKED"
        result["recommendation_impact"] = "Market signal evidence cannot be assessed from unsupported evidence."
        return result
    if market_state not in {"VALUE_RISING", "VALUE_FALLING", "VALUE_STABLE"}:
        result["blocker"] = "BLOCKED"
        result["recommendation_impact"] = "Market signal evidence cannot be assessed from unsupported evidence."
        return result
    if opportunity_state == "GROWING_OPPORTUNITY" and market_state == "VALUE_FALLING":
        result["market_signal_state"] = "UNDERVALUED_SIGNAL"
    elif opportunity_state == "SHRINKING_OPPORTUNITY" and market_state == "VALUE_RISING":
        result["market_signal_state"] = "OVERVALUED_SIGNAL"
    else:
        result["market_signal_state"] = "FAIR_VALUE_SIGNAL"
    result["authoritative"] = True
    return result


def classify_trade_opportunity(
    opportunity_classification: Mapping[str, Any] | None,
    market_value: Mapping[str, Any] | None,
    market_signal: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify trade-opportunity alignment as evidence without suggesting an action."""
    result = {
        "trade_opportunity_state": "UNAVAILABLE",
        "blocker": None,
        "recommendation_impact": "Informational evidence only; it does not change recommendations.",
        "authoritative": False,
    }
    if not candidate or not market_signal or not opportunity_classification or not market_value:
        result["blocker"] = "UNAVAILABLE"
        return result
    if not opportunity_classification.get("state") or not market_value.get("market_value_state"):
        result["trade_opportunity_state"] = "INSUFFICIENT_EVIDENCE"
        result["blocker"] = "INSUFFICIENT_EVIDENCE"
        return result
    if opportunity_classification.get("state") == "INSUFFICIENT_HISTORY":
        result["trade_opportunity_state"] = "INSUFFICIENT_EVIDENCE"
        result["blocker"] = "INSUFFICIENT_EVIDENCE"
        return result
    if not all(item.get("authoritative") for item in (opportunity_classification, market_value, market_signal, candidate)):
        result["blocker"] = "BLOCKED"
        result["recommendation_impact"] = "Trade opportunity evidence cannot be assessed from unsupported evidence."
        return result
    candidate_state = candidate.get("candidate_state")
    signal_state = market_signal.get("market_signal_state")
    if candidate_state not in {"BUY_LOW_CANDIDATE", "SELL_HIGH_CANDIDATE", "FAIR_VALUE"}:
        result["blocker"] = "BLOCKED"
        result["recommendation_impact"] = "Trade opportunity evidence cannot be assessed from unsupported evidence."
        return result
    if signal_state not in {"UNDERVALUED_SIGNAL", "OVERVALUED_SIGNAL", "FAIR_VALUE_SIGNAL"}:
        result["blocker"] = "BLOCKED"
        result["recommendation_impact"] = "Trade opportunity evidence cannot be assessed from unsupported evidence."
        return result
    if (candidate_state == "BUY_LOW_CANDIDATE" and signal_state == "UNDERVALUED_SIGNAL") or (candidate_state == "SELL_HIGH_CANDIDATE" and signal_state == "OVERVALUED_SIGNAL"):
        result["trade_opportunity_state"] = "TRADE_OPPORTUNITY_PRESENT"
    elif candidate_state == "FAIR_VALUE" and signal_state == "FAIR_VALUE_SIGNAL":
        result["trade_opportunity_state"] = "TRADE_OPPORTUNITY_NONE"
    else:
        result["trade_opportunity_state"] = "TRADE_OPPORTUNITY_WEAK"
    result["authoritative"] = True
    return result


def build_decision_center(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Aggregate existing evidence into display-only, non-prioritized panels."""
    evidence = dict(evidence or {})
    freshness = evidence.get("freshness") or "UNAVAILABLE"
    completeness = evidence.get("completeness") or "UNAVAILABLE"
    blocker = evidence.get("blocker")
    if blocker or freshness in {"UNKNOWN", "UNAVAILABLE", "BLOCKED"}:
        status = "BLOCKED"
    elif completeness in {"INCOMPLETE", "UNKNOWN", "UNAVAILABLE"}:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "AVAILABLE"
    panels = []
    for panel in DECISION_CENTER_PANELS:
        panels.append({
            "panel": panel,
            "status": status if panel not in {"MUST_ACT", "NO_ACTION_NEEDED"} else "UNAVAILABLE",
            "why": "Existing verified evidence is summarized here; no action is generated.",
            "affected_area": panel.lower(),
            "freshness": freshness,
            "blocker": blocker,
            "confidence_impact": "No confidence changes; informational evidence only.",
        })
    return {"panels": panels, "decision_effect": "NONE"}


def build_opportunity_view(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build a display-only current/previous/baseline view from supplied evidence."""
    config = dict(config or {})
    current = _coerce_period(config.get("current"))
    previous = _coerce_period(config.get("previous"))
    baseline = _coerce_period(config.get("rolling_baseline"))
    market_value = build_market_value_evidence(config.get("market_value"))
    what_changed = build_what_changed(current, previous, baseline)
    classification = classify_opportunity_trend(current, previous, baseline)
    market_signal = classify_market_signal(classification, what_changed, market_value)
    candidate = dict(config.get("candidate") or {})
    return {
        "current": current,
        "what_changed": what_changed,
        "classification": classification,
        "market_value": market_value,
        "market_signal": market_signal,
        "trade_opportunity": classify_trade_opportunity(classification, market_value, market_signal, candidate),
        "decision_effect": "NONE",
    }


def _state(value: Any, allowed: set[str]) -> str:
    normalized = str(value or "UNAVAILABLE").upper()
    return normalized if normalized in allowed else "UNAVAILABLE"


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 1 else None


def _nonnegative(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _share(value: Any) -> float | None:
    return _number(value)


def _coerce_period(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value or "values" not in value:
        return build_opportunity_evidence(None)
    return build_opportunity_evidence(
        value.get("values"), source=value.get("source"),
        source_recorded_at=value.get("source_recorded_at"), retrieved_at=value.get("retrieved_at"),
        age=value.get("age"), freshness_state=value.get("freshness_state", "UNAVAILABLE"),
        completeness_state=value.get("completeness_state", "COMPLETE"), blocker=value.get("blocker"),
        recommendation_impact=value.get("recommendation_impact"),
    )
