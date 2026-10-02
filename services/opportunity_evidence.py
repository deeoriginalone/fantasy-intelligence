"""Fail-closed opportunity usage evidence and descriptive change facts."""
from __future__ import annotations

import math
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
USAGE_METRICS = (
    "offensive_snaps", "snap_share", "rush_attempts", "pass_attempts", "targets",
    "routes_run", "red_zone_touches", "goal_line_touches", "games_sample",
)
OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY = {
    "offensive_snaps": {
        "status": "SEPARATE_FOUNDATION_ONLY",
        "source": "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv",
        "artifact": "snap_counts_{season}.csv",
        "field": "offense_snaps",
        "semantics_unit": "player offensive snaps; integer count",
        "identity": "pfr_player_id resolved through the nflverse players.csv pfr_id -> gsis_id crosswalk; no name fallback",
        "season_week": "season and week fields in snap_counts",
        "timestamps": "source_recorded_at from snap_counts/timestamp.txt; retrieved_at supplied at retrieval",
        "position_coverage": "not present in snap_counts; position coverage is therefore unverified at this boundary",
        "null_zero": "missing blocks; verified zero is a value",
        "duplicates_completeness": "duplicate or contradictory player/team/week rows block; batch reconciliation is required",
        "attribution": "NFLverse data, licensed under CC BY 4.0.",
        "freshness_threshold": "snap_share.evidence.v1 only when explicitly verified; otherwise blocked",
        "conflict_rule": "ambiguous or contradictory pfr/GSIS identity blocks the row; no guessing",
        "recommendation_effect": "NONE; separate preliminary evidence only",
    },
    "snap_share": {
        "status": "SEPARATE_FOUNDATION_ONLY",
        "source": "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv",
        "artifact": "snap_counts_{season}.csv",
        "field": "offense_pct",
        "semantics_unit": "share of team offensive snaps; verified ratio from 0 to 1",
        "identity": "pfr_player_id resolved through the nflverse players.csv pfr_id -> gsis_id crosswalk; no name fallback",
        "season_week": "season and week fields in snap_counts",
        "timestamps": "source_recorded_at from snap_counts/timestamp.txt; retrieved_at supplied at retrieval",
        "position_coverage": "not present in snap_counts; position coverage is therefore unverified at this boundary",
        "null_zero": "missing or malformed blocks; verified zero is distinct from unavailable",
        "duplicates_completeness": "duplicate or contradictory player/team/week rows block; batch reconciliation is required",
        "attribution": "NFLverse data, licensed under CC BY 4.0.",
        "freshness_threshold": "snap_share.evidence.v1 only when explicitly verified; otherwise blocked",
        "conflict_rule": "ambiguous or contradictory pfr/GSIS identity blocks the row; no guessing",
        "recommendation_effect": "NONE; separate preliminary evidence only",
    },
}
for _metric in (
    "routes_run", "route_participation", "red_zone_carries", "red_zone_targets",
    "red_zone_touches", "carries_inside_5", "carries_inside_10", "goal_line_touches",
):
    OPPORTUNITY_TOUCH_SOURCE_FEASIBILITY[_metric] = {
        "status": "UNAVAILABLE",
        "source": None,
        "artifact": "stats_player_week_{season}.csv.gz and snap_counts_{season}.csv inspected",
        "field": None,
        "semantics_unit": "explicit source field not supplied",
        "identity": "no source record available to resolve for this metric",
        "season_week": "not supplied",
        "timestamps": "not supplied",
        "position_coverage": "not supplied",
        "null_zero": "unavailable; zero must not be inferred",
        "duplicates_completeness": "cannot be assessed without a source",
        "attribution": None,
        "freshness_threshold": "opportunity.evidence.v1 cannot be applied without source data",
        "conflict_rule": "fail closed; do not combine red-zone fields or infer route denominators",
        "recommendation_effect": "NONE",
    }
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
DURATION_VALUES = {"IMMEDIATE", "SHORT_TERM", "MULTI_WEEK", "ONGOING", "SPECULATIVE"}
OPPORTUNITY_SIGNAL_VALUES = {"PRIMARY_USAGE", "SECONDARY_USAGE", "EXPANDING_USAGE", "DECLINING_USAGE", "LIMITED_USAGE", "MIXED_USAGE", "UNAVAILABLE"}
CONTINUITY_VALUES = {"STABLE_MULTI_WEEK", "EXPANDING_MULTI_WEEK", "DECLINING_MULTI_WEEK", "MIXED_MULTI_WEEK", "INSUFFICIENT", "UNAVAILABLE"}


