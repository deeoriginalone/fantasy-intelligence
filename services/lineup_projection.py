"""Preliminary league-scored projections, the shadow Weekly Score v2, projection comparisons, evidence agreement, recent
workload facts, and forward-validation snapshots for My Team lineup decisions.

Everything here is informational. No function authorizes a lineup change, converts consensus
rank into points, treats a missing projection as zero, or lets provider availability override
Sleeper availability.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from decimal import Decimal
from typing import Any, Mapping, Sequence

from services.game_lock import utc_datetime
from services.league_scoring import SCHEMA_VERSION as LEAGUE_SCORING_CONTRACT_ID, SCORING_BASIS, league_score_stat_line
from services.pre_decision_snapshots import SnapshotValidationError, build_pre_decision_snapshot
from services.team_codes import canonical_team

PROJECTION_SOURCE = "JerryGM jgm_baseline stat line, rescored with Sleeper league scoring"
PROJECTION_UNIT = "fantasy_points"
COMPARISON_BASIS = "LEAGUE_SCORED_PROJECTION"
SNAPSHOT_DECISION_TYPE = "MY_TEAM_LINEUP_DECISION"
SNAPSHOT_OUTPUT_VERSION = "lineup.forward_validation.snapshot.v2"
WEEKLY_SCORE_CONTRACT_ID = "weekly-score.v2"
WEEKLY_SCORE_LABEL = "Weekly projection"
WEEKLY_SCORE_DEFINITION = ("Weekly Score v2: this week's projected fantasy points under the league's Sleeper scoring, taken as-is from the league-scored "
                           "provider projection; no season projection ÷ 17, matchup modifier, or health multiplier is applied.")
WEEKLY_SCORE_AUTHORITY = ("SHADOW: informational only. It never selects players, orders slots or the bench, or changes decision confidence; selection "
                          "authority needs an approved freshness threshold, completed forward validation, and an explicit authority decision.")
PROVIDER_ZEROED_STATUSES = frozenset({"OUT", "DOUBTFUL"})
BLOCKING_PROVIDER_BLOCKERS = frozenset({
    "JERRYGM_CONFIGURATION_BLOCKED", "JERRYGM_SEASON_WEEK_MISMATCH", "JERRYGM_SCORING_MISMATCH", "JERRYGM_SOURCE_UNSUPPORTED",
    "JERRYGM_PLAYER_ID_AMBIGUOUS", "JERRYGM_ROSTER_IDENTITY_AMBIGUOUS",
})
STALE_USAGE_BLOCKERS = frozenset({"OPPORTUNITY_DATA_STALE", "OPPORTUNITY_FRESHNESS_THRESHOLD_UNVERIFIED", "OPPORTUNITY_EVIDENCE_NOT_CURRENT"})
STALE_SNAP_BLOCKERS = frozenset({"SNAP_SHARE_EVIDENCE_STALE", "SNAP_SHARE_FRESHNESS_THRESHOLD_UNVERIFIED"})
BASE_LIMITATIONS = (
    "PRELIMINARY: no validated projection-accuracy model or action threshold exists; forward validation is pending.",
    "Provider availability fields (injury status, play probability) are display-only; Sleeper owns availability.",
)
COMPARISON_LIMITATION = ("No validated action threshold exists, so a projected edge never authorizes a lineup change by itself; "
                         "the current starter is kept unless availability, eligibility, or lock rules require a change.")
PROJECTION_BLOCKER_TEXT = {
    "PROVIDER_PROJECTION_NOT_REQUESTED": "not requested", "PROVIDER_PROJECTION_UNAVAILABLE": "no provider projection",
    "PROVIDER_PROJECTION_IDENTITY_UNAVAILABLE": "no exact Sleeper ID", "PROVIDER_SCORING_UNVERIFIED": "league scoring settings are unverified",
    "PROVIDER_SCORING_PRESET_UNSUPPORTED": "no provider preset matches league reception scoring", "PROVIDER_WEEK_UNVERIFIED": "the NFL week is unverified",
    "JERRYGM_CONFIGURATION_BLOCKED": "provider access is not configured", "JERRYGM_REFRESH_FAILED": "the provider request failed",
    "JERRYGM_PLAYER_NOT_RETURNED": "the provider returned no projection", "JERRYGM_FREE_ID_LIMIT_EXCEEDED": "the provider request limit was exceeded",
    "JERRYGM_SOURCE_DEGRADED": "the provider flagged its board as degraded", "JERRYGM_DEFENSE_IDENTITY_UNAVAILABLE": "the team defense identity is unresolved",
    "PROJECTION_STAT_LINE_UNAVAILABLE": "no provider stat line", "LEAGUE_SCORING_UNAVAILABLE": "league scoring settings are unavailable",
    "LEAGUE_SCORING_UNREPRODUCIBLE": "league scoring cannot be reproduced from the stat line", "SCORING_POSITION_UNSUPPORTED": "the position cannot be league-scored",
    "PROJECTION_GAME_STARTED": "his game has started", "PROJECTION_KICKOFF_UNVERIFIED": "his kickoff is unverified",
    "PROJECTION_RETRIEVED_AFTER_KICKOFF": "the projection was retrieved after kickoff", "PLAYER_HAS_NO_GAME": "no game this week",
    "PROVIDER_PROJECTION_ZEROED_FOR_AVAILABILITY": "the provider zeroes projections for players it lists Out or Doubtful",
    "PROVIDER_AVAILABILITY_CONFLICT": "provider availability contradicts Sleeper", "PROJECTION_DATA_THROUGH_WEEK_STALE": "provider stats are not current",
    "PROJECTION_DATA_THROUGH_WEEK_UNEXPECTED": "provider stats are not current", "PROJECTION_DATA_THROUGH_WEEK_AHEAD": "provider stats are for a later week",
    "PROJECTION_SEASON_MISMATCH": "the projection is for another season", "PROJECTION_WEEK_MISMATCH": "the projection is for another week",
    "PROVIDER_PROJECTION_STALE": "the projection is stale", "PROJECTION_GENERATED_AT_UNAVAILABLE": "the projection board time is missing",
    "PROJECTION_RETRIEVED_AT_UNAVAILABLE": "the retrieval time is missing",
}


def projection_blocker_text(code: Any) -> str:
    return PROJECTION_BLOCKER_TEXT.get(str(code or ""), "projection unavailable")


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _position(value: Any) -> str:
    position = str(value or "").strip().upper()
    return {"DST": "DEF", "D/ST": "DEF", "PK": "K"}.get(position, position)


def _name(view: Mapping[str, Any] | None) -> str:
    return (view or {}).get("player") or "Unnamed player"


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _json_default(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _json_native(value: Any) -> Any:
    """JSON-only copy (timestamps as ISO text) so a stored snapshot reloads exactly as captured; non-finite numbers are rejected."""
    return json.loads(json.dumps(value, default=_json_default, allow_nan=False))


def data_through_state(data_through_week: Any, week: Any) -> tuple[str, str | None]:
    """Classify the provider's latest stat week against the documented Tuesday stats rollover."""
    if not isinstance(week, int) or isinstance(week, bool):
        return "UNVERIFIED", "PROJECTION_WEEK_UNVERIFIED"
    if week == 1:
        return ("CURRENT", None) if data_through_week in (None, 0) else ("UNEXPECTED", "PROJECTION_DATA_THROUGH_WEEK_UNEXPECTED")
    through = _number(data_through_week)
    if through is None or not through.is_integer():
        return "UNEXPECTED", "PROJECTION_DATA_THROUGH_WEEK_UNEXPECTED"
    through = int(through)
    if through == week - 1:
        return "CURRENT", None
    if through == week - 2:
        return "ROLLOVER_LAG", "PROJECTION_DATA_THROUGH_WEEK_ROLLOVER_LAG"
    if through >= week:
        return "AHEAD", "PROJECTION_DATA_THROUGH_WEEK_AHEAD"
    return "STALE", "PROJECTION_DATA_THROUGH_WEEK_STALE"


