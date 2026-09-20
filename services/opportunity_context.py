"""Pure, informational opportunity-strength and usage-stability context."""
from __future__ import annotations
from typing import Any, Mapping, Sequence

STRENGTH_STATES = ("HIGH_OPPORTUNITY", "MODERATE_OPPORTUNITY", "LIMITED_OPPORTUNITY", "UNAVAILABLE")
STABILITY_STATES = ("STABLE", "INCREASING", "DECREASING", "INSUFFICIENT_EVIDENCE")
STRENGTH_HIGH_THRESHOLD = 0.75
STRENGTH_MODERATE_THRESHOLD = 0.50
STABILITY_DELTA_THRESHOLD = 0.05


def _available(value: Any) -> bool:
    return value is not None


def opportunity_strength(*, usage_row: Mapping[str, Any] | None, snap_row: Mapping[str, Any] | None) -> dict[str, Any]:
    usage = dict(usage_row or {})
    snap = dict(snap_row or {})
    values = {
        "snap_share": snap.get("snap_share"),
        "target_share": usage.get("target_share"),
        "carry_share": usage.get("carry_share"),
        "touch_share": usage.get("touch_share"),
    }
    available = [float(value) for value in values.values() if _available(value)]
    if not available:
        return {"state": "UNAVAILABLE", "inputs": values, "reason": "Opportunity strength unavailable because no published usage metrics exist."}
    score = sum(available) / len(available)
    state = "HIGH_OPPORTUNITY" if score >= STRENGTH_HIGH_THRESHOLD else "MODERATE_OPPORTUNITY" if score >= STRENGTH_MODERATE_THRESHOLD else "LIMITED_OPPORTUNITY"
    return {"state": state, "inputs": values, "mean_available_share": score, "reason": "Informational summary of published usage shares; it does not describe player quality or change recommendations."}


def usage_stability(*, current_usage: Mapping[str, Any] | None, prior_usage: Mapping[str, Any] | None, current_snap: Mapping[str, Any] | None, prior_snap: Mapping[str, Any] | None) -> dict[str, Any]:
    current = {"target_share": (current_usage or {}).get("target_share"), "carry_share": (current_usage or {}).get("carry_share"), "touch_share": (current_usage or {}).get("touch_share"), "snap_share": (current_snap or {}).get("snap_share")}
    prior = {"target_share": (prior_usage or {}).get("target_share"), "carry_share": (prior_usage or {}).get("carry_share"), "touch_share": (prior_usage or {}).get("touch_share"), "snap_share": (prior_snap or {}).get("snap_share")}
    pairs = {key: (current[key], prior[key]) for key in current if _available(current[key]) and _available(prior[key])}
    if not pairs:
        return {"state": "INSUFFICIENT_EVIDENCE", "current": current, "prior": prior, "reason": "Usage stability unavailable because current and prior published comparisons are incomplete."}
    deltas = [float(now) - float(before) for now, before in pairs.values()]
    mean_delta = sum(deltas) / len(deltas)
    state = "INCREASING" if mean_delta > STABILITY_DELTA_THRESHOLD else "DECREASING" if mean_delta < -STABILITY_DELTA_THRESHOLD else "STABLE"
    return {"state": state, "current": current, "prior": prior, "mean_delta": mean_delta, "compared_metrics": sorted(pairs), "reason": "Informational comparison of published current and prior usage evidence; it does not infer future performance."}


def opportunity_trend(*, strength: Mapping[str, Any] | None, stability: Mapping[str, Any] | None) -> dict[str, Any]:
    """Summarize published opportunity movement without predicting performance."""
    stability = dict(stability or {})
    strength = dict(strength or {})
    if stability.get("state") == "INSUFFICIENT_EVIDENCE":
        return {"state": "INSUFFICIENT_EVIDENCE", "drivers": [], "evidence": {"strength": strength.get("inputs", {}), "stability": stability}, "reason": "Opportunity trend requires valid current and prior published comparisons."}
    current = stability.get("current") or {}
    prior = stability.get("prior") or {}
    deltas = {metric: float(current[metric]) - float(prior[metric]) for metric in stability.get("compared_metrics", []) if current.get(metric) is not None and prior.get(metric) is not None}
    if not deltas:
        return {"state": "INSUFFICIENT_EVIDENCE", "drivers": [], "evidence": {"strength": strength.get("inputs", {}), "stability": stability}, "reason": "Opportunity trend requires valid current and prior published comparisons."}
    mean_delta = sum(deltas.values()) / len(deltas)
    state = "IMPROVING" if mean_delta > STABILITY_DELTA_THRESHOLD else "DECLINING" if mean_delta < -STABILITY_DELTA_THRESHOLD else "STABLE"
    labels = {"snap_share": "Snap Share", "target_share": "Target Share", "carry_share": "Carry Share", "touch_share": "Touch Share"}
    drivers = [f"{labels[metric]} {'+' if delta >= 0 else ''}{delta * 100:.1f}%" for metric, delta in deltas.items() if abs(delta) > 0]
    return {"state": state, "drivers": drivers, "deltas": deltas, "evidence": {"strength": strength.get("inputs", {}), "stability": stability}, "reason": "Published opportunity movement only; no future-performance or role inference is made."}
