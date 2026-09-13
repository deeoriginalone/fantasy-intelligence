from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.decision_ranking import build_action


def _confidence(row: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    value = (row or {}).get("confidence")
    return value if isinstance(value, Mapping) else None


def _health_action(starter: Mapping[str, Any]):
    player = starter.get("player") or "the affected player"
    health = starter.get("health_evidence") or {}
    blocked = starter.get("decision") == "BLOCKED"
    impact = f"Confirm {player}'s availability before lineup lock; this recommendation's confidence is reduced until health evidence is verified."
    action = f"Review {player}'s health evidence before lineup lock" if blocked else f"Monitor {player} before lineup lock"
    title = f"Review {player} health" if blocked else f"Monitor {player}"
    return build_action(
        action_id=f"team:health:{player}",
        category="lineup",
        title=title,
        action=action,
        reason=("Health verification is unavailable for this recommendation."
             if not blocked else "Health-dependent recommendation is blocked until refresh evidence is restored."),
        urgency="HIGH",
        confidence=_confidence(starter) or {"label": "LOW", "score": 0},
        evidence_complete=False,
        blockers=starter.get("evidence_gaps") or [health.get("blocker") or "PLAYER_HEALTH_UNAVAILABLE"],
        source="team_health",
        metadata={"expected_impact": impact, "affected_player": player, "slot": starter.get("slot")},
    ).to_dict()


def _vacancy_action(starter: Mapping[str, Any]):
    slot = starter.get("slot") or "starter slot"
    impact = f"Restore supported lineup coverage for the vacant {slot} slot."
    return build_action(
        action_id=f"team:vacancy:{slot}",
        category="lineup",
        title=f"Fill {slot}",
        action=f"Fill vacant {slot} starter slot",
        reason=starter.get("reason") or "No eligible roster player is available for this slot.",
        urgency="CRITICAL",
        confidence=starter.get("confidence") or {"label": "BLOCKED", "score": 0},
        risk_reduction=100,
        source="weekly_lineup_intelligence",
        metadata={"expected_impact": impact, "affected_slot": slot},
    ).to_dict()


def _needs_action(team_needs: Mapping[str, Any]):
    for position in ("QB", "RB", "WR", "TE", "FLEX", "K", "DEF"):
        item = dict(team_needs.get(position) or {})
        strategic_need = item.get("strategic_need")
        if strategic_need not in {"ADD_STARTER", "ADD_DEPTH"}:
            continue
        noun = "starter" if strategic_need == "ADD_STARTER" else "depth"
        impact = f"Improve supported {position} {noun} coverage; no point gain is available from the supplied evidence."
        return build_action(
            action_id=f"team:needs:{position}:{strategic_need}",
            category="waiver",
            title=f"Address {position} {noun}",
            action=f"Add {position} {noun}",
            reason=" ".join(item.get("drivers") or []) or f"Supported team-needs evidence identifies a {position} {noun} need.",
            urgency="HIGH" if strategic_need == "ADD_STARTER" else "MEDIUM",
            confidence={"label": "LOW", "score": 0},
            evidence_complete=item.get("state") == "AVAILABLE",
            blockers=[] if item.get("state") == "AVAILABLE" else [item.get("blocker") or "TEAM_NEEDS_UNAVAILABLE"],
            source="team_needs",
            metadata={"expected_impact": impact, "position": position, "strategic_need": strategic_need},
        ).to_dict()
    return None


def build_team_priority_action(
    starters: Sequence[Mapping[str, Any]] | None,
    team_needs: Mapping[str, Any] | None,
    team_health: Mapping[str, Any] | None,
    team_accuracy: Mapping[str, Any] | None,
):
    """Select one deterministic, read-only manager action from supplied evidence."""
    starters = list(starters or ())
    vacancies = [row for row in starters if row.get("vacant")]
    if vacancies:
        return _vacancy_action(vacancies[0])

    monitored = [row for row in starters if row.get("decision") in {"MONITOR", "BLOCKED"} and row.get("health_evidence")]
    if monitored:
        return _health_action(monitored[0])

    need_action = _needs_action(team_needs or {})
    if need_action:
        return need_action
    if (team_accuracy or {}).get("trusted"):
        return build_action(
            action_id="team:review:lineup",
            category="lineup",
            title="Review lineup before lock",
            action="Review lineup before lock",
            reason="No urgent evidence-supported change is required for the current roster.",
            urgency="LOW",
            confidence={"label": "HIGH", "score": 90},
            source="team_accuracy",
            metadata={"expected_impact": "Preserve the supported lineup while confirming final game status."},
        ).to_dict()

    blockers = list((team_accuracy or {}).get("blockers") or [])
    if (team_health or {}).get("state") != "AVAILABLE":
        blockers.append((team_health or {}).get("blocker") or "TEAM_HEALTH_UNAVAILABLE")
    blockers = sorted(set(blocker for blocker in blockers if blocker))
    return build_action(
        action_id="team:review:evidence",
        category="league",
        title="Review My Team evidence",
        action="Review available roster and league evidence before acting",
        reason=(team_accuracy or {}).get("recommendation_impact") or "No supported priority action is available.",
        urgency="MEDIUM",
        confidence={"label": "LOW", "score": 0},
        evidence_complete=False,
        blockers=blockers or ["TEAM_PRIORITY_ACTION_UNAVAILABLE"],
        source="team_accuracy",
        metadata={
            "expected_impact": "No supported fantasy impact is available until the listed evidence gaps are resolved.",
        },
    ).to_dict()
