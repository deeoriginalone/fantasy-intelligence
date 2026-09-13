from collections import Counter
from datetime import date, datetime, timezone

SUPPORTED_HEALTH_STATES = ("HEALTHY", "QUESTIONABLE", "DOUBTFUL", "OUT", "IR")
SUPPORTED_FRESHNESS_STATES = ("FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED", "NOT_APPLICABLE")


def health_freshness_from_report_date(report_date, now=None):
    """Derive freshness from the authoritative injury report date only."""
    if report_date in (None, ""):
        return {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}
    if isinstance(report_date, datetime):
        verified = report_date.astimezone(timezone.utc) if report_date.tzinfo else report_date.replace(tzinfo=timezone.utc)
    elif isinstance(report_date, date):
        verified = datetime.combine(report_date, datetime.min.time(), tzinfo=timezone.utc)
    else:
        verified = datetime.fromisoformat(str(report_date).replace("Z", "+00:00"))
        verified = verified.astimezone(timezone.utc) if verified.tzinfo else verified.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    age = max(0, int((current - verified).total_seconds()))
    state = "FRESH" if age <= 86400 else "AGING" if age <= 172800 else "STALE"
    return {"freshness_state": state, "last_verified": verified.isoformat(), "age": age}


def normalize_health(value):
    value = str(value or "").upper().strip()
    mapping = {
        "HEALTHY": "HEALTHY",
        "ACTIVE": "HEALTHY",
        "HEALTHY / NOT LISTED": "HEALTHY",
        "NOT LISTED": "HEALTHY",
        "QUESTIONABLE": "QUESTIONABLE",
        "Q": "QUESTIONABLE",
        "DOUBTFUL": "DOUBTFUL",
        "D": "DOUBTFUL",
        "OUT": "OUT",
        "O": "OUT",
        "IR": "IR",
        "INJURED_RESERVE": "IR",
    }
    return mapping.get(value)


def player_health_contract(player, source="Sleeper", freshness_state="FRESH", blocker=None):
    if str((player or {}).get("position") or "").upper().replace("DST", "DEF") == "DEF":
        return {
            "state": "AVAILABLE",
            "source": "Not applicable",
            "freshness_state": "NOT_APPLICABLE",
            "blocker": None,
            "health_state": "NOT_APPLICABLE",
            "confidence": "HIGH",
            "recommendation_impact": "Team-defense availability is evaluated through the roster slot and matchup, not player injury status.",
        }
    freshness_state = str(freshness_state or "").upper().strip()
    if freshness_state not in SUPPORTED_FRESHNESS_STATES:
        return {
            "state": "UNKNOWN",
            "source": source,
            "freshness_state": freshness_state or "UNKNOWN",
            "blocker": "UNSUPPORTED_HEALTH_FRESHNESS_STATE",
            "health_state": None,
            "confidence": "LOW",
            "recommendation_impact": "Health evidence could not be interpreted, so availability-sensitive recommendations are not trusted.",
        }
    if blocker:
        return {
            "state": "BLOCKED",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": blocker,
            "health_state": None,
            "confidence": "LOW",
            "recommendation_impact": "Availability-sensitive recommendations are blocked.",
        }
    if freshness_state == "STALE":
        return {
            "state": "STALE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "HEALTH_EVIDENCE_STALE",
            "health_state": None,
            "confidence": "LOW",
            "recommendation_impact": "Health information may be outdated, so availability-sensitive recommendations are reduced in confidence.",
        }
    if freshness_state in {"UNAVAILABLE", "BLOCKED"}:
        state = freshness_state
        return {
            "state": state,
            "source": source,
            "freshness_state": freshness_state,
            "blocker": f"HEALTH_{freshness_state}",
            "health_state": None,
            "confidence": "LOW",
            "recommendation_impact": "Health evidence is not usable for availability-sensitive recommendations.",
        }
    status = normalize_health((player or {}).get("injury_status"))
    if not status:
        return {
            "state": "UNAVAILABLE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "PLAYER_HEALTH_UNAVAILABLE",
            "health_state": None,
            "confidence": "LOW",
            "recommendation_impact": "Health evidence is unavailable, so availability-sensitive recommendations are reduced in confidence.",
        }
    return {
        "state": "AVAILABLE",
        "source": source,
        "freshness_state": freshness_state,
        "blocker": None,
        "health_state": status,
        "confidence": "HIGH" if freshness_state == "FRESH" else "MEDIUM",
        "recommendation_impact": "Health evidence supports lineup and roster-risk review.",
    }