def build_player_projection(evidence: Mapping[str, Any] | None, *, position: Any, scoring_settings: Mapping[str, Any] | None, season: Any, week: Any,
                            lock: Mapping[str, Any] | None = None, sleeper_team: Any = None, sleeper_health: Mapping[str, Any] | None = None,
                            known_gsis_id: Any = None, unavailable_blocker: str | None = None) -> dict[str, Any]:
    """League-scored PRELIMINARY projection for one player, with every eligibility gate disclosed."""
    position = _position(position)
    lock = dict(lock or {})
    health = dict(sleeper_health or {})
    result = {
        "value": None, "value_range": None, "unit": PROJECTION_UNIT, "source": PROJECTION_SOURCE, "season": season, "week": week,
        "generated_at": None, "retrieved_at": None, "scoring_basis": SCORING_BASIS, "scoring_completeness": "UNAVAILABLE",
        "missing_scoring_components": [], "scoring_components": [], "evidence_state": "UNAVAILABLE", "blocker": None, "blockers": [],
        "decision_eligible": False, "provider_points": None, "provider_scoring_preset": None,
        "data_through_week": None, "data_through_state": "UNAVAILABLE", "provider_availability": None, "availability_disagreement": None,
        "identity": {"provider_id": None, "gsis_id": None, "method": None}, "attribution": None, "limitations": list(BASE_LIMITATIONS),
        "confidence": {"state": "UNAVAILABLE", "reason": "No projection is available for this player."}, "recommendation_impact": "INFORMATIONAL_ONLY",
    }

    def done(state: str, *blockers: str | None) -> dict[str, Any]:
        found = list(dict.fromkeys(blocker for blocker in blockers if blocker))
        result.update(evidence_state=state, blockers=found, blocker=found[0] if found else None)
        return result

    if not isinstance(evidence, Mapping) or not evidence:
        return done("UNAVAILABLE", unavailable_blocker or "PROVIDER_PROJECTION_UNAVAILABLE")
    result.update(
        generated_at=evidence.get("source_record_time"), retrieved_at=evidence.get("retrieved_at"), attribution=evidence.get("attribution"),
        provider_points=_number(evidence.get("projected_ppg")), provider_scoring_preset=evidence.get("scoring_format"),
        data_through_week=evidence.get("data_through_week"),
        identity={"provider_id": evidence.get("provider_id") or evidence.get("sleeper_id"), "gsis_id": evidence.get("gsis_id"),
                  "method": evidence.get("identity_method") or "EXACT_SLEEPER_ID"},
    )
    availability = dict(evidence.get("provider_availability") or {})
    if availability:
        result["provider_availability"] = {**availability, "authority": "DISPLAY_ONLY"}
    provider_state = str(evidence.get("state") or "UNAVAILABLE").upper()
    provider_blockers = [str(item) for item in (evidence.get("blockers") or []) if item]
    if provider_state in {"UNAVAILABLE", "BLOCKED"} or result["provider_points"] is None:
        blocked = provider_state == "BLOCKED" or any(item in BLOCKING_PROVIDER_BLOCKERS for item in provider_blockers)
        return done("BLOCKED" if blocked else "UNAVAILABLE", *(provider_blockers or ["PROVIDER_PROJECTION_UNAVAILABLE"]))
    if provider_state == "STALE":
        return done("STALE", *(provider_blockers or ["PROVIDER_PROJECTION_STALE"]))
    try:
        season_matches = int(evidence.get("season")) == int(season)
        week_matches = int(evidence.get("week")) == int(week)
    except (TypeError, ValueError):
        season_matches = week_matches = False
    if not season_matches:
        return done("BLOCKED", "PROJECTION_SEASON_MISMATCH")
    if not week_matches:
        return done("BLOCKED", "PROJECTION_WEEK_MISMATCH")
    if not result["generated_at"]:
        return done("UNAVAILABLE", "PROJECTION_GENERATED_AT_UNAVAILABLE")
    if not result["retrieved_at"]:
        return done("UNAVAILABLE", "PROJECTION_RETRIEVED_AT_UNAVAILABLE")
    provider_position = _position(evidence.get("provider_position"))
    if provider_position and position and provider_position != position:
        return done("BLOCKED", "PROJECTION_IDENTITY_CONFLICT")
    provider_team, team = canonical_team(evidence.get("provider_team")), canonical_team(sleeper_team)
    if provider_team and team and provider_team != team:
        return done("BLOCKED", "PROJECTION_TEAM_CONFLICT")
    known = str(known_gsis_id or "").strip()
    provider_gsis = str(result["identity"]["gsis_id"] or "").strip()
    if known and provider_gsis and provider_gsis != known:
        return done("BLOCKED", "PROJECTION_IDENTITY_CONFLICT")

    status = str(availability.get("injury_status") or "").strip().upper()
    roster_status = "".join(char for char in str(evidence.get("roster_status") or "").lower() if char.isalnum())
    provider_inactive = status in PROVIDER_ZEROED_STATUSES or roster_status not in {"", "active"}
    sleeper_state = str(health.get("state") or "").upper()
    sleeper_label = health.get("label") or "available"
    provider_label = availability.get("injury_status") or evidence.get("roster_status")
    if provider_inactive and health.get("availability") != "UNAVAILABLE":
        if sleeper_state == "HEALTHY":
            result["availability_disagreement"] = (f"The provider lists this player {provider_label} and zeroes his projection, but Sleeper lists him "
                                                   f"{sleeper_label}; Sleeper owns availability, so the provider line is withheld.")
            return done("BLOCKED", "PROVIDER_AVAILABILITY_CONFLICT")
        result["limitations"].append(f"The provider zeroes projections for players it lists Out or Doubtful (provider: {provider_label}; "
                                     f"Sleeper: {sleeper_label}), so no role projection is available.")
        return done("UNAVAILABLE", "PROVIDER_PROJECTION_ZEROED_FOR_AVAILABILITY")
    p_play = _number(availability.get("p_play"))
    if health.get("availability") == "UNAVAILABLE" and not provider_inactive and not lock.get("no_game"):
        result["availability_disagreement"] = f"Sleeper lists this player {sleeper_label}; the provider projection still assumes he plays (display only)."
    elif p_play is not None and p_play <= 0 and health.get("availability") != "UNAVAILABLE":
        result["availability_disagreement"] = (f"The provider's availability model gives this player no chance to play, but Sleeper lists him {sleeper_label}; "
                                               "Sleeper owns availability, so the provider's role projection is used unchanged.")

    through_state, through_blocker = data_through_state(result["data_through_week"], week)
    result["data_through_state"] = through_state
    if through_state == "AHEAD":
        return done("BLOCKED", through_blocker)
    if through_state in {"UNEXPECTED", "STALE", "UNVERIFIED"}:
        return done("UNAVAILABLE", through_blocker)
    scored = league_score_stat_line(evidence.get("stat_line"), scoring_settings, position=position,
                                    breakdown=evidence.get("breakdown"), coverage=evidence.get("stat_line_coverage"))
    result.update(value=scored["value"], value_range=scored["value_range"], scoring_completeness=scored["scoring_completeness"],
                  missing_scoring_components=scored["missing_scoring_components"], scoring_components=scored["components"])
    result["limitations"] += scored["limitations"]
    if scored["value"] is None and scored["value_range"] is None:
        return done("UNAVAILABLE", scored["blocker"] or "LEAGUE_SCORING_UNREPRODUCIBLE", *provider_blockers)
    result["confidence"] = {"state": "UNAVAILABLE", "reason": "No validated projection-accuracy model exists yet, so reliability is not rated until forward validation completes."}
    degraded = []
    if scored["scoring_completeness"] != "COMPLETE":
        degraded.append(scored["blocker"] or "LEAGUE_SCORING_PARTIAL")
    if through_state == "ROLLOVER_LAG":
        degraded.append(through_blocker)
        result["limitations"].append("The provider's latest stats lag one week (documented Tuesday stats rollover), so this projection is not treated as current.")
    eligibility = []
    if lock.get("no_game") or lock.get("state") == "BYE":
        eligibility.append("PLAYER_HAS_NO_GAME")
    elif lock.get("state") == "LOCKED":
        eligibility.append("PROJECTION_GAME_STARTED")
    elif lock.get("state") == "OPEN":
        retrieved, kickoff = utc_datetime(result["retrieved_at"]), utc_datetime(lock.get("kickoff_utc"))
        if retrieved is None or kickoff is None or retrieved >= kickoff:
            eligibility.append("PROJECTION_RETRIEVED_AFTER_KICKOFF")
    elif lock.get("state") != "NOT_APPLICABLE":
        eligibility.append("PROJECTION_KICKOFF_UNVERIFIED")
    result["decision_eligible"] = not eligibility
    return done("DEGRADED" if degraded else "PRELIMINARY", *eligibility, *degraded, *provider_blockers)