def build_watch_opportunity_explanation(signal: Mapping[str, Any] | None, continuity: Mapping[str, Any] | None) -> dict[str, Any]:
    """Translate preliminary opportunity evidence into manager-facing WATCH context."""
    signal, continuity = dict(signal or {}), dict(continuity or {})
    if signal.get("signal") == "EXPANDING_USAGE" or continuity.get("state") == "EXPANDING_MULTI_WEEK":
        text = "Opportunity expanding; monitor whether the trend continues."
    elif signal.get("signal") == "DECLINING_USAGE" or continuity.get("state") == "DECLINING_MULTI_WEEK":
        text = "Opportunity declining; monitor for further loss of usage."
    elif signal.get("signal") == "MIXED_USAGE" or continuity.get("state") == "MIXED_MULTI_WEEK":
        text = "Mixed opportunity signals; wait for clearer evidence."
    elif signal.get("signal") == "LIMITED_USAGE":
        text = "Limited opportunity evidence; await more observations."
    else:
        text = "Await more opportunity observations before treating usage as meaningful."
    return {"text": text, "evidence_level": signal.get("evidence_level") or continuity.get("evidence_level") or "UNAVAILABLE", "impact": "WATCH context only; recommendation authority is unchanged."}


def build_preliminary_opportunity_alert(signal: Mapping[str, Any] | None, continuity: Mapping[str, Any] | None) -> dict[str, Any]:
    """Create an informational alert without changing any decision authority."""
    signal, continuity = dict(signal or {}), dict(continuity or {})
    mapping = {
        "EXPANDING_USAGE": "Opportunity Rising",
        "EXPANDING_MULTI_WEEK": "Emerging Usage",
        "DECLINING_USAGE": "Opportunity Declining",
        "DECLINING_MULTI_WEEK": "Opportunity Declining",
        "MIXED_USAGE": "Mixed Signals",
        "MIXED_MULTI_WEEK": "Mixed Signals",
        "LIMITED_USAGE": "Observation Needed",
        "INSUFFICIENT": "Observation Needed",
    }
    key = signal.get("signal") if signal.get("signal") in mapping else continuity.get("state")
    alert = mapping.get(key)
    return {"alert": alert, "evidence_level": "PRELIMINARY" if alert else "UNAVAILABLE", "recommendation_impact": "Informational only; no recommendation, ranking, or transaction impact."}


