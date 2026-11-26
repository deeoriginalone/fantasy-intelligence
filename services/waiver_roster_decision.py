"""W1 waiver roster decision engine: compare verified available players with the manager's own roster.

Pure and read-only. It consumes contracts the waiver route already builds (verified candidates, the
current Sleeper roster and lineup, the identity-verified FantasyPros consensus via DynastyProcess,
schedule-owned bye and kickoff-lock evidence, league settings, and the verified FAAB balance) and never
reads the network or database or submits a claim, drop, or bid.

Consensus ranks are ordinal and position-specific: lower ECR is better, ranks are never converted into
fantasy points, never compared across positions, and an unranked player is never treated as worse.
Rest-of-season ranks are used only for bench/depth comparisons, including whether a player can be released.

W3 publishes the waiver.ros_value.v1 contract: per-player rest-of-season states from the same DynastyProcess
snapshot, same-position comparisons only, protected players with reasons, and a post-move lineup check. A drop is
recommended only when fresh rest-of-season evidence for both players and the post-move roster both support it.

W4 adds waiver.ros_materiality.v1 and waiver.replacement_context.v1. An ordinal ROS ECR edge authorizes a release only
when the published expert ranges are clearly separated (the candidate's worst expert rank is better than the roster
player's best). Replacement context describes, per position, how many verified available players reach a player's
expert range. Neither produces points, percentages, a value score, or a FAAB amount.

waiver.cross_position_drop.v1 lets a move release a bench player at a different position when no same-position release is verified:
the candidate must fill a verified need (the shared team-needs depth target) or be an expert-unanimous starter upgrade, and rank ahead
of the player he displaces at his own position for the rest of the season; the released player must be an unprotected, unlocked,
ranked bench player at a surplus position that keeps its depth target, with STRONG waiver replacement depth, and the post-move lineup
check must pass. Ranks are still never compared across positions.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

from services.game_lock import build_game_lock
from services.schedule_bye_evidence import team_bye_evidence
from services.team_codes import canonical_team
from services.team_needs import team_needs_contract

CONTRACT_ID = "waiver.roster_decision.v1"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
CONSENSUS_SOURCE = "FantasyPros consensus via DynastyProcess"
SLOT_POSITIONS = {
    "QB": ("QB",), "RB": ("RB",), "WR": ("WR",), "TE": ("TE",), "K": ("K",), "DEF": ("DEF",), "DST": ("DEF",),
    "FLEX": ("RB", "WR", "TE"), "W/R/T": ("RB", "WR", "TE"), "WR/RB/TE": ("RB", "WR", "TE"),
    "WRRB_FLEX": ("RB", "WR"), "REC_FLEX": ("WR", "TE"), "SUPER_FLEX": ("QB", "RB", "WR", "TE"),
}
COVERAGE_HEALTH = ("HEALTHY", "QUESTIONABLE")
UNUSABLE_HEALTH = ("OUT", "IR")
DROPPABLE_LOCK_STATES = ("OPEN", "BYE")
NO_SAFE_DROP_REASON = "CANDIDATE IMPROVES THE ROSTER, BUT NO SAFE DROP IS VERIFIED."
FAAB_DISCLOSURE = "Advanced FAAB valuation is not yet supported."
ROS_UNAVAILABLE_LABEL = "REST-OF-SEASON VALUE: UNAVAILABLE"
KIND_LABELS = {"MUST_FILL": "Must fill this week", "CURRENT_WEEK_UPGRADE": "Current-week upgrade", "DEPTH_UPGRADE": "Bench depth (rest of season)"}
DECISION_LABELS = {"ADD": "ADD", "ADD_DROP": "ADD + DROP", "MONITOR": "MONITOR"}
URGENCY_ORDER = {"REQUIRED": 0, "MATERIAL": 1, "OPTIONAL": 2}
KIND_ORDER = {"MUST_FILL": 0, "CURRENT_WEEK_UPGRADE": 1, "DEPTH_UPGRADE": 2}
UNRANKED = {"state": "UNRANKED", "ecr": None}
ROS_VALUE_CONTRACT_ID = "waiver.ros_value.v1"
ROS_PLAYER_STATES = ("RANKED", "UNRANKED", "STALE", "IDENTITY_UNRESOLVED", "POSITION_CONFLICT", "SCORING_UNSUPPORTED", "SOURCE_UNAVAILABLE", "BLOCKED")
ROS_IDENTITY_FAILURES = frozenset({"PROVIDER_ID_ABSENT_FROM_CROSSWALK", "SLEEPER_ID_MISSING", "DUPLICATE_PROVIDER_ID", "DUPLICATE_SLEEPER_ID",
                                   "CONTEXTUAL_IDENTITY_AMBIGUOUS", "TEAM_DEFENSE_IDENTITY_UNVERIFIED", "DUPLICATE_RANK_PLAYER_ID"})
HEALTH_RISK_STATES = ("QUESTIONABLE", "DOUBTFUL")
MOVE_STATE_LABELS = {
    "ADD_DROP": "ADD + DROP", "ADD_DROP_CROSS": "ADD + DROP — CROSS-POSITION", "ADD": "ADD — OPEN ROSTER SPOT", "NO_SAFE_DROP": "MONITOR — NO SAFE DROP VERIFIED",
    "ROS_VALUE_UNAVAILABLE": "MONITOR — ROS VALUE UNAVAILABLE", "QUESTIONABLE": "MONITOR — HEALTH DESIGNATION",
    "FLEX_CROSS_POSITION": "MONITOR — CROSS-POSITION CHOICE REQUIRED", "NO_CANDIDATE": "MONITOR — NO VERIFIED REPLACEMENT",
    "ROS_EDGE_NOT_MATERIAL": "MONITOR — CLOSE ROS CALL", "ROS_MATERIALITY_UNVERIFIED": "MONITOR — ROS MATERIALITY UNVERIFIED",
}
ROS_MATERIALITY_CONTRACT_ID = "waiver.ros_materiality.v1"
REPLACEMENT_CONTEXT_CONTRACT_ID = "waiver.replacement_context.v1"
MATERIALITY_BLOCKERS = ("ROS_EDGE_NOT_MATERIAL", "ROS_MATERIALITY_UNVERIFIED")
MATERIALITY_LABELS = {"CLEAR_EDGE": "CLEAR ROS EDGE", "CLOSE_CALL": "CLOSE ROS CALL", "TIED": "COMPARABLE ROS VALUE", "ROSTER_BETTER": "ROSTER PLAYER AHEAD",
                      "UNVERIFIED": "MATERIALITY UNVERIFIED", "NOT_COMPARABLE": "NOT COMPARABLE", "NOT_APPLICABLE": "NOT APPLICABLE"}
REPLACEMENT_LABELS = {"STRONG": "REPLACEMENT DEPTH STRONG", "LIMITED": "REPLACEMENT DEPTH LIMITED", "SCARCE": "NO COMPARABLE REPLACEMENT",
                      "UNVERIFIED": "REPLACEMENT CONTEXT UNVERIFIED"}
REPLACEMENT_RULE = ("Comparable means a healthy, addable available player at the same position whose fresh rest-of-season expert range reaches this "
                    "player's range (his best published expert rank is at or ahead of this player's worst). STRONG: two or more comparable players, so one "
                    "competing claim still leaves another; LIMITED: exactly one; SCARCE: none.")
POSITION_PLURALS = {"QB": "QBs", "RB": "RBs", "WR": "WRs", "TE": "TEs", "K": "kickers", "DEF": "defenses"}
CROSS_POSITION_CONTRACT_ID = "waiver.cross_position_drop.v1"
CROSS_POSITION_RULE = ("A bench player at a different position is released only when no same-position release is verified and: the candidate is healthy, "
                       "verified available, and fresh-ranked for the rest of the season; he fills a required slot, fills a position below its supported "
                       "depth target, or is a starter upgrade every published expert agrees on (or a clear rest-of-season edge), and he ranks ahead of the "
                       "player he displaces at his own position for the rest of the season; the released player is an unprotected, unlocked bench player "
                       "with a fresh rank, the weakest releasable player at a position that stays at or above its depth target, and has STRONG waiver "
                       "replacement depth; and every starting slot, including FLEX, stays fillable. Ranks are never compared across positions.")
CROSS_ADD_BASIS_TEXT = {"REQUIRED_SLOT_FILL": "fills a required starting slot this week", "VERIFIED_NEED": "fills a verified depth need",
                        "UNANIMOUS_STARTER_UPGRADE": "is a starter upgrade every published expert agrees on this week",
                        "CLEAR_ROS_EDGE": "is clearly ahead for the rest of the season"}
DROP_CANDIDATES_CONTRACT_ID = "waiver.drop_candidates.v1"
MANAGER_PLAN_CONTRACT_ID = "waiver.manager_plan.v1"
VALUE_BID_UNAVAILABLE = "VALUE-BASED BID UNAVAILABLE"


def normalize_position(value: Any) -> str:
    value = str(value or "").upper().strip()
    return "DEF" if value == "DST" else value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if isfinite(float(value)) else None


def consensus_rank_row_is_current(row: Any, *, horizon_data: Mapping[str, Any] | None, position: Any, horizon: str, season: Any, week: Any) -> bool:
    """The waiver consensus-rank validity rule: same position, horizon, PPR scoring, season and week, within the source age limit."""
    horizon_data = horizon_data or {}
    if not isinstance(row, Mapping):
        return False
    ecr = row.get("ecr")
    return (
        normalize_position(row.get("position")) == normalize_position(position)
        and row.get("horizon") == horizon
        and row.get("scoring") == "PPR"
        and row.get("season") == season
        and (horizon != "this_week" or row.get("week") == week)
        and isinstance(row.get("source_age_seconds"), (int, float))
        and isinstance(horizon_data.get("max_age_seconds"), (int, float))
        and 0 <= row["source_age_seconds"] <= horizon_data["max_age_seconds"]
        and isinstance(ecr, (int, float)) and not isinstance(ecr, bool)
        and isfinite(float(ecr)) and float(ecr) > 0
    )


def consensus_rank(horizon_data: Mapping[str, Any] | None, player_id: Any, *, position: Any, horizon: str, season: Any, week: Any) -> dict[str, Any]:
    horizon_data = horizon_data or {}
    row = (horizon_data.get("ranks") or {}).get(str(player_id or ""))
    if not consensus_rank_row_is_current(row, horizon_data=horizon_data, position=position, horizon=horizon, season=season, week=week):
        return {**UNRANKED, "horizon": horizon}
    return {
        "state": "RANKED", "horizon": horizon, "ecr": float(row["ecr"]),
        "expert_best_rank": _number(row.get("expert_best_rank")), "expert_worst_rank": _number(row.get("expert_worst_rank")),
        "expert_rank_sd": _number(row.get("expert_rank_sd")), "expert_range_state": _range_state(row),
        "source": row.get("source") or horizon_data.get("source") or CONSENSUS_SOURCE,
        "source_date": row.get("source_date"), "source_age_seconds": row.get("source_age_seconds"), "week": row.get("week"),
        "freshness_state": "FRESH",
    }


def _ranked(rank: Mapping[str, Any] | None) -> bool:
    return (rank or {}).get("state") == "RANKED"


def _rank_key(rank: Mapping[str, Any] | None) -> tuple[int, float]:
    return (0, rank["ecr"]) if _ranked(rank) else (1, 0.0)


def _range_text(rank: Mapping[str, Any]) -> str | None:
    best, worst = rank.get("expert_best_rank"), rank.get("expert_worst_rank")
    return f"{best:g}–{worst:g}" if best is not None and worst is not None else None


def _range_state(row: Mapping[str, Any]) -> str:
    """Expert-range integrity: VALID only for a complete, positive range that brackets the consensus rank (best <= ECR <= worst)."""
    published = row.get("expert_range_state")
    if published in ("MISSING", "INVALID"):
        return published
    ecr, best, worst, sd = (row.get(key) for key in ("ecr", "expert_best_rank", "expert_worst_rank", "expert_rank_sd"))
    if best is None and worst is None:
        return "MISSING"
    if any(_number(value) is None for value in (ecr, best, worst)) or best <= 0 or not best <= ecr <= worst:
        return "INVALID"
    if sd is not None and (_number(sd) is None or sd < 0):
        return "INVALID"
    return "VALID"


def expert_separation(candidate_rank: Mapping[str, Any], roster_rank: Mapping[str, Any]) -> dict[str, Any]:
    """UNANIMOUS only when both expert ranges are valid and the candidate's worst published expert rank is ahead of the roster player's best one."""
    valid = all(_range_state(rank) == "VALID" for rank in (candidate_rank, roster_rank))
    candidate_range, roster_range = (_range_text(candidate_rank), _range_text(roster_rank)) if valid else (None, None)
    if not valid:
        state = "UNVERIFIED"
    else:
        state = "UNANIMOUS" if candidate_rank["expert_worst_rank"] < roster_rank["expert_best_rank"] else "SPLIT"
    return {"state": state, "candidate_range": candidate_range, "roster_range": roster_range,
            "rule": "UNANIMOUS when the candidate's worst published expert rank is better than the roster player's best published expert rank."}


def week_context(team: Any, *, season: Any, week: Any, bye_rows: Sequence[Mapping[str, Any]] | None, schedule_rows: Sequence[Mapping[str, Any]] | None,
                 now: Any = None, mode: str = "LIVE", schedule_max_age_seconds: Any = None) -> dict[str, Any]:
    code = canonical_team(team)
    bye = team_bye_evidence(bye_rows, season=season, team=code, week=week, now=now)
    bye_verified = bye.get("authoritative") is True
    on_bye = bye_verified and bye.get("is_current_week_bye") is True
    lock = build_game_lock(code, schedule_rows=schedule_rows, season=season, week=week, now=now, is_bye=on_bye,
                           bye_authoritative=True if on_bye else None, mode=mode, max_age_seconds=schedule_max_age_seconds)
    return {"team": code, "bye_verified": bye_verified, "on_bye": on_bye, "bye_week": bye.get("bye_week"), "lock_state": lock.get("state"),
            "lock_reason": lock.get("reason"), "opponent": lock.get("opponent"), "venue": lock.get("venue"), "kickoff_display": lock.get("kickoff_display")}


def _valid_week(season: Any, week: Any) -> bool:
    return (isinstance(season, int) and not isinstance(season, bool) and season > 0
            and isinstance(week, int) and not isinstance(week, bool) and 1 <= week <= 18)


def _duration_text(seconds: Any) -> str:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        return "an unknown time"
    days, remainder = divmod(int(abs(seconds)), 86400)
    hours = remainder // 3600
    parts = ([f"{days} day{'s' if days != 1 else ''}"] if days else []) + ([f"{hours} hour{'s' if hours != 1 else ''}"] if hours or not days else [])
    return " ".join(parts)


def ranking_horizon_summary(rankings: Mapping[str, Any] | None, horizon: str, *, full_ppr: Any) -> dict[str, Any]:
    """Horizon evidence state (AVAILABLE, STALE, SCORING_UNSUPPORTED, SOURCE_UNAVAILABLE, BLOCKED) from the newest upstream source date."""
    rankings = rankings or {}
    data = dict((rankings.get("horizons") or {}).get(horizon) or {})
    ranks = data.get("ranks") or {}
    max_age = data.get("max_age_seconds")
    latest, age, freshness = data.get("latest_source_date"), data.get("latest_source_age_seconds"), data.get("freshness_state")
    if freshness is None and ranks:
        # Evaluations without the source summary: derive it from rank rows that carry their own upstream source date and age.
        rows = [row for row in ranks.values() if isinstance(row, Mapping) and row.get("source_date")]
        ages = [row["source_age_seconds"] for row in rows if isinstance(row.get("source_age_seconds"), (int, float)) and not isinstance(row.get("source_age_seconds"), bool)]
        age = min(ages) if ages else None
        latest = max((str(row["source_date"]) for row in rows), default=None)
        freshness = ("UNAVAILABLE" if age is None or latest is None or not isinstance(max_age, (int, float)) else "FUTURE_DATED" if age < 0
                     else "FRESH" if age <= max_age else "STALE")
    freshness = freshness or "UNAVAILABLE"
    label = "rest-of-season" if horizon == "rest_of_season" else "current-week"
    if full_ppr is not True:
        state, blocker = "SCORING_UNSUPPORTED", "LEAGUE_NOT_FULL_PPR"
        reason = "League reception scoring is not verified as Full PPR, so PPR consensus ranks cannot be applied."
    elif freshness == "STALE":
        state, blocker = "STALE", "SOURCE_STALE"
        reason = f"The newest {label} consensus was published {latest}, {_duration_text(age)} ago; the limit is {_duration_text(max_age)}."
    elif freshness == "FUTURE_DATED":
        state, blocker, reason = "BLOCKED", "SOURCE_FUTURE_DATED", f"The {label} consensus carries a future source date ({latest}), so it cannot be trusted."
    elif freshness == "FRESH" and data.get("state") == "AVAILABLE" and ranks:
        state, blocker = "AVAILABLE", None
        reason = f"Fresh {label} consensus published {latest} ({_duration_text(age)} old; limit {_duration_text(max_age)})."
    elif freshness == "FRESH":
        state, blocker, reason = "BLOCKED", "NO_VERIFIED_RANKS", f"The {label} consensus is current, but no rank passed season and identity verification."
    elif ranks:
        state, blocker = "BLOCKED", "SOURCE_FRESHNESS_UNVERIFIED"
        reason = f"{label.capitalize()} consensus ranks are loaded, but no upstream source date and age limit verify their freshness, so they are not used."
    else:
        state, blocker = "SOURCE_UNAVAILABLE", "RANKING_SOURCE_UNAVAILABLE"
        reason = f"No {label} consensus is loaded" + (f" ({rankings['refresh_error']})" if rankings.get("refresh_error") else "") + "."
    identity_failures: dict[str, str] = {}
    for diagnostic in data.get("diagnostics") or []:
        failure = str(diagnostic.get("reason") or "")
        if failure == "POSITION_CONFLICT" or failure in ROS_IDENTITY_FAILURES:
            # Research candidates share the published name and position; they stay unresolved and never receive the rank.
            linked = ([match.get("sleeper_id") for match in diagnostic.get("crosswalk_matches") or []] + [diagnostic.get("player_id")]
                      + [candidate.get("player_id") for candidate in diagnostic.get("investigation_candidates") or []])
            for player_id in linked:
                if player_id not in (None, "", "NA"):
                    identity_failures.setdefault(str(player_id), failure)
    by_position: dict[str, int] = {}
    if state == "AVAILABLE":
        for row in ranks.values():
            position = normalize_position((row or {}).get("position"))
            by_position[position] = by_position.get(position, 0) + 1
    return {"horizon": horizon, "state": state, "blocker": blocker, "reason": reason, "source": rankings.get("source") or CONSENSUS_SOURCE,
            "source_date": latest, "age_seconds": age, "max_age_seconds": max_age, "freshness_state": freshness,
            "ranked_count": sum(by_position.values()), "ranked_by_position": by_position, "retrieved_at": rankings.get("last_successful_refresh"),
            "refresh_error": rankings.get("refresh_error"), "version": rankings.get("version"), "identity_failures": identity_failures,
            "freshness_rule": "Freshness comes only from the upstream scrape date; reading or re-downloading the cache never renews it."}


def ros_player_value(summary: Mapping[str, Any], rankings: Mapping[str, Any] | None, player_id: Any, position: Any, *, season: Any) -> dict[str, Any]:
    """One player's waiver.ros_value.v1 state; a missing rank stays UNRANKED and is never replaced by a number."""
    pid, position = str(player_id or ""), normalize_position(position)
    view = {"contract_id": ROS_VALUE_CONTRACT_ID, "player_id": pid, "position": position, "ros_ecr": None, "source": summary.get("source"),
            "source_date": summary.get("source_date"), "age_seconds": summary.get("age_seconds"), "freshness_state": summary.get("freshness_state"),
            "identity_method": None, "evidence_state": None, "blocker": None, "range_state": "NOT_RANKED", "expert_best_rank": None,
            "expert_worst_rank": None, "expert_rank_sd": None}
    if summary.get("state") != "AVAILABLE":
        state = summary.get("state") if summary.get("state") in {"STALE", "SCORING_UNSUPPORTED", "SOURCE_UNAVAILABLE"} else "BLOCKED"
        return {**view, "evidence_state": state, "blocker": summary.get("blocker")}
    data = ((rankings or {}).get("horizons") or {}).get("rest_of_season") or {}
    row = (data.get("ranks") or {}).get(pid)
    if row is None:
        failure = (summary.get("identity_failures") or {}).get(pid)
        if failure:
            return {**view, "evidence_state": "POSITION_CONFLICT" if failure == "POSITION_CONFLICT" else "IDENTITY_UNRESOLVED", "blocker": failure}
        return {**view, "evidence_state": "UNRANKED", "blocker": "NO_ROS_RANK"}
    if normalize_position(row.get("position")) != position:
        return {**view, "evidence_state": "POSITION_CONFLICT", "blocker": "POSITION_CONFLICT"}
    if not consensus_rank_row_is_current(row, horizon_data=data, position=position, horizon="rest_of_season", season=season, week=None):
        return {**view, "evidence_state": "BLOCKED", "blocker": "ROS_RANK_ROW_INVALID"}
    if not row.get("source_date"):
        return {**view, "evidence_state": "BLOCKED", "blocker": "ROS_SOURCE_DATE_MISSING"}
    range_state = _range_state(row)
    valid = range_state == "VALID"
    # An invalid or missing expert range keeps the rank; it only withholds materiality evidence.
    return {**view, "ros_ecr": float(row["ecr"]), "source_date": row.get("source_date"), "age_seconds": row.get("source_age_seconds"),
            "freshness_state": "FRESH", "identity_method": row.get("identity_method"), "evidence_state": "RANKED", "range_state": range_state,
            "expert_best_rank": float(row["expert_best_rank"]) if valid else None, "expert_worst_rank": float(row["expert_worst_rank"]) if valid else None,
            "expert_rank_sd": _number(row.get("expert_rank_sd")) if valid else None}


