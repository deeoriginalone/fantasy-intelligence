"""Fail-closed context contract for identifying an existing decision."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

SCHEMA_VERSION = "unified-decision-context.v1"
DECISION_EFFECT = "NONE"
CONTEXT_STATES = {"AVAILABLE", "UNAVAILABLE", "BLOCKED", "STALE", "INSUFFICIENT_EVIDENCE"}
FRESHNESS_STATES = {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}
COMPLETENESS_STATES = {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}
REQUIRED_FIELDS = (
    "season",
    "week",
    "decision_type",
    "decision_subject",
    "decision_output",
)


def build_unified_decision_context(
    *,
    season: Any = None,
    week: Any = None,
    decision_type: Any = None,
    decision_subject: Any = None,
    decision_subject_type: Any = None,
    stable_identity: Any = None,
    decision_output: Any = None,
    source: Any = None,
    source_recorded_at: Any = None,
    retrieved_at: Any = None,
    freshness_state: str = "UNAVAILABLE",
    completeness_state: str = "UNAVAILABLE",
    blockers: Any = None,
    lineage: Any = None,
) -> dict[str, Any]:
    """Normalize supplied context without deriving any missing decision field."""
    normalized_freshness = _state(freshness_state, FRESHNESS_STATES, "FRESHNESS_STATE_UNSUPPORTED")
    normalized_completeness = _state(completeness_state, COMPLETENESS_STATES, "COMPLETENESS_STATE_UNSUPPORTED")
    normalized = {
        "season": _integer(season),
        "week": _integer(week),
        "decision_type": _text(decision_type),
        "decision_subject": deepcopy(decision_subject),
        "decision_subject_type": _text(decision_subject_type),
        "stable_identity": deepcopy(stable_identity),
        "decision_output": deepcopy(decision_output),
        "source": deepcopy(source),
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "freshness_state": normalized_freshness,
        "completeness_state": normalized_completeness,
        "blockers": _blockers(blockers),
        "lineage": deepcopy(lineage),
        "schema_version": SCHEMA_VERSION,
        "decision_effect": DECISION_EFFECT,
    }

    missing = _missing_fields(normalized)
    if missing:
        normalized["blockers"].extend(f"MISSING_{field.upper()}" for field in missing)
    if normalized_freshness == "BLOCKED":
        normalized["blockers"].append("FRESHNESS_BLOCKED")
    elif normalized_freshness == "STALE":
        normalized["blockers"].append("FRESHNESS_STALE")
    elif normalized_freshness == "UNAVAILABLE":
        normalized["blockers"].append("FRESHNESS_UNAVAILABLE")
    if normalized_completeness != "COMPLETE":
        normalized["blockers"].append(f"COMPLETENESS_{normalized_completeness}")
    normalized["blockers"] = list(dict.fromkeys(normalized["blockers"]))
    normalized["state"] = _context_state(normalized, missing)
    normalized["authoritative"] = False
    return normalized


def _missing_fields(context: Mapping[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = context.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def _context_state(context: Mapping[str, Any], missing: list[str]) -> str:
    if context["freshness_state"] == "STALE":
        return "STALE"
    if context["freshness_state"] in {"BLOCKED", "UNAVAILABLE"}:
        return "BLOCKED" if context["freshness_state"] == "BLOCKED" else "UNAVAILABLE"
    if missing or context["completeness_state"] in {"INCOMPLETE", "UNAVAILABLE"}:
        return "INSUFFICIENT_EVIDENCE"
    if context["blockers"]:
        return "BLOCKED"
    return "AVAILABLE"


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _state(value: Any, allowed: set[str], blocker: str) -> str:
    normalized = str(value or "UNAVAILABLE").upper()
    return normalized if normalized in allowed else "BLOCKED"


def _blockers(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item) for item in values if item is not None and str(item)]