def _with_health_metadata(payload, last_verified=None, age=None):
    payload["last_verified"] = last_verified
    payload["age"] = age
    return payload


def team_health_contract(
    roster,
    source="Sleeper",
    freshness_state="FRESH",
    blocker=None,
    last_verified=None,
    age=None,
):
    freshness_state = str(freshness_state or "").upper().strip()
    empty_counts = {"healthy": None, "questionable": None, "doubtful": None, "out": None, "ir": None, "unknown": None}
    if freshness_state not in SUPPORTED_FRESHNESS_STATES:
        return _with_health_metadata({
            "state": "UNKNOWN",
            "source": source,
            "freshness_state": freshness_state or "UNKNOWN",
            "blocker": "UNSUPPORTED_HEALTH_FRESHNESS_STATE",
            **empty_counts,
            "recommendation_impact": "Health evidence could not be interpreted, so availability-sensitive recommendations are not trusted.",
        }, last_verified, age)
    if blocker or freshness_state == "BLOCKED":
        return _with_health_metadata({
            "state": "BLOCKED",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": blocker or "HEALTH_BLOCKED",
            **empty_counts,
            "recommendation_impact": "Health-dependent recommendations are blocked.",
        }, last_verified, age)
    if freshness_state == "UNAVAILABLE":
        return _with_health_metadata({
            "state": "UNAVAILABLE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "TEAM_HEALTH_UNAVAILABLE",
            **empty_counts,
            "recommendation_impact": "Health confidence is reduced because team health evidence is unavailable.",
        }, last_verified, age)
    if freshness_state == "STALE":
        return _with_health_metadata({
            "state": "STALE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "TEAM_HEALTH_STALE",
            **empty_counts,
            "recommendation_impact": "Health information may be outdated, so availability-sensitive recommendations are reduced in confidence.",
        }, last_verified, age)
    counts = Counter()
    for player in roster or []:
        if str((player or {}).get("position") or "").upper().replace("DST", "DEF") == "DEF":
            continue
        status = normalize_health((player or {}).get("injury_status"))
        counts[status or "UNKNOWN"] += 1
    return _with_health_metadata({
        "state": "AVAILABLE",
        "source": source,
        "freshness_state": freshness_state,
        "blocker": None,
        "healthy": counts["HEALTHY"],
        "questionable": counts["QUESTIONABLE"],
        "doubtful": counts["DOUBTFUL"],
        "out": counts["OUT"],
        "ir": counts["IR"],
        "unknown": counts["UNKNOWN"],
        "recommendation_impact": (
            "Availability risk is reflected in roster review."
            if last_verified is not None or age is not None
            else "Health status is available, but freshness timestamp evidence is unavailable; availability-sensitive recommendations are not trusted."
        ),
    }, last_verified, age)

def apply_player_health_to_recommendations(players, source="Sleeper", freshness_state="FRESH", blocker=None):
    """Apply health evidence only to the affected player recommendation."""
    for player in players or []:
        if player.get("vacant"):
            player.setdefault("decision", "BLOCKED")
            continue
        health = player_health_contract(player, source=source, freshness_state=freshness_state, blocker=blocker)
        player["health_evidence"] = health
        gaps = list(player.get("evidence_gaps") or [])
        if health.get("blocker"):
            gaps.append(health["blocker"])
        player["evidence_gaps"] = sorted(set(gaps))
        current = dict(player.get("confidence") or {})
        current_score = int(current.get("score") or 0)
        if health.get("state") == "AVAILABLE":
            player.setdefault("decision", "START")
            continue
        if health.get("state") == "BLOCKED":
            player["decision"] = "BLOCKED"
            player["confidence"] = {"label": "BLOCKED", "score": 0}
        else:
            player["decision"] = "MONITOR"
            player["confidence"] = {"label": "LOW", "score": min(current_score, 50) if current_score else 35}
        player["reason"] = health.get("recommendation_impact") or player.get("reason")
    return players
