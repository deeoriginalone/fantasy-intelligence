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