def compare_ros_values(candidate: Mapping[str, Any], roster: Mapping[str, Any], *, candidate_name: Any, roster_name: Any) -> dict[str, Any]:
    """Same-position rest-of-season comparison (lower ECR is better); ranks at different positions are never compared."""
    if candidate.get("position") != roster.get("position"):
        return {"state": "NOT_COMPARABLE", "reason": f"Rest-of-season ranks are positional; a {candidate.get('position')} rank is never compared with a {roster.get('position')} rank."}
    for name, value in ((candidate_name, candidate), (roster_name, roster)):
        if value.get("evidence_state") != "RANKED":
            state_text = str(value.get("evidence_state") or "UNAVAILABLE").replace("_", " ").lower()
            return {"state": "UNVERIFIED", "blocker": value.get("blocker"), "reason": f"{name} has no fresh rest-of-season rank ({state_text})."}
    position, candidate_ecr, roster_ecr = candidate["position"], candidate["ros_ecr"], roster["ros_ecr"]
    # Ordinal order only: whether the edge is meaningful is decided by ros_materiality, never by this ECR order.
    if candidate_ecr < roster_ecr:
        state, reason = "CANDIDATE_BETTER", f"{candidate_name} ranks ahead of {roster_name} for the rest of the season ({position} ROS ECR {candidate_ecr:.1f} vs {roster_ecr:.1f}; lower is better)."
    elif candidate_ecr > roster_ecr:
        state, reason = "ROSTER_BETTER", f"{roster_name} ranks ahead of {candidate_name} for the rest of the season ({position} ROS ECR {roster_ecr:.1f} vs {candidate_ecr:.1f}; lower is better)."
    else:
        state, reason = "TIED", f"Rest-of-season consensus does not separate them (both {position} ROS ECR {candidate_ecr:.1f})."
    return {"state": state, "candidate_ecr": candidate_ecr, "roster_ecr": roster_ecr, "reason": reason}


def _span(value: Mapping[str, Any]) -> str | None:
    return f"{value['expert_best_rank']:g}–{value['expert_worst_rank']:g}" if value.get("range_state") == "VALID" else None


def ros_materiality(candidate: Mapping[str, Any], roster: Mapping[str, Any], *, candidate_name: Any, roster_name: Any) -> dict[str, Any]:
    """waiver.ros_materiality.v1: whether a same-position rest-of-season edge is clearly separated by the published expert ranges.

    ROS ECR stays an ordinal positional rank (lower is better). CLEAR_EDGE needs the candidate's worst published expert rank to
    be better than the roster player's best one; no ECR-gap threshold, points, percentage, or dispersion score is used.
    """
    position, candidate_ecr, roster_ecr = candidate.get("position"), candidate.get("ros_ecr"), roster.get("ros_ecr")
    view = {"contract_id": ROS_MATERIALITY_CONTRACT_ID, "position": position, "candidate": candidate_name, "roster": roster_name,
            "candidate_ecr": candidate_ecr, "roster_ecr": roster_ecr, "candidate_range": _span(candidate), "roster_range": _span(roster),
            "candidate_sd": candidate.get("expert_rank_sd"), "roster_sd": roster.get("expert_rank_sd"),
            "rule": "CLEAR_EDGE only when the candidate's worst published expert rank is better than the roster player's best (lower is better)."}

    def result(state, separation, evidence_state, effect, reason, summary=None):
        return {**view, "state": state, "label": MATERIALITY_LABELS[state], "separation": separation, "evidence_state": evidence_state,
                "decision_effect": effect, "reason": reason, "summary": summary or reason}

    if position != roster.get("position"):
        return result("NOT_COMPARABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE",
                      f"Rest-of-season ranks are positional; a {position} rank is never compared with a {roster.get('position')} rank.")
    for name, value in ((candidate_name, candidate), (roster_name, roster)):
        if value.get("evidence_state") != "RANKED":
            state_text = str(value.get("evidence_state") or "UNAVAILABLE").replace("_", " ").lower()
            return result("UNVERIFIED", "UNVERIFIED", "ROS_UNVERIFIED", "DOES_NOT_SUPPORT_RELEASE",
                          f"{name} has no fresh rest-of-season rank ({state_text}), so a rest-of-season edge cannot be verified.")
    if candidate_ecr == roster_ecr:
        return result("TIED", "UNVERIFIED" if not (_span(candidate) and _span(roster)) else "OVERLAPPING", "AVAILABLE", "DOES_NOT_SUPPORT_RELEASE",
                      f"Rest-of-season consensus does not separate them (both {position} ROS ECR {candidate_ecr:.1f}).")
    ahead, behind = (candidate_name, roster_name) if candidate_ecr < roster_ecr else (roster_name, candidate_name)
    order = f"{ahead} ranks ahead of {behind} for the rest of the season ({position} ROS ECR {min(candidate_ecr, roster_ecr):.1f} vs {max(candidate_ecr, roster_ecr):.1f}; lower is better)"
    missing = [name for name, value in ((candidate_name, candidate), (roster_name, roster)) if value.get("range_state") != "VALID"]
    if missing:
        invalid = any(value.get("range_state") == "INVALID" for value in (candidate, roster))
        evidence = "RANGE_INVALID" if invalid else "RANGE_MISSING"
        problem = "failed integrity checks" if invalid else "are unavailable"
        if candidate_ecr > roster_ecr:
            return result("ROSTER_BETTER", "UNVERIFIED", evidence, "KEEP_ROSTER_PLAYER", f"{order}.")
        return result("UNVERIFIED", "UNVERIFIED", evidence, "DOES_NOT_SUPPORT_RELEASE",
                      f"{order}, but the expert ranges for {' and '.join(missing)} {problem}, so consensus separation cannot be verified.")
    if candidate_ecr > roster_ecr:
        apart = roster["expert_worst_rank"] < candidate["expert_best_rank"]
        return result("ROSTER_BETTER", "NON_OVERLAPPING" if apart else "OVERLAPPING", "AVAILABLE", "KEEP_ROSTER_PLAYER",
                      f"{order}" + (f", and their expert ranges do not overlap ({roster_name} {_span(roster)} vs {candidate_name} {_span(candidate)})." if apart else "."))
    if candidate["expert_worst_rank"] < roster["expert_best_rank"]:
        return result("CLEAR_EDGE", "NON_OVERLAPPING", "AVAILABLE", "SUPPORTS_RELEASE",
                      f"Clear rest-of-season edge: every published expert rank for {candidate_name} ({_span(candidate)}) is better than every published "
                      f"expert rank for {roster_name} ({_span(roster)}); {position} ROS ECR {candidate_ecr:.1f} vs {roster_ecr:.1f}.",
                      f"Expert ranges do not overlap ({candidate_name} {_span(candidate)} vs {roster_name} {_span(roster)}).")
    return result("CLOSE_CALL", "OVERLAPPING", "AVAILABLE", "DOES_NOT_SUPPORT_RELEASE",
                  f"{order}, but their expert ranges overlap ({candidate_name} {_span(candidate)} vs {roster_name} {_span(roster)}), so the edge is a close call.",
                  f"Expert ranges overlap ({candidate_name} {_span(candidate)} vs {roster_name} {_span(roster)}), so the rest-of-season edge is a close call, not a clear upgrade.")


def _pool_entry(model: Mapping[str, Any]) -> dict[str, Any]:
    return {**model["ros_value"], "player": model["name"], "team": model["context"]["team"]}


