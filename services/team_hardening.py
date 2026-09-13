from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.weekly_lineup_intelligence import eligible, slot_allows


def build_team_trust_summary(team_accuracy: Mapping[str, Any], team_health: Mapping[str, Any], starters: Sequence[Mapping[str, Any]], bench: Sequence[Mapping[str, Any]]):
    accuracy = dict(team_accuracy or {})
    health = dict(team_health or {})
    weekly_available = sum(player.get("weekly_score") is not None for player in [*starters, *bench])
    weekly_total = len([*starters, *bench])
    matchup = accuracy.get("matchups") or {}
    settings = accuracy.get("league_settings") or {}
    blockers = list(accuracy.get("blockers") or [])
    return {
        "roster": {"state": "AVAILABLE" if starters else "UNAVAILABLE", "label": "Verified roster supplied." if starters else "Roster evidence unavailable."},
        "league_settings": {"state": "AVAILABLE" if settings.get("state") == "AVAILABLE" else "UNAVAILABLE", "label": "Verified league settings." if settings.get("state") == "AVAILABLE" else "League settings unavailable."},
        "health": {"state": health.get("freshness_state") or "UNAVAILABLE", "label": ("Health verification is unavailable; availability-sensitive recommendations have reduced confidence." if health.get("state") == "UNAVAILABLE" else health.get("recommendation_impact") or "Health impact unavailable.")},
        "matchups": {"state": matchup.get("state") or "UNAVAILABLE", "label": "Starter matchup evidence is supported." if matchup.get("state") == "AVAILABLE" else "Matchup evidence is limited or unavailable."},
        "weekly_values": {"state": "AVAILABLE" if weekly_available == weekly_total and weekly_total else "PARTIAL" if weekly_available else "UNAVAILABLE", "label": f"{weekly_available} of {weekly_total} player values available."},
        "confidence": accuracy.get("confidence") or {"label": "LOW", "score": 0},
        "blockers": sorted(set(blockers)),
        "before_lock": "Confirm monitored player availability before lineup lock." if any(player.get("decision") == "MONITOR" for player in starters) else "Review the selected action before lineup lock.",
    }


def build_bench_decisions(starters: Sequence[Mapping[str, Any]], bench: Sequence[Mapping[str, Any]]):
    decisions = []
    assigned = set()
    for starter in starters:
        if starter.get("vacant") or starter.get("decision") not in {"MONITOR", "BLOCKED"}:
            continue
        alternatives = [player for player in bench if slot_allows(starter.get("slot"), player.get("position")) and eligible(player)]
        alternatives.sort(key=lambda player: (-float(player.get("weekly_score") or 0), str(player.get("player") or "")))
        if alternatives and alternatives[0].get("weekly_score") is not None:
            alternative = alternatives[0]
            repeated = alternative.get("player") in assigned
            assigned.add(alternative.get("player"))
            decisions.append({"kind": "CONTINGENCY", "player": alternative.get("player"), "slot": starter.get("slot"), "trigger": f"If {starter.get('player')} remains unavailable or monitored.", "reason": "Conditional alternative; not simultaneously available for multiple slots." if repeated else "Best eligible supplied bench alternative for this slot.", "state": "AVAILABLE"})
        else:
            decisions.append({"kind": "CONTINGENCY", "player": starter.get("player"), "slot": starter.get("slot"), "trigger": f"No supported alternative for {starter.get('slot')}.", "reason": "No supported alternative is available for this slot.", "state": "UNAVAILABLE"})
    return decisions


def build_weekly_risks(starters, team_needs, team_health, team_accuracy):
    risks = []
    monitored = [player for player in starters or [] if player.get("decision") in {"MONITOR", "BLOCKED"}]
    if monitored:
        names = [str(player.get("player")) for player in monitored]
        risks.append({"key": "health:players", "title": "Team health verification required", "reason": f"{len(names)} starter(s) are affected by shared or player-level health evidence.", "action": "Confirm current statuses before lineup lock.", "affected_players": names})
    for player in starters or []:
        if player.get("weekly_score") is None:
            risks.append({"key": f"weekly:{player.get('player')}", "title": f"Weekly value unavailable for {player.get('player')}", "reason": "Do not treat unavailable weekly evidence as zero.", "action": "Review supported weekly evidence."})
    for position in ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF"):
        item = dict((team_needs or {}).get(position) or {})
        if item.get("strategic_need") in {"ADD_STARTER", "ADD_DEPTH"}:
            risks.append({"key": f"need:{position}", "title": f"{position} depth is below target", "reason": " ".join(item.get("drivers") or []) or "Supported Team Needs evidence identifies a roster gap.", "action": f"Review {position} depth options."})
    if (team_health or {}).get("freshness_state") in {"STALE", "UNAVAILABLE", "BLOCKED", "UNKNOWN"} and not monitored:
        risks.append({"key": "health:team", "title": "Team health evidence needs review", "reason": (team_health or {}).get("recommendation_impact") or "Health evidence is limited.", "action": "Confirm current health evidence."})
    if (team_accuracy or {}).get("matchups", {}).get("state") != "AVAILABLE":
        risks.append({"key": "matchup:team", "title": "Matchup evidence is limited", "reason": "Authoritative matchup rank metadata is unavailable.", "action": "Use opponent context without treating rank as authoritative."})
    return sorted({risk["key"]: risk for risk in risks}.values(), key=lambda risk: risk["key"])


def build_roster_outlook(team_needs, team_health):
    needs = team_needs or {}
    depth = [item for item in needs.values() if item.get("strategic_need") in {"ADD_STARTER", "ADD_DEPTH"}]
    return {
        "starter_strength": {"state": "AVAILABLE" if needs else "UNAVAILABLE", "label": "Supported by starter coverage and active league slots." if needs else "Unavailable."},
        "depth": {"state": "REVIEW" if depth else "AVAILABLE", "label": f"{len(depth)} positional depth area(s) need review." if depth else "Supported depth targets are satisfied."},
        "risk": {"state": "REVIEW" if (team_health or {}).get("freshness_state") not in {"FRESH", "AGING"} else "AVAILABLE", "label": (team_health or {}).get("recommendation_impact") or "Risk evidence unavailable."},
        "playoff_readiness": {"state": "UNAVAILABLE", "label": "Playoff readiness evidence is not supplied by the active contract."},
    }


def build_lineup_snapshot(starters, bench_decisions):
    starters = list(starters or ())
    counts = {"ready": 0, "monitor": 0, "blocked": 0}
    attention = []
    for player in starters:
        decision = str(player.get("decision") or "START").upper()
        bucket = "blocked" if decision == "BLOCKED" else "monitor" if decision == "MONITOR" else "ready"
        counts[bucket] += 1
        if bucket != "ready":
            attention.append({"player": player.get("player"), "slot": player.get("slot"), "decision": decision})
    available = [item for item in (bench_decisions or []) if item.get("state") == "AVAILABLE"]
    return {
        "counts": counts,
        "attention": attention,
        "best_contingency": available[0] if available else None,
        "contingency_state": "AVAILABLE" if available else "UNAVAILABLE",
        "state": "BLOCKED" if counts["blocked"] else "REVIEW" if counts["monitor"] else "READY",
    }


def build_bench_plan(bench_decisions):
    available = [item for item in (bench_decisions or []) if item.get("state") == "AVAILABLE"]
    unavailable = [item.get("slot") for item in (bench_decisions or []) if item.get("state") != "AVAILABLE"]
    return {
        "best": available[:1],
        "additional": available[1:4],
        "unavailable_slots": unavailable,
    }
