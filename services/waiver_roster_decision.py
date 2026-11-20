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
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

from services.game_lock import build_game_lock
from services.schedule_bye_evidence import team_bye_evidence
from services.team_codes import canonical_team

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
    "ADD_DROP": "ADD + DROP", "ADD": "ADD — OPEN ROSTER SPOT", "NO_SAFE_DROP": "MONITOR — NO SAFE DROP VERIFIED",
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
                                 schedule_max_age_seconds: Any = None) -> dict[str, Any]:
    """Return the waiver.roster_decision.v1 contract: verdict, priority moves, and per-position outcomes."""
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
                      "roster": {}, "candidates": {}, "drop_status": {}, "protected": {}, "coverage": {}},
        "replacement": {"contract_id": REPLACEMENT_CONTEXT_CONTRACT_ID, "rule": REPLACEMENT_RULE, "positions": {}, "players": {}},
        "depth_notes": [],
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
    drop_context = {"active": active, "protections": protections, "used_drops": set(), "added": [], "ros": ros_summary,
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
    """Same-position release supported by fresh, clearly separated rest-of-season evidence and the post-move lineup check, else the exact blocker.

    material reports whether any pairing cleared the materiality gate, so a close call is distinguishable from a safety block.
    """
    add, ros = intent["add"], context["ros"]
    position = add["position"]
    if ros["state"] != "AVAILABLE":
        return _no_drop("ROS_VALUE_UNAVAILABLE", f"A safe release cannot be verified because rest-of-season value is unavailable: {ros['reason']}")
    if add["ros_value"]["evidence_state"] != "RANKED":
        state = add["ros_value"]["evidence_state"].replace("_", " ").lower()
        return _no_drop("CANDIDATE_ROS_UNRANKED", f"{add['name']} has no fresh rest-of-season rank ({state}), so releasing a roster player for him cannot be verified.")
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
        return _no_drop("NO_SAME_POSITION_RELEASE", f"No {position} on your active roster can be released for {add['name']}, and players are never released across positions.")
    return _no_drop(combined[0][0], " ".join(dict.fromkeys(detail for _, detail in combined)), material)


def _with_add(intent, add, fallbacks):
    """The intent re-pointed at another listed option, with that option's own expert separation (and current-week urgency) recomputed."""
    updated = {**intent, "add": add, "fallbacks": list(fallbacks)[:3]}
    if intent["kind"] == "CURRENT_WEEK_UPGRADE" and not intent.get("forced_monitor"):
        separation = expert_separation(add["week_rank"], intent["over"]["week_rank"])
        updated.update(materiality=separation, urgency="MATERIAL" if separation["state"] == "UNANIMOUS" else "OPTIONAL")
    elif intent["kind"] == "DEPTH_UPGRADE":
        updated["materiality"] = expert_separation(add["ros_rank"], intent["over"]["ros_rank"])
    return updated


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
    if ros["state"] != "AVAILABLE":
        rest = {"state": ros["state"], "text": ros["reason"]}
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
    if kind == "MUST_FILL":
        combination, impact = "REQUIRED_SLOT_FILL", "Fills a required starter slot this week"
        if clear and drop:
            impact += f"; {add['name']} is also clearly ahead of {drop['player']}, who is released, for the rest of the season"
    elif kind == "DEPTH_UPGRADE":
        combination = "C_DEPTH"
        impact = ("Rest-of-season depth upgrade (bench); your current-week lineup is unchanged" if clear else
                  f"Rest-of-season bench add for an open roster spot, not a clear upgrade over {target['name']}; your current-week lineup is unchanged")
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


def _fallback_views(fallbacks, subject, ros_available):
    """Backups with their own ROS materiality against the same roster player; a verified drop is never inherited by a backup."""
    views = []
    for model in fallbacks:
        view = _player_view(model, include_ros=True)
        if subject is not None and ros_available:
            materiality = ros_materiality(model["ros_value"], subject["ros_value"], candidate_name=model["name"], roster_name=subject["name"])
            view["ros_materiality"] = {"state": materiality["state"], "label": materiality["label"], "against": subject["name"]}
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
                attempts.append((option, _safe_drop({**intent, "add": option}, context)))
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
    move = {"kind": intent["kind"], "kind_label": KIND_LABELS[intent["kind"]], "urgency": intent["urgency"], "position": intent["position"], "slot": intent.get("slot"),
            "add": _player_view(add, include_ros=True), "over": _player_view(intent.get("over"), include_ros=True), "slot_player": _player_view(intent.get("slot_player"), include_ros=True),
            "fallbacks": [], "drop": None, "drop_state": None, "drop_blocker": None, "reason": None, "monitor_detail": None, "passed_over": passed_over,
            "materiality": intent.get("materiality"), "materiality_text": None, "trigger": intent.get("trigger"), "ordering": intent.get("ordering"), "disclosures": []}
    if intent["kind"] == "MUST_FILL":
        move["why"] = f"Required: {intent['trigger_text']}."
        if intent.get("ordering") == "VERIFIED_EQUIVALENT_OPTIONS":
            move["disclosures"].append("No current consensus rank separates these options; the order is stable, not a quality ranking.")
        elif intent.get("unranked_count"):
            move["disclosures"].append(f"{intent['ranked_count']} ranked option(s) ordered by current consensus; {intent['unranked_count']} unranked option(s) follow and were not used to prove superiority.")
    elif intent["kind"] == "CURRENT_WEEK_UPGRADE":
        move["why"] = f"Current-week {intent['position']} consensus rank {add['week_rank']['ecr']:.1f} vs {intent['over']['week_rank']['ecr']:.1f} (lower is better)."
    else:
        move["why"] = f"Rest-of-season {intent['position']} consensus rank {add['ros_rank']['ecr']:.1f} vs {intent['over']['ros_rank']['ecr']:.1f} for your weakest bench {intent['position']} (lower is better)."
    if add and intent["kind"] != "DEPTH_UPGRADE":
        rank = add["week_rank"]
        move["evidence"] = {"source": rank.get("source") or CONSENSUS_SOURCE, "horizon": "this_week", "week": rank.get("week"), "source_date": rank.get("source_date"),
                            "freshness_state": rank.get("freshness_state") if _ranked(rank) else "UNAVAILABLE"}
    elif add:
        rank = add["ros_rank"]
        move["evidence"] = {"source": rank.get("source") or CONSENSUS_SOURCE, "horizon": "rest_of_season", "week": None, "source_date": rank.get("source_date"), "freshness_state": rank.get("freshness_state")}
    else:
        move["evidence"] = None
    materiality = intent.get("materiality") or {}
    over_name = (intent.get("over") or {}).get("name")
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
        move.update(decision="ADD_DROP", drop=outcome["drop"], drop_state="VERIFIED", state_label=MOVE_STATE_LABELS["ADD_DROP"],
                    drop_safety={"state": "SUPPORTED", "reason": outcome["drop"]["reason"]})
    else:
        code = outcome["code"]
        label = code if code in ("ROS_VALUE_UNAVAILABLE", *MATERIALITY_BLOCKERS) else "NO_SAFE_DROP"
        move.update(decision="MONITOR", reason=NO_SAFE_DROP_REASON, monitor_detail=outcome["detail"], drop_state="UNVERIFIED", drop_blocker=code,
                    state_label=MOVE_STATE_LABELS[label], drop_safety={"state": "NOT_SUPPORTED", "blocker": code, "reason": outcome["detail"]})
    (move["current_week"], move["rest_of_season"], move["ros_materiality"], move["replacement_context"],
     move["value_combination"], move["impact"]) = _horizon_views(intent, move, context, outcome)
    target = (outcome or {}).get("subject") or intent.get("over") or intent.get("replaced") or intent.get("slot_player")
    subject = {"ros_value": move["drop"]["ros_value"], "name": move["drop"]["player"]} if move["drop"] else ({"ros_value": target["ros_value"], "name": target["name"]} if target else None)
    move["fallbacks"] = _fallback_views(intent.get("fallbacks") or [], subject, ros["state"] == "AVAILABLE")
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


def _drop_status(model, move, context, candidates):
    """Why one roster player is or is not releasable: SAFE, PROTECTED, or UNVERIFIED, with the actual reason.

    A release is judged with its replacement, exactly as a recommended drop is: SAFE needs an available, addable same-position
    player, not already a recommended add, who is clearly ahead for the rest of the season and keeps every starting slot covered.
    """
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
        return {"state": "PROTECTED", "reason": f"No available {position} has a better fresh rest-of-season rank than his {position} ROS ECR {value['ros_ecr']:.1f}, "
                                                "so releasing him would give up rest-of-season value."}
    if not open_better:
        names = ", ".join(candidate["name"] for candidate in better)
        return {"state": "PROTECTED", "reason": f"The only available {position} with a better fresh rest-of-season rank ({names}) "
                                                f"{'is' if len(better) == 1 else 'are'} already a recommended add, so releasing him as well would give up rest-of-season value."}
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
        return {"state": "PROTECTED", "reason": f"Available {position} players rank ahead of him (best: {best['name']}, {position} ROS ECR {best['ros_value']['ros_ecr']:.1f} "
                                                f"vs his {value['ros_ecr']:.1f}), but none is clearly ahead: their expert ranges overlap his, so releasing him would not be a meaningful upgrade."}
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

    return {"roster": {model["id"]: model["ros_value"] for model in models}, "candidates": {model["id"]: model["ros_value"] for model in candidate_models},
            "drop_status": {model["id"]: _drop_status(model, verified.get(model["id"]), context, candidate_models) for model in models},
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