def build_preliminary_opportunity_continuity(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Expose observed multi-week continuity separately from expected duration."""
    evidence = dict(evidence or {})
    observations = list(evidence.get("observations") or [])
    trends = list(evidence.get("trends") or [])
    base = {
        "state": "UNAVAILABLE", "observation_window": evidence.get("observation_window"),
        "sample_count": len(observations), "evidence_level": "UNAVAILABLE",
        "basis": "No supported multi-week continuity is available.",
        "limitations": ["Observed continuity is not expected opportunity duration."],
        "recommendation_impact": "Continuity is informational only.",
    }
    if len(observations) < 2:
        base["state"] = "INSUFFICIENT"
        base["limitations"].append("MULTI_WEEK_SAMPLE_REQUIRED")
        return base
    if str(evidence.get("freshness_state") or "UNAVAILABLE").upper() in {"STALE", "BLOCKED", "UNAVAILABLE"}:
        base["state"] = "INSUFFICIENT"
        base["limitations"].append("Evidence is not current.")
        return base
    differences = [float(item["difference"]) for item in trends if item.get("difference") is not None]
    if not differences:
        base["state"] = "INSUFFICIENT"
        return base
    positive, negative = any(value > 0 for value in differences), any(value < 0 for value in differences)
    base["state"] = "MIXED_MULTI_WEEK" if positive and negative else "EXPANDING_MULTI_WEEK" if positive else "DECLINING_MULTI_WEEK" if negative else "STABLE_MULTI_WEEK"
    base["evidence_level"] = "PRELIMINARY"
    base["basis"] = "Observed dated opportunity trends across multiple weeks; no future duration is inferred."
    base["recommendation_impact"] = "Continuity is preliminary context only; it does not authorize duration, ADD, or FAAB."
    return base


def build_preliminary_opportunity_signal(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Interpret published opportunity observations without creating role authority."""
    evidence = dict(evidence or {})
    observations = list(evidence.get("observations") or [])
    trends = list(evidence.get("trends") or [])
    freshness = str(evidence.get("freshness_state") or "UNAVAILABLE").upper()
    completeness = str(evidence.get("completeness_state") or "UNAVAILABLE").upper()
    base = {
        "signal": "UNAVAILABLE", "signal_basis": "No supported opportunity signal is available.",
        "observation_window": evidence.get("observation_window"), "sample_count": len(observations),
        "source": evidence.get("source") or "UNVERIFIED", "freshness": freshness,
        "completeness": completeness, "evidence_level": "UNAVAILABLE",
        "limitations": ["This is not an authoritative player role."],
        "recommendation_impact": "Opportunity signal is unavailable.",
    }
    if not observations:
        return base
    if freshness in {"STALE", "BLOCKED", "UNAVAILABLE"}:
        base["evidence_level"] = "INSUFFICIENT"
        base["limitations"].append("Evidence is not current.")
        base["recommendation_impact"] = "Stale or unavailable opportunity evidence cannot change the recommendation."
        return base
    if completeness != "COMPLETE":
        base["evidence_level"] = "INSUFFICIENT"
        base["limitations"].append("Required opportunity evidence is incomplete.")
        base["recommendation_impact"] = "Incomplete opportunity evidence may not authorize an action."
        return base
    differences = [float(item["difference"]) for item in trends if item.get("difference") is not None]
    if len(observations) < 2 or not differences:
        base["evidence_level"] = "INSUFFICIENT"
        base["limitations"].append("MULTI_WEEK_SAMPLE_REQUIRED")
        base["recommendation_impact"] = "One observation is context only; WATCH authority is unchanged."
        return base
    positive = any(value > 0 for value in differences)
    negative = any(value < 0 for value in differences)
    signal = "MIXED_USAGE" if positive and negative else "EXPANDING_USAGE" if positive else "DECLINING_USAGE" if negative else "LIMITED_USAGE"
    base.update(
        signal=signal,
        signal_basis="Per-metric dated opportunity changes; no composite score or role threshold is applied.",
        evidence_level="PRELIMINARY",
        recommendation_impact="Preliminary opportunity signal provides WATCH context only; it cannot create role, duration, ADD, drop, or FAAB authority.",
    )
    return base


def build_opportunity_duration_authority(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate an explicit forward-looking duration fact; history alone is insufficient."""
    evidence = dict(evidence or {})
    duration = evidence.get("opportunity_duration") or evidence.get("duration")
    required = (evidence.get("source"), evidence.get("retrieved_at"), evidence.get("freshness_state") == "FRESH", evidence.get("completeness_state") == "COMPLETE", evidence.get("observation_window"), evidence.get("sample_count"), evidence.get("duration_basis"))
    established = duration in DURATION_VALUES and all(required) and evidence.get("duration_authority") is True and not evidence.get("blocker")
    return {
        "state": "ESTABLISHED" if established else "UNAVAILABLE",
        "value": duration if established else None,
        "basis": evidence.get("duration_basis") or "An explicit forward-looking duration fact is required; historical continuity alone is insufficient.",
        "observation_window": evidence.get("observation_window"),
        "sample_count": evidence.get("sample_count"),
        "source": evidence.get("source") or "UNVERIFIED",
        "source_recorded_at": evidence.get("source_recorded_at"),
        "retrieved_at": evidence.get("retrieved_at"),
        "freshness": evidence.get("freshness_state") or "UNAVAILABLE",
        "completeness": evidence.get("completeness_state") or "UNAVAILABLE",
        "evidence_level": "ESTABLISHED" if established else "UNAVAILABLE",
        "limitations": [] if established else ["FORWARD_DURATION_AUTHORITY_UNAVAILABLE"],
        "recommendation_impact": "Established duration may satisfy the waiver duration gate." if established else "Observed history does not establish expected future duration.",
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
OPPORTUNITY_TREND_DIRECTIONS = {"UP", "DOWN", "FLAT", "UNAVAILABLE"}
ROLE_CLASSIFICATIONS = {"IMMEDIATE_STARTER", "FLEX_OPTION", "DEPTH_ADD", "SHORT_TERM_REPLACEMENT", "SPECULATIVE", "UNAVAILABLE"}
DURATION_CLASSIFICATIONS = {"SHORT_TERM", "MEDIUM_TERM", "SEASON_LONG", "UNAVAILABLE"}
WHAT_CHANGED_CATEGORIES = {
    "SNAP_SHARE", "TARGETS", "TOUCHES", "ROUTES", "RED_ZONE",
    "RECEPTIONS", "RECEIVING_YARDS", "RECEIVING_TDS", "RUSHING_YARDS", "RUSHING_TDS",
    "PASSING_YARDS", "PASSING_TDS",
}
PRODUCTION_EVIDENCE_FIELDS = (
    "passing_yards", "passing_tds", "passing_interceptions",
    "rushing_yards", "rushing_tds", "receptions", "receiving_yards", "receiving_tds",
)
OPPORTUNITY_CLASSIFICATIONS = OPPORTUNITY_SIGNAL_VALUES


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
    """Normalize supported target/carry/touch shares and disclose absent metrics."""
    values = dict(values or {})
    freshness = _state(freshness_state, FRESHNESS_STATES)
    completeness = _state(completeness_state, COMPLETENESS_STATES)
    supported = {
        "targets": _usage_number(values.get("targets")),
        "target_share": _number(values.get("target_share")),
        "carries": _usage_number(values.get("carries")),
        "carry_share": _number(values.get("carry_share")),
        "touch_share": _number(values.get("touch_share")),
        "rush_attempts": _usage_number(values.get("rush_attempts")),
        "pass_attempts": _usage_number(values.get("pass_attempts")),
        "games_sample": _usage_number(values.get("games_sample")),
    }
    supported.update({field: _production_number(values.get(field)) for field in PRODUCTION_EVIDENCE_FIELDS})
    unavailable = [name for name in ("snap_share", "route_participation", "red_zone_share", "role_classification")]
    authoritative = bool(source and retrieved_at and freshness in {"FRESH", "AGING"} and completeness == "COMPLETE" and not blocker and all(supported[name] is not None for name in ("target_share", "carry_share", "touch_share")))
    return {
        "player_id": player_id, "season": season, "week": week, **supported,
        "sample_start_week": week, "sample_end_week": week,
        "snap_share": None, "route_participation": None, "red_zone_share": None, "role_classification": None,
        "source": source or "UNVERIFIED", "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at,
        "freshness_state": freshness, "completeness_state": completeness, "blocker": blocker,
        "unavailable_metrics": unavailable, "unavailable_metric_blocker": "OPPORTUNITY_METRIC_SOURCE_UNAVAILABLE",
        "authoritative": authoritative, "recommendation_impact": "Preliminary opportunity evidence is informational only; it does not create role, duration, or recommendation authority.",
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
    result = {
        "state": "UNAVAILABLE",
        "current_week": dict(current or {}),
        "previous_week": dict(previous or {}),
        "rolling_baseline": dict(rolling_baseline or {}),
        "changes": [],
        "blockers": [],
        "blocker": "OPPORTUNITY_COMPARISON_UNAVAILABLE",
        "recommendation_impact": "Evidence only; no recommendation or score changes are made.",
    }
    if published_weeks is not None:
        rows = sorted([dict(row) for row in published_weeks if row.get("player_id") == player_id and row.get("season") == season], key=lambda row: row.get("week", 0))
        if not rows:
            result["blocker"] = "OPPORTUNITY_COMPARISON_UNAVAILABLE"
            return result
        latest = next((row for row in reversed(rows) if requested_week is None or row.get("week") <= requested_week), rows[-1])
        prior = next((row for row in reversed(rows[:-1]) if row.get("week") < latest.get("week")), None)
        result["current_week"] = latest.get("week")
        result["previous_week"] = prior.get("week") if prior else None
        result["rolling_baseline"] = None
        if prior:
            for metric, label in (
                ("target_share", "Target Share"), ("carry_share", "Carry Share"), ("touch_share", "Touch Share"),
                ("receptions", "Receptions"), ("receiving_yards", "Receiving Yards"),
                ("receiving_tds", "Receiving TDs"), ("rushing_yards", "Rushing Yards"),
                ("rushing_tds", "Rushing TDs"), ("passing_yards", "Passing Yards"),
                ("passing_tds", "Passing TDs"),
            ):
                earlier, later = prior.get(metric), latest.get(metric)
                if earlier is None or later is None:
                    continue
                result["changes"].append({"metric": metric, "label": label, "direction": "UP" if later > earlier else "DOWN" if later < earlier else "UNCHANGED", "delta": round(later - earlier, 4), "current": later, "previous": earlier, "baseline": None})
            result["state"] = "AVAILABLE" if result["changes"] else "UNAVAILABLE"
            result["blocker"] = None if result["changes"] else "OPPORTUNITY_VALUES_UNAVAILABLE"
        else:
            result["blocker"] = "MULTI_WEEK_SAMPLE_REQUIRED"
        return result
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
        "receptions": "Receptions", "receiving_yards": "Receiving Yards", "receiving_tds": "Receiving TDs",
        "rushing_yards": "Rushing Yards", "rushing_tds": "Rushing TDs",
        "passing_yards": "Passing Yards", "passing_tds": "Passing TDs",
    }
    for metric, label in labels.items():
        if any(period.get(metric) is None for period in (current, previous, rolling_baseline)):
            continue
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


def _foundation_metadata(record: Mapping[str, Any] | None, *, blockers: list[str] | None = None) -> dict[str, Any]:
    record = dict(record or {})
    source_record_time = record.get("source_record_time") or record.get("source_recorded_at")
    freshness = _state(record.get("freshness_state"), FRESHNESS_STATES)
    completeness = _state(record.get("completeness_state"), COMPLETENESS_STATES)
    all_blockers = list(dict.fromkeys([*(record.get("blockers") or []), *(blockers or [])]))
    if not record.get("source") or not source_record_time or not record.get("retrieved_at"):
        all_blockers.append("OPPORTUNITY_SOURCE_METADATA_UNAVAILABLE")
    if freshness not in {"FRESH", "AGING"}:
        all_blockers.append("OPPORTUNITY_EVIDENCE_NOT_CURRENT")
    if completeness != "COMPLETE":
        all_blockers.append("OPPORTUNITY_EVIDENCE_INCOMPLETE")
    return {
        "source": record.get("source") or "UNVERIFIED",
        "source_record_time": source_record_time,
        "source_recorded_at": source_record_time,
        "retrieved_at": record.get("retrieved_at"),
        "age": record.get("age"),
        "freshness_state": freshness,
        "completeness_state": completeness,
        "evidence_level": record.get("evidence_level") or ("ESTABLISHED" if not all_blockers else "UNAVAILABLE"),
        "blockers": list(dict.fromkeys(all_blockers)),
        "recommendation_impact": record.get("recommendation_impact") or "Informational evidence only; recommendation authority is unchanged.",
    }


def build_opportunity_evidence_contract(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Normalize explicit opportunity facts without deriving missing usage."""
    data = {**dict(record or {}), **overrides}
    required_values = ("offensive_snaps", "snap_share", "rush_attempts", "targets", "routes_run", "red_zone_touches", "goal_line_touches", "games_sample")
    blockers = []
    if data.get("player_id") in (None, ""):
        blockers.append("OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE")
    position = str(data.get("position") or "").upper().replace("DST", "DEF")
    position_required = {
        "QB": ("pass_attempts", "rush_attempts"),
        "RB": ("rush_attempts", "targets"),
        "WR": ("targets",),
        "TE": ("targets",),
    }
    required = position_required.get(position, required_values)
    if any(data.get(field) is None for field in required) or data.get("games_sample") is None:
        blockers.append("OPPORTUNITY_VALUES_UNAVAILABLE")
    unavailable_metrics = [
        metric for metric in ("offensive_snaps", "snap_share", "routes_run", "red_zone_touches", "goal_line_touches")
        if data.get(metric) is None
    ]
    metadata = _foundation_metadata(data, blockers=blockers)
    available = bool(data.get("available")) and not metadata["blockers"]
    return {
        "player_id": data.get("player_id"), "player_name": data.get("player_name"), "position": data.get("position"),
        "available": available, "offensive_snaps": data.get("offensive_snaps"), "snap_share": data.get("snap_share"),
        "rush_attempts": data.get("rush_attempts"), "pass_attempts": data.get("pass_attempts"), "targets": data.get("targets"), "routes_run": data.get("routes_run"),
        "red_zone_touches": data.get("red_zone_touches"), "goal_line_touches": data.get("goal_line_touches"),
        "games_sample": data.get("games_sample"), "sample_start_week": data.get("sample_start_week"),
        "sample_end_week": data.get("sample_end_week"),
        **{field: data.get(field) for field in PRODUCTION_EVIDENCE_FIELDS},
        "unavailable_metrics": list(dict.fromkeys([*unavailable_metrics, *(data.get("unavailable_metrics") or [])])),
        "blockers": metadata["blockers"], **metadata,
    }


def build_opportunity_trend(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Describe explicit usage deltas; missing samples remain unavailable."""
    data = {**dict(record or {}), **overrides}
    blockers = []
    sample_size = data.get("sample_size")
    changes = {key: data.get(key) for key in ("snap_share_change", "touch_change", "target_change", "route_change", "red_zone_change")}
    if data.get("player_id") in (None, ""):
        blockers.append("OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE")
    if not isinstance(sample_size, int) or sample_size < 2:
        blockers.append("OPPORTUNITY_TREND_SAMPLE_UNAVAILABLE")
    required_changes = {key: value for key, value in changes.items() if key != "route_change"}
    if any(value is None for value in required_changes.values()):
        blockers.append("OPPORTUNITY_TREND_VALUES_UNAVAILABLE")
    direction = "UNAVAILABLE"
    if not blockers:
        numeric = [float(value) for value in required_changes.values()]
        direction = "UP" if all(value >= 0 for value in numeric) and any(value > 0 for value in numeric) else "DOWN" if all(value <= 0 for value in numeric) and any(value < 0 for value in numeric) else "FLAT" if all(value == 0 for value in numeric) else "UNAVAILABLE"
        if direction == "UNAVAILABLE":
            blockers.append("OPPORTUNITY_TREND_DIRECTION_MIXED")
    metadata = _foundation_metadata(data, blockers=blockers)
    return {"player_id": data.get("player_id"), **changes, "trend_direction": direction, "trend_strength": data.get("trend_strength") if direction != "UNAVAILABLE" else None, "sample_size": sample_size, **metadata}


def build_role_classification(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Derive an informational role only from verified usage observations."""
    data = {**dict(record or {}), **overrides}
    role = data.get("role") or data.get("role_classification")
    derived_role, derived_basis = _derive_usage_role(data) if not role else (None, None)
    role = role or derived_role
    blockers = [] if role in ROLE_CLASSIFICATIONS - {"UNAVAILABLE"} else ["ROLE_CLASSIFICATION_UNAVAILABLE"]
    metadata = _foundation_metadata(data, blockers=blockers)
    available = role in ROLE_CLASSIFICATIONS - {"UNAVAILABLE"} and not metadata["blockers"]
    return {"player_id": data.get("player_id"), "role": role if available else "UNAVAILABLE", "role_confidence": data.get("role_confidence") if available else None, "reasons": list(data.get("reasons") or []) + ([derived_basis] if available and derived_basis else []), "basis": derived_basis or data.get("role_basis"), **metadata}


def build_opportunity_duration(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Accept an explicit duration classification without projecting duration."""
    data = {**dict(record or {}), **overrides}
    duration = data.get("duration_classification") or data.get("duration")
    blockers = [] if duration in DURATION_CLASSIFICATIONS - {"UNAVAILABLE"} else ["OPPORTUNITY_DURATION_UNAVAILABLE"]
    metadata = _foundation_metadata(data, blockers=blockers)
    available = duration in DURATION_CLASSIFICATIONS - {"UNAVAILABLE"} and not metadata["blockers"]
    return {"player_id": data.get("player_id"), "duration_available": available, "duration_classification": duration if available else "UNAVAILABLE", "confidence": data.get("confidence") if available else None, "reasons": list(data.get("reasons") or []), **metadata}


def build_opportunity_classification(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Combine explicit role, trend, and duration facts without creating authority."""
    data = {**dict(record or {}), **overrides}
    role = data.get("role") if data.get("role") in ROLE_CLASSIFICATIONS - {"UNAVAILABLE"} else None
    trend = data.get("trend_direction") if data.get("trend_direction") in OPPORTUNITY_TREND_DIRECTIONS - {"UNAVAILABLE"} else None
    duration = data.get("duration") if data.get("duration") in DURATION_CLASSIFICATIONS - {"UNAVAILABLE"} else None
    blockers = []
    if not role: blockers.append("ROLE_CLASSIFICATION_UNAVAILABLE")
    if not trend: blockers.append("OPPORTUNITY_TREND_UNAVAILABLE")
    if not duration: blockers.append("OPPORTUNITY_DURATION_UNAVAILABLE")
    metadata = _foundation_metadata(data, blockers=blockers)
    available = not metadata["blockers"]
    return {"player_id": data.get("player_id"), "classification": data.get("classification") if available else "UNAVAILABLE", "role": role if available else "UNAVAILABLE", "trend_direction": trend if available else "UNAVAILABLE", "duration": duration if available else "UNAVAILABLE", "confidence": data.get("confidence") if available else None, "reasons": list(data.get("reasons") or []), **metadata}


def build_what_changed_contract(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Publish one explicit descriptive change with freshness provenance."""
    data = {**dict(record or {}), **overrides}
    category = data.get("category")
    old_value, new_value = data.get("old_value"), data.get("new_value")
    blockers = []
    if category not in WHAT_CHANGED_CATEGORIES: blockers.append("WHAT_CHANGED_CATEGORY_UNAVAILABLE")
    if old_value is None or new_value is None: blockers.append("WHAT_CHANGED_VALUES_UNAVAILABLE")
    change = data.get("change")
    if change is None and not blockers:
        try: change = new_value - old_value
        except TypeError: blockers.append("WHAT_CHANGED_VALUES_UNAVAILABLE")
    direction = "UNAVAILABLE" if blockers else "UP" if change > 0 else "DOWN" if change < 0 else "FLAT"
    metadata = _foundation_metadata(data, blockers=blockers)
    return {"player_id": data.get("player_id"), "category": category if not blockers else "UNAVAILABLE", "old_value": old_value, "new_value": new_value, "change": change, "direction": direction, **metadata}


def build_opportunity_foundation(record: Mapping[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    """Expose the evidence-only foundation without connecting it to decisions."""
    data = {**dict(record or {}), **overrides}
    provenance = {key: data.get(key) for key in ("player_id", "source", "source_record_time", "source_recorded_at", "retrieved_at", "age", "freshness_state", "completeness_state", "evidence_level", "recommendation_impact")}
    trend = build_opportunity_trend({**provenance, **(data.get("trend") or data)})
    role = build_role_classification({**provenance, **(data.get("role_evidence") or data)})
    duration = build_opportunity_duration({**provenance, **(data.get("duration_evidence") or data)})
    classification_input = data.get("classification_evidence") or data
    classification = build_opportunity_classification(
        classification_input,
        player_id=data.get("player_id"),
        source=data.get("source"),
        source_record_time=data.get("source_record_time") or data.get("source_recorded_at"),
        retrieved_at=data.get("retrieved_at"), age=data.get("age"),
        freshness_state=data.get("freshness_state"), completeness_state=data.get("completeness_state"),
    )
    changed = build_what_changed_contract({**provenance, **(data.get("what_changed") or data)})
    return {
        "evidence": build_opportunity_evidence_contract(data),
        "trend": trend,
        "role": role,
        "duration": duration,
        "classification": classification,
        "what_changed": changed,
        "decision_effect": "NONE",
    }


def build_preliminary_opportunity_comparison(foundation: Mapping[str, Any] | None = None, *, player_id=None, player_name=None, position=None) -> dict[str, Any]:
    """Summarize supported within-player usage evidence without ranking authority."""
    foundation = dict(foundation or {})
    evidence = dict(foundation.get("evidence") or {})
    trend = dict(foundation.get("trend") or {})
    changed = foundation.get("what_changed") or {}
    supported_metrics = [
        metric for metric in ("targets", "rush_attempts", "target_share", "carry_share", "touch_share", "pass_attempts", "fantasy_points_ppr", "games_sample", *PRODUCTION_EVIDENCE_FIELDS)
        if evidence.get(metric) is not None
    ]
    unavailable_metrics = [
        "routes_run", "route_participation", "red_zone_touches", "goal_line_touches", "offensive_snaps", "role", "duration"
    ]
    current_window = foundation.get("current_window") or evidence
    prior_window = foundation.get("prior_window")
    rolling_window = foundation.get("rolling_window") or foundation.get("rolling_4_week")
    has_evidence = bool(supported_metrics)
    status = "PRELIMINARY" if has_evidence else "UNAVAILABLE"
    evidence_level = "PRELIMINARY" if has_evidence else "INSUFFICIENT"
    trend_direction = trend.get("trend_direction") or "UNAVAILABLE"
    reasons = ["Supported current usage is informational context only."] if has_evidence else ["No supported opportunity values are available."]
    if trend_direction != "UNAVAILABLE":
        reasons.append(f"Supported usage trend: {trend_direction}.")
    if changed and changed.get("direction") not in (None, "UNAVAILABLE"):
        reasons.append(f"{changed.get('category', 'Usage')} changed {changed.get('direction').lower()} across the supported comparison window.")
    return {
        "player_id": player_id or evidence.get("player_id"), "player_name": player_name or evidence.get("player_name"), "position": position or evidence.get("position"),
        "status": status, "evidence_level": evidence_level, "comparison_scope": "WITHIN_POSITION_USAGE",
        "current_window": current_window, "prior_window": prior_window, "rolling_window": rolling_window,
        "supported_metrics": supported_metrics, "unavailable_metrics": unavailable_metrics,
        "trend_direction": trend_direction, "trend_reasons": reasons, "what_changed": changed,
        "limitations": ["Routes, scoring-area usage, authoritative role, and duration remain unavailable unless explicitly supplied."],
        "blockers": list(dict.fromkeys(evidence.get("blockers") or [])),
        "source": evidence.get("source") or "UNVERIFIED", "source_record_time": evidence.get("source_record_time"), "retrieved_at": evidence.get("retrieved_at"), "age": evidence.get("age"),
        "freshness_state": evidence.get("freshness_state", "UNAVAILABLE"), "completeness_state": evidence.get("completeness_state", "UNAVAILABLE"),
        "recommendation_impact": "Informational context only; waiver priority is unchanged.", "decision_effect": "NONE",
    }


PLAYER_COMPARISON_FIELDS = {
    "RB": {"usage": ("carries", "carry_share", "touch_share"), "production": ("rushing_yards", "rushing_tds", "receptions")},
    "WR": {"usage": ("targets", "target_share"), "production": ("receptions", "receiving_yards", "receiving_tds")},
    "TE": {"usage": ("targets", "target_share"), "production": ("receptions", "receiving_yards", "receiving_tds")},
    "QB": {"usage": ("pass_attempts",), "production": ("passing_yards", "passing_tds", "passing_interceptions")},
}
PLAYER_COMPARISON_SHARE_FIELDS = {"target_share", "carry_share", "touch_share"}
PLAYER_COMPARISON_MISSING_EVIDENCE = ("routes", "red_zone usage", "goal_line usage", "duration")
PLAYER_COMPARISON_LABELS = {
    "carries": "Carries", "targets": "Targets", "pass_attempts": "Pass Attempts",
    "carry_share": "Carry Share", "target_share": "Target Share", "touch_share": "Touch Share",
    "rushing_yards": "Rushing Yards", "rushing_tds": "Rushing TDs", "receptions": "Receptions",
    "receiving_yards": "Receiving Yards", "receiving_tds": "Receiving TDs",
    "passing_yards": "Passing Yards", "passing_tds": "Passing TDs", "passing_interceptions": "Interceptions",
}


def _comparison_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _comparison_display(field: str, value: float | None) -> str:
    if value is None:
        return "UNAVAILABLE"
    if field in PLAYER_COMPARISON_SHARE_FIELDS:
        return f"{round(value * 100)}%"
    return str(int(value)) if float(value).is_integer() else str(round(value, 1))


def build_waiver_player_comparison(reader: Mapping[str, Any] | None, *, position: Any) -> dict[str, Any]:
    """Expose published per-player usage and production as context only; never ranks or sorts."""
    normalized = str(position or "").upper().replace("DST", "DEF")
    base = {
        "status": "UNAVAILABLE", "position": normalized, "usage": {}, "production": {},
        "current_window": None, "prior_window": None, "rolling_window": None,
        "what_changed": {"state": "INSUFFICIENT_EVIDENCE", "changes": []},
        "sample": {"weeks": 0, "first_week": None, "last_week": None},
        "freshness": {"state": "UNAVAILABLE", "source": None, "retrieved_at": None},
        "limitations": list(PLAYER_COMPARISON_MISSING_EVIDENCE), "summary": [], "blockers": [],
        "decision_effect": "NONE",
    }
    fields = PLAYER_COMPARISON_FIELDS.get(normalized)
    if fields is None:
        base["status"] = "NOT_APPLICABLE" if normalized in {"K", "DEF"} else "UNAVAILABLE"
        base["blockers"] = ["PLAYER_COMPARISON_POSITION_UNSUPPORTED"]
        return base
    reader = dict(reader or {})
    rows = sorted((dict(row) for row in reader.get("rows") or [] if isinstance(row, Mapping)), key=lambda row: row.get("week") or 0)
    if reader.get("state") != "AVAILABLE" or not rows:
        base["status"] = "BLOCKED" if reader.get("state") == "BLOCKED" else "UNAVAILABLE"
        base["blockers"] = list(reader.get("blockers") or ["PLAYER_COMPARISON_EVIDENCE_UNAVAILABLE"])
        if rows:
            base["freshness"] = {"state": rows[-1].get("freshness_state") or "UNAVAILABLE", "source": rows[-1].get("source"), "retrieved_at": rows[-1].get("retrieved_at")}
        return base
    tracked = (*fields["usage"], *fields["production"])
    counting = [field for field in tracked if field not in PLAYER_COMPARISON_SHARE_FIELDS]

    def window(row):
        return {"week": row.get("week"), **{field: _comparison_number(row.get(field)) for field in tracked}}

    current, prior, rolling_rows = rows[-1], (rows[-2] if len(rows) >= 2 else None), rows[-4:]
    rolling_totals = {}
    for field in counting:
        values = [_comparison_number(row.get(field)) for row in rolling_rows]
        rolling_totals[field] = None if any(value is None for value in values) else sum(values)
    sample_totals = {}
    for field in counting:
        values = [_comparison_number(row.get(field)) for row in rows]
        sample_totals[field] = None if any(value is None for value in values) else sum(values)
    changes = []
    if prior is not None:
        for field in tracked:
            now_value, prior_value = _comparison_number(current.get(field)), _comparison_number(prior.get(field))
            if now_value is None or prior_value is None:
                continue
            delta = round(now_value - prior_value, 4)
            shown = f"{'+' if delta >= 0 else ''}{round(delta * 100)} pts" if field in PLAYER_COMPARISON_SHARE_FIELDS else f"{'+' if delta >= 0 else ''}{_comparison_display(field, delta)}"
            changes.append({"field": field, "label": PLAYER_COMPARISON_LABELS[field], "prior_week": prior.get("week"), "current_week": current.get("week"), "delta": delta, "display": shown})
    first_week, last_week = rows[0].get("week"), current.get("week")
    span = f"Wk {last_week}" if first_week == last_week else f"Wks {first_week}-{last_week}"

    def summary_value(field):
        if field in PLAYER_COMPARISON_SHARE_FIELDS:
            return f"{PLAYER_COMPARISON_LABELS[field]} (Wk {last_week}): {_comparison_display(field, _comparison_number(current.get(field)))}"
        return f"{PLAYER_COMPARISON_LABELS[field]} ({span}): {_comparison_display(field, sample_totals[field])}"

    blockers = [f"PLAYER_COMPARISON_FIELD_UNAVAILABLE:{field}" for field in tracked if _comparison_number(current.get(field)) is None]
    base.update({
        "status": "PRELIMINARY",
        "usage": {field: _comparison_number(current.get(field)) for field in fields["usage"]},
        "production": {field: sample_totals.get(field) for field in fields["production"]},
        "current_window": window(current),
        "prior_window": window(prior) if prior is not None else None,
        "rolling_window": {"weeks": [row.get("week") for row in rolling_rows], "totals": rolling_totals},
        "what_changed": {"state": "AVAILABLE" if changes else "INSUFFICIENT_EVIDENCE", "changes": changes},
        "sample": {"weeks": len(rows), "first_week": first_week, "last_week": last_week},
        "freshness": {"state": current.get("freshness_state") or "UNAVAILABLE", "source": current.get("source"), "retrieved_at": current.get("retrieved_at")},
        "summary": [summary_value(field) for field in tracked],
        "blockers": blockers,
    })
    return base


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


def published_opportunity_row_blockers(row: Mapping[str, Any]) -> list[str]:
    """Validate persisted opportunity provenance without authorizing recommendations."""
    blockers = []
    if not row.get("source"):
        blockers.append("OPPORTUNITY_SOURCE_UNSUPPORTED")
    if row.get("source_authority") not in {"automated", "automated:nflverse"}:
        blockers.append("OPPORTUNITY_SOURCE_AUTHORITY_UNSUPPORTED")
    for field in ("source_recorded_at", "retrieved_at", "artifact_id", "version", "checksum", "freshness_threshold_id"):
        if not row.get(field):
            blockers.append(f"OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:{field}")
    if row.get("freshness_state") not in {"FRESH", "AGING"}:
        blockers.append("OPPORTUNITY_EVIDENCE_NOT_CURRENT")
    if row.get("completeness_state") != "COMPLETE":
        blockers.append("OPPORTUNITY_INCOMPLETE")
    if row.get("publication_state") != "PUBLISHED":
        blockers.append("OPPORTUNITY_PUBLICATION_STATE_INVALID")
    lineage = row.get("lineage") or {}
    if isinstance(lineage, Mapping) and lineage.get("reconciliation", {}).get("reconciled") is False:
        blockers.append("OPPORTUNITY_RECONCILIATION_UNVERIFIED")
    return list(dict.fromkeys(blockers))


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


def _production_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _derive_usage_role(data: Mapping[str, Any]) -> tuple[str | None, str | None]:
    position = str(data.get("position") or "").upper().replace("DST", "DEF")
    if position not in {"QB", "RB", "WR", "TE"} or data.get("games_sample") is None:
        return None, None
    if position == "QB":
        usage = (data.get("pass_attempts") or 0) + (data.get("rush_attempts") or 0)
    elif position == "RB":
        usage = (data.get("rush_attempts") or 0) + (data.get("targets") or 0)
    else:
        usage = data.get("targets")
    if usage is None or float(usage) <= 0:
        return None, None
    snap_share = data.get("snap_share")
    routes = data.get("routes_run")
    if snap_share is not None and float(snap_share) >= 0.75:
        return "IMMEDIATE_STARTER", "High verified offensive snap share with position-appropriate usage."
    if snap_share is not None and float(snap_share) >= 0.50:
        return "FLEX_OPTION", "Verified offensive snap share and position-appropriate usage support a flexible role."
    if routes is not None and float(routes) > 0:
        return "DEPTH_ADD", "Verified routes and position-appropriate usage support a depth role."
    return "DEPTH_ADD", "Verified position-appropriate usage supports a depth role."


def _usage_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


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
