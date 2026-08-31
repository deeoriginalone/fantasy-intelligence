from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


VALID_STATES = {"READY", "APPROXIMATE", "INCOMPLETE", "STALE", "BLOCKED"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _freshness_seconds(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, str):
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (_utc_now() - ts).total_seconds()


def evaluate_readiness(
    *,
    required_inputs: Optional[Dict[str, Any]] = None,
    optional_inputs: Optional[Dict[str, Any]] = None,
    timestamps: Optional[Dict[str, Any]] = None,
    freshness_thresholds: Optional[Dict[str, float]] = None,
    blockers: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    required_inputs = required_inputs or {}
    optional_inputs = optional_inputs or {}
    timestamps = timestamps or {}
    freshness_thresholds = freshness_thresholds or {}
    blockers = list(blockers or [])

    reasons: List[str] = []

    for name, value in required_inputs.items():
        if _is_missing(value):
            reasons.append(f"missing required input: {name}")

    for name, value in optional_inputs.items():
        if _is_missing(value):
            reasons.append(f"missing optional input: {name}")

    for name, value in timestamps.items():
        threshold = freshness_thresholds.get(name)
        if threshold is None:
            continue
        age = _freshness_seconds(value)
        if age is None:
            reasons.append(f"stale timestamp for {name}: unparseable")
            continue
        if age > threshold:
            reasons.append(f"stale input: {name} exceeds {threshold}s")

    for blocker in blockers:
        if blocker:
            reasons.append(f"blocker: {blocker}")

    if any(reason.startswith("blocker:") for reason in reasons):
        return {"readiness_status": "BLOCKED", "reasons": reasons}

    if any(reason.startswith("stale input:") for reason in reasons) or any(reason.startswith("stale timestamp") for reason in reasons):
        return {"readiness_status": "STALE", "reasons": reasons}

    if any(reason.startswith("missing required input:") for reason in reasons):
        return {"readiness_status": "INCOMPLETE", "reasons": reasons}

    if any(reason.startswith("missing optional input:") for reason in reasons):
        return {"readiness_status": "APPROXIMATE", "reasons": reasons}

    if not reasons:
        return {"readiness_status": "READY", "reasons": []}

    return {"readiness_status": "APPROXIMATE", "reasons": reasons}