def _replacement_pools(candidate_models: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-position replacement population, grouped and sorted once: verified available players with a fresh ROS rank, a valid expert range, and a supported add."""
    pools = {}
    for position in POSITIONS:
        at = [model for model in candidate_models if model["position"] == position]
        ranked = [model for model in at if model["ros_value"]["evidence_state"] == "RANKED"]
        capable = [model for model in ranked if model["ros_value"]["range_state"] == "VALID"]
        actionable = [model for model in ranked if model["depth_addable"]]
        comparison = sorted((model for model in capable if model["depth_addable"]), key=lambda model: (model["ros_value"]["ros_ecr"], model["name"], model["id"]))
        pools[position] = {"position": position, "comparison": [_pool_entry(model) for model in comparison],
                           "counts": {"available": len(at), "ros_ranked": len(ranked), "ros_unranked": len(at) - len(ranked), "materiality_capable": len(capable),
                                      "actionable": len(actionable), "comparison": len(comparison)}}
    return pools


def _option_text(entry: Mapping[str, Any]) -> str:
    return f"{entry['player']} ({entry['position']} ROS ECR {entry['ros_ecr']:.1f}, experts {_span(entry)})"


def _possessive(name: Any) -> str:
    return f"{name}'" if str(name).endswith("s") else f"{name}'s"


def _names(names: Sequence[Any]) -> str:
    names = [str(name) for name in names]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def replacement_context(value: Mapping[str, Any], name: Any, pool: Mapping[str, Any] | None, *, exclude_ids: Sequence[Any] = ()) -> dict[str, Any]:
    """waiver.replacement_context.v1: how replaceable one player's rest-of-season tier is from the verified available pool at his position.

    Positional only, built from the W2 universe and W3 evidence; it never yields points, a value score, or a FAAB amount.
    """
    position = value.get("position")
    plural = POSITION_PLURALS.get(position, f"{position}s")
    base = {"contract_id": REPLACEMENT_CONTEXT_CONTRACT_ID, "player": name, "player_id": value.get("player_id"), "position": position,
            "counts": dict((pool or {}).get("counts") or {}), "rule": REPLACEMENT_RULE, "comparable_count": None, "clearly_ahead_count": None,
            "population": None, "nearest": []}

    def unverified(reason):
        return {**base, "state": "UNVERIFIED", "label": REPLACEMENT_LABELS["UNVERIFIED"], "reason": reason}

    if value.get("evidence_state") != "RANKED":
        return unverified(f"{name} has no fresh rest-of-season rank, so replaceability cannot be judged.")
    if value.get("range_state") != "VALID":
        return unverified(f"{_possessive(name)} rest-of-season expert range is unavailable or failed integrity checks, so replaceability cannot be judged.")
    subject, skipped = str(value.get("player_id")), {str(player_id) for player_id in exclude_ids}
    comparison = (pool or {}).get("comparison") or []
    recommended = [entry["player"] for entry in [*((pool or {}).get("recommended_adds") or []), *(entry for entry in comparison if str(entry["player_id"]) in skipped)]
                   if str(entry["player_id"]) != subject]
    note = f" Excludes {_names(recommended)}, already recommended to add." if recommended else ""
    options = [entry for entry in comparison if str(entry["player_id"]) not in skipped | {subject}]
    if not options:
        return unverified(f"No healthy, addable available {position} has a fresh rest-of-season rank with a valid expert range, so replaceability cannot be judged.{note}")
    reach = [entry for entry in options if entry["expert_best_rank"] <= value["expert_worst_rank"]]
    ahead = [entry for entry in reach if entry["expert_worst_rank"] < value["expert_best_rank"]]
    band, owner = _span(value), _possessive(name)
    if len(reach) >= 2:
        state = "STRONG"
        named = f" of them, {_names([entry['player'] for entry in ahead])}," if 0 < len(ahead) <= 3 else " of them"
        reason = (f"{len(reach)} healthy available {plural} have fresh rest-of-season expert ranges reaching {owner} ({band})"
                  + (f"; {len(ahead)}{named} {'is' if len(ahead) == 1 else 'are'} clearly ahead" if ahead else "") + f".{note}")
    elif reach:
        state = "LIMITED"
        reason = f"Only {_option_text(reach[0])} reaches {owner} rest-of-season expert range ({band})" + (" and is clearly ahead." if ahead else ".") + note
    else:
        state = "SCARCE"
        reason = f"No healthy available {position} reaches {owner} rest-of-season expert range ({band}); the best available is {_option_text(options[0])}.{note}"
    return {**base, "state": state, "label": REPLACEMENT_LABELS[state], "comparable_count": len(reach), "clearly_ahead_count": len(ahead),
            "population": len(options), "nearest": [dict(entry) for entry in (reach or options)[:3]], "reason": reason}


def player_value_context(decision: Mapping[str, Any] | None, ros_value: Mapping[str, Any], name: Any, *, rostered: bool) -> dict[str, Any]:
    """Lookup view for one player: ROS materiality against the natural comparison and replacement context, from the decision's stored pools.

    A rostered player is compared with the best verified available player at his position; an available player is compared with
    your weakest rest-of-season-ranked active player at that position.
    """
    position = ros_value.get("position")
    pool = (((decision or {}).get("replacement") or {}).get("positions") or {}).get(position)
    if not pool:
        reason = "Rest-of-season materiality and replacement context were not evaluated for this position."
        return {"materiality": {"state": "NOT_APPLICABLE", "label": MATERIALITY_LABELS["NOT_APPLICABLE"], "reason": reason},
                "replacement": {"state": "UNVERIFIED", "label": REPLACEMENT_LABELS["UNVERIFIED"], "reason": reason, "nearest": []}}
    context = replacement_context(ros_value, name, pool)
    verified = next((move for move in (decision or {}).get("moves") or [] if (move.get("drop") or {}).get("player_id") == ros_value.get("player_id")), None)
    if rostered and verified and verified["drop"].get("basis") == "cross_position":
        # Released for a player at a different position: positional ranks are not compared, so no materiality applies to him.
        add = verified.get("add") or {}
        reason = (f"Verified release for ADD {add.get('player')} ({add.get('position')}), a different position: the release rests on {position} surplus and "
                  f"waiver replacement depth, never on a cross-position rank comparison.")
        return {"materiality": {"state": "NOT_APPLICABLE", "label": "CROSS-POSITION RELEASE", "reason": reason}, "replacement": context}
    if rostered and verified:
        # He is already the verified drop of a priority move: the materiality that matters is against the player replacing him.
        return {"materiality": verified["drop"]["materiality"], "replacement": context}
    if rostered:
        best = next((entry for entry in pool["comparison"] if str(entry["player_id"]) != str(ros_value.get("player_id"))), None)
        materiality = (ros_materiality(best, ros_value, candidate_name=best["player"], roster_name=name) if best else
                       {"state": "NOT_APPLICABLE", "label": MATERIALITY_LABELS["NOT_APPLICABLE"],
                        "reason": f"No healthy available {position} has a fresh rest-of-season rank with a valid expert range to compare."})
    else:
        reference = pool.get("reference")
        materiality = (ros_materiality(ros_value, reference["ros_value"], candidate_name=name, roster_name=reference["player"]) if reference else
                       {"state": "NOT_APPLICABLE", "label": MATERIALITY_LABELS["NOT_APPLICABLE"],
                        "reason": f"You have no active {position} with a fresh rest-of-season rank to compare with."})
    return {"materiality": materiality, "replacement": context}


def _player_view(model: Mapping[str, Any] | None, *, include_ros: bool = False) -> dict[str, Any] | None:
    if not model:
        return None
    view = {"player_id": model["id"], "player": model["name"], "position": model["position"], "team": model["context"]["team"],
            "rank": dict(model["week_rank"]), "health_state": model["health_state"], "lock_state": model["context"]["lock_state"],
            "opponent": model["context"]["opponent"], "venue": model["context"]["venue"], "kickoff_display": model["context"]["kickoff_display"],
            "on_bye": model["context"]["on_bye"]}
    if include_ros:
        view["ros_rank"] = dict(model["ros_rank"])
        view["ros_value"] = dict(model["ros_value"])
    return view


def build_waiver_roster_decision(*, roster: Sequence[Mapping[str, Any]] | None, candidates: Sequence[Mapping[str, Any]] | None,
                                 rankings: Mapping[str, Any] | None, league_settings: Mapping[str, Any] | None, season: Any, week: Any,
                                 schedule_rows: Sequence[Mapping[str, Any]] | None = None, bye_rows: Sequence[Mapping[str, Any]] | None = None,
                                 now: Any = None, mode: str = "LIVE", pool_allowed: bool = False, pool_blockers: Sequence[str] = (),
                                 owned_player_ids: Sequence[Any] | None = None, roster_capacity: Any = None,
                                 empty_required_slots: Sequence[str] | None = None, faab_balance: Mapping[str, Any] | None = None,
                                 schedule_max_age_seconds: Any = None, team_needs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the waiver.roster_decision.v1 contract: verdict, priority moves, and per-position outcomes.

    team_needs is the page's shared team-needs result; it must match the contract recomputed from the active roster, otherwise
    positional need and surplus are CONTRADICTORY and no cross-position release is made.
    """
    settings = dict(league_settings or {})
    horizons = dict((rankings or {}).get("horizons") or {})
    this_week_data = dict(horizons.get("this_week") or {})
    ros_data = dict(horizons.get("rest_of_season") or {})
    full_ppr = settings.get("full_ppr") is True
    ranks_usable = full_ppr and this_week_data.get("state") == "AVAILABLE" and bool(this_week_data.get("ranks"))
    ros_summary = ranking_horizon_summary(rankings, "rest_of_season", full_ppr=full_ppr)
    ros_available = ros_summary["state"] == "AVAILABLE"
    balance = dict(faab_balance or {})
    result = {
        "contract_id": CONTRACT_ID, "season": season, "week": week, "decision_effect": "RECOMMENDATION_ONLY", "submits_transactions": False,
        "moves": [], "positions": {}, "hold_positions": [], "insufficient_positions": [], "lineup_notes": [], "blockers": [],
        "evidence": {"source": CONSENSUS_SOURCE, "week": week, "this_week_state": "AVAILABLE" if ranks_usable else "UNAVAILABLE",
                     "rest_of_season_state": ros_summary["state"], "scoring": "PPR consensus; league Full PPR" if full_ppr else "League scoring not verified as Full PPR"},
        "rest_of_season": {"state": ros_summary["state"], "label": None if ros_available else ROS_UNAVAILABLE_LABEL,
                           "reason": (f"{ros_summary['reason']} It is used for bench depth and drop safety, never for current-week ordering."
                                      if ros_available else f"{ros_summary['reason']} Rest-of-season value and drop safety are not evaluated."),
                           **{key: ros_summary[key] for key in ("source", "source_date", "age_seconds", "max_age_seconds", "freshness_state", "retrieved_at", "blocker")}},
        "ros_value": {"contract_id": ROS_VALUE_CONTRACT_ID, "summary": {key: value for key, value in ros_summary.items() if key != "identity_failures"},
                      "roster": {}, "candidates": {}, "drop_status": {}, "no_same_position_upgrade": [], "protected": {}, "coverage": {}},
        "replacement": {"contract_id": REPLACEMENT_CONTEXT_CONTRACT_ID, "rule": REPLACEMENT_RULE, "positions": {}, "players": {}},
        "depth_notes": [],
        "team_needs": {"state": "UNAVAILABLE", "positions": {}, "source": "shared team-needs contract",
                       "reason": "Team needs were not evaluated because the roster comparison did not run."},
        "drop_candidates": {"contract_id": DROP_CANDIDATES_CONTRACT_ID, "state": "UNAVAILABLE", "players": [], "rule": None},
        "faab": {"state": balance.get("state") or "UNAVAILABLE", "remaining": balance.get("remaining") if balance.get("state") == "AVAILABLE" else None,
                 "budget": balance.get("budget") if balance.get("state") == "AVAILABLE" else None, "disclosure": FAAB_DISCLOSURE},
        "move_checker_focus": None,
    }

    roster = [dict(player) for player in (roster or []) if isinstance(player, Mapping)]
    blockers = []
    if not pool_allowed:
        blockers.extend(pool_blockers or ["WAIVER_OWNERSHIP_OR_ELIGIBILITY_UNVERIFIED"])
    if settings.get("state") != "AVAILABLE":
        blockers.append(settings.get("blocker") or "LEAGUE_SETTINGS_UNAVAILABLE")
    if not roster:
        blockers.append("WAIVER_OWNER_ROSTER_UNAVAILABLE")
    elif any(not str(player.get("player_id") or "").strip() or normalize_position(player.get("position")) not in POSITIONS for player in roster):
        blockers.append("WAIVER_ROSTER_IDENTITY_UNVERIFIED")
    if blockers:
        result["blockers"] = list(dict.fromkeys(blockers))
        for position in POSITIONS:
            result["positions"][position] = _position_summary(position, "BLOCKED", "Withheld: a hard safety check failed.")
        return _finish(result, "BLOCKED", global_reasons=["A hard safety contract failed: " + ", ".join(result["blockers"]) + "."])

    if not _valid_week(season, week):
        result["blockers"] = ["CURRENT_WEEK_UNVERIFIED"]
        for position in POSITIONS:
            result["positions"][position] = _position_summary(position, "INSUFFICIENT_EVIDENCE", "The current NFL week is not verified, so bye, lock, and current-week ranks cannot be checked.")
        result["insufficient_positions"] = list(POSITIONS)
        return _finish(result, "INSUFFICIENT_EVIDENCE", global_reasons=["The current NFL week is not verified."])

    context = dict(season=season, week=week, bye_rows=bye_rows, schedule_rows=schedule_rows, now=now, mode=mode, schedule_max_age_seconds=schedule_max_age_seconds)
    ros = {"summary": ros_summary, "rankings": rankings, "data": ros_data, "available": ros_available}
    models = [_roster_model(player, ranks_usable, this_week_data, ros, context) for player in roster]
    roster_ids = {model["id"] for model in models}
    active = [model for model in models if not model["reserve"] and not model["taxi"]]
    if any(model["is_starter"] is None for model in active):
        result["blockers"] = ["CURRENT_LINEUP_UNVERIFIED"]
        for position in POSITIONS:
            result["positions"][position] = _position_summary(position, "INSUFFICIENT_EVIDENCE", "Your current Sleeper lineup could not be verified.")
        result["insufficient_positions"] = list(POSITIONS)
        return _finish(result, "INSUFFICIENT_EVIDENCE", global_reasons=["Your current Sleeper lineup could not be verified."])
    team_need_view = _team_needs_view(team_needs, active, settings)
    result["team_needs"] = team_need_view

    owned = {str(value) for value in (owned_player_ids or [])} | roster_ids
    candidate_models = []
    seen = set()
    for raw in candidates or []:
        model = _candidate_model(raw, owned, ranks_usable, this_week_data, ros, context)
        if model and model["id"] not in seen:
            seen.add(model["id"])
            candidate_models.append(model)

    starting_slots = {normalize_position(key): int(value or 0) for key, value in (settings.get("starter_slots") or {}).items()}
    flex_positions = {normalize_position(value) for value in settings.get("flex_eligible_positions") or []}
    evaluated_positions = [position for position in POSITIONS if starting_slots.get(position, 0) > 0 or position in flex_positions]
    global_reasons = []
    if not full_ppr:
        global_reasons.append("League reception scoring is not verified as Full PPR, so PPR consensus ranks cannot be applied.")
    elif not ranks_usable:
        global_reasons.append("No fresh current-week consensus ranks are available.")

    needs, lineup_gaps = _slot_needs(settings, active, empty_required_slots)
    bench = [model for model in active if model["is_starter"] is False]
    protected = set()
    protections = {}
    covering = []
    for need in sorted(needs, key=lambda item: (len(item["coverage_positions"]) > 1, item["index"])):
        cover, leaders = _coverage(need, bench, protected)
        if leaders:
            occupant_name = (need.get("occupant") or {}).get("name")
            trigger = "verified bye" if need["trigger"] == "BYE" else "empty slot" if need["trigger"] == "EMPTY_SLOT" else "injury"
            for leader in leaders:
                protected.add(leader["id"])
                protections[leader["id"]] = (f"Can cover the {need['slot']} slot this week" + (f" for {occupant_name}" if occupant_name else "")
                                             + f" ({trigger}); consensus ranks are positional, so no cross-position best backup is named.")
            need["coverage"] = leaders
            options = "; ".join(f"{leader['name']} ({leader['position']}" + (", Questionable" if leader["health_state"] == "QUESTIONABLE" else "") + ")" for leader in leaders)
            result["lineup_notes"].append({"slot": need["slot"], "player": None, "player_id": None, "replaces": occupant_name, "trigger": need["trigger"], "health_state": None,
                                           "options": [{"player": leader["name"], "player_id": leader["id"], "position": leader["position"], "health_state": leader["health_state"]}
                                                       for leader in leaders],
                                           "note": f"{need['slot']} has verified internal coverage" + (f" for {occupant_name}" if occupant_name else "")
                                                   + f" from {'/'.join(leader['position'] for leader in leaders)} bench options: {options}. Consensus ranks are positional, "
                                                   "so no cross-position best is named; choose who starts. No waiver move is needed."})
        if cover:
            protected.add(cover["id"])
            protections[cover["id"]] = (f"Covers the {need['slot']} slot this week" + (f" for {need['occupant']['name']}" if need.get("occupant") else "")
                                        + f" ({'verified bye' if need['trigger'] == 'BYE' else 'empty slot' if need['trigger'] == 'EMPTY_SLOT' else 'injury'}).")
            need["coverage"] = cover
            covering.append({**cover, "lineup_slot": need["slot"], "covering_for": (need.get("occupant") or {}).get("name")})
            result["lineup_notes"].append({"slot": need["slot"], "player": cover["name"], "player_id": cover["id"], "replaces": (need.get("occupant") or {}).get("name"),
                                           "trigger": need["trigger"], "health_state": cover["health_state"],
                                           "note": f"Start {cover['name']} in the {need['slot']} slot" + (f" for {need['occupant']['name']}" if need.get("occupant") else "")
                                                   + (" (Questionable)" if cover["health_state"] == "QUESTIONABLE" else "") + "; no waiver move is needed."})
    protections.update(_health_risk_protections(active, bench, protections))
    for model in active:
        if model["context"]["lock_state"] == "LOCKED":
            protections.setdefault(model["id"], "His game has already kicked off this week, so his roster spot is locked.")

    intents = []
    used_adds = set()
    need_occupants = {need["occupant"]["id"] for need in needs if need.get("occupant")}
    position_status = {}
    for need in needs:
        if need.get("coverage"):
            continue
        intent = _must_fill_intent(need, candidate_models, used_adds)
        intents.append(intent)
        if intent.get("add"):
            used_adds.add(intent["add"]["id"])
        for position in need["positions"]:
            position_status.setdefault(position, ("MUST_FILL", f"The {need['slot']} slot needs a starter this week: {_trigger_text(need)}."))

    for position in evaluated_positions:
        if position in position_status:
            continue
        status, reason, intent, disclosure = _current_week_position(position, active, candidate_models, used_adds, need_occupants, ranks_usable, global_reasons, lineup_gaps, covering)
        position_status[position] = (status, reason)
        if intent:
            intents.append(intent)
            if intent.get("add"):
                used_adds.add(intent["add"]["id"])
        result["positions"][position] = _position_summary(position, status, reason, **disclosure)

    if ros_available:
        for position in evaluated_positions:
            intent = _depth_intent(position, active, candidate_models, used_adds, protections)
            if intent:
                intents.append(intent)
                used_adds.add(intent["add"]["id"])

    open_spots = max(0, int(roster_capacity) - len(active)) if isinstance(roster_capacity, int) and not isinstance(roster_capacity, bool) else 0
    sequence = [str(slot).upper() for slot in settings.get("starter_slot_sequence") or []]
    drop_context = {"active": active, "protections": protections, "used_drops": set(), "added": [], "ros": ros_summary, "needs": team_need_view,
                    "slot_positions": [SLOT_POSITIONS[slot] for slot in sequence if slot in SLOT_POSITIONS], "pools": _replacement_pools(candidate_models)}
    moves = []
    for intent in sorted(intents, key=lambda item: (URGENCY_ORDER[item["urgency"]], KIND_ORDER[item["kind"]], POSITIONS.index(item["position"]) if item["position"] in POSITIONS else 9)):
        move = _resolve(intent, drop_context, open_spots)
        if move is None:
            continue
        if move["kind"] == "DEPTH_UPGRADE" and move["decision"] == "MONITOR" and move.get("drop_blocker") in MATERIALITY_BLOCKERS:
            result["depth_notes"].append(_depth_note(move))
            continue
        if move["decision"] == "ADD":
            open_spots -= 1
        add_model = move.pop("_add_model")
        if move["decision"] in ("ADD", "ADD_DROP"):
            drop_context["added"].append(add_model)
        if move.get("drop"):
            drop_context["used_drops"].add(move["drop"]["player_id"])
        moves.append(move)
    for priority, move in enumerate(moves, 1):
        move["priority"] = priority
    result["moves"] = moves
    result["ros_value"].update(_ros_value_block(models, candidate_models, moves, drop_context))
    result["replacement"] = _replacement_block(drop_context)
    result["drop_candidates"] = _drop_candidates_block(active, moves, drop_context, result["replacement"])

    for position in evaluated_positions:
        if position not in result["positions"]:
            status, reason = position_status.get(position, ("INSUFFICIENT_EVIDENCE", "No supported comparison was completed."))
            result["positions"][position] = _position_summary(position, status, reason)
    for position in POSITIONS:
        if position not in evaluated_positions:
            result["positions"][position] = _position_summary(position, "NOT_APPLICABLE", "This league has no starting slot for this position.")
    result["hold_positions"] = [position for position in POSITIONS if result["positions"][position]["status"] in ("HOLD", "LOCKED")]
    result["insufficient_positions"] = [position for position in POSITIONS if result["positions"][position]["status"] == "INSUFFICIENT_EVIDENCE"]
    focus = next((move for move in moves if move.get("over") or move.get("drop") or move.get("slot_player")), None)
    if focus:
        player = focus.get("over") or focus.get("slot_player") or focus.get("drop")
        result["move_checker_focus"] = {"player_id": player["player_id"], "player": player["player"], "position": player["position"], "move_priority": focus["priority"]}
    if result["insufficient_positions"] and not global_reasons:
        global_reasons.append("Comparisons could not be completed for: " + ", ".join(result["insufficient_positions"]) + ".")
    verdict = _verdict_state(moves, result["insufficient_positions"])
    return _finish(result, verdict, global_reasons=global_reasons)


def _ros_views(ros, player_id, position, context):
    value = ros_player_value(ros["summary"], ros["rankings"], player_id, position, season=context["season"])
    rank = (consensus_rank(ros["data"], player_id, position=position, horizon="rest_of_season", season=context["season"], week=context["week"])
            if ros["available"] and value["evidence_state"] == "RANKED" else {**UNRANKED, "horizon": "rest_of_season"})
    return value, rank


def _roster_model(player, ranks_usable, this_week_data, ros, context):
    position = normalize_position(player.get("position"))
    player_id = str(player.get("player_id") or "")
    week_rank = consensus_rank(this_week_data, player_id, position=position, horizon="this_week", season=context["season"], week=context["week"]) if ranks_usable else dict(UNRANKED)
    ros_value, ros_rank = _ros_views(ros, player_id, position, context)
    health = player.get("health_state")
    return {"id": player_id, "name": player.get("player") or player_id, "position": position, "is_starter": player.get("is_starter"),
            "lineup_index": player.get("lineup_index"), "lineup_slot": player.get("lineup_slot"), "reserve": player.get("reserve") is True,
            "taxi": player.get("taxi") is True, "health_state": health, "health_fresh": player.get("health_freshness_state") == "FRESH",
            "week_rank": week_rank, "ros_rank": ros_rank, "ros_value": ros_value, "context": week_context(player.get("team"), **context)}


def _candidate_model(raw, owned, ranks_usable, this_week_data, ros, context):
    raw = dict(raw or {})
    player_id = str(raw.get("player_id") or "").strip()
    position = normalize_position(raw.get("position"))
    if not player_id or player_id in owned or position not in POSITIONS:
        return None
    if raw.get("identity_state") != "RESOLVED" or raw.get("ownership_state") != "VERIFIED" or raw.get("eligibility_state") != "VERIFIED":
        return None
    health = raw.get("health_state")
    if raw.get("health_freshness_state") != "FRESH" or raw.get("health_source") != "Sleeper API" or health not in COVERAGE_HEALTH:
        return None
    ctx = week_context(raw.get("team"), **context)
    week_rank = consensus_rank(this_week_data, player_id, position=position, horizon="this_week", season=context["season"], week=context["week"]) if ranks_usable else dict(UNRANKED)
    ros_value, ros_rank = _ros_views(ros, player_id, position, context)
    playable = ctx["lock_state"] == "OPEN" and ctx["bye_verified"] and not ctx["on_bye"]
    return {"id": player_id, "name": raw.get("player") or player_id, "position": position, "health_state": health, "monitor_only": health == "QUESTIONABLE",
            "current_week_actionable": health == "HEALTHY" and playable, "questionable_playable": health == "QUESTIONABLE" and playable,
            "depth_addable": health == "HEALTHY" and ctx["lock_state"] in DROPPABLE_LOCK_STATES, "week_rank": week_rank, "ros_rank": ros_rank,
            "ros_value": ros_value, "context": ctx}


def _team_needs_view(supplied, active, settings):
    """The shared team-needs contract for the active roster. A page copy that disagrees with it is CONTRADICTORY and authorizes no release."""
    computed = team_needs_contract([{"position": model["position"]} for model in active], settings)
    available = bool(computed) and all(item.get("state") == "AVAILABLE" for item in computed.values())
    view = {"state": "AVAILABLE" if available else "UNAVAILABLE", "positions": computed, "source": "shared team-needs contract",
            "reason": None if available else "League roster settings are not verified, so positional depth targets are unavailable."}
    if isinstance(supplied, Mapping) and supplied:
        keys = ("state", "rostered_or_eligible", "depth_target", "required_slots")
        mismatched = [position for position, item in computed.items()
                      if tuple((supplied.get(position) or {}).get(key) for key in keys) != tuple(item.get(key) for key in keys)]
        if mismatched:
            view.update(state="CONTRADICTORY", reason=(f"The page's team-needs result disagrees with your active roster at {', '.join(mismatched)}, "
                                                       "so positional need and surplus are not used."))
    return view


def _slot_needs(settings, active, empty_required_slots):
    sequence = [str(slot).upper() for slot in settings.get("starter_slot_sequence") or []]
    occupants = {model["lineup_index"]: model for model in active if model["is_starter"] is True and isinstance(model["lineup_index"], int)}
    reported_empty = [normalize_position(slot) for slot in empty_required_slots] if isinstance(empty_required_slots, (list, tuple)) else None
    needs, gaps = [], []
    for index, slot in enumerate(sequence):
        positions = SLOT_POSITIONS.get(slot)
        if not positions:
            continue
        occupant = occupants.get(index)
        if occupant is None:
            if reported_empty is not None and normalize_position(slot) in reported_empty:
                needs.append({"index": index, "slot": slot, "positions": positions, "coverage_positions": positions, "trigger": "EMPTY_SLOT", "occupant": None})
            else:
                gaps.append({"index": index, "slot": slot, "positions": positions})
            continue
        if occupant["context"]["lock_state"] == "LOCKED":
            continue
        if occupant["context"]["on_bye"]:
            needs.append({"index": index, "slot": slot, "positions": (occupant["position"],), "coverage_positions": positions, "trigger": "BYE", "occupant": occupant})
        elif occupant["health_fresh"] and occupant["health_state"] in UNUSABLE_HEALTH:
            needs.append({"index": index, "slot": slot, "positions": (occupant["position"],), "coverage_positions": positions, "trigger": "UNUSABLE_HEALTH", "occupant": occupant})
    return needs, gaps


def _can_cover(model):
    ctx = model["context"]
    return ctx["bye_verified"] and not ctx["on_bye"] and ctx["lock_state"] == "OPEN" and model["health_fresh"] and model["health_state"] in COVERAGE_HEALTH


def _coverage(need, bench, protected):
    """Bench coverage for one slot need, as (single cover, per-position leaders).

    Consensus ranks are positional, so options are ranked only within one position: a like-for-like option at the occupant's
    position first, otherwise the only eligible position. When several other positions could cover a multi-position slot, no
    cross-position best is named and the best option at each position is returned instead.
    """
    options = [model for model in bench if model["id"] not in protected and model["position"] in need["coverage_positions"] and _can_cover(model)]
    if not options:
        return None, []

    def key(model):
        return model["health_state"] != "HEALTHY", _rank_key(model["week_rank"]), model["name"], model["id"]

    occupant = need.get("occupant")
    same = [model for model in options if occupant is not None and model["position"] == occupant["position"]]
    single = same or (options if len({model["position"] for model in options}) == 1 else [])
    if single:
        return min(single, key=key), []
    return None, [min(group, key=key) for position in need["coverage_positions"] if (group := [model for model in options if model["position"] == position])]


def _trigger_text(need):
    occupant = need.get("occupant")
    if need["trigger"] == "BYE":
        return f"{occupant['name']} is on a verified bye"
    if need["trigger"] == "UNUSABLE_HEALTH":
        return f"{occupant['name']} is listed {occupant['health_state']}"
    return "the required slot is empty in your Sleeper lineup"


def _must_fill_intent(need, candidate_models, used_adds):
    intent = {"kind": "MUST_FILL", "urgency": "REQUIRED", "slot": need["slot"], "trigger": need["trigger"], "trigger_text": _trigger_text(need),
              "slot_player": need.get("occupant"), "over": None, "replaced": None}
    positions = need["positions"]
    intent["position"] = positions[0] if len(positions) == 1 else need["slot"]
    if len(positions) > 1:
        leaders = []
        for position in positions:
            pool = sorted((model for model in candidate_models if model["position"] == position and model["current_week_actionable"] and model["id"] not in used_adds),
                          key=lambda model: (_rank_key(model["week_rank"]), model["name"], model["id"]))
            if pool:
                leaders.append(pool[0])
        intent.update(add=None, fallbacks=leaders, forced_monitor="FLEX_CROSS_POSITION",
                      monitor_detail="This slot accepts several positions; consensus ranks are not compared across positions, so choose among the listed per-position leaders.")
        return intent
    pool = sorted((model for model in candidate_models if model["position"] == positions[0] and model["current_week_actionable"] and model["id"] not in used_adds),
                  key=lambda model: (_rank_key(model["week_rank"]), model["name"], model["id"]))
    if not pool:
        intent.update(add=None, fallbacks=[], forced_monitor="NO_CANDIDATE",
                      monitor_detail=f"No verified, healthy, unlocked {positions[0]} with a current game is available.")
        return intent
    ranked_count = sum(1 for model in pool if _ranked(model["week_rank"]))
    # The occupant who cannot play this week is releasable only through the rest-of-season starter rules in _safe_drop.
    intent.update(add=pool[0], fallbacks=pool[1:4], ordering="CURRENT_CONSENSUS_RANK" if ranked_count else "VERIFIED_EQUIVALENT_OPTIONS",
                  ranked_count=ranked_count, unranked_count=len(pool) - ranked_count, replaced=need.get("occupant"))
    return intent


def _current_week_position(position, active, candidate_models, used_adds, need_occupants, ranks_usable, global_reasons, lineup_gaps, covering=()):
    starters = [model for model in active if model["is_starter"] is True and model["position"] == position and model["id"] not in need_occupants]
    starters += [model for model in covering if model["position"] == position]
    locked = [model for model in starters if model["context"]["lock_state"] == "LOCKED"]
    comparable = [model for model in starters if model["context"]["lock_state"] != "LOCKED"]
    ranked_starters = [model for model in comparable if _ranked(model["week_rank"])]
    unranked_starters = [model for model in comparable if not _ranked(model["week_rank"])]
    pool = [model for model in candidate_models if model["position"] == position and model["id"] not in used_adds]
    healthy = [model for model in pool if model["current_week_actionable"]]
    healthy_ranked = sorted((model for model in healthy if _ranked(model["week_rank"])), key=lambda model: (model["week_rank"]["ecr"], model["name"], model["id"]))
    questionable_ranked = sorted((model for model in pool if model["questionable_playable"] and _ranked(model["week_rank"])),
                                 key=lambda model: (model["week_rank"]["ecr"], model["name"], model["id"]))
    unranked_count = len(healthy) - len(healthy_ranked)
    disclosure = {"ranked_candidates": len(healthy_ranked), "unranked_candidates": unranked_count,
                  "starters": [{"player": model["name"], "player_id": model["id"], "rank": dict(model["week_rank"]), "lock_state": model["context"]["lock_state"]} for model in starters],
                  "best_candidate": _player_view(healthy_ranked[0]) if healthy_ranked else None,
                  "locked_starters": [model["name"] for model in locked], "unranked_starters": [model["name"] for model in unranked_starters]}
    if not ranks_usable:
        return "INSUFFICIENT_EVIDENCE", global_reasons[0] if global_reasons else "Current-week consensus ranks are unavailable.", None, disclosure
    if any(position in gap["positions"] for gap in lineup_gaps):
        return "INSUFFICIENT_EVIDENCE", "An unfilled lineup slot for this position could not be verified in your Sleeper lineup.", None, disclosure
    if not starters:
        return "INSUFFICIENT_EVIDENCE", f"No current {position} starter was found to compare.", None, disclosure
    if not comparable:
        return "LOCKED", "Your starters' games have already kicked off; no current-week move is possible.", None, disclosure
    target = max(ranked_starters, key=lambda model: (model["week_rank"]["ecr"], model["name"])) if ranked_starters else None
    upgrades = [model for model in healthy_ranked if target and model["week_rank"]["ecr"] < target["week_rank"]["ecr"]]
    if upgrades:
        primary = upgrades[0]
        separation = expert_separation(primary["week_rank"], target["week_rank"])
        intent = {"kind": "CURRENT_WEEK_UPGRADE", "urgency": "MATERIAL" if separation["state"] == "UNANIMOUS" else "OPTIONAL", "position": position,
                  "slot": target["lineup_slot"], "add": primary, "over": target, "replaced": target, "fallbacks": upgrades[1:4], "materiality": separation}
        return "UPGRADE", f"{primary['name']} ranks ahead of {target['name']} this week.", intent, disclosure
    if unranked_starters:
        names = ", ".join(model["name"] for model in unranked_starters)
        return "INSUFFICIENT_EVIDENCE", f"{names} has no current consensus rank; an available player cannot be shown better than an unranked starter.", None, disclosure
    questionable = [model for model in questionable_ranked if model["week_rank"]["ecr"] < target["week_rank"]["ecr"]]
    if questionable:
        primary = questionable[0]
        intent = {"kind": "CURRENT_WEEK_UPGRADE", "urgency": "OPTIONAL", "position": position, "slot": target["lineup_slot"], "add": primary, "over": target,
                  "replaced": target, "fallbacks": questionable[1:4], "materiality": expert_separation(primary["week_rank"], target["week_rank"]),
                  "forced_monitor": "QUESTIONABLE", "monitor_detail": f"{primary['name']} is listed Questionable; a health designation prevents a supported ADD."}
        return "UPGRADE", f"{primary['name']} ranks ahead of {target['name']} but is Questionable.", intent, disclosure
    if healthy_ranked:
        return "HOLD", f"Your {position} starter(s) rank ahead of every ranked available {position} this week.", None, disclosure
    if not healthy:
        return "HOLD", f"No verified, healthy, unlocked {position} with a current game is available this week.", None, disclosure
    return "INSUFFICIENT_EVIDENCE", f"No available {position} has a current consensus rank to compare.", None, disclosure


def _depth_intent(position, active, candidate_models, used_adds, protected):
    bench = [model for model in active if model["is_starter"] is False and model["position"] == position and model["id"] not in protected]
    ranked_bench = [model for model in bench if _ranked(model["ros_rank"])]
    if not ranked_bench:
        return None
    weakest = max(ranked_bench, key=lambda model: (model["ros_rank"]["ecr"], model["name"]))
    pool = sorted((model for model in candidate_models if model["position"] == position and model["depth_addable"] and _ranked(model["ros_rank"]) and model["id"] not in used_adds
                   and model["ros_rank"]["ecr"] < weakest["ros_rank"]["ecr"]), key=lambda model: (model["ros_rank"]["ecr"], model["name"], model["id"]))
    if not pool:
        return None
    return {"kind": "DEPTH_UPGRADE", "urgency": "OPTIONAL", "position": position, "slot": "BENCH", "add": pool[0], "over": weakest, "replaced": None,
            "fallbacks": pool[1:4], "materiality": expert_separation(pool[0]["ros_rank"], weakest["ros_rank"])}


def _health_risk_protections(active, bench, protections):
    """Keep a backup for each unlocked starter carrying a Questionable or Doubtful designation.

    Ranks are positional, so when the slot accepts several positions the best eligible backup at each position is kept
    instead of choosing between positions.
    """
    held = {}
    starters = sorted((model for model in active if model["is_starter"] is True),
                      key=lambda model: (model["lineup_index"] if isinstance(model["lineup_index"], int) else 99, model["id"]))
    for starter in starters:
        if starter["context"]["lock_state"] == "LOCKED" or not starter["health_fresh"] or starter["health_state"] not in HEALTH_RISK_STATES:
            continue
        slot = str(starter.get("lineup_slot") or starter["position"]).upper()
        for position in SLOT_POSITIONS.get(slot, (starter["position"],)):
            options = [model for model in bench if model["position"] == position and model["id"] not in protections and model["id"] not in held and _can_cover(model)]
            options.sort(key=lambda model: (model["health_state"] != "HEALTHY", _rank_key(model["week_rank"]), model["name"], model["id"]))
            if options:
                held[options[0]["id"]] = f"Backup for {starter['name']} ({starter['health_state'].title()}) at {slot} this week."
    return held


def _max_filled_slots(slot_positions, player_positions):
    """Most starting slots fillable at once: a bipartite matching of slots to players by position eligibility."""
    owner = [None] * len(player_positions)

    def assign(slot, seen):
        for index, position in enumerate(player_positions):
            if index in seen or position not in slot_positions[slot]:
                continue
            seen.add(index)
            if owner[index] is None or assign(owner[index], seen):
                owner[index] = slot
                return True
        return False

    return sum(1 for slot in range(len(slot_positions)) if assign(slot, set()))


def _plays_this_week(model):
    if "current_week_actionable" in model:
        return bool(model["current_week_actionable"] or model["questionable_playable"])
    if model["context"]["lock_state"] == "LOCKED":
        return model["is_starter"] is True
    return _can_cover(model)


def _coverage_loss(before, add, drop, slots):
    after = [model for model in before if model["id"] != drop["id"]] + ([add] if add else [])
    if _max_filled_slots(slots, [model["position"] for model in after]) < _max_filled_slots(slots, [model["position"] for model in before]):
        return "would leave a starting slot with no eligible player on your roster."
    week_before = _max_filled_slots(slots, [model["position"] for model in before if _plays_this_week(model)])
    if _max_filled_slots(slots, [model["position"] for model in after if _plays_this_week(model)]) < week_before:
        return "would leave fewer starting slots covered this week (bye, injury, or kickoff lock)."
    return None


def _post_move_safety(add, drop, context):
    """A release must not reduce the starting slots (including FLEX) the roster can fill this week or for the season,
    whether the move is made on its own or after the higher-priority moves already recommended."""
    slots = context["slot_positions"]
    if not slots:
        return {"state": "UNSAFE", "reason": "League starting slots are not verified, so post-move lineup safety cannot be checked."}
    baselines = [("", context["active"])]
    if context["used_drops"] or context["added"]:
        after_moves = [model for model in context["active"] if model["id"] not in context["used_drops"]] + list(context["added"])
        baselines.append((" after the higher-priority moves", after_moves))
    for timing, before in baselines:
        loss = _coverage_loss(before, add, drop, slots)
        if loss:
            return {"state": "UNSAFE", "reason": f"Releasing {drop['name']}{timing} {loss}"}
    return {"state": "SAFE", "reason": "Every starting slot, including FLEX, can still be filled this week and for the rest of the season."}


def _drop_hold(member, context):
    if member["id"] in context["used_drops"]:
        return "DROP_ALREADY_USED", f"{member['name']} is already the drop for a higher-priority move."
    if member["id"] in context["protections"]:
        return "PROTECTED", f"{member['name']} is protected: {context['protections'][member['id']]}"
    lock = member["context"]["lock_state"]
    if lock not in DROPPABLE_LOCK_STATES:
        return "LOCK_UNVERIFIED", f"{member['name']} cannot be released because his game lock state is {'unverified' if lock == 'LOCK_UNVERIFIED' else str(lock).lower()}."
    return None


def _drop_view(add, member, comparison, materiality, safety, role):
    position = member["position"]
    lead = {"BENCH": f"{member['name']} is your weakest releasable {position} for the rest of the season",
            "REPLACED_STARTER": f"{member['name']} leaves the lineup and ranks behind {add['name']} for the rest of the season",
            "SLOT_OCCUPANT": f"{member['name']} cannot play this week and ranks behind {add['name']} for the rest of the season"}[role]
    return {"player_id": member["id"], "player": member["name"], "position": position, "basis": "rest_of_season", "add_ecr": comparison["candidate_ecr"],
            "drop_ecr": comparison["roster_ecr"], "role": role, "ros_comparison": comparison, "materiality": materiality, "safety": safety, "ros_value": member["ros_value"],
            "reason": f"{lead} ({position} ROS ECR {comparison['roster_ecr']:.1f} vs {comparison['candidate_ecr']:.1f}; expert ranges {materiality['roster_range']} vs "
                      f"{materiality['candidate_range']} do not overlap); {safety['reason'][0].lower()}{safety['reason'][1:]}"}


def _no_drop(code, detail, material=False, materiality=None, subject=None):
    return {"drop": None, "code": code, "detail": detail, "material": material, "materiality": materiality, "subject": subject}


def _safe_drop(intent, context):
    """A verified release for one add: same position first, then waiver.cross_position_drop.v1, else the exact same-position blocker.

    material reports whether any same-position pairing cleared the materiality gate, so a close call is distinguishable from a safety block.
    A cross-position finding is added to the blocker only when it says something the same-position explanation does not.
    """
    add, ros = intent["add"], context["ros"]
    if ros["state"] != "AVAILABLE":
        return _no_drop("ROS_VALUE_UNAVAILABLE", f"A safe release cannot be verified because rest-of-season value is unavailable: {ros['reason']}")
    if add["ros_value"]["evidence_state"] != "RANKED":
        state = add["ros_value"]["evidence_state"].replace("_", " ").lower()
        return _no_drop("CANDIDATE_ROS_UNRANKED", f"{add['name']} has no fresh rest-of-season rank ({state}), so releasing a roster player for him cannot be verified.")
    same = _same_position_drop(intent, context)
    if same["drop"]:
        return same
    cross = _cross_position_drop(intent, context)
    if cross["drop"]:
        return {**cross, "same_position": {"code": same["code"], "detail": same["detail"]}}
    if cross["note"]:
        same["detail"] = f"{same['detail']} {cross['note']}"
    same["cross_position"] = cross["evaluation"]
    return same


def _same_position_drop(intent, context):
    """Same-position release supported by fresh, clearly separated rest-of-season evidence and the post-move lineup check, else the exact blocker."""
    add = intent["add"]
    position = add["position"]
    blockers, not_material = [], []

    def weigh(member, role):
        held = _drop_hold(member, context)
        if held:
            blockers.append(held)
            return None
        comparison = compare_ros_values(add["ros_value"], member["ros_value"], candidate_name=add["name"], roster_name=member["name"])
        if comparison["state"] == "UNVERIFIED":
            blockers.append(("ROSTER_ROS_UNRANKED", comparison["reason"]))
            return None
        if comparison["state"] != "CANDIDATE_BETTER":
            edge = "slot fill" if intent["kind"] == "MUST_FILL" else "current-week edge"
            blockers.append(("ROSTER_ROS_STRONGER", comparison["reason"] + ("" if role == "BENCH" else f" The {edge} is short-term, so {member['name']} is kept.")))
            return None
        materiality = ros_materiality(add["ros_value"], member["ros_value"], candidate_name=add["name"], roster_name=member["name"])
        if materiality["state"] != "CLEAR_EDGE":
            code = "ROS_EDGE_NOT_MATERIAL" if materiality["state"] == "CLOSE_CALL" else "ROS_MATERIALITY_UNVERIFIED"
            not_material.append((code, f"{materiality['reason']} Releasing {member['name']} is not supported.", materiality, member))
            return None
        return member, comparison, materiality

    bench = [member for member in context["active"] if member["is_starter"] is False and member["position"] == position]
    eligible = [item for item in (weigh(member, "BENCH") for member in bench) if item]
    material = bool(eligible)
    for member, comparison, materiality in sorted(eligible, key=lambda item: (-item[1]["roster_ecr"], item[0]["name"], item[0]["id"])):
        safety = _post_move_safety(add, member, context)
        if safety["state"] == "SAFE":
            return {"drop": _drop_view(add, member, comparison, materiality, safety, "BENCH"), "code": None, "detail": None, "material": True}
        blockers.append(("LINEUP_COVERAGE", safety["reason"]))
    replaced = intent.get("replaced")
    if replaced is not None:
        role = "SLOT_OCCUPANT" if intent["kind"] == "MUST_FILL" else "REPLACED_STARTER"
        weighed = weigh(replaced, role)
        if weighed:
            material = True
            member, comparison, materiality = weighed
            safety = _post_move_safety(add, member, context)
            if safety["state"] == "SAFE":
                return {"drop": _drop_view(add, member, comparison, materiality, safety, role), "code": None, "detail": None, "material": True}
            blockers.append(("LINEUP_COVERAGE", safety["reason"]))
    if not material and not_material:
        # The blocked release reported first is the weakest rest-of-season player, matching the order in which drops are chosen.
        chosen = sorted([item for item in not_material if item[0] == "ROS_EDGE_NOT_MATERIAL"] or not_material,
                        key=lambda item: (-item[3]["ros_value"]["ros_ecr"], item[3]["name"], item[3]["id"]))
        return _no_drop(chosen[0][0], " ".join(dict.fromkeys([item[1] for item in chosen] + [detail for _, detail in blockers])),
                        materiality=chosen[0][2], subject=chosen[0][3])
    combined = blockers + [item[:2] for item in not_material]
    if not combined:
        return _no_drop("NO_SAME_POSITION_RELEASE", f"No {position} on your active roster can be released for {add['name']}.")
    return _no_drop(combined[0][0], " ".join(dict.fromkeys(detail for _, detail in combined)), material)


def _position_count(position, context):
    """Active players at one position after the higher-priority moves already recommended."""
    used = context["used_drops"]
    return (sum(1 for model in context["active"] if model["position"] == position and model["id"] not in used)
            + sum(1 for model in context["added"] if model["position"] == position))


def _weakest_remaining_bench(position, context):
    """The weakest rest-of-season-ranked bench player at one position still on the roster after the higher-priority moves, else None."""
    remaining = [model for model in context["active"] if model["is_starter"] is False and model["position"] == position
                 and model["id"] not in context["used_drops"] and _ranked(model["ros_rank"])]
    return max(remaining, key=lambda model: (model["ros_rank"]["ecr"], model["name"], model["id"])) if remaining else None


def _cross_position_add(intent, context):
    """Candidate side of waiver.cross_position_drop.v1 as (basis or None, evidence, note).

    The note is None when the same-position explanation already says why (the displaced player was weighed and kept).
    """
    add, needs = intent["add"], context.get("needs") or {}
    position = add["position"]
    count, target = _position_count(position, context), ((needs.get("positions") or {}).get(position) or {}).get("depth_target")
    displaced = intent.get("replaced") if intent["kind"] == "MUST_FILL" else intent.get("over")
    if intent["kind"] == "DEPTH_UPGRADE" and displaced is not None and displaced["id"] in context["used_drops"]:
        # The weakest bench player was already released by a higher-priority move; compare with the weakest one still on the roster.
        displaced = _weakest_remaining_bench(position, context)
    evidence = {"player_id": add["id"], "player": add["name"], "position": position, "kind": intent["kind"], "count": count, "depth_target": target,
                "displaced": {"player_id": displaced["id"], "player": displaced["name"], "position": displaced["position"]} if displaced else None,
                "current_week_separation": (intent.get("materiality") or {}).get("state") if intent["kind"] == "CURRENT_WEEK_UPGRADE" else None,
                "ros_comparison": None, "ros_materiality": None}
    if needs.get("state") != "AVAILABLE":
        note = f"A release at a different position is not evaluated: {needs.get('reason')}" if needs.get("state") == "CONTRADICTORY" else None
        return None, evidence, note
    if add.get("health_state") != "HEALTHY":
        return None, evidence, None
    if intent["kind"] == "MUST_FILL":
        return "REQUIRED_SLOT_FILL", evidence, None
    if displaced is None:
        return None, evidence, None
    comparison = compare_ros_values(add["ros_value"], displaced["ros_value"], candidate_name=add["name"], roster_name=displaced["name"])
    evidence.update(ros_comparison=comparison,
                    ros_materiality=ros_materiality(add["ros_value"], displaced["ros_value"], candidate_name=add["name"], roster_name=displaced["name"]))
    if comparison["state"] != "CANDIDATE_BETTER":
        if _drop_hold(displaced, context) is None:
            return None, evidence, None
        return None, evidence, f"{comparison['reason']} A short-term edge does not release a player at a different position either."
    if isinstance(target, int) and count < target:
        return "VERIFIED_NEED", evidence, None
    if evidence["current_week_separation"] == "UNANIMOUS":
        return "UNANIMOUS_STARTER_UPGRADE", evidence, None
    if evidence["ros_materiality"]["state"] == "CLEAR_EDGE":
        return "CLEAR_ROS_EDGE", evidence, None
    return None, evidence, (f"{add['name']} ranks ahead of {displaced['name']} for the rest of the season, but {position} depth is not below its supported "
                            f"target ({count} of {target}) and no horizon shows an edge every published expert agrees on, so no player at a different "
                            "position is released for him.")


def _cross_position_options(add, context):
    """For each different position with a releasable bench player, the weakest one who passes every release check, else the first check failed.

    Protected, locked, already-used, and unranked players are never released and are not reported as options (unranked is not worse).
    """
    needs = (context.get("needs") or {}).get("positions") or {}
    excluded = [model["id"] for model in context["added"]] + [add["id"]]
    options = []
    for position in POSITIONS:
        if position == add["position"]:
            continue
        members = sorted((model for model in context["active"] if model["is_starter"] is False and model["position"] == position
                          and _drop_hold(model, context) is None and model["ros_value"]["evidence_state"] == "RANKED"),
                         key=lambda model: (-model["ros_value"]["ros_ecr"], model["name"], model["id"]))
        if not members:
            continue
        count, target = _position_count(position, context), (needs.get(position) or {}).get("depth_target")
        first = None
        for member in members:
            replacement = replacement_context(member["ros_value"], member["name"], context["pools"].get(position), exclude_ids=excluded)
            option = {"player_id": member["id"], "player": member["name"], "position": position, "ros_ecr": member["ros_value"]["ros_ecr"],
                      "range": _span(member["ros_value"]), "count": count, "count_after": count - 1, "depth_target": target, "replacement": replacement,
                      "safety": None, "blocker": None, "reason": None, "_model": member}
            if not isinstance(target, int) or count - 1 < target:
                option.update(blocker="DEPTH_BELOW_TARGET", reason=f"{position} depth would fall to {count - 1}, below the supported target of {target}")
            elif replacement["state"] != "STRONG":
                option.update(blocker="REPLACEMENT_NOT_STRONG", reason=f"{replacement['label'].lower()} on waivers ({replacement['reason']})")
            else:
                option["safety"] = _post_move_safety(add, member, context)
                if option["safety"]["state"] != "SAFE":
                    option.update(blocker="LINEUP_COVERAGE", reason=option["safety"]["reason"])
            first = first or option
            if option["blocker"] is None or option["blocker"] == "DEPTH_BELOW_TARGET":
                first = option
                break
        options.append(first)
    return options


def _cross_position_drop(intent, context):
    """waiver.cross_position_drop.v1 for one add: a verified release at a different position, or the evaluation that blocked it."""
    add = intent["add"]
    basis, add_evidence, note = _cross_position_add(intent, context)
    evaluation = {"contract_id": CROSS_POSITION_CONTRACT_ID, "rule": CROSS_POSITION_RULE, "add": add_evidence, "basis": basis, "options": [], "state": None}
    result = {"drop": None, "code": None, "detail": None, "material": False, "materiality": None, "subject": None, "evaluation": evaluation, "note": None}
    if basis is None:
        evaluation["state"] = "NOT_SUPPORTED"
        result["note"] = note
        return result
    options = _cross_position_options(add, context)
    evaluation["options"] = [{key: value for key, value in option.items() if key != "_model"} for option in options]
    eligible = [option for option in options if option["blocker"] is None]
    if not eligible:
        evaluation["state"] = "NO_ELIGIBLE_RELEASE" if options else "NO_OPTIONS"
        if options:
            result["note"] = ("A release at a different position was checked: " + "; ".join(f"{option['player']} ({option['position']}) — {option['reason']}"
                                                                                          for option in options) + ".")
        return result
    # Replaceability decides between positions (more available players clearly ahead, then reaching his range); ranks are never compared.
    chosen = min(eligible, key=lambda option: (-(option["replacement"]["clearly_ahead_count"] or 0), -(option["replacement"]["comparable_count"] or 0),
                                               -(option["count_after"] - option["depth_target"]), POSITIONS.index(option["position"]), option["player"], option["player_id"]))
    evaluation.update(state="VERIFIED", chosen=chosen["player_id"])
    result.update(drop=_cross_drop_view(add, chosen, add_evidence, basis, evaluation), material=True)
    return result


def _cross_drop_view(add, option, add_evidence, basis, evaluation):
    member, replacement = option["_model"], option["replacement"]
    position, value, displaced = member["position"], member["ros_value"], add_evidence["displaced"]
    comparison = add_evidence["ros_comparison"] or {"state": "NOT_APPLICABLE", "reason": f"{add['name']} fills a required slot; no {add['position']} on your roster is displaced."}
    materiality = add_evidence["ros_materiality"] or {"state": "NOT_APPLICABLE", "label": MATERIALITY_LABELS["NOT_APPLICABLE"], "reason": comparison["reason"]}
    plural = POSITION_PLURALS.get(position, f"{position}s")
    add_text = {"REQUIRED_SLOT_FILL": f"{add['name']} fills a required {add['position']} starting slot this week",
                "VERIFIED_NEED": f"{add['name']} fills a verified {add['position']} depth need ({add_evidence['count']} rostered against a target of {add_evidence['depth_target']})",
                "UNANIMOUS_STARTER_UPGRADE": f"{add['name']} is a {add['position']} starter upgrade every published expert agrees on this week",
                "CLEAR_ROS_EDGE": f"{add['name']} is clearly ahead for the rest of the season"}[basis]
    if displaced and comparison.get("state") == "CANDIDATE_BETTER":
        add_text += (f" and ranks ahead of {displaced['player']}, who is kept, for the rest of the season ({add['position']} ROS ECR "
                     f"{comparison['candidate_ecr']:.1f} vs {comparison['roster_ecr']:.1f}; {materiality['label']})")
    reason = (f"{member['name']} is your weakest releasable {position} for the rest of the season ({position} ROS ECR {value['ros_ecr']:.1f}"
              + (f", experts {_span(value)}" if _span(value) else "") + f") at a surplus position ({option['count']} {plural} against a supported depth target of "
              f"{option['depth_target']}, leaving {option['count_after']}), and {replacement['comparable_count']} healthy available {plural} have fresh "
              f"rest-of-season expert ranges reaching his, so he is replaceable from waivers. {add_text}. {option['safety']['reason']} "
              "Ranks are not compared across positions.")
    return {"player_id": member["id"], "player": member["name"], "position": position, "basis": "cross_position", "role": "CROSS_POSITION_BENCH",
            "add_ecr": None, "drop_ecr": value["ros_ecr"], "ros_comparison": comparison, "materiality": materiality, "safety": option["safety"],
            "ros_value": value, "replacement": replacement, "add_basis": basis, "add_basis_text": CROSS_ADD_BASIS_TEXT[basis], "displaced": displaced,
            "surplus": {"position": position, "count": option["count"], "count_after": option["count_after"], "depth_target": option["depth_target"]},
            "cross_position": evaluation, "reason": reason}


def _with_add(intent, add, fallbacks):
    """The intent re-pointed at another listed option, with that option's own expert separation (and current-week urgency) recomputed."""
    updated = {**intent, "add": add, "fallbacks": list(fallbacks)[:3]}
    if intent["kind"] == "CURRENT_WEEK_UPGRADE" and not intent.get("forced_monitor"):
        separation = expert_separation(add["week_rank"], intent["over"]["week_rank"])
        updated.update(materiality=separation, urgency="MATERIAL" if separation["state"] == "UNANIMOUS" else "OPTIONAL")
    elif intent["kind"] == "DEPTH_UPGRADE":
        updated["materiality"] = expert_separation(add["ros_rank"], intent["over"]["ros_rank"])
    return updated


def _post_move_view(intent, context):
    """The intent as the manager sees it once the higher-priority moves are made. Display only: moves are resolved and verified with the
    unchanged intent.

    A DEPTH_UPGRADE names its weakest bench player before any move is resolved. When a higher-priority move already releases him, the
    comparison is shown against the weakest ranked bench player still on the roster (the same player the cross-position check compares
    with), or against nobody when none remains. Expert separation is recomputed only while the add still ranks ahead of that player.
    """
    over = intent.get("over")
    if intent["kind"] != "DEPTH_UPGRADE" or over is None or over["id"] not in context["used_drops"]:
        return intent
    remaining = _weakest_remaining_bench(over["position"], context)
    add = intent.get("add")
    ahead = add is not None and remaining is not None and add["ros_rank"]["ecr"] < remaining["ros_rank"]["ecr"]
    return {**intent, "over": remaining, "released_over": over, "still_ahead": ahead,
            "materiality": expert_separation(add["ros_rank"], remaining["ros_rank"]) if ahead else None}


def _depth_why(add, shown):
    position, over = shown["position"], shown.get("over")
    if over is None:
        return (f"Rest-of-season {position} consensus rank {add['ros_rank']['ecr']:.1f} (lower is better); no ranked bench {position} is left to compare "
                "after the higher-priority moves.")
    return f"Rest-of-season {position} consensus rank {add['ros_rank']['ecr']:.1f} vs {over['ros_rank']['ecr']:.1f} for your weakest bench {position} (lower is better)."


def _horizon_views(intent, move, context, outcome=None):
    """Current week, rest of season, ROS materiality and replacement context for one move; they are never collapsed into one value.

    The rest-of-season comparison is made against the player who would leave the roster: the verified drop, otherwise the release
    that was blocked as not material, otherwise the player the candidate would replace.
    """
    ros = context["ros"]
    add, kind, drop = intent.get("add"), intent["kind"], move.get("drop")
    target = intent.get("over") or intent.get("replaced") or intent.get("slot_player")
    blocked = (outcome or {}).get("subject")
    if kind == "CURRENT_WEEK_UPGRADE":
        current = {"state": "CANDIDATE_BETTER", "add_ecr": add["week_rank"]["ecr"], "roster_ecr": target["week_rank"]["ecr"], "roster": target["name"],
                   "text": f"{add['name']} ECR {add['week_rank']['ecr']:.1f} vs {target['name']} ECR {target['week_rank']['ecr']:.1f}: {add['name']} is stronger this week."}
    elif kind == "MUST_FILL":
        occupant = intent.get("slot_player")
        filler = (f"{add['name']} (ECR {add['week_rank']['ecr']:.1f})" if add and _ranked(add["week_rank"]) else add["name"] if add else "No verified player")
        current = {"state": "SLOT_FILL", "text": (f"{occupant['name']} cannot play this week; " if occupant else "The slot is empty; ") + f"{filler} fills the {intent.get('slot')} slot."}
    else:
        current = {"state": "NOT_COMPARED", "text": "Bench depth move: your current-week lineup is unchanged."}
    materiality = None
    cross = bool(drop) and drop.get("basis") == "cross_position"
    if ros["state"] != "AVAILABLE":
        rest = {"state": ros["state"], "text": ros["reason"]}
    elif cross:
        # A cross-position release keeps the displaced player; the rest-of-season comparison stays at the candidate's own position.
        rest = {**drop["ros_comparison"], "roster": (drop.get("displaced") or {}).get("player"), "text": drop["ros_comparison"]["reason"]}
        materiality = drop["materiality"] if (drop.get("displaced") or {}).get("player") else None
    elif drop:
        rest = {**drop["ros_comparison"], "roster": drop["player"], "text": drop["ros_comparison"]["reason"]}
        materiality = drop["materiality"]
    elif add and blocked is not None:
        comparison = compare_ros_values(add["ros_value"], blocked["ros_value"], candidate_name=add["name"], roster_name=blocked["name"])
        rest = {**comparison, "roster": blocked["name"], "text": comparison["reason"]}
        materiality = outcome["materiality"]
    elif add and target:
        comparison = compare_ros_values(add["ros_value"], target["ros_value"], candidate_name=add["name"], roster_name=target["name"])
        rest = {**comparison, "roster": target["name"], "text": comparison["reason"]}
        materiality = ros_materiality(add["ros_value"], target["ros_value"], candidate_name=add["name"], roster_name=target["name"])
    else:
        rest = {"state": "NOT_APPLICABLE", "text": "No same-position rest-of-season comparison applies to this move."}
    rest.update(source=ros["source"], source_date=ros["source_date"], freshness_state=ros["freshness_state"])
    subject = ({"ros_value": drop["ros_value"], "name": drop["player"]} if drop else {"ros_value": blocked["ros_value"], "name": blocked["name"]} if blocked is not None
               else {"ros_value": target["ros_value"], "name": target["name"]} if target else None)
    replacement = None
    if subject is not None and ros["state"] == "AVAILABLE":
        replacement = replacement_context(subject["ros_value"], subject["name"], context["pools"].get(subject["ros_value"]["position"]),
                                          exclude_ids=[model["id"] for model in context["added"]])
    clear = (materiality or {}).get("state") == "CLEAR_EDGE"
    if cross:
        combination = "CROSS_POSITION_RELEASE"
        released = f"{drop['player']} ({drop['position']}), surplus depth with strong waiver replacement, is released"
        if kind == "MUST_FILL":
            impact = f"Fills a required {intent.get('slot') or add['position']} slot this week; {released}"
        elif kind == "DEPTH_UPGRADE":
            kept = (drop.get("displaced") or {}).get("player") or target["name"]
            impact = f"Adds {add['position']} depth for the rest of the season while {kept} stays; your current-week lineup is unchanged; {released}"
        else:
            impact = (f"Current-week upgrade over {target['name']}, who stays as {add['position']} depth; for the rest of the season {add['name']} also ranks "
                      f"ahead of him ({(materiality or {}).get('label') or 'materiality unverified'}); {released}")
    elif kind == "MUST_FILL":
        combination, impact = "REQUIRED_SLOT_FILL", "Fills a required starter slot this week"
        if clear and drop:
            impact += f"; {add['name']} is also clearly ahead of {drop['player']}, who is released, for the rest of the season"
    elif kind == "DEPTH_UPGRADE":
        combination = "C_DEPTH"
        if clear:
            impact = "Rest-of-season depth upgrade (bench); your current-week lineup is unchanged"
        elif target is None:
            impact = (f"Rest-of-season {add['position']} bench add; no ranked bench {add['position']} is left to compare after the higher-priority moves; "
                      "your current-week lineup is unchanged")
        else:
            spot = " for an open roster spot" if move.get("decision") == "ADD" else ""
            impact = f"Rest-of-season bench add{spot}, not a clear upgrade over {target['name']}; your current-week lineup is unchanged"
    elif rest.get("state") == "CANDIDATE_BETTER" and clear:
        combination = "A_BOTH"
        if drop and drop["player_id"] != target["id"]:
            impact = f"Current-week upgrade over {target['name']}; rest-of-season value clearly improves over {drop['player']}, who is released"
        else:
            impact = f"Current-week and clear rest-of-season upgrade over {target['name']}"
    elif rest.get("state") == "CANDIDATE_BETTER":
        combination = "A_CLOSE_ROS"
        impact = (f"Current-week upgrade; for the rest of the season the edge over {rest['roster']} is "
                  + ("a close call" if (materiality or {}).get("state") == "CLOSE_CALL" else "not verified") + ", so it does not justify a season-long release")
    elif rest.get("state") == "ROSTER_BETTER":
        combination, impact = "B_SHORT_TERM", f"Short-term current-week edge only; {rest['roster']} keeps more rest-of-season value"
    else:
        combination, impact = "D_CURRENT_WEEK_ONLY", "Current-week upgrade; rest-of-season value is not verified, so no longer-term conclusion is drawn"
    return current, rest, materiality, replacement, combination, impact


def _fallback_views(fallbacks, subject, ros_available, intent=None, context=None, open_spots=0):
    """Backups with their own ROS materiality against the same roster player and their own claim check.

    A verified drop is never inherited by a backup: each contingent claim is verified with that backup as the add. Backups are
    alternatives if the first claim fails, never cumulative claims.
    """
    views = []
    for model in fallbacks:
        view = _player_view(model, include_ros=True)
        if subject is not None and ros_available:
            materiality = ros_materiality(model["ros_value"], subject["ros_value"], candidate_name=model["name"], roster_name=subject["name"])
            view["ros_materiality"] = {"state": materiality["state"], "label": materiality["label"], "against": subject["name"]}
        if intent is not None and not intent.get("forced_monitor"):
            if open_spots > 0:
                view["claim"] = {"state": "ADD", "drop": None, "blocker": None, "reason": "An active roster spot is open, so nobody is released."}
            else:
                outcome = _safe_drop(_with_add(intent, model, []), context)
                drop = outcome["drop"]
                view["claim"] = {"state": "ADD_DROP" if drop else "MONITOR", "blocker": outcome["code"],
                                 "drop": {key: drop[key] for key in ("player_id", "player", "position", "basis")} if drop else None,
                                 "reason": drop["reason"] if drop else outcome["detail"]}
        views.append(view)
    return views


def _resolve(intent, context, open_spots):
    """One priority move. With a full roster, the first listed option (best current-week or rest-of-season order first) whose release
    passes every W3 safety check and the W4 materiality gate is recommended; an option already added by a higher-priority move is skipped."""
    ros = context["ros"]
    added = {model["id"] for model in context["added"]}
    passed_over, outcome = None, None
    if intent.get("add") is not None:
        options = [model for model in [intent["add"], *(intent.get("fallbacks") or [])] if model["id"] not in added]
        if not options:
            return None
        if options[0] is not intent["add"]:
            intent = _with_add(intent, options[0], options[1:])
        if not intent.get("forced_monitor") and open_spots <= 0:
            attempts = []
            for option in options:
                attempts.append((option, _safe_drop(_with_add(intent, option, []), context)))
                if attempts[-1][1]["drop"]:
                    break
            chosen, outcome = attempts[-1] if attempts[-1][1]["drop"] else attempts[0]
            if chosen is not intent["add"]:
                first, first_attempt = attempts[0]
                rank = first["ros_rank"] if intent["kind"] == "DEPTH_UPGRADE" else first["week_rank"]
                rank_text = (f"{first['position']} {'ROS ECR' if intent['kind'] == 'DEPTH_UPGRADE' else 'ECR'} {rank['ecr']:.1f}" if _ranked(rank) else "unranked")
                materiality = first_attempt.get("materiality")
                summary = (f"releasing {materiality['roster']} for {first['name']} is not supported: {materiality['summary'][0].lower()}{materiality['summary'][1:]}"
                           if materiality else first_attempt["detail"])
                passed_over = {"player_id": first["id"], "player": first["name"], "position": first["position"], "rank_text": rank_text,
                               "blocker": first_attempt["code"], "reason": first_attempt["detail"], "summary": summary}
                intent = _with_add(intent, chosen, [option for option in options if option is not chosen])
    add = intent.get("add")
    shown = _post_move_view(intent, context)
    move = {"kind": intent["kind"], "kind_label": KIND_LABELS[intent["kind"]], "urgency": intent["urgency"], "position": intent["position"], "slot": intent.get("slot"),
            "add": _player_view(add, include_ros=True), "over": _player_view(shown.get("over"), include_ros=True), "slot_player": _player_view(intent.get("slot_player"), include_ros=True),
            "fallbacks": [], "drop": None, "drop_state": None, "drop_blocker": None, "reason": None, "monitor_detail": None, "passed_over": passed_over,
            "materiality": shown.get("materiality"), "materiality_text": None, "trigger": intent.get("trigger"), "ordering": intent.get("ordering"), "disclosures": []}
    if intent["kind"] == "MUST_FILL":
        move["why"] = f"Required: {intent['trigger_text']}."
        if intent.get("ordering") == "VERIFIED_EQUIVALENT_OPTIONS":
            move["disclosures"].append("No current consensus rank separates these options; the order is stable, not a quality ranking.")
        elif intent.get("unranked_count"):
            move["disclosures"].append(f"{intent['ranked_count']} ranked option(s) ordered by current consensus; {intent['unranked_count']} unranked option(s) follow and were not used to prove superiority.")
    elif intent["kind"] == "CURRENT_WEEK_UPGRADE":
        move["why"] = f"Current-week {intent['position']} consensus rank {add['week_rank']['ecr']:.1f} vs {intent['over']['week_rank']['ecr']:.1f} (lower is better)."
    else:
        move["why"] = _depth_why(add, shown)
    if add and intent["kind"] != "DEPTH_UPGRADE":
        rank = add["week_rank"]
        move["evidence"] = {"source": rank.get("source") or CONSENSUS_SOURCE, "horizon": "this_week", "week": rank.get("week"), "source_date": rank.get("source_date"),
                            "freshness_state": rank.get("freshness_state") if _ranked(rank) else "UNAVAILABLE"}
    elif add:
        rank = add["ros_rank"]
        move["evidence"] = {"source": rank.get("source") or CONSENSUS_SOURCE, "horizon": "rest_of_season", "week": None, "source_date": rank.get("source_date"), "freshness_state": rank.get("freshness_state")}
    else:
        move["evidence"] = None
    materiality = shown.get("materiality") or {}
    over_name = (shown.get("over") or {}).get("name")
    if materiality.get("state") == "UNANIMOUS":
        move["materiality_text"] = (f"Expert ranges do not overlap: every published expert rank for {add['name']} ({materiality['candidate_range']}) is better than "
                                    f"every published expert rank for {over_name} ({materiality['roster_range']}).")
    elif materiality.get("state") == "SPLIT":
        move["materiality_text"] = f"CLOSE CALL: expert rank ranges overlap ({materiality['candidate_range']} vs {materiality['roster_range']})."
    elif materiality:
        move["materiality_text"] = "Expert rank ranges are unavailable, so how decisive this edge is cannot be verified."
    forced = intent.get("forced_monitor")
    if forced:
        move.update(decision="MONITOR", reason={"QUESTIONABLE": "HEALTH DESIGNATION PREVENTS A SUPPORTED ADD.", "FLEX_CROSS_POSITION": "CROSS-POSITION CHOICE REQUIRED.",
                                                 "NO_CANDIDATE": "NO VERIFIED AVAILABLE REPLACEMENT."}[forced], monitor_detail=intent.get("monitor_detail"), drop_state="NOT_EVALUATED",
                    state_label=MOVE_STATE_LABELS[forced], drop_safety={"state": "NOT_EVALUATED", "reason": "No supported ADD exists yet, so no release is evaluated."})
    elif open_spots > 0:
        move.update(decision="ADD", drop_state="NOT_REQUIRED", state_label=MOVE_STATE_LABELS["ADD"],
                    drop_safety={"state": "NOT_REQUIRED", "reason": "An active roster spot is open, so nobody is released."})
        move["disclosures"].append("Your roster has an open active spot, so no drop is needed.")
    elif outcome["drop"]:
        cross = outcome["drop"].get("basis") == "cross_position"
        move.update(decision="ADD_DROP", drop=outcome["drop"], drop_state="VERIFIED", state_label=MOVE_STATE_LABELS["ADD_DROP_CROSS" if cross else "ADD_DROP"],
                    drop_safety={"state": "SUPPORTED", "reason": outcome["drop"]["reason"]})
        if cross:
            same = outcome.get("same_position") or {}
            move["cross_position"] = outcome["drop"]["cross_position"]
            move["disclosures"].append("Cross-position release: positional ranks are never compared across positions; this release rests on the released "
                                       "player's positional surplus, his waiver replacement depth, and the post-move lineup check."
                                       + (f" No same-position release was verified: {same['detail']}" if same.get("detail") else ""))
    else:
        code = outcome["code"]
        label = code if code in ("ROS_VALUE_UNAVAILABLE", *MATERIALITY_BLOCKERS) else "NO_SAFE_DROP"
        move.update(decision="MONITOR", reason=NO_SAFE_DROP_REASON, monitor_detail=outcome["detail"], drop_state="UNVERIFIED", drop_blocker=code,
                    state_label=MOVE_STATE_LABELS[label], drop_safety={"state": "NOT_SUPPORTED", "blocker": code, "reason": outcome["detail"]})
        if outcome.get("cross_position"):
            move["cross_position"] = outcome["cross_position"]
    released = shown.get("released_over")
    if released is not None:
        position = intent["position"]
        move["released_over"] = {"player_id": released["id"], "player": released["name"], "position": released["position"]}
        move["disclosures"].append(f"{released['name']} is already released by a higher-priority move, so "
                                   + (f"this compares against your weakest bench {position} still on the roster." if shown.get("over") is not None
                                      else f"no ranked bench {position} is left to compare."))
        if move["decision"] == "MONITOR" and shown.get("over") is not None and not shown["still_ahead"]:
            move["reason"] = "NO LONGER AN UPGRADE AFTER THE HIGHER-PRIORITY MOVES."
    (move["current_week"], move["rest_of_season"], move["ros_materiality"], move["replacement_context"],
     move["value_combination"], move["impact"]) = _horizon_views(shown, move, context, outcome)
    target = (outcome or {}).get("subject") or shown.get("over") or intent.get("replaced") or intent.get("slot_player")
    cross = bool(move["drop"]) and move["drop"].get("basis") == "cross_position"
    # Backups are judged against the player who leaves the roster; after a cross-position release that is still the displaced same-position player.
    subject = ({"ros_value": move["drop"]["ros_value"], "name": move["drop"]["player"]} if move["drop"] and not cross
               else {"ros_value": target["ros_value"], "name": target["name"]} if target else None)
    move["fallbacks"] = _fallback_views(intent.get("fallbacks") or [], subject, ros["state"] == "AVAILABLE", intent=intent, context=context, open_spots=open_spots)
    if ros["state"] != "AVAILABLE" and intent["kind"] != "DEPTH_UPGRADE":
        move["disclosures"].append(ROS_UNAVAILABLE_LABEL)
    move["decision_label"] = DECISION_LABELS[move["decision"]]
    move["_add_model"] = add
    return move


def _depth_note(move):
    """A same-position ROS comparison that is not a meaningful upgrade (close call or unverified separation): shown under HOLD, never as churn."""
    state = "CLOSE_CALL" if move["drop_blocker"] == "ROS_EDGE_NOT_MATERIAL" else "UNVERIFIED"
    materiality = move.get("ros_materiality") or {}
    text = (f"{materiality['reason']} No release is recommended." if materiality.get("state") in ("CLOSE_CALL", "UNVERIFIED") else move["monitor_detail"])
    return {"position": move["position"], "state": state, "label": MATERIALITY_LABELS[state], "add": move["add"], "over": move["over"],
            "ros_materiality": materiality, "replacement_context": move["replacement_context"], "fallbacks": move["fallbacks"],
            "blocker": move["drop_blocker"], "detail": move["monitor_detail"], "text": text}


def _drop_status(model, move, context, candidates, value_holds=None):
    """Why one roster player is or is not releasable: SAFE, PROTECTED, or UNVERIFIED, with the actual reason.

    A release is judged with its replacement, exactly as a recommended drop is: SAFE needs an available, addable same-position
    player, not already a recommended add, who is clearly ahead for the rest of the season and keeps every starting slot covered.
    A PROTECTED status that rests only on same-position value (no available player ranks better, the only better ones are already
    recommended adds, or their expert ranges overlap his) is also recorded in value_holds; protection rules and lineup coverage are not.
    """
    def value_hold(reason):
        if value_holds is not None:
            value_holds.add(model["id"])
        return {"state": "PROTECTED", "reason": reason}

    if move:
        return {"state": "SAFE", "reason": f"Verified drop for ADD {move['add']['player']}: {move['drop']['reason']}"}
    if model["reserve"] or model["taxi"]:
        return {"state": "PROTECTED", "reason": f"On {'IR (reserve)' if model['reserve'] else 'the taxi squad'}; releasing him would not open an active roster spot."}
    if model["id"] in context["protections"]:
        return {"state": "PROTECTED", "reason": context["protections"][model["id"]]}
    if model["is_starter"] is True:
        return {"state": "PROTECTED", "reason": "Current starter: released only for a same-position player who is stronger this week and clearly ahead for the rest of the season."}
    if model["context"]["lock_state"] not in DROPPABLE_LOCK_STATES:
        return {"state": "UNVERIFIED", "reason": "His game lock state could not be verified, so a release cannot be checked."}
    if context["ros"]["state"] != "AVAILABLE":
        return {"state": "UNVERIFIED", "reason": f"Rest-of-season value is unavailable: {context['ros']['reason']}"}
    value, position = model["ros_value"], model["position"]
    if value["evidence_state"] != "RANKED":
        return {"state": "UNVERIFIED", "reason": f"No fresh rest-of-season rank ({value['evidence_state'].replace('_', ' ').lower()}), so releasing him cannot be verified."}
    better = sorted((candidate for candidate in candidates if candidate["position"] == position and candidate["depth_addable"]
                     and candidate["ros_value"]["evidence_state"] == "RANKED" and candidate["ros_value"]["ros_ecr"] < value["ros_ecr"]),
                    key=lambda candidate: (candidate["ros_value"]["ros_ecr"], candidate["name"], candidate["id"]))
    added = {candidate["id"] for candidate in context["added"]}
    open_better = [candidate for candidate in better if candidate["id"] not in added]
    if not better:
        return value_hold(f"No available {position} has a better fresh rest-of-season rank than his {position} ROS ECR {value['ros_ecr']:.1f}, "
                          "so releasing him would give up rest-of-season value.")
    if not open_better:
        names = ", ".join(candidate["name"] for candidate in better)
        return value_hold(f"The only available {position} with a better fresh rest-of-season rank ({names}) "
                          f"{'is' if len(better) == 1 else 'are'} already a recommended add, so releasing him as well would give up rest-of-season value.")
    judged = [(candidate, ros_materiality(candidate["ros_value"], value, candidate_name=candidate["name"], roster_name=model["name"])) for candidate in open_better]
    first_loss = None
    for replacement, materiality in judged:
        if materiality["state"] != "CLEAR_EDGE":
            continue
        safety = _post_move_safety(replacement, model, context)
        if safety["state"] == "SAFE":
            return {"state": "SAFE", "reason": f"Releasable: available {replacement['name']} is clearly ahead of him for the rest of the season "
                                               f"({position} ROS ECR {replacement['ros_value']['ros_ecr']:.1f} vs {value['ros_ecr']:.1f}; expert ranges "
                                               f"{materiality['candidate_range']} vs {materiality['roster_range']} do not overlap) and the lineup stays covered; "
                                               "no current move uses this release."}
        first_loss = first_loss or safety["reason"]
    if first_loss:
        return {"state": "PROTECTED", "reason": first_loss}
    best = judged[0][0]
    if any(materiality["state"] == "CLOSE_CALL" for _, materiality in judged):
        return value_hold(f"Available {position} players rank ahead of him (best: {best['name']}, {position} ROS ECR {best['ros_value']['ros_ecr']:.1f} "
                          f"vs his {value['ros_ecr']:.1f}), but none is clearly ahead: their expert ranges overlap his, so releasing him would not be a meaningful upgrade.")
    return {"state": "UNVERIFIED", "reason": f"Available {position} players rank ahead of him (best: {best['name']}), but expert ranges are unavailable, "
                                             "so consensus separation cannot be verified."}


def _ros_value_block(models, candidate_models, moves, context):
    verified = {move["drop"]["player_id"]: move for move in moves if move.get("drop")}

    def coverage(group):
        by_position, states = {}, {}
        for model in group:
            state = model["ros_value"]["evidence_state"]
            states[state] = states.get(state, 0) + 1
            bucket = by_position.setdefault(model["position"], {"ranked": 0, "unranked": 0, "materiality_capable": 0})
            bucket["ranked" if state == "RANKED" else "unranked"] += 1
            bucket["materiality_capable"] += model["ros_value"]["range_state"] == "VALID"
        return {"ranked": sum(bucket["ranked"] for bucket in by_position.values()), "unranked": sum(bucket["unranked"] for bucket in by_position.values()),
                "materiality_capable": sum(bucket["materiality_capable"] for bucket in by_position.values()), "by_position": by_position, "states": states}

    value_holds = set()
    drop_status = {model["id"]: _drop_status(model, verified.get(model["id"]), context, candidate_models, value_holds) for model in models}
    return {"roster": {model["id"]: model["ros_value"] for model in models}, "candidates": {model["id"]: model["ros_value"] for model in candidate_models},
            "drop_status": drop_status, "no_same_position_upgrade": sorted(value_holds),
            "protected": dict(context["protections"]), "coverage": {"roster": coverage(models), "candidates": coverage(candidate_models)}}


def _replacement_block(context):
    """waiver.replacement_context.v1 for the page: per-position pools without players already recommended as adds, each position's
    weakest rest-of-season-ranked active player as its reference, and every active player's own context."""
    added = {model["id"] for model in context["added"]}
    positions = {}
    for position, pool in context["pools"].items():
        comparison = [entry for entry in pool["comparison"] if entry["player_id"] not in added]
        remaining = {"position": position, "comparison": comparison, "best_available": comparison[:3],
                     "recommended_adds": [{"player_id": entry["player_id"], "player": entry["player"]} for entry in pool["comparison"] if entry["player_id"] in added],
                     "counts": {**pool["counts"], "recommended_adds_excluded": len(pool["comparison"]) - len(comparison), "remaining": len(comparison)}}
        ranked = [model for model in context["active"] if model["position"] == position and model["ros_value"]["evidence_state"] == "RANKED"]
        reference = max(ranked, key=lambda model: (model["ros_value"]["ros_ecr"], model["name"], model["id"])) if ranked else None
        remaining["reference"] = ({"player": reference["name"], "player_id": reference["id"], "is_starter": reference["is_starter"], "ros_value": reference["ros_value"],
                                   "context": replacement_context(reference["ros_value"], reference["name"], remaining)} if reference else None)
        positions[position] = remaining
    players = {model["id"]: replacement_context(model["ros_value"], model["name"], positions.get(model["position"])) for model in context["active"]}
    return {"contract_id": REPLACEMENT_CONTEXT_CONTRACT_ID, "rule": REPLACEMENT_RULE, "positions": positions, "players": players}


DROP_CANDIDATE_ORDER = {"VERIFIED_DROP": 0, "RELEASABLE": 1, "KEEP": 2, "UNVERIFIED": 3}
DROP_CANDIDATE_LABELS = {"VERIFIED_DROP": "VERIFIED DROP", "RELEASABLE": "RELEASABLE IF THE SPOT IS NEEDED", "KEEP": "KEEP", "UNVERIFIED": "NOT EVALUATED"}
DROP_CANDIDATES_RULE = ("Bench players ordered from most to least expendable by verified evidence, never by a score: verified drops of priority moves first; "
                        "then players whose release keeps their position at its supported depth target and who have STRONG waiver replacement depth "
                        "(more available players clearly ahead, then more whose expert range reaches his); then players to keep; then players without "
                        "a fresh rest-of-season rank, who are not treated as worse. Each entry is an alternative, not a cumulative plan.")


def _drop_candidates_block(active, moves, context, replacement):
    """waiver.drop_candidates.v1: the bottom of the roster, from most to least expendable, with the evidence for each player."""
    needs = context.get("needs") or {}
    positions = needs.get("positions") or {}
    verified = {move["drop"]["player_id"]: move for move in moves if move.get("drop")}
    independent = {**context, "used_drops": set()}
    bench = [model for model in active if model["is_starter"] is False]
    weakest = {}
    for model in bench:
        if _drop_hold(model, independent) is None and model["ros_value"]["evidence_state"] == "RANKED":
            current = weakest.get(model["position"])
            if current is None or (model["ros_value"]["ros_ecr"], model["name"]) > (current["ros_value"]["ros_ecr"], current["name"]):
                weakest[model["position"]] = model
    entries = []
    for model in bench:
        position, value = model["position"], model["ros_value"]
        count = sum(1 for other in active if other["position"] == position)
        target = (positions.get(position) or {}).get("depth_target")
        own = (replacement.get("players") or {}).get(model["id"]) or {}
        week = model["week_rank"]
        entry = {"player_id": model["id"], "player": model["name"], "position": position, "team": model["context"]["team"],
                 "ros_ecr": value.get("ros_ecr"), "ros_range": _span(value) if value.get("evidence_state") == "RANKED" else None,
                 "ros_state": value.get("evidence_state"), "week_ecr": week.get("ecr") if _ranked(week) else None,
                 "count": count, "depth_target": target, "replacement_state": own.get("state"), "replacement_label": own.get("label"),
                 "comparable_count": own.get("comparable_count"), "clearly_ahead_count": own.get("clearly_ahead_count"), "priority": None, "reasons": []}
        held = _drop_hold(model, independent)
        if model["id"] in verified:
            move = verified[model["id"]]
            entry.update(state="VERIFIED_DROP", priority=move.get("priority"), reasons=[f"Verified drop for ADD {move['add']['player']}: {move['drop']['reason']}"])
        elif held:
            entry.update(state="KEEP", reasons=[held[1]])
        elif context["ros"]["state"] != "AVAILABLE" or value.get("evidence_state") != "RANKED" or needs.get("state") != "AVAILABLE":
            why = (f"no fresh rest-of-season rank ({str(value.get('evidence_state') or 'unavailable').replace('_', ' ').lower()})"
                   if context["ros"]["state"] == "AVAILABLE" and value.get("evidence_state") != "RANKED" else
                   "rest-of-season value is unavailable" if context["ros"]["state"] != "AVAILABLE" else (needs.get("reason") or "team needs are unavailable"))
            entry.update(state="UNVERIFIED", reasons=[f"Not ranked here: {why}; an unranked player is not treated as worse."])
        else:
            depth_ok = isinstance(target, int) and count - 1 >= target
            replaceable = own.get("state") == "STRONG"
            # A bare release (no add) must keep every starting slot, including FLEX, fillable this week and for the season.
            safety = _post_move_safety(None, model, independent)
            reasons = [(f"{position}: {count} rostered against a supported depth target of {target}" + (" (surplus)" if count > target else "")
                        + ("; releasing him keeps the target." if depth_ok else f"; releasing him would leave {count - 1}, below the target."))]
            reasons.append(f"{own.get('label')}: {own.get('reason')}")
            if safety["state"] != "SAFE":
                reasons.append(safety["reason"])
            if weakest.get(position) is not None and weakest[position]["id"] != model["id"]:
                reasons.append(f"{weakest[position]['name']} ranks below him at {position} for the rest of the season, so he would be released first.")
            entry.update(state="RELEASABLE" if depth_ok and replaceable and safety["state"] == "SAFE" else "KEEP", reasons=reasons)
        entry["label"] = DROP_CANDIDATE_LABELS[entry["state"]]
        entries.append(entry)
    entries.sort(key=lambda entry: (DROP_CANDIDATE_ORDER[entry["state"]], entry["priority"] or 0, -(entry["clearly_ahead_count"] or 0),
                                    -(entry["comparable_count"] or 0), -((entry["count"] - 1 - entry["depth_target"]) if isinstance(entry["depth_target"], int) else -99),
                                    POSITIONS.index(entry["position"]) if entry["position"] in POSITIONS else 9, entry["player"], entry["player_id"]))
    for rank, entry in enumerate(entries, 1):
        entry["order"] = rank
    return {"contract_id": DROP_CANDIDATES_CONTRACT_ID, "state": "AVAILABLE" if context["ros"]["state"] == "AVAILABLE" and needs.get("state") == "AVAILABLE" else "PARTIAL",
            "rule": DROP_CANDIDATES_RULE, "players": entries}


def _position_summary(position, status, reason, **extra):
    ranked, unranked = extra.get("ranked_candidates"), extra.get("unranked_candidates")
    summary = {"position": position, "status": status, "reason": reason, "ranked_candidates": ranked, "unranked_candidates": unranked,
               "starters": extra.get("starters") or [], "best_candidate": extra.get("best_candidate"), "locked_starters": extra.get("locked_starters") or [],
               "unranked_starters": extra.get("unranked_starters") or []}
    summary["rank_disclosure"] = (f"{ranked} ranked candidate(s) compared; {unranked} additional player(s) were unranked and were not used to prove superiority."
                                  if isinstance(ranked, int) and isinstance(unranked, int) else None)
    return summary


def _verdict_state(moves, insufficient_positions):
    if any(move["urgency"] == "REQUIRED" for move in moves) or any(
        move["kind"] == "CURRENT_WEEK_UPGRADE" and move["urgency"] == "MATERIAL" and move["decision"] in ("ADD", "ADD_DROP") for move in moves
    ):
        return "ACT"
    if moves:
        return "OPTIONAL"
    if insufficient_positions:
        return "INSUFFICIENT_EVIDENCE"
    return "PASS"


def _finish(result, state, *, global_reasons):
    moves, holds = result["moves"], result["hold_positions"]
    executable = [move for move in moves if move["decision"] in ("ADD", "ADD_DROP")]
    # A pass is a full pass only when rest-of-season depth and its materiality were evaluated too; otherwise "Save FAAB" is withheld.
    unverified_depth = sorted({note["position"] for note in result.get("depth_notes") or [] if note["state"] == "UNVERIFIED"})
    full_pass = state == "PASS" and (result.get("rest_of_season") or {}).get("state") == "AVAILABLE" and not unverified_depth
    if state == "BLOCKED":
        headline, detail = "BLOCKED", "Waiver recommendations are withheld because a hard safety check failed."
    elif state == "ACT":
        headline = "ACT"
        detail = f"{len(executable)} supported move(s) to make before waivers run." if executable else "A required starter slot needs a move; review the priority moves."
    elif state == "OPTIONAL":
        headline, detail = "OPTIONAL", "Supported improvements exist, but none is required and some need your judgment."
    elif state == "PASS":
        headline = "NO WAIVER MOVE RECOMMENDED"
        detail = "Your supported current roster options rank ahead of the available alternatives at the positions that could be compared."
        if (result.get("rest_of_season") or {}).get("state") != "AVAILABLE":
            detail += (" Rest-of-season depth upgrades were not evaluated because rest-of-season value is unavailable; "
                       "refresh it before deciding to save FAAB.")
        elif unverified_depth:
            detail += (f" Rest-of-season expert separation could not be verified for {', '.join(unverified_depth)} depth, "
                       "so saving FAAB is not yet supported.")
    else:
        headline, detail = "INSUFFICIENT EVIDENCE", "The roster comparison could not be completed, so no move or pass can be supported."
    result["verdict"] = {
        "state": state, "headline": headline, "detail": detail, "reasons": list(dict.fromkeys(global_reasons or [])),
        "save_faab": full_pass, "save_faab_text": "Save FAAB." if full_pass else None,
        "hold_text": " · ".join(holds) if holds else None,
        "counts": {"moves": len(moves), "executable": len(executable), "monitor": sum(1 for move in moves if move["decision"] == "MONITOR")},
    }
    return result


def _first_sentence(text: Any) -> str:
    text = str(text or "").strip()
    end = text.find(". ")
    return text if end < 0 else text[:end + 1]


def _plan_evidence(move: Mapping[str, Any]) -> list[str]:
    """How strong each part of a move's evidence is, in the engine's own vocabulary (no score)."""
    lines = []
    separation = (move.get("materiality") or {}).get("state")
    if move.get("kind") == "CURRENT_WEEK_UPGRADE":
        lines.append({"UNANIMOUS": "This week: every published expert ranks him ahead (expert ranges do not overlap).",
                      "SPLIT": "This week: ahead by consensus, but expert ranges overlap (close call)."}.get(separation, "This week: expert ranges unavailable."))
    elif move.get("kind") == "MUST_FILL":
        lines.append("This week: fills a required starting slot.")
    materiality = move.get("ros_materiality") or {}
    if materiality.get("label"):
        against = (move.get("rest_of_season") or {}).get("roster")
        lines.append(f"Rest of season: {materiality['label']}" + (f" vs {against}." if against else "."))
    drop = move.get("drop") or {}
    replacement = move.get("replacement_context") or {}
    if drop and replacement.get("label"):
        lines.append(f"Release: {replacement['label']} for {drop.get('player')} ({drop.get('position')}).")
    return lines


def _add_line(move: Mapping[str, Any]) -> str:
    """The move's add in the Priority Moves wording: ADD when the move is executable, CANDIDATE while it is monitored, and NO ADD RECOMMENDED
    when no player is supported (the move's monitor reason says why); never an empty or missing player."""
    add = (move.get("add") or {}).get("player")
    if not add:
        return "NO ADD RECOMMENDED"
    return f"{'CANDIDATE' if move.get('decision') == 'MONITOR' else 'ADD'} {add}"


def _plan_move(move: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not move:
        return None
    add, drop = move.get("add") or {}, move.get("drop") or {}
    claims = []
    for backup in move.get("fallbacks") or []:
        claim = backup.get("claim") or {}
        claims.append({"add": backup.get("player"), "add_id": backup.get("player_id"), "team": backup.get("team"), "position": backup.get("position"),
                       "state": claim.get("state") or "NOT_EVALUATED", "drop": (claim.get("drop") or {}).get("player"),
                       "drop_position": (claim.get("drop") or {}).get("position"), "reason": _first_sentence(claim.get("reason"))})
    return {"priority": move.get("priority"), "decision": move.get("decision"), "state_label": move.get("state_label"), "kind": move.get("kind"),
            "position": move.get("position"), "add": {"player_id": add.get("player_id"), "player": add.get("player"), "team": add.get("team"), "position": add.get("position")} if add else None,
            "add_line": _add_line(move),
            "drop": {"player_id": drop.get("player_id"), "player": drop.get("player"), "position": drop.get("position"), "basis": drop.get("basis")} if drop else None,
            "over": (move.get("over") or {}).get("player"), "why": " ".join(part for part in (move.get("why"), move.get("materiality_text")) if part),
            "improvement": move.get("impact"), "current_week": (move.get("current_week") or {}).get("text"), "rest_of_season": (move.get("rest_of_season") or {}).get("text"),
            "drop_safety": (move.get("drop_safety") or {}).get("reason"), "monitor_reason": move.get("monitor_detail"), "evidence": _plan_evidence(move),
            "claims": claims, "faab": move.get("faab") or {}, "market_lines": list((move.get("market") or {}).get("lines") or [])}


def _plan_positions(decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    moves, needs = decision.get("moves") or [], ((decision.get("team_needs") or {}).get("positions") or {})
    rows = []
    for position in POSITIONS:
        summary = (decision.get("positions") or {}).get(position) or {}
        need = needs.get(position) or {}
        at = [move for move in moves if move.get("position") == position]
        released = [move for move in moves if move.get("decision") == "ADD_DROP" and (move.get("drop") or {}).get("position") == position]
        status = summary.get("status")
        if any(move.get("decision") in ("ADD", "ADD_DROP") for move in at):
            label = "FILL" if any(move.get("kind") == "MUST_FILL" for move in at) else "UPGRADE"
        elif at:
            label = "MONITOR"
        elif status in ("BLOCKED", "NOT_APPLICABLE"):
            label = status.replace("_", " ")
        elif need.get("strategic_need") == "ADD_STARTER":
            label = "NEED"
        elif need.get("depth_status") == "ABOVE_TARGET" or released:
            label = "SURPLUS"
        elif status == "INSUFFICIENT_EVIDENCE":
            label = "UNVERIFIED"
        else:
            label = "HOLD"
        details = []
        if need.get("state") == "AVAILABLE" and status != "NOT_APPLICABLE":
            depth = {"BELOW_TARGET": " (below target)", "ABOVE_TARGET": " (surplus)", "AT_TARGET": ""}.get(need.get("depth_status"), "")
            details.append(f"{need.get('rostered_or_eligible')} rostered · depth target {need.get('depth_target')}{depth}")
        for move in at:
            add = (move.get("add") or {}).get("player") or "no add recommended"
            details.append(f"#{move.get('priority')} {move.get('state_label')}: {add}" + (f" over {move['over']['player']}" if move.get("over") else ""))
        for move in released:
            details.append(f"{move['drop']['player']} released by #{move.get('priority')}")
        if not at and summary.get("reason"):
            details.append(summary["reason"])
        rows.append({"position": position, "label": label, "status": status, "detail": " · ".join(details)})
    return rows


def _plan_faab(decision: Mapping[str, Any], move: Mapping[str, Any] | None, market: Mapping[str, Any] | None) -> dict[str, Any]:
    """FAAB evidence for the plan: the verified balance and descriptive league history only; no value-based bid is derived."""
    balance, market = decision.get("faab") or {}, dict(market or {})
    budget = (market.get("budget_context") or {})
    distribution = budget.get("distribution") or {}
    position = (move or {}).get("position")
    summary = (market.get("position_summaries") or {}).get(position) or {}
    guardrail = (move or {}).get("faab") or {}
    return {"state": balance.get("state"), "remaining": balance.get("remaining"), "budget": balance.get("budget"),
            "league_median_remaining": distribution.get("median_remaining") if budget.get("state") == "AVAILABLE" else None,
            "league_teams_verified": f"{distribution.get('n')}/{budget.get('total')}" if budget.get("state") == "AVAILABLE" else None,
            "market_state": market.get("state"), "market_label": market.get("label"), "scope": market.get("scope_text"), "position": position,
            "position_history": summary.get("text"), "contested_bids": (summary.get("contested_bids") or {}).get("text"),
            "uncontested_bids": (summary.get("uncontested_bids") or {}).get("text"),
            "player_history": next((line for line in ((move or {}).get("market") or {}).get("lines") or [] if line.startswith("Player history")), None),
            "coverage": (market.get("completeness") or {}).get("text"), "limitations": list(market.get("limitations") or []),
            "guardrail": guardrail if guardrail.get("state") == "PROVISIONAL" else None,
            "value_bid": VALUE_BID_UNAVAILABLE, "disclosure": FAAB_DISCLOSURE}


DROP_STATUS_LABELS = {"VERIFIED_DROP": "VERIFIED DROP", "SAFE": "RELEASABLE FOR A SAME-POSITION UPGRADE", "PROTECTED": "PROTECTED",
                      "NO_SAME_POSITION_UPGRADE": "NO SAME-POSITION UPGRADE", "UNVERIFIED": "UNVERIFIED"}


def roster_player_status(decision: Mapping[str, Any] | None, player_id: Any) -> dict[str, Any]:
    """The lookup's DROP STATUS and ROSTER SPOT for one rostered player, read from the shared decision (display only).

    DROP STATUS is the same-position check (waiver.ros_value.v1 drop_status): can an available player at his position replace him? ROSTER
    SPOT is waiver.drop_candidates.v1: can his spot be freed for a player at another position? A bench player kept only because no available
    player at his position is a verified rest-of-season upgrade (ros_value no_same_position_upgrade) reads NO SAME-POSITION UPGRADE, so he is
    never shown as PROTECTED beside a releasable roster spot. Every other PROTECTED status (a protection rule, a current starter, IR/taxi, or
    a release the post-move lineup check rejects) stays PROTECTED. The underlying states are unchanged.
    """
    pid = str(player_id or "")
    decision = decision or {}
    ros_value = decision.get("ros_value") or {}
    entry = next((item for item in (decision.get("drop_candidates") or {}).get("players") or [] if item.get("player_id") == pid), None)
    status = (ros_value.get("drop_status") or {}).get(pid)
    view = None
    if status:
        state = status.get("state")
        if any((move.get("drop") or {}).get("player_id") == pid for move in decision.get("moves") or []):
            key = "VERIFIED_DROP"
        elif state == "PROTECTED" and pid in set(ros_value.get("no_same_position_upgrade") or ()):
            key = "NO_SAME_POSITION_UPGRADE"
        else:
            key = state
        view = {**status, "label": DROP_STATUS_LABELS.get(key, str(state or "").replace("_", " "))}
    return {"drop_status": view, "roster_spot": entry}


MOVE_DROP_LINE_STATES = {"VERIFIED": "VERIFIED", "NOT_REQUIRED": "NOT_NEEDED", "UNVERIFIED": "NOT_VERIFIED", "NOT_EVALUATED": "NOT_EVALUATED"}
CLAIM_DROP_LINE_STATES = {"ADD_DROP": "VERIFIED", "ADD": "NOT_NEEDED", "MONITOR": "NOT_VERIFIED"}


def _drop_line(priority: Any, *, state: str, drop: Mapping[str, Any] | None, state_label: Any = None, backup: bool = False) -> dict[str, Any]:
    """What a priority ADD or backup claim does with the roster: a verified drop, no drop needed (open roster spot), a drop that is still
    required but not verified, or no release evaluated yet. The absence of a drop is never shown as missing evidence when none is needed."""
    claim = f"backup claim for Priority Move #{priority}" if backup else f"Priority Move #{priority}"
    line = {"state": state, "player_id": None, "player": None, "position": None}
    if state == "VERIFIED" and drop:
        verified = f"verified backup claim for Priority Move #{priority}" if backup else f"verified by Priority Move #{priority}"
        return {**line, "player_id": drop.get("player_id"), "player": drop.get("player"), "position": drop.get("position"),
                "text": f"{drop.get('player')} ({drop.get('position')}) — {verified}"}
    if state == "NOT_NEEDED":
        return {**line, "text": f"Not needed — open roster spot ({claim})"}
    if state == "NOT_VERIFIED":
        return {**line, "text": f"None verified ({state_label}, {claim})" if state_label else f"None verified ({claim})"}
    return {**line, "state": "NOT_EVALUATED", "text": f"Not evaluated — no supported ADD exists yet ({claim})"}


def priority_by_player(decision: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Each candidate's part in the Priority Moves (the ADD or a contingent backup claim) with its drop line, keyed by Sleeper player ID, so
    Candidate Evidence and the Player-to-Roster Checks restate the same decision. The first move that names a player wins."""
    entries: dict[str, dict[str, Any]] = {}
    for move in (decision or {}).get("moves") or []:
        priority = move.get("priority")
        if move.get("add"):
            entries.setdefault(str(move["add"].get("player_id")), {
                "role": "ADD", "priority": priority, "decision": move.get("decision"), "state_label": move.get("state_label"), "drop": move.get("drop"),
                "drop_line": _drop_line(priority, state=MOVE_DROP_LINE_STATES.get(move.get("drop_state"), "NOT_EVALUATED"), drop=move.get("drop"),
                                        state_label=move.get("state_label"))})
        for backup in move.get("fallbacks") or []:
            claim = backup.get("claim") or {}
            entries.setdefault(str(backup.get("player_id")), {
                "role": "BACKUP", "priority": priority, "claim": claim,
                "drop_line": _drop_line(priority, state=CLAIM_DROP_LINE_STATES.get(claim.get("state"), "NOT_EVALUATED"), drop=claim.get("drop"), backup=True)})
    return entries


def build_manager_plan(decision: Mapping[str, Any] | None, *, market: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """waiver.manager_plan.v1: the shared decision restated for the top of /waivers (what to do, who to add and drop, backup plan, FAAB evidence).

    Pure and read-only: it never re-derives a move, a drop, or a bid. League market history stays descriptive, so the bid line is always
    VALUE-BASED BID UNAVAILABLE unless the existing provisional K/DEF slot-fill guardrail applies.
    """
    decision = dict(decision or {})
    verdict = decision.get("verdict") or {}
    moves = decision.get("moves") or []
    executable = [move for move in moves if move.get("decision") in ("ADD", "ADD_DROP")]
    monitors = [move for move in moves if move.get("decision") == "MONITOR"]
    best = executable[0] if executable else None
    state = verdict.get("state") or "INSUFFICIENT_EVIDENCE"
    if best:
        add, drop = (best.get("add") or {}).get("player"), (best.get("drop") or {}).get("player")
        headline = f"ADD {add} · DROP {drop}" if drop else f"ADD {add} (open roster spot)"
    elif monitors:
        headline = f"MONITOR {(monitors[0].get('add') or {}).get('player') or monitors[0].get('position')} — no move is supported yet"
    elif state == "PASS":
        headline = "NO WAIVER MOVE RECOMMENDED" + (" · Save FAAB." if verdict.get("save_faab") else "")
    else:
        headline = verdict.get("headline") or state.replace("_", " ")
    candidates = [entry for entry in (decision.get("drop_candidates") or {}).get("players") or [] if entry.get("state") in ("VERIFIED_DROP", "RELEASABLE")]
    plan_best = _plan_move(best)
    return {"contract_id": MANAGER_PLAN_CONTRACT_ID, "state": state, "headline": headline, "detail": verdict.get("detail"), "reasons": list(verdict.get("reasons") or []),
            "best_move": plan_best, "backup_claims": (plan_best or {}).get("claims") or [], "more_moves": [_plan_move(move) for move in executable[1:]],
            "monitor": [_plan_move(move) for move in monitors], "faab": _plan_faab(decision, best or (monitors[0] if monitors else None), market),
            "drop_candidates": candidates[:3], "drop_candidates_rule": (decision.get("drop_candidates") or {}).get("rule"),
            "positions": _plan_positions(decision), "blockers": list(decision.get("blockers") or []), "submits_transactions": False}


def selected_player_priority(decision: Mapping[str, Any] | None, player_id: Any) -> dict[str, Any] | None:
    """The Priority Moves decision involving one roster player, restated for the Waiver Move Checker so the two never diverge."""
    pid = str(player_id or "")
    if not pid or not decision:
        return None
    for move in decision.get("moves") or []:
        # A comparison re-pointed after a higher-priority release is display only; it never links the bench player to this move.
        replaced = (move.get("over") or {}).get("player_id") == pid and not move.get("released_over")
        role = ("REPLACED" if replaced else "SLOT" if (move.get("slot_player") or {}).get("player_id") == pid
                else "DROP" if (move.get("drop") or {}).get("player_id") == pid else None)
        if role:
            plan = _plan_move(move)
            primary = {"add": (move.get("add") or {}).get("player"), "add_id": (move.get("add") or {}).get("player_id"), "team": (move.get("add") or {}).get("team"),
                       "week_ecr": ((move.get("add") or {}).get("rank") or {}).get("ecr"), "ros_ecr": ((move.get("add") or {}).get("ros_value") or {}).get("ros_ecr"),
                       "state": move.get("decision"), "drop": (move.get("drop") or {}).get("player"), "drop_position": (move.get("drop") or {}).get("position")}
            options = ([primary] if move.get("add") else []) + [{"add": backup.get("player"), "add_id": backup.get("player_id"), "team": backup.get("team"),
                                    "week_ecr": (backup.get("rank") or {}).get("ecr") if (backup.get("rank") or {}).get("state") == "RANKED" else None,
                                    "ros_ecr": (backup.get("ros_value") or {}).get("ros_ecr"), "state": (backup.get("claim") or {}).get("state") or "NOT_EVALUATED",
                                    "drop": ((backup.get("claim") or {}).get("drop") or {}).get("player"),
                                    "drop_position": ((backup.get("claim") or {}).get("drop") or {}).get("position")} for backup in move.get("fallbacks") or []]
            return {"state": "IN_PRIORITY_MOVE", "role": role, "move": plan, "options": options}
    entry = next((item for item in (decision.get("drop_candidates") or {}).get("players") or [] if item.get("player_id") == pid), None)
    return {"state": "NO_PRIORITY_MOVE", "role": None, "move": None, "options": [], "drop_candidate": entry}