def projection_range(projection: Mapping[str, Any] | None) -> tuple[float, float] | None:
    value_range = (projection or {}).get("value_range")
    if not isinstance(value_range, Mapping):
        return None
    low, high = _number(value_range.get("low")), _number(value_range.get("high"))
    return (low, high) if low is not None and high is not None else None


def projection_text(projection: Mapping[str, Any] | None) -> str:
    projection = projection or {}
    if projection.get("value") is not None:
        return f"{projection['value']:.2f}"
    bounds = projection_range(projection)
    if bounds is not None:
        return f"{bounds[0]:.2f}–{bounds[1]:.2f} (partial scoring)"
    return "Unavailable"


def build_weekly_score_v2(projection: Mapping[str, Any] | None, *, provider_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Weekly Score v2: the current-week league-scored projection, exposed only as SHADOW evidence.

    The value is the ``build_player_projection`` result as-is: exact only when league scoring is COMPLETE, otherwise the existing
    range with a null value. A missing projection stays null, never zero. Freshness counts only under an explicitly supplied
    provider threshold. Nothing here feeds lineup selection, ordering, or decision confidence.
    """
    projection = projection if isinstance(projection, Mapping) else {}
    evidence = provider_evidence if isinstance(provider_evidence, Mapping) else {}
    source_state = str(projection.get("evidence_state") or "UNAVAILABLE").upper()
    completeness = projection.get("scoring_completeness") or "UNAVAILABLE"
    exact = _number(projection.get("value")) if completeness == "COMPLETE" else None
    bounds = projection_range(projection)
    usable = source_state in {"PRELIMINARY", "DEGRADED"} and (exact is not None or bounds is not None)
    if usable:
        state = "PRELIMINARY" if source_state == "PRELIMINARY" and exact is not None else "DEGRADED"
    else:
        state, exact, bounds = (source_state if source_state in {"BLOCKED", "STALE"} else "UNAVAILABLE"), None, None
    threshold_id = str(evidence.get("freshness_threshold_id") or "").strip()
    provider_freshness = str(evidence.get("freshness_state") or "").upper()
    if threshold_id and threshold_id != "UNVERIFIED" and provider_freshness in {"FRESH", "AGING", "STALE"}:
        freshness_state, threshold = provider_freshness, {"state": "VERIFIED", "id": threshold_id}
    else:
        freshness_state, threshold = "UNAVAILABLE", {"state": "UNAPPROVED", "id": None}
    blockers = [str(item) for item in projection.get("blockers") or [] if item]
    if usable and freshness_state == "UNAVAILABLE":
        blockers.append("JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED")
    if not usable and not blockers:
        blockers.append("PROVIDER_PROJECTION_UNAVAILABLE")
    blockers = list(dict.fromkeys(blockers))
    if state == "PRELIMINARY":
        note = "Preliminary · informational only"
    elif state == "DEGRADED":
        reason = ("Partial scoring" if completeness != "COMPLETE" else "Provider stats lag a week" if projection.get("data_through_state") == "ROLLOVER_LAG"
                  else "Degraded")
        note = f"{reason} · informational only"
    else:
        reason = "the projection is stale" if state == "STALE" else projection_blocker_text(blockers[0])
        note = reason[:1].upper() + reason[1:]
    shown = f"{exact:.2f} pts" if exact is not None else f"{bounds[0]:.2f}–{bounds[1]:.2f} pts" if bounds is not None else "Unavailable"
    return {
        "contract_id": WEEKLY_SCORE_CONTRACT_ID, "label": WEEKLY_SCORE_LABEL, "definition": WEEKLY_SCORE_DEFINITION, "basis": COMPARISON_BASIS,
        "unit": PROJECTION_UNIT, "direction": "HIGHER_IS_BETTER", "state": state, "value": exact,
        "value_range": {"low": bounds[0], "high": bounds[1]} if bounds is not None else None,
        "evidence_level": "PRELIMINARY" if usable else "INSUFFICIENT", "authority": "SHADOW", "used_for": "SHADOW_EVIDENCE",
        "recommendation_impact": "INFORMATIONAL_ONLY", "decision_effect": "NONE",
        "source": projection.get("source") or PROJECTION_SOURCE, "attribution": projection.get("attribution"),
        "source_generated_at": projection.get("generated_at"), "retrieved_at": projection.get("retrieved_at"),
        "season": projection.get("season"), "week": projection.get("week"), "identity": dict(projection.get("identity") or {}),
        "scoring_context": projection.get("scoring_basis") or SCORING_BASIS, "scoring_contract": LEAGUE_SCORING_CONTRACT_ID,
        "scoring_completeness": completeness,
        "missing_scoring_rules": sorted({str(item.get("rule")) for item in projection.get("missing_scoring_components") or [] if isinstance(item, Mapping)}),
        "data_through_week": projection.get("data_through_week"), "freshness_state": freshness_state, "freshness_threshold": threshold,
        "blocker": blockers[0] if blockers else None, "blockers": blockers, "display": {"value": shown, "note": note},
    }


def weekly_score_v2_basis(scores: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    """Lineup-level disclosure of the shadow Weekly Score v2; informational only."""
    scores = [score for score in scores or [] if isinstance(score, Mapping)]
    exact = [score for score in scores if score.get("value") is not None]
    ranged = [score for score in scores if score.get("value") is None and score.get("value_range")]
    usable = exact + ranged
    verified = bool(usable) and all((score.get("freshness_threshold") or {}).get("state") == "VERIFIED" for score in usable)
    return {
        "contract_id": WEEKLY_SCORE_CONTRACT_ID, "label": WEEKLY_SCORE_LABEL, "definition": WEEKLY_SCORE_DEFINITION, "unit": PROJECTION_UNIT,
        "state": "PRELIMINARY" if exact else "DEGRADED" if ranged else "UNAVAILABLE", "exact_players": len(exact), "range_players": len(ranged),
        "identified_players": len(scores), "counts": dict(sorted(Counter(str(score.get("state")) for score in scores).items())),
        "freshness_threshold_state": "VERIFIED" if verified else "UNAPPROVED", "evidence_level": "PRELIMINARY" if usable else "INSUFFICIENT",
        "authority": "SHADOW", "used_for": "SHADOW_EVIDENCE", "recommendation_impact": "INFORMATIONAL_ONLY", "authority_reason": WEEKLY_SCORE_AUTHORITY,
    }


def _floor_value(view: Mapping[str, Any]) -> float | None:
    projection = view.get("projection") or {}
    if projection.get("value") is not None:
        return float(projection["value"])
    bounds = projection_range(projection)
    return bounds[0] if bounds else None


def best_projection_alternative(candidates: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any] | None, list[Mapping[str, Any]]]:
    """Highest league-scored projection, preferring decision-eligible projections; partial scoring ranks by its guaranteed minimum."""
    scored = [view for view in candidates or [] if _floor_value(view) is not None]
    unscored = [view for view in candidates or [] if _floor_value(view) is None]
    scored.sort(key=lambda view: (not (view.get("projection") or {}).get("decision_eligible"), -_floor_value(view), str(view.get("player_id"))))
    return (scored[0] if scored else None), unscored


def _compact(view: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if view is None:
        return None
    projection = view.get("projection") or {}
    lock = view.get("lock") or {}
    return {
        "player": _name(view), "player_id": view.get("player_id"), "position": view.get("position"), "nfl_team": view.get("nfl_team"),
        "projection": projection.get("value"), "projection_range": projection.get("value_range"), "projection_text": projection_text(projection),
        "projection_state": projection.get("evidence_state"), "projection_blocker": projection.get("blocker"),
        "decision_eligible": bool(projection.get("decision_eligible")), "scoring_completeness": projection.get("scoring_completeness"),
        "provider_points": projection.get("provider_points"), "health": (view.get("health") or {}).get("label"),
        "availability": view.get("availability"), "lock_state": lock.get("state"), "lock_label": lock.get("label"),
        "kickoff": lock.get("kickoff_display"), "kickoff_utc": lock.get("kickoff_utc"), "opponent": lock.get("opponent") or view.get("opponent"),
        "workload": ((view.get("opportunity") or {}).get("workload") or {}).get("text"),
    }


def compare_projections(current: Mapping[str, Any] | None, alternative: Mapping[str, Any] | None, *, action_threshold: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Classify a current-starter vs alternative projection comparison; it never authorizes a lineup change."""
    result = {
        "state": "INSUFFICIENT_EVIDENCE", "preferred": None, "preferred_player": None, "current": _compact(current), "alternative": _compact(alternative),
        "projection_delta": None, "delta_range": None, "unit": PROJECTION_UNIT, "basis": COMPARISON_BASIS,
        "action_threshold": dict(action_threshold) if action_threshold else None, "reasons": [], "blockers": [],
        "limitations": [COMPARISON_LIMITATION], "authorizes_lineup_change": False, "recommendation_impact": "INFORMATIONAL_ONLY",
    }

    def outcome(state: str, blocker: str | None, reason: str) -> dict[str, Any]:
        result["state"] = state
        if blocker:
            result["blockers"].append(blocker)
        result["reasons"].append(reason)
        return result

    if current is None:
        return outcome("INSUFFICIENT_EVIDENCE", "COMPARISON_STARTER_MISSING", "No current starter occupies this slot, so there is nothing to compare against.")
    if alternative is None:
        return outcome("INSUFFICIENT_EVIDENCE", "COMPARISON_ALTERNATIVE_MISSING", "No eligible bench alternative with a league-scored projection exists for this slot.")
    for view in (current, alternative):
        if view.get("player_id") is None or view.get("identity_state") not in {"RESOLVED", "SANDBOX_NAME"}:
            return outcome("BLOCKED", "IDENTITY_UNRESOLVED", f"{_name(view)}'s player identity is unresolved.")
        if (view.get("projection") or {}).get("blocker") in {"PROJECTION_IDENTITY_CONFLICT", "PROJECTION_TEAM_CONFLICT"}:
            return outcome("BLOCKED", "IDENTITY_CONFLICT", f"The provider's identity for {_name(view)} conflicts with Sleeper, so the comparison is blocked.")
    for view in (current, alternative):
        lock = view.get("lock") or {}
        if lock.get("state") == "LOCKED":
            return outcome("BLOCKED", "GAME_LOCKED", f"{_name(view)}'s game has started; Sleeper locks players at kickoff.")
        if lock.get("state") == "BYE" or lock.get("no_game"):
            return outcome("BLOCKED", "PLAYER_ON_BYE", f"{_name(view)} is on bye and cannot score this week.")
        if lock.get("state") not in {"OPEN", "NOT_APPLICABLE"}:
            return outcome("BLOCKED", "LOCK_UNVERIFIED", f"{_name(view)}'s kickoff lock is unverified: {lock.get('reason') or 'no schedule evidence'}")
    if current.get("availability") == "UNAVAILABLE":
        return outcome("BLOCKED", "CURRENT_STARTER_UNAVAILABLE", f"{_name(current)} cannot play ({(current.get('health') or {}).get('label') or 'unavailable'}); "
                                                                  "the slot needs a replacement regardless of projections.")
    if alternative.get("availability") == "UNAVAILABLE":
        return outcome("BLOCKED", "ALTERNATIVE_UNAVAILABLE", f"{_name(alternative)} cannot start this week.")
    for view in (current, alternative):
        if (view.get("projection") or {}).get("blocker") == "PROVIDER_AVAILABILITY_CONFLICT":
            return outcome("BLOCKED", "CONTRADICTORY_EVIDENCE", f"The provider's availability for {_name(view)} contradicts Sleeper, so the provider line is withheld.")
    missing = [view for view in (current, alternative) if not (view.get("projection") or {}).get("decision_eligible")]
    if missing:
        details = "; ".join(f"{_name(view)} ({projection_blocker_text((view.get('projection') or {}).get('blocker'))})" for view in missing)
        result["blockers"].extend(sorted({(view.get("projection") or {}).get("blocker") or "PROJECTION_UNAVAILABLE" for view in missing}))
        return outcome("INSUFFICIENT_EVIDENCE", None, f"No usable projection for {details}; a missing projection is never treated as zero.")
    left, right = current["projection"], alternative["projection"]
    if left.get("generated_at") != right.get("generated_at"):
        return outcome("INSUFFICIENT_EVIDENCE", "PROJECTION_BOARD_MISMATCH", "The two projections come from different provider boards.")
    (current_low, current_high), (alternative_low, alternative_high) = projection_range(left), projection_range(right)
    low, high = alternative_low - current_high, alternative_high - current_low
    result["delta_range"] = {"low": round(low, 2), "high": round(high, 2)}
    delta = round(right["value"] - left["value"], 2) if left.get("value") is not None and right.get("value") is not None else None
    if delta is None and low <= 0 <= high:
        return outcome("INSUFFICIENT_EVIDENCE", "LEAGUE_SCORING_PARTIAL", "The projected ordering depends on league scoring rules the stat line cannot reproduce exactly.")
    result["projection_delta"] = delta
    if delta is not None:
        favored = "ALTERNATIVE" if delta > 0 else "CURRENT" if delta < 0 else "TIE"
        edge = abs(delta)
    else:
        favored = "ALTERNATIVE" if low > 0 else "CURRENT"
        edge = min(abs(low), abs(high))
    result.update(preferred=favored, preferred_player=_name(alternative) if favored == "ALTERNATIVE" else _name(current) if favored == "CURRENT" else None)
    threshold = _number((action_threshold or {}).get("points")) if (action_threshold or {}).get("id") else None
    clean = all((view.get("projection") or {}).get("evidence_state") == "PRELIMINARY" for view in (current, alternative))
    if threshold is not None and threshold > 0 and clean and favored != "TIE" and edge >= threshold:
        return outcome("SUPPORTED_COMPARISON", None, f"The projected edge ({edge:.2f}) meets the approved action threshold {action_threshold['id']} ({threshold:g}).")
    if favored == "TIE":
        return outcome("CLOSE_CALL", None, "The league-scored projections tie.")
    qualifier = "" if delta is not None else " in every reproducible scoring case"
    return outcome("CLOSE_CALL", None, f"{result['preferred_player']} projects {edge:.2f} more league points{qualifier}, but no validated action threshold exists.")


def _sleeper_availability(view: Mapping[str, Any]) -> str:
    return "UNAVAILABLE" if view.get("is_bye") else str((view.get("health") or {}).get("availability") or "UNCERTAIN")


def _opportunity_direction(current: Mapping[str, Any], alternative: Mapping[str, Any]) -> dict[str, Any]:
    domain = {"domain": "RECENT_OPPORTUNITY", "favors": None, "state": "UNAVAILABLE", "detail": None}
    if current.get("position") != alternative.get("position"):
        return {**domain, "detail": "Recent workload is not compared across positions."}
    order = {"LIMITED_OPPORTUNITY": 1, "MODERATE_OPPORTUNITY": 2, "HIGH_OPPORTUNITY": 3}
    mine, theirs = ((view.get("opportunity") or {}) for view in (current, alternative))
    if mine.get("state") != "AVAILABLE" or theirs.get("state") != "AVAILABLE" or not order.get(mine.get("strength")) or not order.get(theirs.get("strength")):
        return {**domain, "detail": "Current published workload is unavailable for at least one player."}
    favors = "ALTERNATIVE" if order[theirs["strength"]] > order[mine["strength"]] else "CURRENT" if order[mine["strength"]] > order[theirs["strength"]] else "NEUTRAL"
    return {**domain, "state": "AVAILABLE", "favors": favors, "detail": f"{_name(current)}: {mine.get('label')}; {_name(alternative)}: {theirs.get('label')}"}


def _matchup_direction(current: Mapping[str, Any], alternative: Mapping[str, Any]) -> dict[str, Any]:
    domain = {"domain": "MATCHUP_CONTEXT", "favors": None, "state": "UNAVAILABLE", "detail": None}
    if current.get("position") != alternative.get("position"):
        return {**domain, "detail": "Positional matchup ranks are not compared across positions."}
    left, right = ((view.get("matchup") or {}).get("easiest_rank") for view in (current, alternative))
    if left is None or right is None:
        return {**domain, "detail": "Matchup evidence is unavailable for at least one player."}
    favors = "ALTERNATIVE" if right < left else "CURRENT" if left < right else "NEUTRAL"
    return {**domain, "state": "AVAILABLE", "favors": favors,
            "detail": f"{_name(current)}: {(current.get('matchup') or {}).get('signal')}; {_name(alternative)}: {(alternative.get('matchup') or {}).get('signal')} (context only)"}


def evidence_agreement(current: Mapping[str, Any] | None, alternative: Mapping[str, Any] | None, comparison: Mapping[str, Any]) -> dict[str, Any]:
    """Independent evidence domains for one comparison; never weighted, averaged, or turned into a probability."""
    base = {"recommendation_impact": "INFORMATIONAL_ONLY", "method": "Each domain is reported independently; nothing is weighted or averaged."}
    if current is None or alternative is None:
        return {**base, "state": "INSUFFICIENT_EVIDENCE", "domains": [], "contradictions": [], "label": "No comparison player."}
    preferred = comparison.get("preferred")
    if comparison.get("state") in {"CLOSE_CALL", "SUPPORTED_COMPARISON"} and preferred in {"ALTERNATIVE", "CURRENT", "TIE"}:
        edge = comparison.get("projection_delta")
        detail = ("Tied" if preferred == "TIE" else f"{comparison.get('preferred_player')} by {abs(edge):.2f} league points" if edge is not None
                  else f"{comparison.get('preferred_player')} in every reproducible scoring case")
        projection = {"domain": "PROJECTION", "favors": "NEUTRAL" if preferred == "TIE" else preferred, "state": "AVAILABLE", "detail": detail}
    else:
        projection = {"domain": "PROJECTION", "favors": None, "state": "UNAVAILABLE", "detail": " ".join(comparison.get("reasons") or []) or "Projection comparison unavailable."}
    order = {"AVAILABLE": 2, "UNCERTAIN": 1, "UNAVAILABLE": 0}
    mine, theirs = _sleeper_availability(current), _sleeper_availability(alternative)
    favors = "CURRENT" if order.get(mine, 1) > order.get(theirs, 1) else "ALTERNATIVE" if order.get(theirs, 1) > order.get(mine, 1) else "NEUTRAL"
    availability = {"domain": "AVAILABILITY", "favors": favors, "state": "AVAILABLE",
                    "detail": f"{_name(current)}: {(current.get('health') or {}).get('label') or mine.title()}; "
                              f"{_name(alternative)}: {(alternative.get('health') or {}).get('label') or theirs.title()} (Sleeper)"}
    environment = {"domain": "GAME_ENVIRONMENT", "favors": None, "state": "UNSUPPORTED",
                   "detail": "No supported game-environment evidence (for example, betting totals) is connected; nothing is inferred."}
    domains = [projection, _opportunity_direction(current, alternative), _matchup_direction(current, alternative), environment, availability]
    contradictions = [f"{_name(view)}: {text}" for view in (current, alternative) if (text := (view.get("projection") or {}).get("availability_disagreement"))]
    if "IDENTITY_CONFLICT" in (comparison.get("blockers") or []):
        contradictions.append("Provider identity conflicts with Sleeper.")
    directional = [domain["favors"] for domain in domains if domain["favors"] in {"CURRENT", "ALTERNATIVE"}]
    if contradictions:
        state = "CONTRADICTORY"
    elif len(directional) < 2:
        state = "INSUFFICIENT_EVIDENCE"
    elif len(set(directional)) == 1:
        state = "AGREES"
    else:
        state = "MIXED"
    names = {"CURRENT": _name(current), "ALTERNATIVE": _name(alternative), "NEUTRAL": "neutral"}
    label = "; ".join(f"{domain['domain'].replace('_', ' ').title()}: {names.get(domain['favors'], 'unavailable')}"
                      for domain in domains if domain["state"] != "UNSUPPORTED")
    return {**base, "state": state, "domains": domains, "contradictions": contradictions, "label": label}


WORKLOAD_FIELDS = (
    ("carries", "carry", "carries", "count"), ("targets", "target", "targets", "count"), ("receptions", "reception", "receptions", "count"),
    ("snap_share", "snap share", "snap share", "share"), ("target_share", "target share", "target share", "share"),
    ("red_zone_share", "red-zone share", "red-zone share", "share"), ("route_participation", "route participation", "route participation", "share"),
)


def recent_workload(usage: Mapping[str, Any] | None, snaps: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Latest published week's factual workload; shown even when stale (and labelled), withheld when rows fail validation."""
    usage = usage or {}
    rows = [row for row in usage.get("rows") or [] if isinstance(row, Mapping) and isinstance(row.get("week"), int)]
    blockers = [str(item) for item in usage.get("blockers") or [] if item]
    base = {"state": "UNAVAILABLE", "season": None, "week": None, "source": None, "retrieved_at": None, "freshness_state": None,
            "blockers": blockers, "decision_effect": "INFORMATIONAL_ONLY"}
    if not rows:
        return {**base, "reason": "No published usage rows exist for this player."}
    if any(item not in STALE_USAGE_BLOCKERS for item in blockers):
        return {**base, "state": "BLOCKED", "reason": "Published usage rows failed validation, so workload facts are withheld."}
    latest = max(rows, key=lambda row: row["week"])
    state = "AVAILABLE" if usage.get("state") == "AVAILABLE" else "STALE" if "OPPORTUNITY_DATA_STALE" in blockers else "UNVERIFIED"
    snaps = snaps or {}
    snap = None
    if not set(snaps.get("blockers") or []) - STALE_SNAP_BLOCKERS:
        snap = next((_number(row.get("snap_share")) for row in snaps.get("rows") or [] if isinstance(row, Mapping) and row.get("week") == latest["week"]), None)
    facts = {key: _number(latest.get(key)) for key, *_ in WORKLOAD_FIELDS}
    if snap is not None:
        facts["snap_share"] = snap
    reason = (None if state == "AVAILABLE" else "The latest published usage is outside its freshness limit." if state == "STALE"
              else "No usage freshness threshold is approved, so currency is unverified.")
    return {**base, **facts, "state": state, "season": latest.get("season"), "week": latest["week"], "source": latest.get("source"),
            "retrieved_at": _iso(latest.get("retrieved_at")), "freshness_state": latest.get("freshness_state"), "reason": reason}


def workload_summary(workload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Factual recent-workload text from published usage evidence; never a grade or a weight."""
    workload = dict(workload or {})
    unsupported = ["goal-line carries", "red-zone carry and target counts"]
    if not workload or workload.get("state") in {None, "UNAVAILABLE", "BLOCKED"}:
        return {"state": workload.get("state") or "UNAVAILABLE", "week": None, "facts": [], "text": "Recent workload unavailable",
                "reason": workload.get("reason") or "No published usage evidence was supplied.", "unsupported": unsupported, "decision_effect": "INFORMATIONAL_ONLY"}
    facts = []
    for key, singular, plural, kind in WORKLOAD_FIELDS:
        value = _number(workload.get(key))
        if value is None:
            continue
        text = f"{value:g} {singular if value == 1 else plural}" if kind == "count" else f"{value * 100:.0f}% {plural}"
        facts.append({"metric": key, "value": value, "text": text})
    week, state = workload.get("week"), str(workload.get("state")).upper()
    body = " · ".join(fact["text"] for fact in facts)
    if not facts:
        text = "Recent workload unavailable"
    elif state == "AVAILABLE":
        text = f"Week {week}: {body}"
    else:
        text = f"Last published Week {week} ({state.lower()}): {body}"
    return {"state": state, "week": week, "facts": facts, "text": text, "reason": workload.get("reason"), "unsupported": unsupported,
            "decision_effect": "INFORMATIONAL_ONLY"}


SNAPSHOT_WEEKLY_VALUE_FIELDS = ("basis", "unit", "state", "value", "evidence_level", "blocker", "baseline", "matchup_modifier", "injury_multiplier", "source",
                                "freshness_state")
SNAPSHOT_HEALTH_FIELDS = ("status", "state", "label", "availability", "verified", "source", "freshness_state", "last_verified")
SNAPSHOT_LOCK_FIELDS = ("contract_id", "state", "team", "opponent", "venue", "kickoff_utc", "kickoff_display", "decision_authority", "freshness_state",
                        "freshness_threshold_id", "schedule_source", "source_recorded_at", "retrieved_at")
SNAPSHOT_PROJECTION_FIELDS = ("source", "unit", "scoring_basis", "generated_at", "retrieved_at", "data_through_week", "decision_eligible", "blockers",
                              "missing_scoring_components", "confidence", "recommendation_impact")
SNAPSHOT_WEEKLY_SCORE_FIELDS = ("contract_id", "state", "value", "value_range", "unit", "evidence_level", "authority", "used_for", "recommendation_impact",
                                "source", "source_generated_at", "retrieved_at", "season", "week", "scoring_context", "scoring_contract", "scoring_completeness",
                                "missing_scoring_rules", "freshness_state", "freshness_threshold", "data_through_week", "blockers")


def _utc_iso(value: Any) -> str | None:
    parsed = utc_datetime(value)
    return parsed.isoformat() if parsed is not None else None


def build_forward_validation_snapshots(views: Sequence[Mapping[str, Any]], decisions: Sequence[Mapping[str, Any]], *, season: Any, week: Any, captured_at: Any,
                                       player_decisions: Mapping[Any, Mapping[str, Any]] | None = None, lineup: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Decision-time evidence for players whose games have not started; built read-only and never persisted here.

    ``player_decisions`` maps each Sleeper ID to the START/SIT/FLEX/MONITOR decision shown for him, and ``lineup`` carries the lineup-level
    contract context. Both are copied, never derived, so a stored snapshot can be read without the live page or later evidence.
    """
    result = {
        "state": "UNAVAILABLE", "decision_type": SNAPSHOT_DECISION_TYPE, "captured_at": _iso(captured_at), "snapshots": [], "skipped": [],
        "persistence": {"state": "NOT_PERSISTED", "store": "pre_decision_snapshots", "blocker": "PRE_KICKOFF_CAPTURE_NOT_RUN_BY_PAGE",
                        "reason": "Viewing My Team never saves snapshots; the explicit pre-kickoff capture step appends them to the append-only snapshot store."},
        "purpose": "Compare decision-time projections with actual Sleeper points after games finish; never used to train or calibrate a projection model.",
        "decision_effect": "NONE",
    }
    slots, starters, comparisons = {}, {}, {}
    for decision in decisions or []:
        if (decision.get("recommended") or {}).get("player_id") is not None:
            slots.setdefault(decision["recommended"]["player_id"], decision.get("slot"))
        if (decision.get("current") or {}).get("player_id") is not None:
            starters.setdefault(decision["current"]["player_id"], decision.get("slot"))
        comparison = decision.get("projection_comparison") or {}
        for side in ("current", "alternative"):
            player_id = (comparison.get(side) or {}).get("player_id")
            if player_id is not None:
                comparisons.setdefault(player_id, {"slot": decision.get("slot"), "role": side, "state": comparison.get("state"),
                                                   "preferred": comparison.get("preferred"), "projection_delta": comparison.get("projection_delta")})
    for view in sorted(views or [], key=lambda item: str(item.get("player_id"))):
        player_id, lock = view.get("player_id"), view.get("lock") or {}
        projection = view.get("projection") or {}
        reason = ("IDENTITY_UNRESOLVED" if player_id is None or view.get("identity_state") != "RESOLVED"
                  else "NO_GAME" if lock.get("no_game") or lock.get("state") == "BYE"
                  else f"LOCK_{lock.get('state') or 'UNVERIFIED'}" if lock.get("state") != "OPEN"
                  else "PROJECTION_RETRIEVED_AFTER_KICKOFF" if "PROJECTION_RETRIEVED_AFTER_KICKOFF" in (projection.get("blockers") or [])
                  else None)
        if reason:
            result["skipped"].append({"player": _name(view), "player_id": player_id, "reason": reason})
            continue
        health, value = view.get("health") or {}, view.get("value") or {}
        weekly = view.get("weekly_score_v2") or {}
        decision = (player_decisions or {}).get(player_id) or {}
        output = {
            "player": _name(view), "position": view.get("position"), "recommended_slot": slots.get(player_id), "current_slot": starters.get(player_id) or "BENCH",
            "health": health.get("status"), "availability": view.get("availability"), "kickoff_utc": lock.get("kickoff_utc"),
            "lock_state": lock.get("state"), "league_scored_projection": projection.get("value"), "league_scored_range": projection.get("value_range"),
            "scoring_completeness": projection.get("scoring_completeness"), "provider_points": projection.get("provider_points"),
            "provider_scoring_preset": projection.get("provider_scoring_preset"), "projection_evidence_state": projection.get("evidence_state"),
            "recent_workload": ((view.get("opportunity") or {}).get("workload") or {}).get("text"), "comparison": comparisons.get(player_id),
            "decision": decision.get("decision"), "slot_status": decision.get("status"), "slot_basis": decision.get("basis"), "changed": decision.get("changed"),
            "decision_confidence": decision.get("decision_confidence"), "why": decision.get("why"), "drivers": list(decision.get("drivers") or []),
            "related_slots": list(decision.get("related_slots") or []), "missing_evidence": decision.get("missing_evidence"),
            "nfl_team": view.get("nfl_team"), "opponent": lock.get("opponent") or view.get("opponent"), "venue": lock.get("venue") or view.get("home_away"),
            "availability_reason": view.get("availability_reason"),
            "weekly_value": {key: value.get(key) for key in SNAPSHOT_WEEKLY_VALUE_FIELDS} if value else None,
            "weekly_score_v2": {key: weekly.get(key) for key in SNAPSHOT_WEEKLY_SCORE_FIELDS} if weekly else None,
            "health_evidence": {key: health.get(key) for key in SNAPSHOT_HEALTH_FIELDS},
            "lock": {key: lock.get(key) for key in SNAPSHOT_LOCK_FIELDS},
            "projection_evidence": {key: projection.get(key) for key in SNAPSHOT_PROJECTION_FIELDS},
            "lineup": dict(lineup) if lineup else None,
            "contract_versions": {"snapshot_output": SNAPSHOT_OUTPUT_VERSION, "lineup_decision": (lineup or {}).get("schema_version"),
                                  "game_lock": lock.get("contract_id"), "league_scored_projection": LEAGUE_SCORING_CONTRACT_ID,
                                  "weekly_score": weekly.get("contract_id")},
        }
        evidence_state = {"PRELIMINARY": "AVAILABLE", "DEGRADED": "INSUFFICIENT_EVIDENCE", "BLOCKED": "BLOCKED", "STALE": "STALE"}.get(projection.get("evidence_state"), "UNAVAILABLE")
        blockers = [*(projection.get("blockers") or []), *([value["blocker"]] if value.get("blocker") else [])]
        try:
            snapshot = build_pre_decision_snapshot(
                season=season, week=week, decision_type=SNAPSHOT_DECISION_TYPE, decision_subject=f"sleeper:{player_id}", decision_output=_json_native(output),
                evidence_state=evidence_state,
                evidence_source=_json_native({"projection": projection.get("source"), "schedule": lock.get("schedule_source"), "health": health.get("source"),
                                              "weekly_value": value.get("source")}),
                evidence_lineage=_json_native({"attribution": projection.get("attribution"), "data_through_week": projection.get("data_through_week"),
                                               "generated_at": projection.get("generated_at")}),
                source_recorded_at=_utc_iso(projection.get("generated_at")), retrieved_at=_utc_iso(projection.get("retrieved_at")), freshness_state="UNAVAILABLE",
                completeness_state="COMPLETE" if projection.get("scoring_completeness") == "COMPLETE" else "INCOMPLETE" if projection.get("value_range") else "UNAVAILABLE",
                confidence=_json_native(projection.get("confidence")), blockers=list(dict.fromkeys(blockers)), captured_at=_iso(captured_at),
                entity_identity=_json_native({"sleeper_id": player_id, **(projection.get("identity") or {})}),
            )
        except (SnapshotValidationError, ValueError, TypeError) as error:
            result["skipped"].append({"player": _name(view), "player_id": player_id, "reason": f"SNAPSHOT_INVALID: {error}"})
            continue
        result["snapshots"].append(snapshot)
    result["state"] = "BUILT_NOT_PERSISTED" if result["snapshots"] else "UNAVAILABLE"
    return result


def comparison_brief(comparison: Mapping[str, Any]) -> dict[str, list[str]]:
    """Two to four factual reasons and the information that could change one projection comparison."""
    current, alternative = comparison.get("current") or {}, comparison.get("alternative") or {}
    if not current or not alternative:
        return {"why": list(comparison.get("reasons") or [])[:4], "what_could_change": []}
    why = []
    if comparison.get("state") in {"CLOSE_CALL", "SUPPORTED_COMPARISON"}:
        why.append(f"League-scored projection: {alternative['player']} {alternative['projection_text']} vs {current['player']} {current['projection_text']} points.")
    why.extend(comparison.get("reasons") or [])
    why.append(f"Health (Sleeper): {current['player']} {current.get('health') or 'Unavailable'}; {alternative['player']} {alternative.get('health') or 'Unavailable'}.")
    if current.get("workload") or alternative.get("workload"):
        why.append(f"Recent workload: {current['player']} {current.get('workload') or 'unavailable'}; {alternative['player']} {alternative.get('workload') or 'unavailable'}.")
    changes = []
    for side in (current, alternative):
        if side.get("health") in {"Questionable", "Doubtful", "Unknown"}:
            changes.append(f"Official game-day status for {side['player']} ({side['health']}).")
        if side.get("lock_state") == "LOCK_UNVERIFIED":
            changes.append(f"A verified kickoff time for {side['player']} (fresh automated schedule within an approved freshness limit).")
    if comparison.get("state") == "CLOSE_CALL":
        changes.append("An approved projection action threshold; without one, no projected edge authorizes a lineup change.")
    if "LEAGUE_SCORING_PARTIAL" in (comparison.get("blockers") or []) or "PARTIAL" in {current.get("scoring_completeness"), alternative.get("scoring_completeness")}:
        changes.append("Exact league scoring for the stat-line components the provider combines.")
    changes.append("A new provider projection board or late-week depth-chart news.")
    return {"why": list(dict.fromkeys(why))[:4], "what_could_change": list(dict.fromkeys(changes))[:4]}
