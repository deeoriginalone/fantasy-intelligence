"""Source-priority and freshness contract for schedule and bye evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from services.integrity.integrity_service import schedule_bye_freshness_limits


def _timestamp(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        value = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def evidence_contract(domain, *, source, source_recorded_at=None, retrieved_at=None, imported_at=None, max_age_seconds=None, now=None):
    if domain not in {"schedule", "bye"}:
        return {
            "domain": domain, "source": str(source or "UNVERIFIED"),
            "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at,
            "imported_at": imported_at, "age": None, "freshness_state": "BLOCKED",
            "completeness_state": "UNAVAILABLE", "freshness_threshold_id": None,
            "blocker": "UNSUPPORTED_EVIDENCE_DOMAIN", "fallback_used": None,
            "recommendation_impact": "The affected recommendation is blocked because its evidence domain is unsupported.",
            "authoritative": False, "source_tier": "UNVERIFIED",
        }
    threshold=schedule_bye_freshness_limits().get(domain,{})
    threshold_id=threshold.get("id")
    max_age_seconds=threshold.get("seconds") if max_age_seconds is None else max_age_seconds
    """Prefer automated data, disclose cache/CSV fallback, and fail closed without an approved threshold."""
    source = str(source or "UNVERIFIED")
    source_key = source.lower()
    if source_key.startswith("automated:"):
        tier, fallback_used = "AUTOMATED_SOURCE", None
    elif source_key.startswith("cache:"):
        tier, fallback_used = "VERIFIED_LOCAL_CACHE", "VERIFIED_LOCAL_CACHE"
    elif source_key.startswith("csv:"):
        tier, fallback_used = "CSV_BOOTSTRAP_OR_RECOVERY", "CSV_BOOTSTRAP_OR_RECOVERY"
    else:
        tier, fallback_used = "UNVERIFIED", None
    # Local import time is disclosure only; it cannot make an old CSV source fresh.
    source_time = _timestamp(source_recorded_at) or _timestamp(retrieved_at)
    if source_time is None:
        return {
            "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
            "retrieved_at": retrieved_at, "imported_at": imported_at, "age": None,
            "freshness_state": "UNAVAILABLE", "completeness_state": "INCOMPLETE", "freshness_threshold_id": threshold_id,
            "blocker": f"{domain.upper()}_SOURCE_TIMESTAMP_UNVERIFIED", "fallback_used": fallback_used,
            "recommendation_impact": f"{domain.title()} evidence is visible but cannot support the affected recommendation.",
            "authoritative": False, "source_tier": tier,
        }
    try:
        max_age_seconds = int(max_age_seconds)
    except (TypeError, ValueError):
        max_age_seconds = None
    if max_age_seconds is None or max_age_seconds <= 0:
        return {
            "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
            "retrieved_at": retrieved_at, "imported_at": imported_at, "age": None,
            "freshness_state": "UNAVAILABLE", "completeness_state": "COMPLETE",
            "freshness_threshold_id": threshold_id, "blocker": f"{domain.upper()}_FRESHNESS_THRESHOLD_UNVERIFIED", "fallback_used": fallback_used,
            "recommendation_impact": f"{domain.title()} evidence is present but cannot be used until its freshness threshold is approved.",
            "authoritative": False, "source_tier": tier,
        }
    evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
    age = max(0, int((evaluation_time - source_time).total_seconds()))
    if age <= int(max_age_seconds) * .8:
        state, blocker = "FRESH", None
    elif age <= int(max_age_seconds):
        state, blocker = "AGING", None
    else:
        state, blocker = "STALE", f"{domain.upper()}_DATA_STALE"
    return {
        "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at, "imported_at": imported_at, "age": age,
        "freshness_state": state, "completeness_state": "COMPLETE", "freshness_threshold_id": threshold_id, "blocker": blocker,
        "fallback_used": fallback_used,
        "recommendation_impact": f"{domain.title()} evidence supports the affected recommendation." if not blocker else f"{domain.title()} evidence is stale and cannot support the affected recommendation.",
        "authoritative": not bool(blocker), "source_tier": tier,
    }
