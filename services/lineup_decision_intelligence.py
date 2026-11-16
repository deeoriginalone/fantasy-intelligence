"""Starting Lineup Decision Intelligence for My Team (read-only decision support).

Selection uses only lineup-authorized evidence: league slot eligibility, availability
(health designation, bye week, and schedule-owned kickoff locks), and the repository Weekly
Score when it exists for every compared player. Kickoff locks come only from the automated
nflverse schedule; when a kickoff cannot be verified the player is LOCK_UNVERIFIED and no
START/SIT change involving him is recommended. This week's positional consensus rank is
displayed as context and orders same-position players only when a caller explicitly enables
``consensus_authority``; it is never converted to points, never compared across positions,
and never locks a player. League-scored provider projections (the JerryGM stat line rescored
with the league's Sleeper scoring settings) are PRELIMINARY comparisons that never select
players, raise decision confidence, or authorize a change without an approved action
threshold. No lineup is submitted.
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from services.game_lock import (
    LOCK_CONTRACT_ID, LOCK_RULE, SCHEDULE_SOURCE_PREFIX, VERIFIED_LOCK_STATES, age_label, kickoff_display, not_applicable_lock, unverified_lock, utc_datetime,
)
from services.jerrygm_projections import build_projection_edge
from services.lineup_evidence import build_matchup_evidence
from services.lineup_projection import (
    COMPARISON_BASIS,
    PROJECTION_SOURCE,
    best_projection_alternative,
    build_forward_validation_snapshots,
    build_player_projection,
    compare_projections,
    comparison_brief,
    evidence_agreement as projection_evidence_agreement,
    workload_summary,
)
from services.team_health import normalize_health
from services.weekly_lineup_intelligence import STARTER_SLOTS, confidence as evidence_completeness

SCHEMA_VERSION = "lineup-decision.v1"
VALUE_BASIS = "REPOSITORY_WEEKLY_SCORE"
VALUE_UNIT = "weekly value points"
VALUE_DEFINITION = "Repository Weekly Score: season projection / 17, adjusted by the matchup modifier and health multiplier."
SLOT_CODES = {
    "QB": ("QB", ("QB",)),
    "RB": ("RB", ("RB",)),
    "WR": ("WR", ("WR",)),
    "TE": ("TE", ("TE",)),
    "K": ("K", ("K",)),
    "DEF": ("DEF", ("DEF",)),
    "DST": ("DEF", ("DEF",)),
    "FLEX": ("FLEX", ("RB", "WR", "TE")),
    "W/R/T": ("FLEX", ("RB", "WR", "TE")),
    "WRRB_FLEX": ("W/R FLEX", ("RB", "WR")),
    "REC_FLEX": ("W/T FLEX", ("WR", "TE")),
    "SUPER_FLEX": ("SUPER FLEX", ("QB", "RB", "WR", "TE")),
}
FLEX_BASES = {"FLEX", "W/R FLEX", "W/T FLEX", "SUPER FLEX"}
SANDBOX_SLOT_SEQUENCE = tuple(name.rstrip("0123456789") for name, _ in STARTER_SLOTS)
NON_PLAYING_STATUSES = {"OUT", "IR", "INJURED RESERVE", "PUP", "SUS", "SUSPENDED", "NFI", "INACTIVE"}
UNKNOWN_STATUSES = {"", "UNKNOWN", "NOT AVAILABLE", "UNAVAILABLE", "NONE"}
VERIFIED_FRESHNESS = {"FRESH", "AGING"}
HEALTH_LABELS = {"HEALTHY": "Active", "QUESTIONABLE": "Questionable", "DOUBTFUL": "Doubtful", "OUT": "Out", "IR": "IR", "UNKNOWN": "Unknown", "NOT_APPLICABLE": "Not applicable"}
# Verified open decisions lead; a pinned slot whose kickoff cannot be verified is a check-in-Sleeper item after them.
ATTENTION_ORDER = {"BLOCKED": 0, "VACANT": 1, "REPLACEMENT_REQUIRED": 2, "SELECTION_UNRESOLVED": 3, "CHANGE": 4, "LOCK_UNVERIFIED": 5, "AVAILABILITY_WATCH": 6}
STATUS_LABELS = {
    "BLOCKED": "Blocked",
    "VACANT": "No eligible player",
    "REPLACEMENT_REQUIRED": "Replacement required",
    "SELECTION_UNRESOLVED": "Choose a starter",
    "CHANGE": "Supported change",
    "AVAILABILITY_WATCH": "Availability watch",
    "STABLE": "Stable",
    "UNRESOLVED": "No supported change",
    "NO_ALTERNATIVE": "No eligible alternative",
    "LOCKED": "Locked: game started",
    "LOCK_UNVERIFIED": "Kickoff lock unverified: changes withheld",
}
DRIVER_LABELS = {
    "ELIGIBILITY_DRIVEN": "Eligibility-driven",
    "HEALTH_DRIVEN": "Health-driven",
    "PROJECTION_DRIVEN": "Projection-driven (weekly value)",
    "CONSENSUS_RANK_DRIVEN": "Consensus-rank-driven (same-position expert ordering)",
    "GAME_LOCKED": "Locked at kickoff",
    "LOCK_UNVERIFIED": "Kickoff lock unverified",
    "MATCHUP_SUPPORTED": "Matchup-supported",
    "OPPORTUNITY_SUPPORTED": "Opportunity-supported (informational)",
    "MULTI_FACTOR": "Multi-factor",
    "REDUCED_SCOPE": "Reduced scope: evidence incomplete",
}
PINNED_LOCK_STATES = ("LOCKED", "LOCK_UNVERIFIED")
NOT_COMPARABLE_REASONS = {"BYE", "HEALTH", "GAME_LOCKED", "IDENTITY_UNRESOLVED"}
LOCK_SUMMARY_CONTRACT_ID = "lineup.lock_summary.v1"
PRIMARY_LOCK_STATES = ("OPEN", "LOCKED", "LOCK_UNVERIFIED", "BYE")
LOCK_CHIP_LABELS = {"OPEN": "Open", "LOCKED": "Locked", "LOCK_UNVERIFIED": "Lock unverified", "BYE": "Bye", "NOT_APPLICABLE": "Lock n/a"}
WEEK_STATE_LABELS = {
    "PRE_KICKOFF": "Pre-kickoff", "IN_PROGRESS": "In progress", "MOSTLY_LOCKED": "Mostly locked", "COMPLETE": "Week complete",
    "LOCK_COVERAGE_INCOMPLETE": "Lock coverage incomplete", "NOT_APPLICABLE": "Not applicable",
}
WEEK_STATE_IMPACT = {
    "PRE_KICKOFF": "Every verified player can still be moved before his own kickoff.",
    "IN_PROGRESS": "Locked players stay where they are; open players can still change before their kickoffs.",
    "MOSTLY_LOCKED": "Locked players stay where they are; only players with later kickoffs can still change.",
    "COMPLETE": "No lineup change is possible: every lineup-relevant game has started.",
    "LOCK_COVERAGE_INCOMPLETE": "Players whose kickoff cannot be verified are never moved in or out; verified open players can still change.",
    "NOT_APPLICABLE": "Season Sandbox has no live kickoffs, so lock state does not apply.",
}
LOCK_REASON_TEXT = {
    "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED": "schedule freshness is not approved",
    "SCHEDULE_DATA_STALE": "the schedule is past its approved freshness limit",
    "SCHEDULE_SOURCE_TIMESTAMP_UNVERIFIED": "the schedule has no source timestamp",
    "SCHEDULE_UNAVAILABLE": "no schedule is loaded for this week",
    "SCHEDULE_GAME_NOT_FOUND": "no game was found for the player's team",
    "SCHEDULE_GAME_CONFLICT": "the schedule lists conflicting games for the player's team",
    "SCHEDULE_BYE_CONFLICT": "bye and schedule evidence disagree",
    "BYE_EVIDENCE_UNVERIFIED": "the bye is not from an approved source",
    "SCHEDULE_TEAM_UNRESOLVED": "the player's NFL team is missing",
    "SCHEDULE_TEAM_IDENTITY_MISMATCH": "the scheduled teams are unrecognized",
    "SCHEDULE_SOURCE_NOT_AUTOMATED": "the schedule is not from the automated source",
    "SCHEDULE_KICKOFF_UNAVAILABLE": "the kickoff time is missing",
    "SCHEDULE_WEEK_UNVERIFIED": "the NFL week is unverified",
    "SCHEDULE_LOCK_NOT_SUPPLIED": "no schedule evidence was supplied",
    "IDENTITY_UNRESOLVED": "the player's identity is unresolved",
}
OPEN_WINDOW_STATUSES = {"CHANGE", "REPLACEMENT_REQUIRED", "SELECTION_UNRESOLVED", "AVAILABILITY_WATCH", "STABLE", "UNRESOLVED"}
VALUE_BLOCKER_TEXT = {
    "PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE": "no automated weekly projection feed is connected",
    "WEEKLY_VALUE_UNAVAILABLE": "no weekly value was supplied",
    "LEAGUE_SCORING_NOT_FULL_PPR": "league reception scoring differs from the Full-PPR value basis",
    "LEAGUE_SCORING_UNVERIFIED": "league scoring settings are unverified",
}
PROVIDER_BLOCKER_TEXT = {
    "PROVIDER_PROJECTION_NOT_REQUESTED": "not requested for this page",
    "PROVIDER_PROJECTION_IDENTITY_UNAVAILABLE": "no exact Sleeper ID",
    "PROVIDER_SCORING_PRESET_UNSUPPORTED": "no provider preset matches league reception scoring",
    "PROVIDER_SCORING_UNVERIFIED": "league scoring settings are unverified",
    "PROVIDER_WEEK_UNVERIFIED": "the NFL week is unverified",
    "JERRYGM_CONFIGURATION_BLOCKED": "provider access is not configured",
    "JERRYGM_REFRESH_FAILED": "the provider request failed",
    "JERRYGM_PLAYER_NOT_RETURNED": "the provider returned no projection",
    "JERRYGM_FREE_ID_LIMIT_EXCEEDED": "the provider request limit was exceeded",
    "JERRYGM_ROSTER_IDENTITY_AMBIGUOUS": "the Sleeper ID is ambiguous on this roster",
}
CONSENSUS_SOURCE = "FantasyPros consensus via DynastyProcess"
CONSENSUS_BASIS = "WEEKLY_POSITIONAL_CONSENSUS_RANK"
CONSENSUS_UNIT = "consensus rank within position (lower is better)"
CONSENSUS_DEFINITION = ("This week's average expert rank within one position (FantasyPros PPR pages for RB, WR, and TE). "
                        "It orders players at the same position; it is not projected points and is never converted to points.")
CONSENSUS_REASONS = {
    "Game already started": ("CONSENSUS_RANK_GAME_STARTED", "game already started (lineup locked)"),
    "Source is stale or future-dated": ("CONSENSUS_RANK_STALE", "the published consensus is outside its freshness limit"),
    "Ranking belongs to another NFL week": ("CONSENSUS_RANK_WEEK_MISMATCH", "the published rank is for another NFL week"),
    "Season or NFL week is unverified": ("CONSENSUS_RANK_WEEK_UNVERIFIED", "the NFL week could not be verified"),
    "KICKOFF_UNAVAILABLE": ("CONSENSUS_RANK_KICKOFF_UNVERIFIED", "this week's kickoff could not be verified"),
    "KICKOFF_CURRENT_TEAM_NOT_SUPPLIED": ("CONSENSUS_RANK_KICKOFF_UNVERIFIED", "this week's kickoff could not be verified"),
    "POSITION_CONFLICT": ("CONSENSUS_RANK_POSITION_CONFLICT", "the ranked position conflicts with Sleeper"),
    "Consensus rank is invalid": ("CONSENSUS_RANK_INVALID", "the published rank is invalid"),
    "TEAM_DEFENSE_IDENTITY_UNVERIFIED": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "CONTEXTUAL_IDENTITY_AMBIGUOUS": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "PROVIDER_ID_ABSENT_FROM_CROSSWALK": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "SLEEPER_ID_MISSING": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "DUPLICATE_PROVIDER_ID": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "DUPLICATE_SLEEPER_ID": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
    "DUPLICATE_RANK_PLAYER_ID": ("CONSENSUS_RANK_IDENTITY_PENDING", "the ranking identity is not verified"),
}
NOT_PUBLISHED = ("CONSENSUS_RANK_NOT_PUBLISHED", "not in this week's published consensus")
FLOOR_CEILING = {
    "state": "UNSUPPORTED",
    "floor": None,
    "median": None,
    "ceiling": None,
    "volatility": None,
    "reason": "No validated weekly outcome-distribution contract exists. The repository Weekly Score and provider projectedPPG are point estimates, and ranges are never derived by scaling a projection.",
    "required_boundary": [
        "A per-player weekly outcome distribution (provider percentiles, or an in-repository model over published Full-PPR weekly production) keyed by exact player ID, season, and week, with source timestamps and freshness.",
        "A documented method with minimum-sample rules and league-scoring alignment.",
        "Backtest or calibration tests against completed weeks, plus Floor, Median, Ceiling, and Volatility entries in METRIC_DEFINITIONS before display.",
    ],
}


def _finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _position(row):
    return str((row or {}).get("position") or "").upper().replace("DST", "DEF")


def _name(view):
    return (view or {}).get("player") or "Unnamed player"


def _names(views):
    return ", ".join(_name(view) for view in views) or "none"


def _points(value):
    return f"{value:.2f}"


def build_slot_contract(league_settings: Mapping[str, Any] | None, *, mode: str) -> dict[str, Any]:
    """Expand league starter slots in lineup order with their configured eligibility."""
    settings = dict(league_settings or {})
    limitations = []
    if settings.get("state") == "AVAILABLE":
        sequence = [str(code).upper() for code in settings.get("starter_slot_sequence") or []]
        state, source = "AVAILABLE", settings.get("source") or "League settings"
        if not sequence:
            return {"state": "BLOCKED", "source": source, "blocker": "LEAGUE_STARTER_SLOTS_UNAVAILABLE", "slots": [], "limitations": []}
    elif mode == "MOCK":
        sequence = list(SANDBOX_SLOT_SEQUENCE)
        state, source = "SANDBOX_DEFAULT", "Season Sandbox default slots"
        limitations.append("Season Sandbox has no live league; the repository default starting slots are used.")
    else:
        return {"state": "BLOCKED", "source": settings.get("source"), "blocker": settings.get("blocker") or "LEAGUE_SETTINGS_UNAVAILABLE", "slots": [], "limitations": []}
    unsupported = sorted({code for code in sequence if code not in SLOT_CODES})
    if unsupported:
        return {"state": "BLOCKED", "source": source, "blocker": "LEAGUE_SLOT_TYPE_UNSUPPORTED", "unsupported_slot_codes": unsupported, "slots": [], "limitations": limitations}
    totals = Counter(SLOT_CODES[code][0] for code in sequence)
    seen = Counter()
    slots = []
    for index, code in enumerate(sequence):
        base, positions = SLOT_CODES[code]
        seen[base] += 1
        slots.append({
            "index": index,
            "slot": f"{base}{seen[base]}" if totals[base] > 1 else base,
            "code": "DEF" if code == "DST" else code,
            "eligible_positions": list(positions),
            "flex": base in FLEX_BASES,
        })
    return {"state": state, "source": source, "blocker": None, "slots": slots, "limitations": limitations}


def build_scoring_context(league_settings: Mapping[str, Any] | None, *, mode: str) -> dict[str, Any]:
    """Describe how league scoring constrains the value basis and provider projections."""
    settings = dict(league_settings or {})
    reception = _finite(settings.get("reception_points"))
    if mode == "MOCK" and settings.get("state") != "AVAILABLE":
        return {
            "state": "NOT_APPLICABLE", "source": "Season Sandbox", "scoring_format": None, "reception_points": None,
            "value_alignment": "SANDBOX", "provider_preset": None,
            "label": "Season Sandbox: no league scoring settings apply",
            "limitations": ["Sandbox weekly values come from the repository's Full-PPR season projections; no league scoring is applied."],
        }
    if settings.get("state") != "AVAILABLE" or settings.get("scoring_settings_state") != "AVAILABLE" or reception is None:
        return {
            "state": "UNAVAILABLE", "source": settings.get("source"), "scoring_format": None, "reception_points": None,
            "value_alignment": "UNVERIFIED", "provider_preset": None,
            "label": "Scoring format unavailable",
            "limitations": ["League scoring settings are unavailable; no scoring format is assumed, and weekly values are not used for selection."],
        }
    preset = {1.0: "ppr", 0.5: "half", 0.0: "standard"}.get(reception)
    limitations = ["Repository weekly values use Full-PPR season projections; custom league weights beyond reception value are not applied."]
    if preset:
        limitations.append(f"Provider projections use the '{preset}' preset; only the reception value is verified against league settings.")
    else:
        limitations.append("No provider preset matches league reception scoring, so provider projections are not requested.")
    return {
        "state": "AVAILABLE", "source": settings.get("source"), "scoring_format": settings.get("scoring_format"),
        "reception_points": reception, "value_alignment": "ALIGNED" if reception == 1.0 else "MISMATCH",
        "provider_preset": preset, "label": f"{settings.get('scoring_format')} ({reception:g} per reception)",
        "limitations": limitations,
    }


def _health(row, team_health):
    health = dict(team_health or {})
    freshness = str(health.get("freshness_state") or "UNAVAILABLE").upper()
    base = {"source": health.get("source") or "UNAVAILABLE", "freshness_state": freshness, "last_verified": health.get("last_verified")}
    raw = str(row.get("injury_status") or "").strip()
    if _position(row) == "DEF":
        return {**base, "status": raw or "Not applicable", "state": "NOT_APPLICABLE", "label": "Not applicable", "availability": "AVAILABLE", "verified": True, "impact": "Team defenses have no player injury designation."}
    upper = raw.upper()
    normalized = normalize_health(raw)
    team_verified = health.get("state") == "AVAILABLE" and freshness in VERIFIED_FRESHNESS
    if normalized in {"OUT", "IR"} or upper in NON_PLAYING_STATUSES or "RESERVE-RET" in upper:
        state = normalized or upper
        impact = "Excluded from the active lineup." if team_verified else "Excluded from the active lineup; the designation comes from unverified health evidence."
        return {**base, "status": raw, "state": state, "label": HEALTH_LABELS.get(state, raw.title()), "availability": "UNAVAILABLE", "verified": team_verified, "impact": impact}
    if row.get("health_status_available") is False or upper in UNKNOWN_STATUSES or normalized is None:
        return {**base, "status": raw or "Unknown", "state": "UNKNOWN", "label": "Unknown", "availability": "UNCERTAIN", "verified": False, "scope": "PLAYER",
                "impact": "Health status is unknown and is never treated as healthy; confirm before kickoff."}
    label = HEALTH_LABELS[normalized]
    if not team_verified:
        return {**base, "status": raw, "state": normalized, "label": label, "availability": "UNCERTAIN", "verified": False, "scope": "TEAM",
                "impact": f"Reported {label} status is not verified as current (health evidence {freshness}); confirm before kickoff."}
    if normalized in {"QUESTIONABLE", "DOUBTFUL"}:
        return {**base, "status": raw, "state": normalized, "label": label, "availability": "UNCERTAIN", "verified": True, "scope": "PLAYER",
                "impact": f"{label}: game-day availability is uncertain; check the official inactive list before kickoff."}
    return {**base, "status": raw, "state": "HEALTHY", "label": label, "availability": "AVAILABLE", "verified": True, "impact": "Available."}


def _value(row, *, value_alignment, mode):
    score = _finite(row.get("weekly_score"))
    evidence = row.get("weekly_evidence") or {}
    detail = {
        "basis": VALUE_BASIS, "unit": VALUE_UNIT,
        "baseline": _finite(row.get("weekly_baseline")),
        "matchup_modifier": _finite(row.get("matchup_modifier")),
        "injury_multiplier": _finite(row.get("injury_multiplier")),
        "source": "Automated weekly evidence" if evidence else "Season Sandbox local weekly value" if mode == "MOCK" else "Supplied weekly value",
        "freshness_state": str((evidence.get("projection") or {}).get("freshness_state") or "UNAVAILABLE").upper(),
    }
    if score is None:
        blocker = (evidence.get("projection") or {}).get("blocker") or "WEEKLY_VALUE_UNAVAILABLE"
        return {**detail, "state": "UNAVAILABLE", "value": None, "evidence_level": "INSUFFICIENT", "blocker": blocker}
    if value_alignment in {"MISMATCH", "UNVERIFIED"}:
        blocker = "LEAGUE_SCORING_NOT_FULL_PPR" if value_alignment == "MISMATCH" else "LEAGUE_SCORING_UNVERIFIED"
        return {**detail, "state": "BLOCKED", "value": None, "evidence_level": "INSUFFICIENT", "blocker": blocker}
    return {**detail, "state": "AVAILABLE", "value": score, "evidence_level": "PRELIMINARY", "blocker": None}


def _provider(row, provider_projections):
    payload = provider_projections or {}
    player_id = str(row.get("source_player_id") or "").strip()
    evidence = (payload.get("players") or {}).get(player_id) if player_id else None
    if not evidence:
        if not payload:
            blocker = "PROVIDER_PROJECTION_NOT_REQUESTED"
        elif not player_id:
            blocker = "PROVIDER_PROJECTION_IDENTITY_UNAVAILABLE"
        else:
            blocker = (payload.get("blockers") or ["PROVIDER_PROJECTION_NOT_REQUESTED"])[0]
        return {"state": "UNAVAILABLE", "projected_ppg": None, "evidence": None, "blocker": blocker,
                "reason": PROVIDER_BLOCKER_TEXT.get(blocker, "provider projection unavailable"), "recommendation_impact": "INFORMATIONAL_ONLY"}
    value = _finite(evidence.get("projected_ppg"))
    blocker = (evidence.get("blockers") or [None])[0]
    return {
        "state": evidence.get("state") or "UNAVAILABLE", "projected_ppg": value, "evidence": evidence,
        "evidence_level": evidence.get("evidence_level"), "freshness_state": evidence.get("freshness_state") or "UNAVAILABLE",
        "scoring_format": evidence.get("scoring_format"), "metric_name": evidence.get("metric_name"), "source": evidence.get("source"),
        "season": evidence.get("season"), "week": evidence.get("week"), "data_through_week": evidence.get("data_through_week"),
        "source_record_time": evidence.get("source_record_time"), "retrieved_at": evidence.get("retrieved_at"), "age_seconds": evidence.get("age_seconds"),
        "attribution": evidence.get("attribution"), "limitations": list(evidence.get("limitations") or []),
        "blocker": blocker if value is None else None,
        "reason": PROVIDER_BLOCKER_TEXT.get(blocker, "provider projection unavailable") if value is None else None,
        "recommendation_impact": "INFORMATIONAL_ONLY",
    }


def _matchup(row, *, season, week):
    evidence = (row.get("weekly_evidence") or {}).get("matchup") or (row.get("lineup_evidence") or {}).get("matchup")
    if not evidence:
        evidence = build_matchup_evidence(row, season=season, week=week)
    level = evidence.get("evidence_level") or "INSUFFICIENT"
    rank_applicable = _position(row) not in {"K", "DEF"}
    authoritative = bool(evidence.get("authoritative"))
    signal = evidence.get("matchup_signal") if level in {"PRELIMINARY", "ESTABLISHED"} else None
    rank = evidence.get("value") if authoritative and rank_applicable else None
    population_size = evidence.get("comparison_population_size")
    direction = "rank 1 is hardest" if evidence.get("rank_directionality") == "LOWER_IS_HARDER" else None
    if authoritative:
        state = "ESTABLISHED"
        if rank is not None:
            label = f"{signal or 'Matchup rank'}: rank {rank} of {population_size or 'the documented population'}" + (f" ({direction})" if direction else "")
        else:
            label = "Matchup evidence supported; matchup rank not applicable for this position"
    elif signal:
        state = "PRELIMINARY"
        label = f"Preliminary signal: {signal} (context only, not an authoritative rank)"
    else:
        state = "UNAVAILABLE"
        label = "Matchup evidence unavailable; not treated as favorable, difficult, or neutral"
    easiest = None
    if signal:
        try:
            easiest = int(population_size) - int(evidence.get("value")) + 1
        except (TypeError, ValueError):
            easiest = None
    return {
        "state": state, "opponent": row.get("opponent"), "rank": rank, "rank_applicable": rank_applicable,
        "rank_authoritative": authoritative and rank is not None, "signal": signal, "easiest_rank": easiest,
        "population_size": population_size, "directionality": evidence.get("rank_directionality"),
        "sample_games": evidence.get("sample_size"), "freshness_state": evidence.get("freshness_state") or "UNAVAILABLE",
        "source": evidence.get("source"), "blockers": list(evidence.get("blockers") or []), "label": label,
        "recommendation_impact": "CONTEXT_ONLY" if state != "UNAVAILABLE" else "NONE",
    }


def _opportunity(entry):
    if not entry:
        return {"state": "UNAVAILABLE", "label": "Opportunity evidence unavailable", "reason": "No opportunity evidence was supplied for this player.",
                "workload": workload_summary(None), "decision_effect": "INFORMATIONAL_ONLY"}
    workload = workload_summary(entry.get("recent_workload"))
    if entry.get("state") != "AVAILABLE":
        blockers = list(entry.get("blockers") or [])
        reason = ("Opportunity identity is unresolved." if "OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE" in blockers
                  else "No current published usage rows." if "OPPORTUNITY_READER_NO_ROWS" in blockers
                  else "Opportunity evidence is unavailable.")
        return {"state": entry.get("state") or "UNAVAILABLE", "label": "Opportunity evidence unavailable", "reason": reason, "blockers": blockers,
                "workload": workload, "decision_effect": "INFORMATIONAL_ONLY"}
    strength = (entry.get("opportunity_strength") or {}).get("state") or "UNAVAILABLE"
    trend = entry.get("opportunity_trend") or {}
    words = {"HIGH_OPPORTUNITY": "High opportunity", "MODERATE_OPPORTUNITY": "Moderate opportunity", "LIMITED_OPPORTUNITY": "Limited opportunity"}
    label = words.get(strength, "Opportunity strength unavailable")
    if trend.get("state") in {"IMPROVING", "DECLINING", "STABLE"}:
        label += f"; usage {trend['state'].lower()}"
    return {"state": "AVAILABLE", "strength": strength, "trend": trend.get("state") or "INSUFFICIENT_EVIDENCE", "drivers": list(trend.get("drivers") or []), "label": label,
            "workload": workload, "decision_effect": "INFORMATIONAL_ONLY"}


def _projection_confidence(value, provider):
    """Reliability of a player's projected output; never inferred from a projection merely existing."""
    if value["state"] != "AVAILABLE" and provider.get("projected_ppg") is None:
        return {"state": "UNAVAILABLE", "reason_code": "PROJECTION_UNAVAILABLE", "reason": "No projection is available for this player."}
    gaps = []
    if value["state"] == "AVAILABLE":
        gaps.append("the repository Weekly Score is preliminary (no authoritative metric definition)")
    if provider.get("projected_ppg") is not None and provider.get("freshness_state") not in VERIFIED_FRESHNESS:
        gaps.append("the provider freshness threshold is unverified")
    model = "No validated projection-accuracy model exists, so reliability is not rated."
    if gaps:
        return {"state": "INSUFFICIENT_EVIDENCE", "reason_code": "PROJECTION_EVIDENCE_INCOMPLETE", "reason": f"Projection evidence is incomplete: {'; '.join(gaps)}. {model}"}
    return {"state": "UNAVAILABLE", "reason_code": "PROJECTION_ACCURACY_MODEL_UNAVAILABLE", "reason": model}


