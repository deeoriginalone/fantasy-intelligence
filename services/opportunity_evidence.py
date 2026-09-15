"""Fail-closed opportunity usage evidence and descriptive change facts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

METRICS = (
    "snap_share",
    "route_participation",
    "target_share",
    "rush_share",
    "red_zone_share",
    "goal_line_share",
    "role_stability",
)
TREND_METRICS = (
    "target_share",
    "snap_share",
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
FRESHNESS_STATES = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
COMPLETENESS_STATES = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}


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
) -> dict[str, Any]:
    """Describe metric movements without drawing player-level conclusions."""
    result = {
        "state": "UNAVAILABLE",
        "current_week": dict(current or {}),
        "previous_week": dict(previous or {}),
        "rolling_baseline": dict(rolling_baseline or {}),
        "changes": [],
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
    result["state"] = "AVAILABLE"
    result["blocker"] = None
    return result


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


def build_opportunity_view(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build a display-only current/previous/baseline view from supplied evidence."""
    config = dict(config or {})
    current = _coerce_period(config.get("current"))
    previous = _coerce_period(config.get("previous"))
    baseline = _coerce_period(config.get("rolling_baseline"))
    market_value = build_market_value_evidence(config.get("market_value"))
    what_changed = build_what_changed(current, previous, baseline)
    classification = classify_opportunity_trend(current, previous, baseline)
    return {
        "current": current,
        "what_changed": what_changed,
        "classification": classification,
        "market_value": market_value,
        "market_signal": classify_market_signal(classification, what_changed, market_value),
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
