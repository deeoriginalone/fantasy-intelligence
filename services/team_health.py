from collections import Counter

SUPPORTED_HEALTH_STATES = ("HEALTHY", "QUESTIONABLE", "DOUBTFUL", "OUT", "IR")
SUPPORTED_FRESHNESS_STATES = ("FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED")


def normalize_health(value):
    value = str(value or "").upper().strip()
    mapping = {
        "HEALTHY": "HEALTHY",
        "ACTIVE": "HEALTHY",
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


def team_health_contract(roster, source="Sleeper", freshness_state="FRESH", blocker=None):
    freshness_state = str(freshness_state or "").upper().strip()
    empty_counts = {"healthy": None, "questionable": None, "doubtful": None, "out": None, "ir": None, "unknown": None}
    if freshness_state not in SUPPORTED_FRESHNESS_STATES:
        return {
            "state": "UNKNOWN",
            "source": source,
            "freshness_state": freshness_state or "UNKNOWN",
            "blocker": "UNSUPPORTED_HEALTH_FRESHNESS_STATE",
            **empty_counts,
            "recommendation_impact": "Health evidence could not be interpreted, so availability-sensitive recommendations are not trusted.",
        }
    if blocker or freshness_state == "BLOCKED":
        return {
            "state": "BLOCKED",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": blocker or "HEALTH_BLOCKED",
            **empty_counts,
            "recommendation_impact": "Health-dependent recommendations are blocked.",
        }
    if freshness_state == "UNAVAILABLE":
        return {
            "state": "UNAVAILABLE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "TEAM_HEALTH_UNAVAILABLE",
            **empty_counts,
            "recommendation_impact": "Health confidence is reduced because team health evidence is unavailable.",
        }
    if freshness_state == "STALE":
        return {
            "state": "STALE",
            "source": source,
            "freshness_state": freshness_state,
            "blocker": "TEAM_HEALTH_STALE",
            **empty_counts,
            "recommendation_impact": "Health information may be outdated, so availability-sensitive recommendations are reduced in confidence.",
        }
    counts = Counter()
    for player in roster or []:
        status = normalize_health((player or {}).get("injury_status"))
        counts[status or "UNKNOWN"] += 1
    return {
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
        "recommendation_impact": "Availability risk is reflected in roster review.",
    }