def _utc_time(value):
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _consensus_reasons(consensus):
    """Map Sleeper IDs to the published reason their weekly consensus row was withheld."""
    horizon = ((consensus or {}).get("horizons") or {}).get("this_week") or {}
    reasons = {}
    for item in horizon.get("diagnostics") or []:
        ids = {str(match.get("sleeper_id")) for match in item.get("crosswalk_matches") or [] if match.get("sleeper_id") not in (None, "", "NA")}
        if item.get("player_id"):
            ids.add(str(item["player_id"]))
        if item.get("page") == "dst":
            team = str(item.get("team") or "").upper().strip()
            ids.add({"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}.get(team, team))
        for player_id in ids - {""}:
            reasons.setdefault(player_id, item.get("reason"))
    return reasons


def _consensus_rank(player_id, position, *, consensus, reasons, season, week, alignment, now):
    """Validate one player's current-week consensus rank; anything unproven is unranked, never worse or zero."""
    if not consensus:
        return {"state": "NOT_REQUESTED", "ecr": None, "label": None, "blocker": "CONSENSUS_RANK_NOT_REQUESTED", "reason": "not requested", "recommendation_impact": "NONE"}
    horizon = (consensus.get("horizons") or {}).get("this_week") or {}
    base = {"source": consensus.get("source") or CONSENSUS_SOURCE, "retrieved_at": consensus.get("last_successful_refresh"),
            "max_age_seconds": horizon.get("max_age_seconds"), "ecr": None, "label": None, "evidence_level": "INSUFFICIENT", "recommendation_impact": "NONE"}

    def withheld(code, reason, state="UNAVAILABLE"):
        return {**base, "state": state, "blocker": code, "reason": reason}

    if alignment == "MISMATCH":
        return withheld("CONSENSUS_RANK_SCORING_MISMATCH", "league reception scoring differs from the PPR consensus", "BLOCKED")
    if alignment != "ALIGNED":
        return withheld("CONSENSUS_RANK_SCORING_UNVERIFIED", "league scoring is not verified as Full-PPR")
    if season is None or week is None:
        return withheld("CONSENSUS_RANK_WEEK_UNVERIFIED", "the NFL week is unverified")
    if not player_id:
        return withheld("CONSENSUS_RANK_IDENTITY_UNAVAILABLE", "no exact Sleeper ID")
    row = (horizon.get("ranks") or {}).get(str(player_id)) if horizon.get("state") == "AVAILABLE" else None
    if not row:
        if str(player_id) in reasons:
            return withheld(*CONSENSUS_REASONS.get(reasons[str(player_id)], NOT_PUBLISHED))
        if horizon.get("state") != "AVAILABLE":
            return withheld("CONSENSUS_RANK_UNAVAILABLE", "this week's consensus is unavailable")
        return withheld(*NOT_PUBLISHED)
    try:
        same_week = row.get("horizon") == "this_week" and int(row.get("season")) == int(season) and int(row.get("week")) == int(week)
    except (TypeError, ValueError):
        same_week = False
    if not same_week:
        return withheld("CONSENSUS_RANK_WEEK_MISMATCH", "the rank is not for this NFL week", "BLOCKED")
    if str(row.get("scoring") or "").upper() != "PPR":
        return withheld("CONSENSUS_RANK_SCORING_MISMATCH", "the rank is not from the PPR consensus", "BLOCKED")
    if _position(row) != position:
        return withheld("CONSENSUS_RANK_POSITION_CONFLICT", "the ranked position conflicts with the roster position", "BLOCKED")
    ecr = _finite(row.get("ecr"))
    if ecr is None or ecr <= 0:
        return withheld("CONSENSUS_RANK_INVALID", "the published rank is invalid")
    published = _utc_time(row.get("source_date"))
    if published is None:
        return withheld("CONSENSUS_RANK_TIMESTAMP_UNAVAILABLE", "the publication date is missing")
    max_age = _finite(horizon.get("max_age_seconds"))
    if max_age is None or max_age <= 0:
        return withheld("CONSENSUS_RANK_FRESHNESS_UNVERIFIED", "no freshness limit was supplied")
    age = (now - published).total_seconds()
    if age < 0 or age > max_age:
        return withheld("CONSENSUS_RANK_STALE", f"the published consensus is outside its {max_age / 3600:g}-hour limit")
    kickoff = _utc_time((row.get("game_evidence") or {}).get("kickoff"))
    if kickoff is not None and kickoff <= now:
        return withheld(*CONSENSUS_REASONS["Game already started"])
    return {
        **base, "state": "AVAILABLE", "ecr": ecr, "position": position, "label": f"{position} {ecr:g}",
        "source_date": row.get("source_date"), "age_seconds": int(age), "freshness_state": "FRESH",
        "identity_method": row.get("identity_method"), "evidence_level": "PRELIMINARY",
        "recommendation_impact": "SAME_POSITION_ORDERING", "blocker": None, "reason": None,
    }


def _rank_of(view):
    rank = (view or {}).get("consensus_rank") or {}
    return rank.get("ecr") if rank.get("state") == "AVAILABLE" else None


def _locked(view):
    """Schedule-owned lock: the player's game has kicked off (consensus publication never locks a player)."""
    return ((view or {}).get("lock") or {}).get("state") == "LOCKED"


def _lock_unverified(view):
    return ((view or {}).get("lock") or {}).get("state") == "LOCK_UNVERIFIED"


def _lock_reason(views):
    return next((view["lock"].get("reason") for view in views if view is not None and (view.get("lock") or {}).get("reason")), None) or "no schedule-owned kickoff evidence"


def _player_lock(raw_id, *, mode, game_locks, season, week):
    if mode == "MOCK":
        return not_applicable_lock(season=season, week=week)
    lock = ((game_locks or {}).get("players") or {}).get(raw_id) if raw_id else None
    if lock:
        return dict(lock)
    return unverified_lock("SCHEDULE_LOCK_NOT_SUPPLIED", "No schedule-owned kickoff evidence was supplied for this player, so his lock state cannot be verified.",
                           season=season, week=week)


def _rank_gap(view, rec):
    """Why an alternative cannot be compared with the recommended player by consensus rank."""
    if view["position"] != rec["position"]:
        return "different position"
    if _value_of(view) is not None:
        return "has a weekly value; ranks and values are not mixed"
    return view["consensus_rank"].get("reason") or "no current-week consensus rank"


def _player_views(roster, *, mode, team_health, value_alignment, provider_projections, opportunity, season, week, consensus=None, consensus_reasons=None, now=None,
                  game_locks=None, scoring_settings=None, consensus_authority=False):
    opportunity_by_id = {
        str(entry.get("source_player_id")): entry
        for entry in ((opportunity or {}).get("players") or [])
        if entry.get("source_player_id") is not None
    }
    raw_ids = [str(row.get("source_player_id") or row.get("local_player_id") or "").strip() for row in roster or []]
    duplicate_ids = {player_id for player_id, count in Counter(raw_ids).items() if player_id and count > 1}
    views = []
    for row_index, (row, raw_id) in enumerate(zip(roster or [], raw_ids)):
        if raw_id and raw_id not in duplicate_ids:
            player_id, identity_state = raw_id, "RESOLVED"
        elif raw_id:
            player_id, identity_state = None, "AMBIGUOUS"
        elif mode == "MOCK" and row.get("player"):
            player_id, identity_state = f"sandbox:{row['player']}", "SANDBOX_NAME"
        else:
            player_id, identity_state = None, "UNRESOLVED"
        health = _health(row, team_health)
        value = _value(row, value_alignment=value_alignment, mode=mode)
        provider = _provider(row, provider_projections)
        consensus_rank = _consensus_rank(player_id if identity_state == "RESOLVED" else None, _position(row), consensus=consensus, reasons=consensus_reasons or {},
                                         season=season, week=week, alignment=value_alignment, now=now or datetime.now(timezone.utc))
        if not consensus_authority and consensus_rank.get("state") == "AVAILABLE":
            consensus_rank["recommendation_impact"] = "DISPLAY_ONLY"
        lock = _player_lock(raw_id if identity_state == "RESOLVED" else None, mode=mode, game_locks=game_locks, season=season, week=week)
        current_index = row.get("sleeper_lineup_index") if row.get("sleeper_current_starter") else None
        on_bye = bool(row.get("is_bye")) or lock["state"] == "BYE"
        if player_id is None:
            availability, reason, scope = "UNAVAILABLE", "IDENTITY_UNRESOLVED", "PLAYER"
        elif on_bye:
            availability, reason, scope = "UNAVAILABLE", "BYE", "PLAYER"
        elif health["availability"] == "UNAVAILABLE":
            availability, reason, scope = "UNAVAILABLE", "HEALTH", "PLAYER"
        elif lock["state"] == "LOCKED" and current_index is None:
            # Sleeper locks players at kickoff, so a benched player whose game has started cannot enter the lineup.
            availability, reason, scope = "UNAVAILABLE", "GAME_LOCKED", "PLAYER"
        elif lock["state"] == "LOCK_UNVERIFIED" and current_index is None:
            # Fail closed: a benched player whose kickoff cannot be verified may already be locked, so he cannot be recommended in.
            availability, reason, scope = "UNAVAILABLE", "LOCK_UNVERIFIED", "PLAYER"
        elif health["availability"] == "UNCERTAIN":
            availability, reason, scope = "UNCERTAIN", "HEALTH", health.get("scope") or "PLAYER"
        elif not row.get("opponent"):
            availability, reason, scope = "UNCERTAIN", "SCHEDULE_UNVERIFIED", "TEAM" if week is None else "PLAYER"
        else:
            availability, reason, scope = "AVAILABLE", None, None
        projection = build_player_projection(provider.get("evidence"), position=_position(row), scoring_settings=scoring_settings, season=season, week=week,
                                             lock=lock, sleeper_team=row.get("nfl_team"), sleeper_health=health, known_gsis_id=row.get("sleeper_gsis_id"),
                                             unavailable_blocker=provider.get("blocker"))
        views.append({
            "row_index": row_index,
            "lock_key": raw_id or f"row:{row_index}",
            "player": row.get("player") or "Unnamed player",
            "player_id": player_id,
            "identity_state": identity_state,
            "position": _position(row),
            "nfl_team": row.get("nfl_team"),
            "opponent": row.get("opponent"),
            "home_away": row.get("home_away"),
            "game_time": row.get("game_time_pacific"),
            "is_bye": on_bye,
            "availability": availability,
            "availability_reason": reason,
            "availability_scope": scope,
            "health": health,
            "value": value,
            "provider_projection": provider,
            "projection": projection,
            "lock": lock,
            "consensus_rank": consensus_rank,
            "matchup": _matchup(row, season=season, week=week),
            "opportunity": _opportunity(opportunity_by_id.get(str(row.get("source_player_id")))),
            "projection_confidence": _projection_confidence(value, provider),
            "is_current_starter": current_index is not None,
            "current_index": current_index if isinstance(current_index, int) and not isinstance(current_index, bool) else None,
            "current_code": str(row.get("sleeper_lineup_slot") or "").upper().replace("DST", "DEF") or None,
        })
    return views


def _plural(count, singular, plural=None):
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def _lock_reason_text(view):
    if view["identity_state"] not in {"RESOLVED", "SANDBOX_NAME"}:
        return LOCK_REASON_TEXT["IDENTITY_UNRESOLVED"]
    return LOCK_REASON_TEXT.get((view.get("lock") or {}).get("blocker"), "kickoff evidence is unavailable")


def _attach_lock_status(views, slots):
    """Per-player lock presentation: one primary state, the game, a concise reason, and the recommendation impact."""
    slot_labels = {slot["index"]: slot["slot"] for slot in slots}
    for view in views:
        lock = view.get("lock") or {}
        state = lock.get("state") if lock.get("state") in LOCK_CHIP_LABELS else "LOCK_UNVERIFIED"
        starter = bool(view["is_current_starter"])
        unable = view["availability"] == "UNAVAILABLE" and view["availability_reason"] in {"HEALTH", "BYE"}
        slot_eligible = not slots or any(_eligible(view, slot) for slot in slots)
        context = lock.get("display_context") or {}
        opponent, venue = lock.get("opponent") or view.get("opponent"), lock.get("venue") or view.get("home_away")
        game_text = "BYE" if state == "BYE" else f"{'@' if venue == 'AWAY' else 'vs'} {opponent}" if opponent else None
        if state in {"OPEN", "LOCKED"} and lock.get("kickoff_display"):
            kickoff_text = f"Kickoff {lock['kickoff_display']}"
        elif state == "BYE":
            kickoff_text = "No game this week"
        elif state == "NOT_APPLICABLE":
            kickoff_text = "No live kickoff (Season Sandbox)"
        elif context.get("kickoff_display"):
            kickoff_text = f"Stored kickoff {context['kickoff_display']} (unverified; {context['label'].lower()})"
        else:
            kickoff_text = "Kickoff unverified"
        out = _unavailable_reason(view)
        if state == "OPEN":
            reason = "His game has not started."
            if starter:
                impact = (f"Listed {view['health']['label']}: replace him before kickoff." if view["availability"] == "UNAVAILABLE"
                          else "Can still change before kickoff; confirm his status." if view["availability"] == "UNCERTAIN" else "Can still change before kickoff.")
            else:
                impact = (f"Cannot help this week ({out})." if unable else "No starting slot accepts his position." if not slot_eligible
                          else "Can still enter your lineup before kickoff.")
        elif state == "LOCKED":
            reason = "His game has started."
            if starter:
                impact = (f"Locked in your lineup while {out}; no replacement is possible after kickoff." if view["availability"] == "UNAVAILABLE"
                          else "Locked in your lineup; no change is possible.")
            else:
                impact = "Locked on your bench; cannot enter your lineup."
        elif state == "BYE":
            reason = "His team is on bye."
            impact = "Cannot score this week; move him out of your lineup." if starter else "Cannot score this week; never recommended in."
        elif state == "NOT_APPLICABLE":
            reason, impact = "Season Sandbox has no live kickoff.", "Lock state does not apply."
        else:
            text = _lock_reason_text(view)
            reason = text[:1].upper() + text[1:] + "."
            impact = ("Kept in your lineup until his kickoff can be verified." if starter
                      else f"Cannot help this week ({out}); his lock state does not affect your lineup." if unable
                      else "Not recommended into your lineup until his kickoff can be verified.")
        view["lock_status"] = {
            "state": state, "label": LOCK_CHIP_LABELS[state], "role": "STARTER" if starter else "BENCH",
            "slot": slot_labels.get(view["current_index"]) if starter else None, "game_text": game_text, "kickoff_text": kickoff_text,
            "kickoff_utc": lock.get("kickoff_utc") if state in {"OPEN", "LOCKED"} else None,
            "kickoff_display": lock.get("kickoff_display") if state in {"OPEN", "LOCKED"} else None,
            "context_label": context.get("label"), "reason": reason, "impact": impact,
            # A lineup-relevant player could change the lineup: any current starter, or a bench player able to play who fits a starting slot.
            "lineup_relevant": starter or (not unable and slot_eligible), "decision_authority": bool(lock.get("decision_authority")),
        }
    return views


def _current_lineup(views, slots):
    starters = [view for view in views if view["is_current_starter"]]

    def result(state, blocker, by_index=None):
        by_index = by_index or {}
        rows = [{"slot": slots[index]["slot"], "player": _name(view), "player_id": view["player_id"], "position": view["position"], "injury_status": view["health"]["status"]}
                for index, view in sorted(by_index.items())]
        empty = [slot["slot"] for slot in slots if slot["index"] not in by_index] if by_index else []
        return {"state": state, "blocker": blocker, "slots": rows, "by_index": by_index, "empty_slots": empty}

    if not starters:
        return result("UNAVAILABLE", "CURRENT_LINEUP_UNAVAILABLE")
    if not slots:
        return result("UNAVAILABLE", "LEAGUE_SLOTS_UNAVAILABLE")
    by_index = {}
    for view in starters:
        index = view["current_index"]
        if view["player_id"] is None:
            return result("BLOCKED", "CURRENT_LINEUP_IDENTITY_UNAVAILABLE")
        if index is None or not 0 <= index < len(slots) or index in by_index:
            return result("BLOCKED", "CURRENT_LINEUP_SLOT_CONTRADICTORY")
        slot = slots[index]
        if (view["current_code"] and view["current_code"] != slot["code"]) or view["position"] not in slot["eligible_positions"]:
            return result("BLOCKED", "CURRENT_LINEUP_SLOT_CONTRADICTORY")
        by_index[index] = view
    return result("AVAILABLE" if len(by_index) == len(slots) else "INCOMPLETE", None, by_index)


def _eligible(view, slot):
    return view["position"] in slot["eligible_positions"]


def _matchable(views, slots):
    """True when every view can occupy a distinct slot (augmenting-path bipartite matching)."""
    owner = {}

    def place(view, seen):
        for slot in slots:
            if slot["index"] in seen or not _eligible(view, slot):
                continue
            seen.add(slot["index"])
            if slot["index"] not in owner or place(owner[slot["index"]], seen):
                owner[slot["index"]] = view
                return True
        return False

    return all(place(view, set()) for view in views)


def _max_matching_size(views, slots):
    """Largest number of views that can occupy distinct slots."""
    owner = {}

    def place(view, seen):
        for slot in slots:
            if slot["index"] in seen or not _eligible(view, slot):
                continue
            seen.add(slot["index"])
            if slot["index"] not in owner or place(owner[slot["index"]], seen):
                owner[slot["index"]] = view
                return True
        return False

    return sum(1 for view in views if place(view, set()))


def _assign(selected, slots, preferred_index):
    """Assign selected players to slots, keeping as many players as possible in their current slot."""
    order = sorted(selected, key=lambda view: (sum(_eligible(view, slot) for slot in slots), view["player_id"]))
    best = {"kept": -1, "assignment": None}

    def search(position, used, assignment, kept):
        if kept + (len(order) - position) <= best["kept"]:
            return
        if position == len(order):
            best.update(kept=kept, assignment=dict(assignment))
            return
        view = order[position]
        options = [slot for slot in slots if slot["index"] not in used and _eligible(view, slot)]
        options.sort(key=lambda slot: (slot["index"] != preferred_index.get(view["player_id"]), slot["index"]))
        for slot in options:
            used.add(slot["index"])
            assignment[slot["index"]] = view
            search(position + 1, used, assignment, kept + (slot["index"] == preferred_index.get(view["player_id"])))
            used.discard(slot["index"])
            del assignment[slot["index"]]

    search(0, set(), {}, 0)
    return best["assignment"] or {}


def _slot_options(slot, assignment, pool, slots):
    """Bench options for an open slot: eligible players, plus players who fit after one starter moves into it."""
    options, via = [], {}
    for view in pool:
        if _eligible(view, slot):
            options.append(view)
            continue
        hop = next((other for other in slots if other["index"] in assignment and _eligible(view, other) and _eligible(assignment[other["index"]], slot)), None)
        if hop is not None:
            options.append(view)
            via[view["player_id"]] = f"if {_name(assignment[hop['index']])} moves from {hop['slot']} to {slot['slot']}"
    return options, via


def optimize_lineup_assignment(slots: Sequence[Mapping[str, Any]], views: Sequence[Mapping[str, Any]], current_by_index: Mapping[int, Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """Choose the highest supported lineup without treating missing value as zero.

    Available current starters without a supported value stay in the lineup because no
    evidence can show an alternative is better; they may change slots only when that lets
    another slot be filled. Players with supported values are added by descending value
    while the whole group remains legally assignable (exact here because a player's value
    does not depend on the slot). A bench player fills a remaining slot only when every
    maximum legal lineup needs them; other open slots stay unresolved for the manager.
    """
    slot_by_index = {slot["index"]: slot for slot in slots}
    usable = [view for view in views if view["availability"] != "UNAVAILABLE" and view["player_id"] is not None]
    kept = [view for index, view in sorted(current_by_index.items())
            if index in slot_by_index and view["availability"] != "UNAVAILABLE" and view["value"]["state"] != "AVAILABLE" and _eligible(view, slot_by_index[index])]
    kept_ids = {view["player_id"] for view in kept}
    pool = sorted((view for view in usable if view["player_id"] not in kept_ids and view["value"]["state"] == "AVAILABLE"),
                  key=lambda view: (-view["value"]["value"], not view["is_current_starter"], view["player_id"]))
    selected = list(kept)
    for view in pool:
        if _matchable([*selected, view], slots):
            selected.append(view)
    selected_ids = {view["player_id"] for view in selected}
    leftovers = sorted((view for view in usable if view["player_id"] not in selected_ids), key=lambda view: (_name(view), view["player_id"]))
    candidates = [view for view in leftovers if _matchable([*selected, view], slots)]
    target = _max_matching_size([*selected, *candidates], slots)
    # Matroid rank test: a candidate is forced when every maximum lineup includes them.
    forced = [view for view in candidates if _max_matching_size([*selected, *(other for other in candidates if other is not view)], slots) < target]
    forced_ids = {view["player_id"] for view in forced}
    filled = [*selected, *forced]
    needed = target - len(filled)
    choices = [view for view in candidates if view["player_id"] not in forced_ids and _matchable([*filled, view], slots)] if needed else []
    preferred = {view["player_id"]: view["current_index"] for view in usable if view["current_index"] is not None}
    assignment = _assign(filled, slots, preferred)
    if needed and _max_matching_size(choices, [slot for slot in slots if slot["index"] not in assignment]) < needed:
        # Filling requires moving starters: arrange around a deterministic extension, then leave its slots open.
        extension = []
        for view in choices:
            if len(extension) < needed and _matchable([*filled, *extension, view], slots):
                extension.append(view)
        extension_ids = {view["player_id"] for view in extension}
        assignment = {index: view for index, view in _assign([*filled, *extension], slots, preferred).items() if view["player_id"] not in extension_ids}
    entries = {}
    for index, view in assignment.items():
        basis = "CURRENT_KEPT" if view["player_id"] in kept_ids else "ONLY_ELIGIBLE_OPTION" if view["player_id"] in forced_ids else "SUPPORTED_VALUE"
        entries[index] = {"view": view, "basis": basis, "candidates": [view] if basis == "ONLY_ELIGIBLE_OPTION" else [], "via": {}}
    for slot in slots:
        if slot["index"] in entries:
            continue
        options, via = _slot_options(slot, assignment, choices, slots)
        entries[slot["index"]] = {"view": None, "basis": "UNRESOLVED" if options else "VACANT", "candidates": options, "via": via}
    return entries


def apply_consensus_ranks(slots: Sequence[Mapping[str, Any]], entries: dict[int, dict[str, Any]], views: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """Second evidence tier for starters without a supported weekly value.

    Within one position, a bench player with a strictly better current-week consensus rank
    replaces a kept, ranked starter (same position, so slot legality is unchanged); when tied
    bench players compete for the last place, that slot is left for the manager. Open slots are
    then re-evaluated against the updated lineup and bench, and filled only when every option
    plays one position, all are ranked, and the best rank is unique. Players with a weekly
    value, unranked players, locked players, and different positions are never compared by rank.
    """
    def rankable(view):
        return _rank_of(view) is not None and _value_of(view) is None

    entries = {index: dict(entry) for index, entry in entries.items()}
    lineup_ids = {entry["view"]["player_id"] for entry in entries.values() if entry["view"] is not None}
    bench = [view for view in views if view["availability"] != "UNAVAILABLE" and view["player_id"] is not None and view["player_id"] not in lineup_ids]
    for position in sorted({view["position"] for view in views}):
        kept = sorted(((index, entry["view"]) for index, entry in entries.items()
                       if entry["basis"] == "CURRENT_KEPT" and entry["view"]["position"] == position and rankable(entry["view"])), key=lambda item: item[0])
        options = [view for view in bench if view["position"] == position and rankable(view)]
        if not kept or not options:
            continue
        kept_ids = {view["player_id"] for _, view in kept}
        ordered = sorted([view for _, view in kept] + options, key=lambda view: (_rank_of(view), view["player_id"] not in kept_ids, view["player_id"]))
        top, rest = ordered[:len(kept)], ordered[len(kept):]
        cut = _rank_of(top[-1])
        tied_out = [view for view in rest if _rank_of(view) == cut and view["player_id"] not in kept_ids]
        incoming = [view for view in top if view["player_id"] not in kept_ids]
        settled = [view for view in incoming if not (tied_out and _rank_of(view) == cut)]
        tied_in = len(incoming) - len(settled)
        top_ids = {view["player_id"] for view in top}
        outgoing = [(index, view) for index, view in kept if view["player_id"] not in top_ids]
        for (index, _), view in zip(outgoing, [*settled, *([None] * tied_in)]):
            entries[index] = {"view": view, "basis": "SUPPORTED_RANK" if view is not None else "UNRESOLVED", "candidates": [], "via": {}}
        settled_ids = {view["player_id"] for view in settled}
        bench = [view for view in bench if view["player_id"] not in settled_ids] + [view for _, view in outgoing]
    assignment = {index: entry["view"] for index, entry in entries.items() if entry["view"] is not None and entry["basis"] not in PINNED_LOCK_STATES}

    def evaluate_open(slot):
        options, via = _slot_options(slot, assignment, sorted(bench, key=lambda view: (_name(view), view["player_id"])), slots)
        direct = sorted((view for view in options if view["player_id"] not in via), key=lambda view: (_rank_of(view) is None, _rank_of(view) or 0, view["player_id"]))
        if not via and len(direct) == 1:
            return direct[0], "ONLY_ELIGIBLE_OPTION", direct, {}, False
        if not via and direct and len({view["position"] for view in direct}) == 1 and all(rankable(view) for view in direct):
            best = [view for view in direct if _rank_of(view) == _rank_of(direct[0])]
            return (direct[0], "SUPPORTED_RANK", direct, {}, False) if len(best) == 1 else (None, "UNRESOLVED", best, {}, True)
        return None, "UNRESOLVED" if options else "VACANT", options, via, False

    def open_slots():
        return [slot for slot in slots if entries[slot["index"]]["view"] is None and entries[slot["index"]]["basis"] == "UNRESOLVED"]

    filled = True
    while filled:
        filled = False
        for slot in open_slots():
            pick, basis, candidates, via, tie = evaluate_open(slot)
            if pick is not None:
                entries[slot["index"]] = {"view": pick, "basis": basis, "candidates": candidates, "via": {}, "rank_tie": False}
                assignment[slot["index"]] = pick
                bench = [view for view in bench if view["player_id"] != pick["player_id"]]
                filled = True
    # Options for slots that stay open are rebuilt from the final lineup and bench.
    for slot in open_slots():
        _, basis, candidates, via, tie = evaluate_open(slot)
        entries[slot["index"]] = {"view": None, "basis": basis, "candidates": candidates, "via": via, "rank_tie": tie}
    return entries


def _value_of(view):
    return view["value"]["value"] if view and view["value"]["state"] == "AVAILABLE" else None


def _value_edge(rec, alt):
    base = {"unit": VALUE_UNIT, "basis": VALUE_BASIS, "recommended": _value_of(rec), "alternative": _value_of(alt)}
    if rec is None or alt is None:
        return {**base, "state": "UNAVAILABLE", "delta": None, "reason": "No supported comparison player."}
    missing = [_name(view) for view in (rec, alt) if _value_of(view) is None]
    if missing:
        return {**base, "state": "UNAVAILABLE", "delta": None, "reason": f"Weekly value unavailable for {', '.join(missing)}."}
    return {**base, "state": "AVAILABLE", "delta": round(base["recommended"] - base["alternative"], 2), "evidence_level": "PRELIMINARY", "reason": None}


def _provider_edge(rec, alt):
    if rec is None or alt is None:
        return {"state": "UNAVAILABLE", "recommended": None, "alternative": None, "delta": None, "blocker": None, "reason": "No comparison player.", "recommendation_impact": "INFORMATIONAL_ONLY"}
    left, right = rec["provider_projection"], alt["provider_projection"]
    base = {"recommended": left.get("projected_ppg"), "alternative": right.get("projected_ppg"), "unit": "fantasy_points_per_game",
            "scoring_format": left.get("scoring_format") or right.get("scoring_format"), "recommendation_impact": "INFORMATIONAL_ONLY"}
    if left.get("projected_ppg") is None or right.get("projected_ppg") is None:
        return {**base, "state": "UNAVAILABLE", "delta": None, "blocker": "PROVIDER_PROJECTION_UNAVAILABLE", "reason": "Provider projection unavailable for at least one player."}
    edge = build_projection_edge(left["evidence"], right["evidence"])
    if edge.get("state") != "AVAILABLE":
        withheld = edge.get("blocker") == "JERRYGM_COMPARISON_FRESHNESS_UNAVAILABLE"
        reason = "Difference withheld: the provider freshness threshold is unverified." if withheld else "Difference withheld: provider evidence is not comparable."
        return {**base, "state": "UNAVAILABLE", "delta": None, "blocker": edge.get("blocker"), "reason": reason}
    return {**base, "state": "AVAILABLE", "delta": round(edge["comparison_edge"], 2), "blocker": None, "evidence_level": edge.get("evidence_level"), "reason": None}


def _rank_edge(rec, alt):
    """Same-position consensus comparison; delta > 0 means the recommended player is ranked better."""
    base = {"unit": CONSENSUS_UNIT, "basis": CONSENSUS_BASIS, "recommended": _rank_of(rec), "alternative": _rank_of(alt), "delta": None,
            "population": f"{rec['position']} weekly consensus" if rec else None, "recommendation_impact": "SAME_POSITION_ORDERING"}
    if rec is None or alt is None:
        return {**base, "state": "UNAVAILABLE", "reason": "No comparison player."}
    if rec["position"] != alt["position"]:
        return {**base, "state": "UNAVAILABLE", "reason": f"{_name(rec)} ({rec['position']}) and {_name(alt)} ({alt['position']}) play different positions; positional consensus ranks cannot compare them."}
    missing = [view for view in (rec, alt) if _rank_of(view) is None]
    if missing:
        return {**base, "state": "UNAVAILABLE", "reason": "No current-week consensus rank for " + "; ".join(f"{_name(view)} ({view['consensus_rank']['reason']})" for view in missing) + "."}
    return {**base, "state": "AVAILABLE", "delta": round(base["alternative"] - base["recommended"], 2), "evidence_level": "PRELIMINARY",
            "source_date": rec["consensus_rank"].get("source_date"), "reason": None}


def _evidence_agreement(rec, counterpart, *, value_edge, rank_edge):
    """Disclose whether the informational provider projection agrees with the deciding evidence; never decides."""
    if value_edge["state"] == "AVAILABLE" and value_edge["delta"]:
        basis, favored = "weekly value", value_edge["delta"] > 0
    elif rank_edge["state"] == "AVAILABLE" and rank_edge["delta"]:
        basis, favored = "this week's consensus rank", rank_edge["delta"] > 0
    else:
        return {"state": "NOT_APPLICABLE", "label": None, "recommendation_impact": "INFORMATIONAL_ONLY"}
    left, right = rec["provider_projection"].get("projected_ppg"), counterpart["provider_projection"].get("projected_ppg")
    if left is None or right is None:
        return {"state": "UNAVAILABLE", "label": "Provider projection unavailable for at least one player, so agreement cannot be checked.", "recommendation_impact": "INFORMATIONAL_ONLY"}
    leader, trailer = (rec, counterpart) if favored else (counterpart, rec)
    projected = {rec["player_id"]: left, counterpart["player_id"]: right}
    numbers = f"{_name(rec)} {_points(left)} vs {_name(counterpart)} {_points(right)} per game"
    if projected[leader["player_id"]] > projected[trailer["player_id"]]:
        state, text = "AGREES", f"The JerryGM provider projection agrees with {basis}: {numbers}."
    elif projected[leader["player_id"]] < projected[trailer["player_id"]]:
        state, text = "DISAGREES", f"Sources disagree: {basis} favors {_name(leader)}, but the JerryGM provider projection favors {_name(trailer)} ({numbers})."
    else:
        state, text = "NEUTRAL", f"The JerryGM provider projection ties ({numbers})."
    return {"state": state, "label": text + " The provider projection is informational only (freshness threshold unapproved) and does not change this decision or its confidence.",
            "recommendation_impact": "INFORMATIONAL_ONLY"}


def _value_drivers(rec, alt):
    """Identify which supported weekly-value components decide rec over alt (no weights invented)."""
    left, right = rec["value"], alt["value"]
    parts = [left.get("baseline"), right.get("baseline"), left.get("matchup_modifier"), right.get("matchup_modifier"), left.get("injury_multiplier"), right.get("injury_multiplier")]
    if any(part is None for part in parts):
        return ["PROJECTION_DRIVEN"], ["Weekly value components are not separable; the supplied weekly values decide."], False
    base_r, base_a, mod_r, mod_a, mult_r, mult_a = parts
    drivers, notes, matchup_decided = [], [], False
    if base_r > base_a:
        drivers.append("PROJECTION_DRIVEN")
        if mod_r > mod_a and rec["matchup"]["state"] in {"PRELIMINARY", "ESTABLISHED"}:
            drivers.append("MATCHUP_SUPPORTED")
    else:
        health_flips = base_r * mult_r > base_a * mult_a
        matchup_flips = base_r * (1 + mod_r) > base_a * (1 + mod_a)
        if health_flips and not matchup_flips:
            drivers.append("HEALTH_DRIVEN")
            notes.append(f"{_name(alt)}'s health adjustment decides this comparison.")
        elif matchup_flips and not health_flips:
            drivers.append("MATCHUP_SUPPORTED")
            matchup_decided = True
            notes.append("The matchup adjustment alone decides this comparison; matchup evidence must not decide alone, so confidence is degraded.")
        else:
            drivers.append("MULTI_FACTOR")
            notes.append("Matchup and health adjustments together decide this comparison.")
    strength = {"HIGH_OPPORTUNITY": 3, "MODERATE_OPPORTUNITY": 2, "LIMITED_OPPORTUNITY": 1}
    if strength.get(rec["opportunity"].get("strength"), 0) > strength.get(alt["opportunity"].get("strength"), 0) > 0:
        drivers.append("OPPORTUNITY_SUPPORTED")
    return drivers, notes, matchup_decided


def _decision_confidence(*, status, basis, rec, counterpart, unranked, value_edge, matchup_decided, has_alternatives, rank_path=False, rank_edge=None, rank_uncompared=(), rank_tie=False, lock_reason=None):
    """How strongly comparative evidence supports the choice; categorical, never a fabricated score."""
    def state(value, reason):
        return {"state": value, "reason": reason}

    if status == "BLOCKED":
        return state("BLOCKED", "Player identity is unresolved, so no recommendation can be made for this slot.")
    if status == "VACANT":
        return state("BLOCKED", "No eligible available player can fill this slot.")
    if status == "LOCK_UNVERIFIED":
        return state("INSUFFICIENT_EVIDENCE", f"Kickoff lock state cannot be verified ({lock_reason or 'no schedule-owned kickoff evidence'}), so no START/SIT change can be recommended until kickoff times are verified.")
    if rec is None:
        if rank_tie:
            return state("INSUFFICIENT_EVIDENCE", "This week's consensus ranks the best options equally, so evidence does not separate them.")
        return state("INSUFFICIENT_EVIDENCE", "Eligible options cannot be ranked with supported evidence.")
    if status == "LOCKED":
        return state("NOT_APPLICABLE", f"{_name(rec)}'s game has already started; Sleeper locks players at kickoff, so no start/sit change is possible.")
    uncertain = rec["availability"] != "AVAILABLE"
    if basis == "ONLY_ELIGIBLE_OPTION" or (status == "REPLACEMENT_REQUIRED" and not has_alternatives):
        if not uncertain:
            return state("ESTABLISHED", "No other eligible bench player can fill this slot, and availability is verified; no comparison is required.")
        return state("DEGRADED", f"No other eligible bench player can fill this slot, but {rec['health']['impact']}")
    if not has_alternatives and counterpart is None:
        if uncertain:
            return state("DEGRADED", f"No eligible alternative exists, but {rec['health']['impact']}")
        return state("NOT_APPLICABLE", "No eligible available alternative exists, so there is no start/sit comparison.")
    if rank_path and value_edge["state"] != "AVAILABLE":
        if rank_edge["state"] != "AVAILABLE":
            return state("INSUFFICIENT_EVIDENCE", f"No supported comparison exists: {rank_edge['reason']}")
        if rank_edge["delta"] == 0:
            return state("INSUFFICIENT_EVIDENCE", "This week's consensus ranks are tied, so evidence does not separate the players.")
        degraders = []
        if uncertain:
            degraders.append(f"{_name(rec)}'s availability is uncertain")
        if rank_uncompared:
            details = ", ".join(f"{_name(view)} ({_rank_gap(view, rec)})" for view in rank_uncompared)
            degraders.append(f"{details} could not be compared")
        if degraders:
            return state("DEGRADED", "This week's consensus ranks favor this choice, but " + "; ".join(degraders) + ".")
        return state("PRELIMINARY", "This week's positional consensus ranks favor this choice. Consensus rank is expert ordering, not projected points, and its lineup use is preliminary, so no percentage is shown.")
    if value_edge["state"] != "AVAILABLE":
        if _value_of(rec) is not None and unranked and counterpart is None:
            return state("DEGRADED", f"{_name(rec)} is the only option with a supported weekly value; {_names(unranked)} could not be compared.")
        return state("INSUFFICIENT_EVIDENCE", f"No supported weekly-value comparison exists: {value_edge['reason']}")
    if value_edge["delta"] == 0:
        return state("INSUFFICIENT_EVIDENCE", "Supported weekly values are tied, so evidence does not separate the players.")
    degraders = []
    if rec["availability"] != "AVAILABLE":
        degraders.append(f"{_name(rec)}'s availability is uncertain")
    cleared = _cleared_value(counterpart)
    if counterpart["availability"] != "AVAILABLE" and cleared is not None and cleared > value_edge["recommended"]:
        degraders.append(f"the comparison depends on {_name(counterpart)}'s health discount")
    if unranked:
        degraders.append(f"{_names(unranked)} could not be compared (no supported weekly value)")
    if matchup_decided:
        degraders.append("the matchup adjustment alone decides the comparison")
    if degraders:
        return state("DEGRADED", "Supported weekly values favor this choice, but " + "; ".join(degraders) + ".")
    return state("PRELIMINARY", "Preliminary repository weekly values for both players support this choice; no validated certainty model exists, so no percentage is shown.")


def _balance(rec, other, value_edge, provider_edge, rank_edge=None):
    advantages, disadvantages = [], []
    if value_edge["state"] == "AVAILABLE" and value_edge["delta"]:
        text = f"Supported weekly value {_points(value_edge['recommended'])} vs {_points(value_edge['alternative'])}"
        (advantages if value_edge["delta"] > 0 else disadvantages).append(text)
    elif _value_of(rec) is None:
        disadvantages.append(f"No supported weekly value for {_name(rec)}")
    if rank_edge is not None and rank_edge["state"] == "AVAILABLE" and rank_edge["delta"]:
        text = f"This week's consensus rank {rec['consensus_rank']['label']} vs {other['consensus_rank']['label']} (expert ordering, not points)"
        (advantages if rank_edge["delta"] > 0 else disadvantages).append(text)
    order = {"AVAILABLE": 2, "UNCERTAIN": 1, "UNAVAILABLE": 0}
    if order[rec["availability"]] != order[other["availability"]]:
        text = f"Availability: {rec['health']['label']} vs {other['health']['label']}"
        (advantages if order[rec["availability"]] > order[other["availability"]] else disadvantages).append(text)
    left, right = rec["matchup"].get("easiest_rank"), other["matchup"].get("easiest_rank")
    if left is not None and right is not None and left != right:
        text = f"Matchup signal: {rec['matchup']['signal']} vs {other['matchup']['signal']} (context only)"
        (advantages if left < right else disadvantages).append(text)
    strength = {"HIGH_OPPORTUNITY": 3, "MODERATE_OPPORTUNITY": 2, "LIMITED_OPPORTUNITY": 1}
    mine, theirs = strength.get(rec["opportunity"].get("strength"), 0), strength.get(other["opportunity"].get("strength"), 0)
    if mine and theirs and mine != theirs:
        text = f"Opportunity: {rec['opportunity']['label']} vs {other['opportunity']['label']} (informational)"
        (advantages if mine > theirs else disadvantages).append(text)
    if provider_edge["state"] == "AVAILABLE" and provider_edge["delta"]:
        text = f"Provider projection {_points(provider_edge['recommended'])} vs {_points(provider_edge['alternative'])} per game (informational)"
        (advantages if provider_edge["delta"] > 0 else disadvantages).append(text)
    return advantages, disadvantages


def _cleared_value(view):
    value, multiplier = _value_of(view), view["value"].get("injury_multiplier")
    return value / multiplier if value is not None and multiplier else None


def _trigger(code, label, view, slot, evidence, impact):
    return {"code": code, "label": label, "player": _name(view), "slot": slot, "evidence": evidence, "decision_impact": impact, "reevaluation_required": True}


def _triggers(slot, rec, counterpart, value_edge, rank_edge=None, rank_decided=False):
    """Only information capable of changing this recommendation or its confidence."""
    triggers = []
    if rec is not None:
        health = rec["health"]
        evidence = f"{health['source']} status {health['status']} ({health['freshness_state']})"
        if health["state"] in {"QUESTIONABLE", "DOUBTFUL"} and health["verified"]:
            fallback = f" {_name(counterpart)} is the best supported fallback." if counterpart is not None and counterpart["availability"] != "UNAVAILABLE" else ""
            triggers.append(_trigger("OFFICIAL_GAME_STATUS", f"Official game-day status for {_name(rec)} ({health['label']})", rec, slot, evidence, f"If {_name(rec)} is ruled out, {slot} must be re-evaluated.{fallback}"))
        elif rec["availability"] == "UNCERTAIN" and rec.get("availability_scope") == "PLAYER":
            triggers.append(_trigger("AVAILABILITY_VERIFICATION", f"Verified availability for {_name(rec)}", rec, slot, evidence, f"Unverified availability keeps {slot} at MONITOR until confirmed."))
    if counterpart is not None and value_edge["state"] == "AVAILABLE" and value_edge["delta"] > 0:
        health = counterpart["health"]
        cleared = _cleared_value(counterpart)
        if health["state"] in {"QUESTIONABLE", "DOUBTFUL"} and cleared is not None and cleared > value_edge["recommended"]:
            triggers.append(_trigger("OFFICIAL_GAME_STATUS", f"Official game-day status for {_name(counterpart)} ({health['label']})", counterpart, slot,
                                     f"{health['source']} status {health['status']} ({health['freshness_state']})",
                                     f"Without the health discount {_name(counterpart)}'s weekly value would be {_points(cleared)}, above {_name(rec)}'s {_points(value_edge['recommended'])}; re-evaluate if cleared."))
        triggers.append({
            "code": "WEEKLY_VALUE_UPDATE", "label": f"A weekly value update larger than {_points(value_edge['delta'])} points for {_name(rec)} or {_name(counterpart)}",
            "player": f"{_name(rec)} / {_name(counterpart)}", "slot": slot, "evidence": "Repository Weekly Score (preliminary)",
            "decision_impact": "Could reverse this decision.", "reevaluation_required": True,
        })
        adjusted = [view for view in (rec, counterpart) if view["matchup"]["state"] != "ESTABLISHED" and view["value"].get("matchup_modifier")]
        if adjusted:
            triggers.append({
                "code": "MATCHUP_EVIDENCE_UPDATE", "label": f"Supported matchup evidence for {_names(adjusted)}",
                "player": _names(adjusted), "slot": slot, "evidence": "Weekly value includes a matchup adjustment from non-authoritative matchup evidence",
                "decision_impact": "Supported matchup evidence could change the weekly values used in this decision.", "reevaluation_required": True,
            })
    if rank_decided and counterpart is not None:
        triggers.append({
            "code": "CONSENSUS_RANK_UPDATE",
            "label": f"An updated weekly consensus that reorders {_name(rec)} ({rec['consensus_rank']['label']}) and {_name(counterpart)} ({counterpart['consensus_rank']['label']})",
            "player": f"{_name(rec)} / {_name(counterpart)}", "slot": slot,
            "evidence": f"{rec['consensus_rank']['source']}, published {rec['consensus_rank'].get('source_date')}",
            "decision_impact": "Could reverse this decision; consensus ranks are re-checked when My Team opens (six-hour refresh cadence).",
            "reevaluation_required": True,
        })
    return triggers


MISSING_DOMAINS = (("WEEKLY_VALUE", "Weekly value"), ("CONSENSUS_RANK", "Weekly consensus rank"), ("HEALTH", "Verified health"), ("KICKOFF_LOCK", "Verified kickoff lock"),
                   ("MATCHUP", "Matchup evidence"), ("PROVIDER_PROJECTION", "Provider projection"), ("OPPORTUNITY", "Opportunity / workload"))


def _missing_evidence(views, *, consensus_authority=True):
    groups = {domain: {"players": [], "details": []} for domain, _ in MISSING_DOMAINS}

    def add(domain, view, detail):
        group = groups[domain]
        if _name(view) not in group["players"]:
            group["players"].append(_name(view))
        if detail:
            detail = str(detail).rstrip(".")
            detail = detail[:1].lower() + detail[1:]
        if detail and detail not in group["details"]:
            group["details"].append(detail)

    for view in [item for item in views if item is not None]:
        if view["value"]["state"] != "AVAILABLE":
            add("WEEKLY_VALUE", view, VALUE_BLOCKER_TEXT.get(view["value"]["blocker"], "weekly value unavailable"))
        if consensus_authority and view["consensus_rank"]["state"] not in {"AVAILABLE", "NOT_REQUESTED"}:
            add("CONSENSUS_RANK", view, view["consensus_rank"]["reason"])
        if not view["health"]["verified"]:
            add("HEALTH", view, "health status is not verified as current")
        if _lock_unverified(view):
            add("KICKOFF_LOCK", view, view["lock"].get("reason"))
        if view["matchup"]["state"] == "UNAVAILABLE":
            add("MATCHUP", view, "matchup evidence unavailable")
        if view["provider_projection"].get("projected_ppg") is None:
            add("PROVIDER_PROJECTION", view, view["provider_projection"].get("reason"))
        if view["opportunity"]["state"] != "AVAILABLE":
            add("OPPORTUNITY", view, view["opportunity"].get("reason"))
    return [
        {"domain": domain, "label": label, "players": groups[domain]["players"], "detail": "; ".join(groups[domain]["details"])}
        for domain, label in MISSING_DOMAINS if groups[domain]["players"]
    ]


def _evidence_used(*, basis, status, rec, counterpart, slot_contract, current_lineup, value_edge, provider_edge, rank_decided=False):
    used = [{"domain": "LEAGUE_SLOTS", "source": slot_contract.get("source"), "used_for": "ELIGIBILITY"}]
    if current_lineup["state"] in {"AVAILABLE", "INCOMPLETE"}:
        used.append({"domain": "CURRENT_LINEUP", "source": "Sleeper roster starters", "used_for": "DEFAULT_SELECTION"})
    if rec is not None:
        used.append({"domain": "HEALTH", "source": rec["health"]["source"], "freshness_state": rec["health"]["freshness_state"], "used_for": "AVAILABILITY"})
        if rec["is_bye"] or (counterpart or {}).get("is_bye"):
            used.append({"domain": "BYE_WEEK", "source": "Schedule evidence", "used_for": "AVAILABILITY"})
        if status in PINNED_LOCK_STATES:
            lock = rec.get("lock") or {}
            used.append({"domain": "GAME_LOCK", "source": lock.get("schedule_source") or "Automated nflverse schedule (unavailable)",
                         "freshness_state": lock.get("freshness_state"), "evidence_level": lock.get("state"), "used_for": "AVAILABILITY"})
    if value_edge["state"] == "AVAILABLE" and (basis == "SUPPORTED_VALUE" or status == "STABLE"):
        used.append({"domain": "WEEKLY_VALUE", "source": rec["value"]["source"], "evidence_level": "PRELIMINARY", "freshness_state": rec["value"]["freshness_state"], "used_for": "SELECTION"})
    if rank_decided:
        rank = rec["consensus_rank"]
        used.append({"domain": "CONSENSUS_RANK", "source": f"{rank['source']} (published {rank.get('source_date')}; retrieved {rank.get('retrieved_at') or 'unavailable'})",
                     "evidence_level": "PRELIMINARY", "freshness_state": rank.get("freshness_state"), "used_for": "SELECTION"})
    if provider_edge.get("recommended") is not None or provider_edge.get("alternative") is not None:
        used.append({"domain": "PROVIDER_PROJECTION", "source": "JerryGM", "used_for": "CONTEXT_ONLY"})
    if rec is not None and rec["matchup"]["state"] != "UNAVAILABLE":
        used.append({"domain": "MATCHUP", "source": rec["matchup"].get("source"), "evidence_level": rec["matchup"]["state"], "used_for": "CONTEXT_ONLY"})
    if rec is not None and rec["opportunity"]["state"] == "AVAILABLE":
        used.append({"domain": "OPPORTUNITY", "source": "Published usage evidence", "used_for": "CONTEXT_ONLY"})
    return used


def _unavailable_reason(view):
    if view["availability_reason"] == "BYE":
        return "on bye"
    if view["availability_reason"] == "GAME_LOCKED":
        return "locked: game already started"
    if view["availability_reason"] == "LOCK_UNVERIFIED":
        return "kickoff lock unverified"
    return f"listed {view['health']['label']}" if view["availability_reason"] == "HEALTH" else "unavailable"


def _rank_why(*, status, basis, rec, counterpart, outgoing, rank_edge, rank_gain):
    rank, position = rec["consensus_rank"], rec["position"]
    if status == "CHANGE" and outgoing is not None and (rank_gain or {}).get("state") == "AVAILABLE":
        text = f"This week's {position} consensus ranks {_name(rec)} {rank['ecr']:g}, ahead of {_name(outgoing)} ({rank_gain['alternative']:g})."
        if counterpart is not None and counterpart is not outgoing and rank_edge["state"] == "AVAILABLE":
            text += f" The best remaining {position} alternative, {_name(counterpart)}, ranks {rank_edge['alternative']:g}."
    elif basis == "SUPPORTED_RANK":
        text = f"Among the eligible {position} options, this week's consensus ranks {_name(rec)} highest ({rank['ecr']:g})"
        text += f", ahead of {_name(counterpart)} ({rank_edge['alternative']:g})." if counterpart is not None and rank_edge["state"] == "AVAILABLE" else "."
    else:
        text = f"{_name(rec)} ranks {rank['ecr']:g} in this week's {position} consensus, ahead of the best {position} alternative, {_name(counterpart)} ({rank_edge['alternative']:g})."
    return text + f" Consensus rank is expert ordering within {position}, not projected points ({rank['source']}, published {rank.get('source_date')})."


def _why(*, status, basis, slot, rec, current, counterpart, unranked, candidates, value_edge, notes, outgoing=None, current_gain=None, unidentified=(), moved_from=None, via=None, rank_edge=None, rank_gain=None, rank_decided=False, rank_tie=False, lock_options=()):
    if status == "BLOCKED":
        return f"Player identity is unresolved for {_names(unidentified)}; no recommendation can be made for {slot}."
    if status == "VACANT":
        return f"No eligible available player can fill {slot}; a roster move is required."
    if status == "LOCKED":
        listed = f" ({_name(rec)} is listed {rec['health']['label']})" if rec["availability"] == "UNAVAILABLE" else ""
        return f"{_name(rec)}'s game has already started{listed}. Sleeper locks players at kickoff, so {slot} cannot change this week."
    if status == "LOCK_UNVERIFIED":
        if rec is None:
            lead = f"{_name(current)} cannot play ({_unavailable_reason(current)}). " if current is not None and current["availability"] == "UNAVAILABLE" else ""
            return lead + f"No player can be recommended for {slot}: kickoff locks cannot be verified for any eligible option ({_names(lock_options)}). {_lock_reason(lock_options)}"
        if rec["availability"] == "UNAVAILABLE":
            return (f"{_name(rec)} cannot play ({_unavailable_reason(rec)}), but his kickoff lock cannot be verified, so no replacement is recommended. "
                    f"{_lock_reason([rec])} Check Sleeper: if his game has not started, replace him before kickoff.")
        return f"{_name(rec)} stays at {slot} because his kickoff lock cannot be verified, so no START/SIT change is recommended. {_lock_reason([rec])}"
    lead = ""
    if status == "REPLACEMENT_REQUIRED":
        lead = f"{_name(current)} cannot play ({_unavailable_reason(current)}). " if current is not None else f"{slot} is empty in your Sleeper lineup. "
    if rec is None and rank_tie and candidates:
        text = f"This week's consensus ranks {_names(candidates)} equally ({candidates[0]['consensus_rank']['label']}) as the best options for {slot}"
        if status == "SELECTION_UNRESOLVED" and current is not None and _rank_of(current) is not None:
            text += f", ahead of {_name(current)} ({current['consensus_rank']['label']})"
        return lead + text + "; choose between them before lock."
    if rec is None:
        via = via or {}
        listed = ", ".join(f"{_name(view)} ({via[view['player_id']]})" if view["player_id"] in via else _name(view) for view in candidates) or "none"
        return lead + f"Eligible options ({listed}) cannot be ranked with supported evidence; choose before lock."
    if basis == "ONLY_ELIGIBLE_OPTION":
        return lead + f"{_name(rec)} is the only remaining eligible available player for {slot}."
    if basis == "CURRENT_KEPT" and moved_from:
        return lead + f"{_name(rec)} moves from {moved_from} to {slot} so the recommended lineup fits; no supported evidence favors benching {_name(rec)}."
    if rank_decided or basis == "SUPPORTED_RANK":
        return lead + _rank_why(status=status, basis=basis, rec=rec, counterpart=counterpart, outgoing=outgoing, rank_edge=rank_edge, rank_gain=rank_gain)
    if basis == "SUPPORTED_VALUE" and value_edge["state"] == "AVAILABLE" and counterpart is not None:
        relation = "ties" if value_edge["delta"] == 0 else f"is {_points(value_edge['delta'])} points higher than"
        text = f"{_name(rec)}'s supported weekly value ({_points(value_edge['recommended'])}) {relation} {_name(counterpart)}'s ({_points(value_edge['alternative'])})."
        if outgoing is not None and outgoing is not counterpart and (current_gain or {}).get("state") == "AVAILABLE":
            text = (f"{_name(rec)}'s supported weekly value ({_points(current_gain['recommended'])}) is {_points(current_gain['delta'])} points higher than "
                    f"{_name(outgoing)}'s ({_points(current_gain['alternative'])}); the best bench alternative, {_name(counterpart)}, trails by {_points(value_edge['delta'])}.")
        return lead + " ".join([text, *notes])
    if basis == "SUPPORTED_VALUE":
        text = f"{_name(rec)} has a supported weekly value ({_points(_value_of(rec))})"
        return lead + text + (f"; {_names(unranked)} could not be compared." if unranked else "; no eligible alternative remains.")
    if status == "NO_ALTERNATIVE":
        return f"No other eligible available player can fill {slot}."
    missing = [view for view in (rec, *unranked) if _value_of(view) is None]
    return f"{_name(rec)} stays in your current lineup because no supported evidence favors a change: weekly value is unavailable for {_names(missing)}."


def _lineup_changes(slots, entries, current_by_index):
    """Deterministic START/SIT pairs and slot moves between the current and recommended lineups."""
    recommended = {entry["view"]["player_id"]: index for index, entry in entries.items() if entry["view"] is not None}
    current = {view["player_id"]: index for index, view in current_by_index.items()}
    incoming = sorted((index, entries[index]["view"]) for player_id, index in recommended.items() if player_id not in current)
    outgoing = {index: view for index, view in current_by_index.items() if view["player_id"] not in recommended}
    pairs, unpaired = [], []
    for index, view in incoming:
        if index in outgoing:
            pairs.append({"index": index, "slot": slots[index]["slot"], "start": view, "sit": outgoing.pop(index), "sit_slot": slots[index]["slot"]})
        else:
            unpaired.append((index, view))
    remaining = sorted(outgoing.items())
    for index, view in unpaired:
        match = remaining.pop(0) if remaining else None
        pairs.append({"index": index, "slot": slots[index]["slot"], "start": view, "sit": match[1] if match else None, "sit_slot": slots[match[0]]["slot"] if match else None})
    for index, view in remaining:
        pairs.append({"index": index, "slot": slots[index]["slot"], "start": None, "sit": view, "sit_slot": slots[index]["slot"]})
    moves = [
        {"player": _name(entries[index]["view"]), "player_id": player_id, "from": slots[current[player_id]]["slot"], "to": slots[index]["slot"]}
        for player_id, index in sorted(recommended.items(), key=lambda item: item[1])
        if player_id in current and current[player_id] != index
    ]
    return sorted(pairs, key=lambda pair: pair["index"]), moves


def _compact(view):
    rank = view.get("consensus_rank") or {}
    lock = view.get("lock") or {}
    projection = view.get("projection") or {}
    return {
        "player": _name(view), "player_id": view["player_id"], "position": view["position"], "opponent": view["opponent"],
        "health": view["health"]["label"], "availability": view["availability"], "value": _value_of(view),
        "provider_ppg": view["provider_projection"].get("projected_ppg"), "matchup": view["matchup"]["label"],
        "ranked": _value_of(view) is not None,
        "consensus_rank": _rank_of(view), "consensus_label": rank.get("label"),
        "consensus_reason": rank.get("reason") if rank.get("state") not in {"AVAILABLE", "NOT_REQUESTED", None} else None,
        "locked": _locked(view), "lock_state": lock.get("state"), "lock_label": lock.get("label"), "kickoff": lock.get("kickoff_display"),
        "lock_status": view.get("lock_status"),
        "projection": projection.get("value"), "projection_range": projection.get("value_range"), "projection_state": projection.get("evidence_state"),
    }


def _slot_decision(slot, entry, *, current_view, paired_sit, bench, slot_contract, current_lineup, has_current, identity_blocked=(), slot_labels=None, lineup_slot_by_id=None,
                   consensus_authority=True, lock_blocked=(), comparison_pool=(), projection_action_threshold=None):
    rec, basis, label = entry["view"], entry["basis"], slot["slot"]
    slot_labels, lineup_slot_by_id = slot_labels or {}, lineup_slot_by_id or {}
    moved_from = slot_labels.get(rec["current_index"]) if rec is not None and rec["current_index"] not in (None, slot["index"]) else None
    moved_to = lineup_slot_by_id.get(current_view["player_id"]) if current_view is not None and current_view is not rec else None
    pinned = basis in PINNED_LOCK_STATES
    alternatives = [] if pinned else [view for view in bench if _eligible(view, slot)]
    valued = sorted((view for view in alternatives if _value_of(view) is not None), key=lambda view: (-_value_of(view), view["player_id"]))
    unranked = sorted((view for view in alternatives if _value_of(view) is None), key=_name)
    best = valued[0] if valued else None
    # Consensus rank is a second evidence tier only when explicitly authorized, and only between players who have no weekly value.
    rank_path = consensus_authority and rec is not None and _value_of(rec) is None and _rank_of(rec) is not None
    comparable = sorted((view for view in alternatives if rank_path and view["position"] == rec["position"] and _rank_of(view) is not None and _value_of(view) is None),
                        key=lambda view: (_rank_of(view), view["player_id"]))
    comparable_ids = {view["player_id"] for view in comparable}
    rank_uncompared = [view for view in sorted(alternatives, key=_name) if rank_path and view["player_id"] not in comparable_ids]
    best_ranked = comparable[0] if comparable else None
    current_out = current_view is not None and current_view["availability"] == "UNAVAILABLE"
    unidentified = [view for view in identity_blocked if _eligible(view, slot)]
    lock_options = [view for view in lock_blocked if _eligible(view, slot)]
    if basis == "VACANT":
        status = "BLOCKED" if unidentified else "LOCK_UNVERIFIED" if lock_options else "VACANT"
    elif pinned:
        status = basis
    elif has_current and (current_out or current_view is None):
        status = "REPLACEMENT_REQUIRED"
    elif rec is None:
        status = "SELECTION_UNRESOLVED"
    elif has_current and not rec["is_current_starter"]:
        status = "CHANGE"
    elif rec["availability"] == "UNCERTAIN" and rec.get("availability_scope") == "PLAYER":
        status = "AVAILABILITY_WATCH"
    elif not alternatives:
        status = "NO_ALTERNATIVE"
    elif _value_of(rec) is not None and best is not None and _value_of(rec) > _value_of(best):
        status = "STABLE"
    elif rank_path and best_ranked is not None and _rank_of(rec) < _rank_of(best_ranked):
        status = "STABLE"
    else:
        status = "UNRESOLVED"
    lock_subjects = [rec] if rec is not None else lock_options
    outgoing = (paired_sit or current_view) if status == "CHANGE" else None
    if rank_path:
        counterpart = best_ranked if best_ranked is not None else outgoing
    else:
        counterpart = best if best is not None else outgoing
    value_edge = _value_edge(rec, counterpart)
    provider_edge = _provider_edge(rec, counterpart)
    rank_edge = _rank_edge(rec, counterpart)
    current_gain = _value_edge(rec, outgoing) if outgoing is not None else None
    rank_gain = _rank_edge(rec, outgoing) if outgoing is not None else None
    rank_decided = rank_path and rank_edge["state"] == "AVAILABLE" and rank_edge["delta"] > 0
    rank_used = rank_path and (rank_decided or basis == "SUPPORTED_RANK")
    if rec is not None and counterpart is None and alternatives:
        missing = [view for view in (rec, *sorted(alternatives, key=_name)) if _value_of(view) is None]
        value_edge["reason"] = f"Weekly value unavailable for {_names(missing)}."
        provider_edge["reason"] = "Not compared: eligible alternatives are not ranked; each option's provider projection is listed separately."
        if rank_path:
            rank_edge["reason"] = "No eligible alternative has a comparable consensus rank: " + ", ".join(f"{_name(view)} ({_rank_gap(view, rec)})" for view in rank_uncompared) + "."
    drivers, notes, matchup_decided = [], [], False
    if status == "LOCKED":
        drivers.append("GAME_LOCKED")
    elif status == "LOCK_UNVERIFIED":
        drivers.append("LOCK_UNVERIFIED")
    else:
        if status == "REPLACEMENT_REQUIRED":
            drivers.append("HEALTH_DRIVEN" if current_out and current_view["availability_reason"] == "HEALTH" else "ELIGIBILITY_DRIVEN")
        if basis == "ONLY_ELIGIBLE_OPTION":
            drivers.append("ELIGIBILITY_DRIVEN")
        elif basis == "SUPPORTED_VALUE" and value_edge["state"] == "AVAILABLE" and value_edge["delta"] > 0:
            more, notes, matchup_decided = _value_drivers(rec, counterpart)
            drivers.extend(more)
        elif rank_used:
            drivers.append("CONSENSUS_RANK_DRIVEN")
        elif rec is not None and not alternatives:
            drivers.append("ELIGIBILITY_DRIVEN")
        elif status not in {"VACANT", "BLOCKED"}:
            drivers.append("REDUCED_SCOPE")
    drivers = list(dict.fromkeys(drivers))
    decision = "MONITOR" if rec is None or rec["availability"] != "AVAILABLE" else "FLEX" if slot["flex"] else "START"
    why = _why(status=status, basis=basis, slot=label, rec=rec, current=current_view, counterpart=counterpart, unranked=unranked, candidates=entry["candidates"], value_edge=value_edge, notes=notes,
               outgoing=outgoing, current_gain=current_gain, unidentified=unidentified, moved_from=moved_from, via=entry.get("via"), rank_edge=rank_edge, rank_gain=rank_gain, rank_decided=rank_used,
               rank_tie=bool(entry.get("rank_tie")), lock_options=lock_options)
    if moved_from and basis != "CURRENT_KEPT":
        why += f" {_name(rec)} moves from {moved_from}."
    if moved_to and moved_to != label:
        why += f" {_name(current_view)} moves to {moved_to}."
    if rec is not None and rec["availability"] == "UNCERTAIN" and status != "LOCKED":
        why += " " + (rec["health"]["impact"] if rec["availability_reason"] == "HEALTH" else "The opponent for this week is not verified; confirm the game before lock.")
    # A slot whose kickoff lock is unverified needs attention only when its pinned starter cannot play, has an uncertain health status, or no player can
    # be recommended; a missing opponent is the same schedule gap the lock state already reports.
    lock_attention = status == "LOCK_UNVERIFIED" and (rec is None or rec["availability"] == "UNAVAILABLE"
                                                      or (rec["availability"] == "UNCERTAIN" and rec.get("availability_scope") == "PLAYER"
                                                          and rec.get("availability_reason") == "HEALTH"))
    requires_attention = lock_attention or (status in ATTENTION_ORDER and status != "LOCK_UNVERIFIED")
    attention_reasons = [STATUS_LABELS[status]] if requires_attention else []
    if rec is not None and rec["availability"] == "UNCERTAIN" and rec.get("availability_scope") == "PLAYER" and status not in {"AVAILABILITY_WATCH", "LOCKED"}:
        attention_reasons.append(f"{_name(rec)}: {rec['health']['label']}")
    advantages, disadvantages = _balance(rec, counterpart, value_edge, provider_edge, rank_edge if rank_path else None) if rec is not None and counterpart is not None else ([], [])
    compared = [rec, counterpart, *unranked] if status not in {"NO_ALTERNATIVE", *PINNED_LOCK_STATES} else lock_subjects
    agreement = _evidence_agreement(rec, counterpart, value_edge=value_edge, rank_edge=rank_edge) if rec is not None and counterpart is not None else {"state": "NOT_APPLICABLE", "label": None, "recommendation_impact": "INFORMATIONAL_ONLY"}
    if status == "LOCKED":
        what_could_change = []
    elif status == "LOCK_UNVERIFIED":
        what_could_change = [{
            "code": "KICKOFF_LOCK_VERIFICATION", "label": f"A verified kickoff time for {_names(lock_subjects)}", "player": _names(lock_subjects), "slot": label,
            "evidence": _lock_reason(lock_subjects), "reevaluation_required": True,
            "decision_impact": f"Fresh automated schedule evidence within an approved freshness limit would allow START/SIT comparisons for {label}.",
        }, *_triggers(label, rec, None, value_edge)]
    else:
        what_could_change = _triggers(label, rec, counterpart, value_edge, rank_edge, rank_decided)
    evidence_used = _evidence_used(basis=basis, status=status, rec=rec, counterpart=counterpart, slot_contract=slot_contract, current_lineup=current_lineup, value_edge=value_edge,
                                   provider_edge=provider_edge, rank_decided=rank_used)
    starter = current_view if has_current else rec
    if rec is not None and starter is not None and rec is not starter:
        alternative, alternative_basis = rec, "RECOMMENDED_CHANGE"
    else:
        alternative, _ = best_projection_alternative([view for view in comparison_pool if _eligible(view, slot)])
        alternative_basis = "BEST_PROJECTED_ALTERNATIVE"
    comparison = compare_projections(starter, alternative, action_threshold=projection_action_threshold)
    comparison.update(slot=label, alternative_basis=alternative_basis if alternative is not None else None,
                      agreement=projection_evidence_agreement(starter, alternative, comparison))
    comparison["brief"] = comparison_brief(comparison)
    if any((view or {}).get("projection", {}).get("value_range") for view in (starter, alternative)):
        evidence_used.append({"domain": "LEAGUE_SCORED_PROJECTION", "source": PROJECTION_SOURCE, "evidence_level": "PRELIMINARY", "used_for": "CONTEXT_ONLY"})
    return {
        "slot": label, "index": slot["index"], "code": slot["code"], "eligible_positions": slot["eligible_positions"], "flex": slot["flex"],
        "status": status, "status_label": STATUS_LABELS[status], "requires_attention": requires_attention, "attention_reasons": attention_reasons,
        "decision": decision, "basis": basis, "moved_from": moved_from,
        "recommended": rec, "current": current_view, "changed": status in {"CHANGE", "REPLACEMENT_REQUIRED"} and rec is not None and has_current,
        "best_alternative": best_ranked if rank_path else best, "counterpart": counterpart, "outgoing": outgoing, "current_gain": current_gain, "rank_gain": rank_gain,
        "candidates": [{**_compact(view), "via": (entry.get("via") or {}).get(view["player_id"])} for view in entry["candidates"]],
        "alternatives": [_compact(view) for view in (*valued, *unranked)], "unranked_alternatives": [_name(view) for view in unranked],
        "rank_uncompared": [{"player": _name(view), "reason": _rank_gap(view, rec)} for view in rank_uncompared],
        "lock_unverified_options": [_name(view) for view in lock_options] if status == "LOCK_UNVERIFIED" and rec is None else [],
        "edge": {"value": value_edge, "provider_projection": provider_edge, "consensus_rank": rank_edge},
        "projection_delta": value_edge["delta"],
        "projection_comparison": comparison,
        "evidence_agreement": agreement,
        "drivers": drivers, "driver_labels": [DRIVER_LABELS[driver] for driver in drivers], "primary_driver": drivers[0] if drivers else None,
        "decision_confidence": _decision_confidence(status=status, basis=basis, rec=rec, counterpart=counterpart, unranked=unranked, value_edge=value_edge, matchup_decided=matchup_decided,
                                                    has_alternatives=bool(alternatives), rank_path=rank_path, rank_edge=rank_edge, rank_uncompared=rank_uncompared, rank_tie=bool(entry.get("rank_tie")),
                                                    lock_reason=_lock_reason(lock_subjects)),
        "projection_confidence": {"recommended": (rec or {}).get("projection_confidence"), "alternative": (counterpart or {}).get("projection_confidence")},
        "advantages": advantages, "disadvantages": disadvantages,
        "missing_evidence": _missing_evidence(compared, consensus_authority=consensus_authority),
        "why": why, "notes": notes,
        "what_could_change": what_could_change,
        "evidence_used": evidence_used,
        "blockers": sorted({view["value"]["blocker"] for view in compared if view is not None and view["value"]["blocker"]}
                           | {view["consensus_rank"]["blocker"] for view in compared if consensus_authority and view is not None and view["consensus_rank"]["state"] not in {"AVAILABLE", "NOT_REQUESTED"}}
                           | {view["lock"]["blocker"] for view in lock_subjects if status == "LOCK_UNVERIFIED" and (view.get("lock") or {}).get("blocker")}
                           | ({"PLAYER_IDENTITY_UNRESOLVED"} if status == "BLOCKED" else set())),
    }


def _value_basis(views, scoring):
    relevant = [view for view in views if view["availability"] != "UNAVAILABLE" and view["player_id"] is not None]
    available = [view for view in relevant if view["value"]["state"] == "AVAILABLE"]
    blockers = sorted({view["value"]["blocker"] for view in relevant if view["value"]["blocker"]})
    state = "AVAILABLE" if relevant and len(available) == len(relevant) else "PARTIAL" if available else "UNAVAILABLE"
    return {
        "metric": VALUE_BASIS, "label": "Repository weekly value", "definition": VALUE_DEFINITION, "unit": VALUE_UNIT,
        "state": state, "available_players": len(available), "eligible_players": len(relevant),
        "evidence_level": "PRELIMINARY" if available else "INSUFFICIENT", "blockers": blockers,
        "reason": "; ".join(VALUE_BLOCKER_TEXT.get(blocker, blocker) for blocker in blockers) or None,
        "scoring_alignment": scoring["value_alignment"], "used_for": "SELECTION",
    }


def _provider_state(provider_projections):
    if not provider_projections:
        return {"state": "NOT_REQUESTED", "label": "Provider projections were not requested.", "returned": 0, "blockers": []}
    players = provider_projections.get("players") or {}
    returned = sum(_finite(row.get("projected_ppg")) is not None for row in players.values())
    blockers = list(provider_projections.get("blockers") or [])
    label = f"{returned} of {len(players)} provider projections returned; informational only." if players else PROVIDER_BLOCKER_TEXT.get((blockers or [""])[0], "Provider projections unavailable.")
    return {"state": provider_projections.get("state") or "UNAVAILABLE", "label": label, "returned": returned, "requested": len(players), "scoring": provider_projections.get("scoring"), "blockers": blockers}


def _consensus_basis(views, consensus, scoring, *, authority=True):
    """Lineup-level disclosure of the weekly consensus comparator: source, dates, coverage, and authority."""
    base = {"metric": CONSENSUS_BASIS, "label": "Weekly positional consensus rank", "source": (consensus or {}).get("source") or CONSENSUS_SOURCE,
            "definition": CONSENSUS_DEFINITION, "unit": CONSENSUS_UNIT, "used_for": "SAME_POSITION_ORDERING" if authority else "NONE",
            "recommendation_impact": "SAME_POSITION_ORDERING" if authority else "DISPLAY_ONLY", "decision_authority": bool(authority)}
    if not consensus:
        return {**base, "state": "NOT_REQUESTED", "ranked_players": 0, "eligible_players": 0, "evidence_level": "INSUFFICIENT", "blockers": [],
                "reason": "Weekly consensus ranks were not requested.", "used_for": "NONE"}
    horizon = (consensus.get("horizons") or {}).get("this_week") or {}
    relevant = [view for view in views if view["player_id"] is not None and (view["availability"] != "UNAVAILABLE" or view["availability_reason"] in {"GAME_LOCKED", "LOCK_UNVERIFIED"})]
    ranked = [view for view in relevant if view["consensus_rank"]["state"] == "AVAILABLE"]
    missing = Counter(view["consensus_rank"]["reason"] for view in relevant if view["consensus_rank"]["state"] != "AVAILABLE")
    if scoring["value_alignment"] == "MISMATCH":
        state = "BLOCKED"
    elif ranked:
        state = "AVAILABLE" if len(ranked) == len(relevant) else "PARTIAL"
    else:
        state = "UNAVAILABLE"
    return {
        **base, "state": state, "ranked_players": len(ranked), "eligible_players": len(relevant),
        "source_dates": sorted({view["consensus_rank"]["source_date"] for view in ranked}),
        "retrieved_at": consensus.get("last_successful_refresh"), "last_attempt": consensus.get("last_attempt"),
        "refresh_error": consensus.get("refresh_error"), "version": consensus.get("version"),
        "cache_freshness_state": consensus.get("cache_freshness_state"), "max_age_seconds": horizon.get("max_age_seconds"),
        "evidence_level": "PRELIMINARY" if ranked else "INSUFFICIENT",
        "blockers": sorted({view["consensus_rank"]["blocker"] for view in relevant if view["consensus_rank"]["blocker"]}),
        "reason": "; ".join(f"{count} player{'s' if count != 1 else ''}: {reason}" for reason, count in sorted(missing.items())) or None,
        "authority": ("PRELIMINARY: the documented decision use of weekly consensus is waiver ordering; lineup use is a disclosed preliminary "
                      "recommendation under the repository evidence states, never ESTABLISHED.") if authority else
                     ("Context only: weekly consensus has no lineup decision authority. It is shown for reference, never selects or locks a player, "
                      "and never overrides a projection comparison (its lineup-use permission is unverified)."),
        "limitations": [
            "Expert ordering within one position, not projected points: never converted to points, never compared across positions, so cross-position FLEX choices stay unresolved.",
            ("Used only when the recommended player has no supported weekly value and both players have a current-week rank; an unranked player is never treated as worse."
             if authority else "Displayed only; lineup selection, kickoff locks, and projection comparisons never use it."),
            "Publication dates have day precision; ranks outside the 48-hour limit, for another NFL week, or for games already started are withheld.",
        ],
    }


def _notices(views, team_health, week, value_basis, consensus_basis=None, *, projection_basis=None):
    notices = []
    shared = [view for view in views if view["availability"] == "UNCERTAIN" and view["availability_scope"] == "TEAM" and view["availability_reason"] == "HEALTH"]
    if shared:
        freshness = str((team_health or {}).get("freshness_state") or "UNAVAILABLE").upper()
        notices.append({"code": "TEAM_HEALTH_UNVERIFIED", "label": f"Team health evidence is {freshness}; {len(shared)} player(s) stay at MONITOR until statuses are verified."})
    if week is None:
        notices.append({"code": "WEEK_UNVERIFIED", "label": "The NFL week is unverified, so opponents and weekly values cannot be confirmed."})
    consensus_state = (consensus_basis or {}).get("state")
    authority = (consensus_basis or {}).get("decision_authority", True)
    if value_basis["state"] != "AVAILABLE" and value_basis["eligible_players"]:
        scope = "partly unavailable" if value_basis["state"] == "PARTIAL" else "unavailable"
        if authority and consensus_state in {"AVAILABLE", "PARTIAL"}:
            notices.append({"code": f"WEEKLY_VALUE_{value_basis['state']}", "label": (
                f"Weekly values are {scope} ({value_basis['reason'] or 'no value supplied'}). Same-position comparisons use this week's consensus rank "
                f"(expert ordering, not points) when both players are ranked; other comparisons stay unresolved, and your current starter is kept.")})
        else:
            notices.append({"code": f"WEEKLY_VALUE_{value_basis['state']}", "label": f"Weekly values are {scope} ({value_basis['reason'] or 'no value supplied'}). Comparisons that need them stay unresolved, and your current starter is kept."})
    if authority and consensus_state in {"UNAVAILABLE", "BLOCKED"}:
        notices.append({"code": f"CONSENSUS_RANK_{consensus_state}", "label": f"This week's consensus ranks are {consensus_state.lower()} ({consensus_basis.get('reason') or 'no current-week rank'}); they are not used."})
    if (projection_basis or {}).get("state") == "PRELIMINARY":
        notices.append({"code": "PROJECTION_PRELIMINARY", "label": (
            "League-scored projections are PRELIMINARY (provider stat lines rescored with your league's Sleeper scoring). No validated action threshold exists, "
            "so a projected edge is shown as a close call and never changes your lineup by itself.")})
    return notices


def _lineup_triggers(decisions, value_basis, notices):
    triggers = []
    pending = [decision for decision in decisions if decision["status"] == "LOCK_UNVERIFIED"]
    if pending:
        subjects = [decision["recommended"] for decision in pending if decision["recommended"] is not None]
        triggers.append({
            "code": "KICKOFF_LOCK_VERIFICATION", "label": "Verified kickoff times (a fresh automated nflverse schedule within an approved freshness limit)", "player": None,
            "slot": ", ".join(decision["slot"] for decision in pending), "evidence": _lock_reason(subjects),
            "decision_impact": f"Would allow START/SIT comparisons for {len(pending)} slot(s); the recommended lineup could change.", "reevaluation_required": True,
        })
    unresolved = [decision for decision in decisions if decision["status"] == "UNRESOLVED" and decision["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"]
    if unresolved and value_basis["state"] != "AVAILABLE":
        triggers.append({
            "code": "WEEKLY_VALUE_AVAILABILITY", "label": "Supported weekly values for compared players", "player": None,
            "slot": ", ".join(decision["slot"] for decision in unresolved), "evidence": value_basis["reason"] or "Weekly value unavailable",
            "decision_impact": f"Would allow a supported START/SIT comparison for {len(unresolved)} slot(s); the recommended lineup could change.",
            "reevaluation_required": True,
        })
    if any(notice["code"] == "TEAM_HEALTH_UNVERIFIED" for notice in notices):
        triggers.append({"code": "TEAM_HEALTH_VERIFICATION", "label": "A verified team health refresh", "player": None, "slot": "Lineup",
                         "evidence": "Team health evidence is not current", "decision_impact": "Would clear or confirm MONITOR states across the lineup.", "reevaluation_required": True})
    return triggers


def _confidence_summary(decisions):
    contested = [decision for decision in decisions if decision["status"] not in {"NO_ALTERNATIVE", "LOCKED"}]
    states = [decision["decision_confidence"]["state"] for decision in contested]
    if "BLOCKED" in states:
        return {"state": "BLOCKED", "reason": "At least one slot cannot be filled with a verified, eligible player."}
    pending = [decision for decision in decisions if decision["status"] == "LOCK_UNVERIFIED"]
    if pending:
        rest = len(decisions) - len(pending)
        return {"state": "INSUFFICIENT_EVIDENCE",
                "reason": f"Current starters stay in {_plural(len(pending), 'slot')} whose kickoff cannot be verified ({', '.join(decision['slot'] for decision in pending)})"
                          + (f"; {rest} other {'slot was' if rest == 1 else 'slots were'} evaluated normally." if rest else ".")}
    if not contested:
        locked = sum(decision["status"] == "LOCKED" for decision in decisions)
        if locked:
            return {"state": "NOT_APPLICABLE", "reason": f"{_plural(locked, 'starting slot')} {'is' if locked == 1 else 'are'} locked after kickoff; "
                    + ("no start/sit comparison remains." if locked == len(decisions) else f"the other {len(decisions) - locked} have no eligible available alternative.")}
        return {"state": "NOT_APPLICABLE", "reason": "No starter has an eligible available alternative."}
    if "INSUFFICIENT_EVIDENCE" in states:
        return {"state": "INSUFFICIENT_EVIDENCE", "reason": f"{states.count('INSUFFICIENT_EVIDENCE')} of {len(contested)} contested slot(s) lack a supported comparison."}
    if "DEGRADED" in states:
        return {"state": "DEGRADED", "reason": f"{states.count('DEGRADED')} of {len(contested)} contested slot(s) carry availability or comparability limits."}
    if "PRELIMINARY" in states:
        return {"state": "PRELIMINARY", "reason": "Contested slots are supported by preliminary evidence (weekly values or this week's consensus ranks); no validated certainty model exists."}
    if all(state == "ESTABLISHED" for state in states):
        return {"state": "ESTABLISHED", "reason": "Contested slots are decided by verified eligibility and availability."}
    return {"state": "NOT_APPLICABLE", "reason": "No contested slot requires a start/sit comparison."}


def _schedule_evidence(views, evaluated_at):
    """The stored schedule behind the roster's lock states: source, oldest record time, latest retrieval, and age at evaluation."""
    locks = [view["lock"] for view in views if (view.get("lock") or {}).get("schedule_source")]
    stamps = sorted(stamp for stamp in (lock.get("source_recorded_at") or lock.get("retrieved_at") for lock in locks) if stamp)
    retrieved = sorted(lock["retrieved_at"] for lock in locks if lock.get("retrieved_at"))
    now, oldest = utc_datetime(evaluated_at), utc_datetime(stamps[0]) if stamps else None
    age = max(0, int((now - oldest).total_seconds())) if now and oldest else None
    sources = sorted({lock["schedule_source"] for lock in locks})
    automated = bool(sources) and all(source.lower().startswith(SCHEDULE_SOURCE_PREFIX) for source in sources)
    return {
        "state": "AVAILABLE" if locks else "UNAVAILABLE",
        "label": ("Automated nflverse schedule" if automated else "Schedule not from the automated source") if locks else None,
        "sources": sources, "recorded_at": stamps[0] if stamps else None, "recorded_display": kickoff_display(oldest) if oldest else None,
        "retrieved_at": retrieved[-1] if retrieved else None, "retrieved_display": kickoff_display(utc_datetime(retrieved[-1])) if retrieved else None,
        "age_seconds": age, "age_label": age_label(age) if age is not None else None,
        "freshness_states": sorted({lock.get("freshness_state") or "UNAVAILABLE" for lock in locks}),
    }


def _lock_entry(view):
    status = view["lock_status"]
    return {"player": _name(view), "player_id": view["player_id"], "position": view["position"], "role": status["role"], "slot": status["slot"],
            "game_text": status["game_text"], "kickoff_utc": status["kickoff_utc"], "kickoff_display": status["kickoff_display"],
            "kickoff_text": status["kickoff_text"], "health": view["health"]["label"], "lineup_relevant": status["lineup_relevant"],
            "context_label": status["context_label"], "reason": status["reason"], "impact": status["impact"]}


def _lock_summary(views, decisions, *, mode, evaluated_at):
    """Lineup-level lock coverage and manager-facing week state, derived only from player lock states and verified kickoffs.

    Each roster player is counted once in exactly one primary state: OPEN, LOCKED, LOCK_UNVERIFIED, or BYE.
    """
    base = {"contract_id": LOCK_SUMMARY_CONTRACT_ID, "authority": "SCHEDULE_OWNED", "lock_rule": LOCK_RULE,
            "evaluated_at": evaluated_at.isoformat() if hasattr(evaluated_at, "isoformat") else evaluated_at,
            "independent_of": ["FantasyPros/DynastyProcess consensus", "provider projections", "opportunity evidence"]}
    unique = {}
    for view in sorted(views, key=lambda item: item["row_index"]):
        unique.setdefault(view["lock_key"], view)
    players = sorted(unique.values(), key=lambda view: (_name(view), view["lock_key"]))
    empty = {"applicable_player_count": 0, "open_count": 0, "locked_count": 0, "unverified_count": 0, "bye_count": 0, "material_unverified_count": 0,
             "lineup_relevant_open_count": 0, "actionable_open_count": 0, "earliest_remaining_kickoff": None, "latest_remaining_kickoff": None,
             "remaining_open_players": [], "actionable_open_players": [], "locked_players": [], "unverified_players": [], "bye_players": [],
             "coverage_text": None, "supported_text": None, "unverified_reasons": {}, "display_context": {"state": "UNAVAILABLE"}, "count_text": "No roster players",
             "schedule_authority": {"threshold_state": "NOT_APPLICABLE", "setting": "SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", "label": None},
             "schedule_evidence": {"state": "UNAVAILABLE", "label": None, "sources": [], "recorded_at": None, "recorded_display": None, "retrieved_at": None,
                                   "retrieved_display": None, "age_seconds": None, "age_label": None, "freshness_states": []}}
    if mode == "MOCK" or not players:
        message = WEEK_STATE_IMPACT["NOT_APPLICABLE"] if mode == "MOCK" else "No roster players are available for lock evaluation."
        return {**base, **empty, "week_state": "NOT_APPLICABLE", "week_state_label": WEEK_STATE_LABELS["NOT_APPLICABLE"], "message": message,
                "recommendation_impact": WEEK_STATE_IMPACT["NOT_APPLICABLE"]}
    groups = {state: [] for state in PRIMARY_LOCK_STATES}
    for view in players:
        state = view["lock_status"]["state"]
        groups[state if state in VERIFIED_LOCK_STATES else "LOCK_UNVERIFIED"].append(view)
    opened, locked, unverified, byes = (groups[state] for state in PRIMARY_LOCK_STATES)
    relevant_open = [view for view in opened if view["lock_status"]["lineup_relevant"]]
    material = [view for view in unverified if view["lock_status"]["lineup_relevant"]]
    if material:
        week_state = "LOCK_COVERAGE_INCOMPLETE"
    elif not locked:
        week_state = "PRE_KICKOFF"
    elif not relevant_open:
        week_state = "COMPLETE"
    elif 2 * len(locked) > len(players) - len(byes):
        week_state = "MOSTLY_LOCKED"
    else:
        week_state = "IN_PROGRESS"
    open_ids = {view["player_id"] for view in opened if view["player_id"] is not None}
    window_ids = set()
    for decision in decisions or []:
        if decision["status"] in OPEN_WINDOW_STATUSES:
            members = [decision.get("current"), decision.get("recommended"), *(decision.get("alternatives") or []), *(decision.get("candidates") or [])]
            window_ids.update(member["player_id"] for member in members if member and member.get("player_id") in open_ids)
    open_entries = sorted((_lock_entry(view) for view in opened), key=lambda entry: (entry["kickoff_utc"] or "", entry["player"], str(entry["player_id"])))
    actionable = [entry for entry in open_entries if entry["player_id"] in window_ids]
    kickoffs = [entry for entry in open_entries if entry["kickoff_utc"]]
    earliest = {"utc": kickoffs[0]["kickoff_utc"], "display": kickoffs[0]["kickoff_display"]} if kickoffs else None
    latest = {"utc": kickoffs[-1]["kickoff_utc"], "display": kickoffs[-1]["kickoff_display"]} if kickoffs else None
    with_context = [view for view in unverified if ((view.get("lock") or {}).get("display_context") or {}).get("kickoff_utc")]
    without_context = [view for view in unverified if not ((view.get("lock") or {}).get("display_context") or {}).get("kickoff_utc")]
    contexts = [view["lock"]["display_context"] for view in with_context]
    oldest = max(contexts, key=lambda context: (context["age_seconds"], context["kickoff_utc"])) if contexts else None
    past = sum(1 for context in contexts if context["kickoff_passed"])

    def grouped(group):
        counts = Counter(_lock_reason_text(view) for view in group)
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return " and ".join(f"{text} ({count})" if len(ordered) > 1 else text for text, count in ordered)

    def series(parts):
        return parts[0] if len(parts) == 1 else " and ".join(parts) if len(parts) == 2 else ", ".join(parts[:-1]) + ", and " + parts[-1]

    reasons = Counter(_lock_reason_text(view) for view in unverified)
    L, O, U, B = len(locked), len(opened), len(unverified), len(byes)
    coverage_parts = []
    if with_context:
        seen = [f"{_plural(count, 'player')} {verb if count != 1 else singular}" for count, singular, verb in (
            (past, "appears past kickoff", "appear past kickoff"), (len(contexts) - past, "appears not yet started", "appear not yet started")) if count]
        coverage_parts.append(" and ".join(seen) + f", but {'this lock state' if len(contexts) == 1 else 'these lock states'} cannot be verified because "
                              f"{grouped(with_context)} (stored schedule {oldest['age_label']} old; kickoff times are display only).")
    if without_context:
        coverage_parts.append(f"Lock status for {_plural(len(without_context), 'more player' if with_context else 'player')} cannot be verified "
                              f"({grouped(without_context)}).")
    coverage = " ".join(coverage_parts) or None
    verified_parts = [f"{count} {singular if count == 1 else verb}" for count, singular, verb in (
        (L, "is locked after kickoff", "are locked after kickoff"), (O, "remains open", "remain open"), (B, "is on bye", "are on bye")) if count]
    if verified_parts:
        verified_parts[0] = verified_parts[0].replace(" ", f" {'player' if verified_parts[0].startswith('1 ') else 'players'} ", 1)
    supported = series(verified_parts) + "." if verified_parts else None
    first_action = actionable[0] if actionable else None
    if week_state == "LOCK_COVERAGE_INCOMPLETE":
        message = " ".join(part for part in (supported, coverage, "Current assignments remain protected.") if part)
    elif week_state == "PRE_KICKOFF":
        message = "No roster games have started." + (f" {_plural(O, 'player')} {'is' if O == 1 else 'are'} open; first kickoff {earliest['display']}." if earliest else "")
    elif week_state == "IN_PROGRESS":
        message = f"Some games have started: {L} locked, {O} open." + (
            f" You can still change players with future kickoffs (next: {first_action['kickoff_display']})." if first_action
            else " No open lineup decision remains right now.")
    elif week_state == "MOSTLY_LOCKED":
        message = f"{_plural(L, 'roster player')} {'is' if L == 1 else 'are'} locked after kickoff." + (
            f" Review {first_action['player']}, whose game has not started (kickoff {first_action['kickoff_display']})." if len(actionable) == 1
            else f" Review the {len(actionable)} players whose games have not started (next kickoff {first_action['kickoff_display']})." if actionable
            else f" {_plural(O, 'player')} {'has' if O == 1 else 'have'} later kickoffs, but no lineup change remains possible for them.")
    else:
        message = "All verified roster games have started. No lineup changes remain this week." + (
            f" {_plural(O, 'bench player')} with later kickoffs cannot play this week ({', '.join(entry['player'] for entry in open_entries)})." if O else "")
    if U and week_state != "LOCK_COVERAGE_INCOMPLETE":
        message += f" Lock status for {_plural(U, 'player')} cannot be verified ({grouped(unverified)}); {'it does' if U == 1 else 'they do'} not affect your lineup."
    if any(view["lock"].get("blocker") == "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED" for view in unverified):
        threshold = ("UNAPPROVED", "Schedule freshness threshold not approved: kickoff times cannot authorize locks or lineup moves.")
    elif any(view["lock"].get("freshness_state") in {"FRESH", "AGING", "STALE"} for view in players):
        threshold = ("APPROVED", "Schedule freshness threshold approved: only verified kickoffs authorize locks and lineup moves.")
    else:
        threshold = ("UNVERIFIED", "Schedule freshness could not be evaluated.")
    return {
        **base, "week_state": week_state, "week_state_label": WEEK_STATE_LABELS[week_state], "message": message,
        "count_text": " · ".join(f"{count} {label}" for count, label in ((O, "open"), (L, "locked"), (U, "unverified"), (B, "bye")) if count),
        "applicable_player_count": len(players), "open_count": O, "locked_count": L, "unverified_count": U, "bye_count": B,
        "material_unverified_count": len(material), "lineup_relevant_open_count": len(relevant_open), "actionable_open_count": len(actionable),
        "earliest_remaining_kickoff": earliest, "latest_remaining_kickoff": latest,
        "remaining_open_players": open_entries, "actionable_open_players": actionable,
        "locked_players": [_lock_entry(view) for view in locked], "unverified_players": [_lock_entry(view) for view in unverified],
        "bye_players": [_lock_entry(view) for view in byes], "coverage_text": coverage, "supported_text": supported, "unverified_reasons": dict(sorted(reasons.items())),
        "display_context": {"state": "HISTORICAL_CONTEXT" if contexts else "UNAVAILABLE", "past_count": past, "future_count": len(contexts) - past,
                            "without_kickoff_count": U - len(contexts), "age_label": (oldest or {}).get("age_label"),
                            "schedule_recorded_at": (oldest or {}).get("schedule_recorded_at"), "schedule_retrieved_at": (oldest or {}).get("schedule_retrieved_at"),
                            "limitation": (oldest or {}).get("limitation"), "decision_authority": False},
        "schedule_authority": {"threshold_state": threshold[0], "setting": "SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", "label": threshold[1]},
        "schedule_evidence": _schedule_evidence(players, evaluated_at),
        "recommendation_impact": WEEK_STATE_IMPACT[week_state],
    }


def _open_deadline(views):
    """Earliest verified kickoff among pre-kickoff players: when this decision window starts closing."""
    kickoffs = sorted((view["lock"]["kickoff_utc"], view["lock"].get("kickoff_display")) for view in views
                      if view is not None and (view.get("lock") or {}).get("state") == "OPEN" and view["lock"].get("kickoff_utc"))
    return {"utc": kickoffs[0][0], "display": kickoffs[0][1]} if kickoffs else None


def _review_decisions(decisions):
    """Open slots where the preliminary projection favors a bench alternative; comparisons only exist between pre-kickoff players."""
    return [decision for decision in decisions
            if (decision.get("projection_comparison") or {}).get("state") in {"CLOSE_CALL", "SUPPORTED_COMPARISON"}
            and decision["projection_comparison"].get("preferred") == "ALTERNATIVE"]


def _summary(decisions, pairs, notices, has_current, lock_summary):
    attention = sorted(
        (decision for decision in decisions if decision["requires_attention"]),
        key=lambda decision: (ATTENTION_ORDER[decision["status"]], -(decision["edge"]["value"]["delta"] or 0) if decision["status"] == "CHANGE" else 0, decision["index"]),
    )
    stable = sorted((decision for decision in decisions if decision["status"] == "STABLE"), key=lambda decision: (
        decision["edge"]["value"]["delta"] is None,
        decision["edge"]["value"]["delta"] if decision["edge"]["value"]["delta"] is not None else (decision["edge"].get("consensus_rank") or {}).get("delta") or 0,
        decision["index"],
    ))
    unresolved = [decision for decision in decisions if decision["status"] == "UNRESOLVED"]
    pending = [decision for decision in decisions if decision["status"] == "LOCK_UNVERIFIED"]
    starts = [pair for pair in pairs if pair["start"] is not None]
    reviews = _review_decisions(decisions)
    week_state = lock_summary["week_state"]
    if any(decision["status"] in {"VACANT", "BLOCKED"} for decision in decisions):
        status = "BLOCKED"
    elif any(decision["status"] in {"REPLACEMENT_REQUIRED", "CHANGE", "SELECTION_UNRESOLVED"} for decision in decisions):
        status = "ACTION REQUIRED"
    elif any(decision["decision"] == "MONITOR" and decision["status"] != "LOCKED" and (decision["status"] != "LOCK_UNVERIFIED" or decision["requires_attention"])
             for decision in decisions):
        status = "MONITOR"
    elif reviews or unresolved:
        status = "REVIEW"
    elif week_state == "COMPLETE":
        status = "WEEK COMPLETE"
    elif week_state == "LOCK_COVERAGE_INCOMPLETE":
        status = "LOCK COVERAGE INCOMPLETE"
    else:
        status = "READY"
    first = attention[0] if attention else None
    actionable = lock_summary.get("actionable_open_players") or []
    deadline = None
    if first is None and reviews:
        sides = [side for decision in reviews for side in (decision["projection_comparison"].get("current"), decision["projection_comparison"].get("alternative")) if side]
        kickoffs = sorted((side["kickoff_utc"], side.get("kickoff")) for side in sides if side.get("kickoff_utc") and side.get("lock_state") == "OPEN")
        action = f"Review {_plural(len(reviews), 'close lineup decision')}" + (f" before {kickoffs[0][1]}" if kickoffs else "")
    elif first is None and week_state == "COMPLETE":
        action = "No lineup changes remain this week."
    elif first is None and week_state == "LOCK_COVERAGE_INCOMPLETE":
        action = ("Keep current assignments for players whose kickoff cannot be verified." if not actionable
                  else f"Review {_plural(len(actionable), 'open player')}; keep current assignments for players whose kickoff cannot be verified.")
    elif first is None and week_state == "MOSTLY_LOCKED":
        action = ("Most players are locked. " + (f"Review {actionable[0]['player']} before his {actionable[0]['kickoff_display']} kickoff." if len(actionable) == 1
                                                  else f"Review the {len(actionable)} players with later kickoffs." if actionable
                                                  else "No lineup change remains possible for the players with later kickoffs."))
    elif first is None and week_state == "IN_PROGRESS":
        action = "Some games have started. " + ("You can still change players with future kickoffs." if actionable else "No open lineup decision remains right now.")
    elif first is None:
        action = "Keep your current lineup" if has_current else "Recommended lineup ready"
    elif first["status"] == "LOCK_UNVERIFIED":
        rec = first["recommended"]
        if rec is None:
            action = f"Verify kickoff locks before filling {first['slot']}"
        elif rec["availability"] == "UNAVAILABLE":
            action = f"Check {_name(rec)} ({rec['health']['label']}) in Sleeper: kickoff lock unverified"
        else:
            action = f"Monitor {_name(rec)} ({rec['health']['label']}); kickoff lock unverified"
    elif first["recommended"] is None:
        if first["status"] == "VACANT":
            action = f"Fill {first['slot']}: no eligible player is available"
        elif first["status"] == "BLOCKED":
            action = f"Lineup blocked at {first['slot']}: player identity is unresolved"
        else:
            action = f"Choose a starter at {first['slot']}" + (f" to replace {_name(first['current'])}" if first["current"] is not None else "")
    elif first["status"] in {"REPLACEMENT_REQUIRED", "CHANGE"} and first.get("moved_from"):
        action = f"Move {_name(first['recommended'])} from {first['moved_from']} to {first['slot']}"
    elif first["status"] in {"REPLACEMENT_REQUIRED", "CHANGE"}:
        verb = "FLEX" if first["flex"] else "START"
        sit = next((pair["sit"] for pair in starts if pair["index"] == first["index"]), None)
        action = f"{verb} {_name(first['recommended'])}" + (f" over {_name(sit)}" if sit is not None else f" at {first['slot']}")
    else:
        action = f"Monitor {_name(first['recommended'])} ({first['recommended']['health']['label']}) before kickoff"
    if first is not None and first["status"] != "LOCK_UNVERIFIED":
        sit = next((pair["sit"] for pair in starts if pair["index"] == first["index"]), None)
        deadline = _open_deadline([first["recommended"], first["current"], first.get("outgoing"), sit])
    if len(starts) > 1:
        def verb(pair):
            return "FLEX" if decisions[pair["index"]]["flex"] else "START"
        why = f"{len(starts)} supported lineup changes: " + "; ".join(f"{verb(pair)} {_name(pair['start'])} over {_name(pair['sit']) if pair['sit'] else 'an empty slot'}" for pair in starts) + "."
    elif first is not None:
        why = first["why"]
    elif reviews:
        details = "; ".join(f"{decision['slot']}: {decision['projection_comparison']['alternative']['player']} {decision['projection_comparison']['alternative']['projection_text']} "
                            f"vs {decision['projection_comparison']['current']['player']} {decision['projection_comparison']['current']['projection_text']}" for decision in reviews)
        why = (f"Preliminary league-scored projections favor a bench alternative in {_plural(len(reviews), 'open slot')} ({details}). "
               "No validated action threshold exists, so these never change your lineup by themselves.")
    elif week_state in {"COMPLETE", "LOCK_COVERAGE_INCOMPLETE", "MOSTLY_LOCKED", "IN_PROGRESS"}:
        why = lock_summary["message"]
    elif has_current:
        why = "No supported evidence favors a change to your current Sleeper lineup." + (f" {len(unresolved)} slot(s) have eligible alternatives that current evidence cannot compare." if unresolved else "")
    else:
        why = "The recommended lineup uses supported weekly values and verified availability."
    risks = [decision for decision in attention if decision["status"] != "CHANGE"]
    availability_notices = [notice for notice in notices if notice["code"] in {"TEAM_HEALTH_UNVERIFIED", "WEEK_UNVERIFIED"}]
    if risks:
        biggest_risk = risks[0]["why"]
    elif week_state == "LOCK_COVERAGE_INCOMPLETE" and lock_summary.get("unverified_count"):
        count = lock_summary["unverified_count"]
        biggest_risk = f"Lock state for {_plural(count, 'player')} cannot be verified here; confirm in Sleeper before moving {'him' if count == 1 else 'any of them'}."
    elif availability_notices:
        biggest_risk = availability_notices[0]["label"]
    else:
        biggest_risk = "No player-specific lineup risk identified."
    values = [_value_of(decision["recommended"]) for decision in decisions]
    total = round(sum(values), 2) if values and all(value is not None for value in values) else None
    return {
        "status": status, "action": action, "action_deadline": deadline, "why": why, "biggest_risk": biggest_risk, "week_state": week_state,
        "change_count": len(starts), "attention_count": len(attention), "stable_count": len(stable), "unresolved_count": len(unresolved),
        "review_count": len(reviews), "no_alternative_count": sum(decision["status"] == "NO_ALTERNATIVE" for decision in decisions),
        "locked_count": sum(decision["status"] == "LOCKED" for decision in decisions),
        "lock_unverified_count": len(pending),
        "decision_confidence": _confidence_summary(decisions),
        "value_total": {"state": "AVAILABLE" if total is not None else "UNAVAILABLE", "value": total, "available": sum(value is not None for value in values), "required": len(values)},
    }, attention, [*attention, *stable, *unresolved]


def _bench(views, lineup_ids):
    rows = [view for view in views if view["player_id"] not in lineup_ids]
    available = sorted((view for view in rows if view["availability"] != "UNAVAILABLE"), key=lambda view: (_value_of(view) is None, -(_value_of(view) or 0), _name(view)))
    unavailable = sorted((view for view in rows if view["availability"] == "UNAVAILABLE"), key=_name)
    bench, order = [], 0
    for view in [*available, *unavailable]:
        ranked = _value_of(view) is not None and view["availability"] != "UNAVAILABLE"
        order += ranked
        bench.append({**_compact(view), "order": order if ranked else None, "reason": None if view["availability"] != "UNAVAILABLE" else _unavailable_reason(view)})
    return bench


def _game_lock_basis(views, game_locks, mode):
    """Lineup-level disclosure of schedule-owned kickoff locks."""
    relevant = [view for view in views if view["player_id"] is not None]
    counts = Counter(view["lock"]["state"] for view in relevant)
    if mode == "MOCK":
        state = "NOT_APPLICABLE"
    elif relevant and sum(counts[state] for state in VERIFIED_LOCK_STATES) == len(relevant):
        state = "AVAILABLE"
    elif sum(counts[state] for state in VERIFIED_LOCK_STATES):
        state = "PARTIAL"
    else:
        state = "UNAVAILABLE"
    unverified = [view for view in relevant if _lock_unverified(view)]
    kickoffs = sorted({view["lock"]["kickoff_utc"] for view in relevant if view["lock"].get("kickoff_utc")})
    return {
        "contract_id": LOCK_CONTRACT_ID, "state": state, "authority": "SCHEDULE_OWNED", "lock_rule": LOCK_RULE,
        "source": "Automated nflverse schedule (nfl_schedule)", "supplied": game_locks is not None,
        "counts": dict(sorted(counts.items())), "blockers": sorted({view["lock"]["blocker"] for view in unverified if view["lock"].get("blocker")}),
        "reason": _lock_reason(unverified) if unverified else None,
        "schedule_sources": list((game_locks or {}).get("schedule_sources") or []), "schedule_retrieved_at": list((game_locks or {}).get("schedule_retrieved_at") or []),
        "freshness_states": sorted({view["lock"].get("freshness_state") for view in relevant if view["lock"].get("freshness_state")}),
        "earliest_kickoff_utc": kickoffs[0] if kickoffs else None, "evaluated_at": (game_locks or {}).get("evaluated_at"),
        "independent_of": ["FantasyPros/DynastyProcess consensus", "provider projections", "opportunity evidence"],
    }


def _projection_basis(views, provider_projections, scoring_settings, action_threshold):
    """Lineup-level disclosure of league-scored projections; informational, never selection authority."""
    relevant = [view for view in views if view["player_id"] is not None]
    projections = [view["projection"] for view in relevant]
    counts = Counter(projection["evidence_state"] for projection in projections)
    usable = [projection for projection in projections if projection.get("value_range")]
    if not provider_projections:
        state = "NOT_REQUESTED"
    elif usable:
        state = "PRELIMINARY"
    else:
        state = "UNAVAILABLE"
    blockers = Counter(projection["blocker"] for projection in projections if projection.get("blocker") and not projection.get("value_range"))
    return {
        "metric": COMPARISON_BASIS, "label": "League-scored projection (preliminary)", "source": PROJECTION_SOURCE, "unit": "fantasy points",
        "scoring_basis": "SLEEPER_LEAGUE_SCORING_SETTINGS" if scoring_settings else "UNAVAILABLE", "state": state,
        "counts": dict(sorted(counts.items())), "projected_players": len(usable), "identified_players": len(relevant),
        "complete_scoring_players": sum(projection["scoring_completeness"] == "COMPLETE" for projection in usable),
        "partial_scoring_players": sum(projection["scoring_completeness"] == "PARTIAL" for projection in usable),
        "missing_scoring_rules": sorted({item["rule"] for projection in usable for item in projection.get("missing_scoring_components") or []}),
        "generated_at": sorted({projection["generated_at"] for projection in usable if projection.get("generated_at")}),
        "retrieved_at": sorted({projection["retrieved_at"] for projection in usable if projection.get("retrieved_at")}),
        "data_through_week": sorted({projection["data_through_week"] for projection in usable if projection.get("data_through_week") is not None}),
        "blocker_counts": dict(sorted(blockers.items())),
        "action_threshold": dict(action_threshold) if action_threshold else {"state": "UNAPPROVED", "id": None,
                                                                            "reason": "No validated projection action threshold exists; comparisons report close calls only."},
        "used_for": "INFORMATIONAL_COMPARISON", "recommendation_impact": "INFORMATIONAL_ONLY",
        "authority": "Never selects players, raises decision confidence, or authorizes a lineup change; consensus rank never overrides it.",
        "limitations": [
            "PRELIMINARY: the provider freshness threshold and projection accuracy are unvalidated; forward validation is pending.",
            "Provider preset points (for example, PPR preset) are context only; the league-scored value applies your league's Sleeper scoring to the provider stat line.",
            "Rules the stat line cannot reproduce exactly are listed; a projection with such rules is a range, and a missing projection is never zero.",
        ],
    }


def _projection_comparisons(decisions):
    """Slot comparisons ordered for decision-first display: largest informational edges first."""
    order = {"SUPPORTED_COMPARISON": 0, "CLOSE_CALL": 1, "INSUFFICIENT_EVIDENCE": 2, "BLOCKED": 3}
    items = [decision for decision in decisions if (decision.get("projection_comparison") or {}).get("alternative") is not None]
    items.sort(key=lambda decision: (order.get(decision["projection_comparison"]["state"], 4), decision["projection_comparison"].get("preferred") != "ALTERNATIVE",
                                     -abs(decision["projection_comparison"].get("projection_delta") or 0), decision["index"]))
    return [{
        "slot": decision["slot"], "index": decision["index"], "flex": decision["flex"], "status": decision["status"], "decision": decision["decision"],
        "decision_confidence": decision["decision_confidence"], "comparison": decision["projection_comparison"],
        "projection_confidence": ((decision["recommended"] or decision["current"] or {}).get("projection") or {}).get("confidence"),
    } for decision in items]


def build_lineup_decision(
    roster: Sequence[Mapping[str, Any]] | None,
    *,
    league_settings: Mapping[str, Any] | None,
    team_health: Mapping[str, Any] | None,
    mode: str = "LIVE",
    season: Any = None,
    week: Any = None,
    provider_projections: Mapping[str, Any] | None = None,
    opportunity: Mapping[str, Any] | None = None,
    consensus_ranks: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    game_locks: Mapping[str, Any] | None = None,
    scoring_settings: Mapping[str, Any] | None = None,
    consensus_authority: bool = False,
    projection_action_threshold: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the read-only Starting Lineup Decision Intelligence contract for My Team.

    ``game_locks`` is the schedule-owned lock contract from ``services.game_lock``; players without
    one are LOCK_UNVERIFIED (outside Season Sandbox). ``scoring_settings`` are the league's raw
    Sleeper scoring settings used to rescore provider stat lines. ``consensus_ranks`` is the
    evaluated weekly ranking payload from ``services.dynastyprocess_rankings``; it is displayed as
    context and orders same-position players without weekly values only when
    ``consensus_authority`` is True. ``projection_action_threshold`` must be an approved threshold
    contract (``id`` and ``points``); without one, projection comparisons are close calls at most.
    """
    now = now or datetime.now(timezone.utc)
    roster = [dict(row) for row in roster or []]
    slot_contract = build_slot_contract(league_settings, mode=mode)
    scoring = build_scoring_context(league_settings, mode=mode)
    views = _player_views(roster, mode=mode, team_health=team_health, value_alignment=scoring["value_alignment"],
                          provider_projections=provider_projections, opportunity=opportunity, season=season, week=week,
                          consensus=consensus_ranks, consensus_reasons=_consensus_reasons(consensus_ranks), now=now,
                          game_locks=game_locks, scoring_settings=scoring_settings, consensus_authority=consensus_authority)
    slots = slot_contract["slots"]
    _attach_lock_status(views, slots)
    current = _current_lineup(views, slots)
    value_basis = _value_basis(views, scoring)
    consensus_basis = _consensus_basis(views, consensus_ranks, scoring, authority=consensus_authority)
    projection_basis = _projection_basis(views, provider_projections, scoring_settings, projection_action_threshold)
    notices = _notices(views, team_health, week, value_basis, consensus_basis, projection_basis=projection_basis)
    consensus_method = ("When a starter has no weekly value, this week's positional consensus rank (expert ordering, never converted to points) may replace that "
                        "starter with a better-ranked player at the same position, or fill an open slot whose options all play one position; cross-position (FLEX) "
                        "choices stay unresolved." if consensus_authority else
                        "This week's positional consensus rank is displayed as context only; it never selects, locks, or compares players.")
    contract = {
        "schema_version": SCHEMA_VERSION, "decision_effect": "READ_ONLY", "mode": mode, "season": season, "week": week,
        "slot_contract": slot_contract, "scoring_context": scoring, "value_basis": value_basis, "consensus_basis": consensus_basis,
        "game_lock_basis": _game_lock_basis(views, game_locks, mode), "projection_basis": projection_basis,
        "provider_projections": _provider_state(provider_projections), "floor_ceiling": dict(FLOOR_CEILING),
        "current_lineup": {key: current[key] for key in ("state", "blocker", "slots", "empty_slots")},
        "players": views, "notices": notices,
        "methodology": ("Whole-lineup assignment over league slots: verified availability first, then the exact maximum of supported weekly values; "
                        "missing values are never zero, and current starters stay when no supported evidence favors a change. " + consensus_method +
                        " Kickoff locks come only from the automated nflverse schedule: started games are locked, and players whose kickoff cannot be verified "
                        "are never moved in or out; each roster player is counted once as open, locked, unverified, or on bye, and the week state "
                        "(pre-kickoff, in progress, mostly locked, complete, or lock coverage incomplete) follows only from those states. League-scored projections (provider stat lines rescored with league scoring) are compared per slot as "
                        "PRELIMINARY, informational close calls; without an approved action threshold they never change the lineup."),
    }
    blocker = slot_contract.get("blocker") or (current["blocker"] if current["state"] == "BLOCKED" else None)
    if blocker:
        reason = "League starting slots are not verified" if slot_contract.get("blocker") else "The current Sleeper lineup contradicts league slots or identity"
        summary = {"status": "BLOCKED", "action": "Lineup recommendation blocked", "why": f"{reason}, so no league-legal recommendation is made.",
                   "biggest_risk": f"{reason}.", "change_count": 0, "attention_count": 0, "stable_count": 0, "unresolved_count": 0, "no_alternative_count": 0,
                   "decision_confidence": {"state": "BLOCKED", "reason": f"{reason}."}, "value_total": {"state": "UNAVAILABLE", "value": None, "available": 0, "required": 0}}
        return {**contract, "state": "BLOCKED", "blocker": blocker, "recommended_lineup": [], "slots": [], "attention": [], "decision_list": [],
                "changes": [], "moves": [], "bench": _bench(views, set()), "summary": summary, "what_could_change": [], "projection_comparisons": [],
                "lock_summary": _lock_summary(views, [], mode=mode, evaluated_at=now),
                "forward_validation": build_forward_validation_snapshots(views, [], season=season, week=week, captured_at=now)}
    has_current = current["state"] in {"AVAILABLE", "INCOMPLETE"}
    # Sleeper locks a starter at kickoff; a starter whose kickoff cannot be verified is pinned too (fail closed in both directions).
    pinned = {index: view for index, view in current["by_index"].items() if view["lock"]["state"] in PINNED_LOCK_STATES} if has_current else {}
    pinned_ids = {view["player_id"] for view in pinned.values()}
    entries = optimize_lineup_assignment([slot for slot in slots if slot["index"] not in pinned], [view for view in views if view["player_id"] not in pinned_ids],
                                         {index: view for index, view in current["by_index"].items() if index not in pinned})
    entries.update({index: {"view": view, "basis": view["lock"]["state"], "candidates": [], "via": {}} for index, view in pinned.items()})
    if consensus_authority and consensus_basis["state"] in {"AVAILABLE", "PARTIAL"}:
        entries = apply_consensus_ranks(slots, entries, views)
    lineup_ids = {entry["view"]["player_id"] for entry in entries.values() if entry["view"] is not None}
    bench_views = [view for view in views if view["player_id"] is not None and view["player_id"] not in lineup_ids and view["availability"] != "UNAVAILABLE"]
    pairs, moves = _lineup_changes(slots, entries, current["by_index"]) if has_current else ([], [])
    paired = {pair["index"]: pair["sit"] for pair in pairs if pair["start"] is not None}
    identity_blocked = [view for view in views if view["availability_reason"] == "IDENTITY_UNRESOLVED"]
    lock_blocked = [view for view in views if view["availability_reason"] == "LOCK_UNVERIFIED"]
    current_ids = {view["player_id"] for view in current["by_index"].values()}
    comparison_pool = [view for view in views if view["player_id"] is not None and view["player_id"] not in lineup_ids and view["player_id"] not in current_ids
                       and view["availability_reason"] not in NOT_COMPARABLE_REASONS]
    slot_labels = {slot["index"]: slot["slot"] for slot in slots}
    lineup_slot_by_id = {entry["view"]["player_id"]: slot_labels[index] for index, entry in entries.items() if entry["view"] is not None}
    decisions = [
        _slot_decision(slot, entries[slot["index"]], current_view=current["by_index"].get(slot["index"]), paired_sit=paired.get(slot["index"]),
                       bench=bench_views, slot_contract=slot_contract, current_lineup=current, has_current=has_current, identity_blocked=identity_blocked,
                       slot_labels=slot_labels, lineup_slot_by_id=lineup_slot_by_id, consensus_authority=consensus_authority, lock_blocked=lock_blocked,
                       comparison_pool=comparison_pool, projection_action_threshold=projection_action_threshold)
        for slot in slots
    ]
    by_index = {decision["index"]: decision for decision in decisions}
    changes = [{
        "slot": pair["slot"], "sit_slot": pair["sit_slot"],
        "start": _compact(pair["start"]) if pair["start"] is not None else None, "sit": _compact(pair["sit"]) if pair["sit"] is not None else None,
        "verb": ("FLEX" if slots[pair["index"]]["flex"] else "START") if pair["start"] is not None else "SIT",
        "decision": by_index[pair["index"]]["decision"], "status": by_index[pair["index"]]["status"], "why": by_index[pair["index"]]["why"],
        "decision_confidence": by_index[pair["index"]]["decision_confidence"], "edge": by_index[pair["index"]]["edge"]["value"],
    } for pair in pairs]
    lock_summary = _lock_summary(views, decisions, mode=mode, evaluated_at=now)
    summary, attention, decision_list = _summary(decisions, pairs, notices, has_current, lock_summary)
    states = {decision["decision_confidence"]["state"] for decision in decisions}
    return {
        **contract,
        "state": "BLOCKED" if "BLOCKED" in states else "INSUFFICIENT_EVIDENCE" if "INSUFFICIENT_EVIDENCE" in states else "PRELIMINARY" if states & {"PRELIMINARY", "DEGRADED"} else "ESTABLISHED",
        "blocker": None,
        "recommended_lineup": [{
            "slot": decision["slot"], "player": _name(decision["recommended"]) if decision["recommended"] is not None else None,
            "player_id": (decision["recommended"] or {}).get("player_id"), "position": (decision["recommended"] or {}).get("position"),
            "basis": decision["basis"], "decision": decision["decision"], "status": decision["status"],
        } for decision in decisions],
        "slots": decisions, "attention": attention, "decision_list": decision_list,
        "changes": changes, "moves": moves, "bench": _bench(views, lineup_ids), "summary": summary,
        "what_could_change": _lineup_triggers(decisions, value_basis, notices),
        "projection_comparisons": _projection_comparisons(decisions), "lock_summary": lock_summary,
        "forward_validation": build_forward_validation_snapshots(views, decisions, season=season, week=week, captured_at=now),
    }


def provider_projection_players(contract: Mapping[str, Any], roster: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Roster rows whose projections can inform a decision or a projection comparison; empty when no slot has one."""
    if not any(decision["status"] not in {"NO_ALTERNATIVE", "VACANT", "LOCKED"} for decision in contract.get("slots") or []):
        return []
    rows = list(roster or [])
    # Benched players withheld only because their kickoff is unverified still need projections for informational comparisons.
    return [rows[view["row_index"]] for view in contract.get("players") or []
            if view["player_id"] is not None and view.get("identity_state") == "RESOLVED"
            and (view["availability"] != "UNAVAILABLE" or view["availability_reason"] == "LOCK_UNVERIFIED")]


def legacy_lineup_rows(contract: Mapping[str, Any], roster: Sequence[Mapping[str, Any]]):
    """Starters/bench in the legacy row shape for existing My Team builders, derived from this contract."""
    rows = list(roster or [])
    starters, used = [], set()
    for decision in contract.get("slots") or []:
        view = decision["recommended"]
        if view is None:
            starters.append({
                "slot": decision["slot"], "player": "Vacant" if decision["status"] == "VACANT" else "Unresolved", "position": "/".join(decision["eligible_positions"]),
                "nfl_team": "--", "vacant": True, "decision": "MONITOR", "reason": decision["why"], "weekly_score": None, "weekly_baseline": None,
                "injury_status": "Needs roster decision", "opponent": None, "is_bye": False, "evidence_gaps": [], "evidence_ready": False, "confidence": {"label": "BLOCKED", "score": 0},
            })
            continue
        used.add(view["row_index"])
        row = dict(rows[view["row_index"]])
        row.update(slot=decision["slot"], vacant=False, decision=decision["decision"], reason=decision["why"], evidence_ready=row.get("weekly_score") is not None)
        row.setdefault("confidence", evidence_completeness(row))
        starters.append(row)
    views = {view["row_index"]: view for view in contract.get("players") or []}
    bench = []
    for index, original in enumerate(rows):
        if index in used:
            continue
        row = dict(original)
        view = views.get(index) or {}
        row.update(vacant=False, decision="SIT" if view.get("availability") == "AVAILABLE" else "MONITOR", evidence_ready=row.get("weekly_score") is not None)
        row.setdefault("confidence", evidence_completeness(row))
        bench.append(row)
    bench.sort(key=lambda row: (_finite(row.get("weekly_score")) is None, -(_finite(row.get("weekly_score")) or 0), str(row.get("player") or "")))
    for order, row in enumerate(bench, 1):
        row["bench_order"] = order
    values = [_finite(row.get("weekly_score")) for row in starters if not row.get("vacant")]
    total = round(sum(values), 2) if values and all(value is not None for value in values) else None
    vacancies = [row["slot"] for row in starters if row.get("vacant")]
    return starters, bench, total, vacancies


def lineup_reconciliation_view(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Current-vs-recommended differences in the legacy reconciliation shape."""
    current = contract.get("current_lineup") or {}
    if current.get("state") not in {"AVAILABLE", "INCOMPLETE"} or contract.get("state") == "BLOCKED" and contract.get("blocker"):
        return {"state": "UNAVAILABLE", "blocker": current.get("blocker") or contract.get("blocker") or "CURRENT_LINEUP_UNAVAILABLE",
                "current": list(current.get("slots") or []), "recommended": [], "changes": [], "changed_recommended": []}
    changes = [{
        "slot": change["slot"], "current": (change["sit"] or {}).get("player"), "current_id": (change["sit"] or {}).get("player_id"),
        "recommended": change["start"]["player"], "recommended_id": change["start"]["player_id"], "authority": change["decision"],
        "reason": change["why"], "recommended_player": change["start"], "watch_item": None, "confidence": None,
    } for change in contract.get("changes") or [] if change["start"] is not None]
    return {"state": "AVAILABLE", "blocker": None, "current": list(current.get("slots") or []), "recommended": list(contract.get("recommended_lineup") or []),
            "changes": changes, "changed_recommended": [change["recommended_player"] for change in changes]}
