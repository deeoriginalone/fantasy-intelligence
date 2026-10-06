from __future__ import annotations

from datetime import datetime, timezone
from math import ceil, isfinite

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from weekly_intelligence import enrich_players, current_week, upcoming_byes
from services.weekly_lineup_intelligence import build_lineup_intelligence, decision, optimize_lineup, sort_key
from services.authoritative_week import build_authoritative_week_contract
from services.jerrygm_projections import build_changed_slot_projections
from services.trade_intelligence import build_trade_intelligence
from services.opportunity_evidence import build_opportunity_view, build_waiver_player_comparison
from services.trade_target_center import build_trade_target_center
from services.decision_ranking import build_action, build_decision_ranking
from services.matchup_intelligence import build_matchup_intelligence
from services.preliminary_matchup_context import build_preliminary_matchup_context
from services.ux_evidence import build_waiver_catalog_name_index, derived_waiver_availability, evaluate_waiver_availability, resolve_waiver_candidate_identity, shared_league_facts, waiver_evidence_contract, waiver_ownership_freshness, waiver_roster_coverage, weekly_evidence_contract
from services.team_needs import build_team_needs_summary, league_settings_contract, team_needs_contract
from services.team_health import team_health_contract, apply_player_health_to_recommendations, health_freshness_from_report_date, normalize_health
from services.ux2_team_accuracy import build_team_accuracy_contract
from services.team_priority import build_team_priority_action
from services.team_hardening import build_bench_decisions, build_bench_plan, build_lineup_snapshot, build_roster_outlook, build_team_trust_summary, build_weekly_risks
from services.player_opportunity_reader import read_player_opportunity, read_player_what_changed
from services.snap_share_reader import read_snap_share
from services.opportunity_context import opportunity_strength, opportunity_trend, usage_stability
from services.player_opportunity_reader import read_player_production
from services.gsis_identity_crosswalk import attach_opportunity_player_ids
from services.gsis_identity_crosswalk import resolve_gsis_crosswalk
from services.dynastyprocess_identity_source import acquire_dynastyprocess_identity_source
from services.nflverse_player_metadata import acquire_nflverse_player_metadata
from services.sleeper_service import get_trending_adds, get_trending_drops, get_nfl_state
from services.espn_player_news import news_for_espn_player, read_espn_nfl_news
from services.dynastyprocess_rankings import read_rankings
from services.dynastyprocess_rankings import read_cached_rankings, refresh_rankings

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
STARTER_SLOTS = ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DEF")
def build_gm_waiver_watch_actions(waivers, ranking_confidence):
    if ranking_confidence == "UNVERIFIED":
        return []
    return [
        build_action(
            action_id=f"waiver-watch:{index}:{candidate['player']}",
            category="waiver",
            title=f"Review {candidate['player']}",
            action=f"Review {candidate['player']} at ${candidate['faab']} FAAB",
            reason=f"Priority score {candidate['priority_score']:.1f}; roster need {candidate['need']}.",
            urgency="HIGH" if candidate.get("need") else "MEDIUM",
            confidence={"label": "MEDIUM", "score": 70},
            risk_reduction=min(100, float(candidate.get("need") or 0) * 25),
            source="waiver_watch",
            metadata={"faab": candidate.get("faab")},
        )
        for index, candidate in enumerate(waivers[:3], 1)
    ]

SNAP_SHARE_DISPLAY_MAX_AGE_SECONDS = 86400


def _numeric_snap_share(row):
    value = (row or {}).get("snap_share")
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_team_opportunity_changes(connection, roster, *, season, week, nflverse_records=None, nflverse_lineage=None, sleeper_records=None):
    """Build informational What Changed evidence for explicitly linked players."""
    result = {"state": "UNAVAILABLE", "players": [], "blockers": [], "decision_effect": "INFORMATIONAL_ONLY"}
    if not isinstance(season, int) or isinstance(season, bool) or season <= 0:
        result["blockers"] = ["OPPORTUNITY_SEASON_INVALID"]
        return result
    if not isinstance(week, int) or isinstance(week, bool) or week <= 0:
        result["blockers"] = ["OPPORTUNITY_WEEK_INVALID"]
        return result
    mapped_roster = attach_opportunity_player_ids(
        roster or [],
        nflverse_records or [],
        nflverse_lineage=nflverse_lineage,
        sleeper_records=sleeper_records,
    ) if nflverse_records is not None else [dict(player) for player in (roster or [])]
    for player in mapped_roster:
        name = player.get("player") or "Unnamed player"
        opportunity_player_id = player.get("opportunity_player_id")
        if not isinstance(opportunity_player_id, str) or not opportunity_player_id.strip():
            result["players"].append({
                "player": name,
                "state": "UNAVAILABLE",
                "opportunity_identity_state": player.get("opportunity_identity_state", "UNRESOLVED"),
                "blockers": ["OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"],
                "decision_effect": "INFORMATIONAL_ONLY",
            })
            continue
        comparison = read_player_what_changed(
            connection,
            player_id=opportunity_player_id,
            season=season,
            week=week,
        )
        comparison["snap_share"] = comparison.get("snap_share_history") or read_snap_share(connection, player_id=opportunity_player_id, season=season, week_start=1, week_end=week)
        snap_rows = comparison["snap_share"].get("rows") or []
        if len(snap_rows) >= 2:
            current_snap, prior_snap = snap_rows[0], snap_rows[1]
            current_snap_share = _numeric_snap_share(current_snap)
            prior_snap_share = _numeric_snap_share(prior_snap)
            if current_snap_share is not None and prior_snap_share is not None:
                comparison["snap_share_change"] = {
                    "state": "AVAILABLE",
                    "current_week": current_snap.get("week"),
                    "prior_week": prior_snap.get("week"),
                    "current": current_snap_share,
                    "prior": prior_snap_share,
                    "direction": "UP" if current_snap_share > prior_snap_share else "DOWN" if current_snap_share < prior_snap_share else "UNCHANGED",
                }
            else:
                comparison["snap_share_change"] = {"state": "UNAVAILABLE", "reason": "Snap-share comparison unavailable because prior and current snap-share values are not both numeric."}
        else:
            comparison["snap_share_change"] = {"state": "UNAVAILABLE", "reason": "Snap-share comparison unavailable because prior and current published rows are not both present."}
        usage_result = read_player_opportunity(connection, player_id=opportunity_player_id, season=season, week_start=1, week_end=week)
        usage_rows = usage_result.get("rows") or []
        comparison["opportunity_strength"] = opportunity_strength(usage_row=(usage_rows[-1] if usage_rows else None), snap_row=(snap_rows[0] if snap_rows else None))
        comparison["usage_stability"] = usage_stability(current_usage=(usage_rows[-1] if usage_rows else None), prior_usage=(usage_rows[-2] if len(usage_rows) > 1 else None), current_snap=(snap_rows[0] if snap_rows else None), prior_snap=(snap_rows[1] if len(snap_rows) > 1 else None))
        comparison["opportunity_trend"] = opportunity_trend(strength=comparison["opportunity_strength"], stability=comparison["usage_stability"])
        result["players"].append({"player": name, "opportunity_player_id": opportunity_player_id, **comparison})
    if not result["players"]:
        result["blockers"] = ["OPPORTUNITY_ROSTER_EMPTY"]
    elif all(item["state"] == "AVAILABLE" for item in result["players"]):
        result["state"] = "AVAILABLE"
    elif any(item["state"] == "BLOCKED" for item in result["players"]):
        result["state"] = "BLOCKED"
        result["blockers"] = list(dict.fromkeys(
            blocker for item in result["players"] for blocker in item.get("blockers", [])
        ))
    else:
        result["state"] = "UNAVAILABLE"
        result["blockers"] = list(dict.fromkeys(
            blocker for item in result["players"] for blocker in item.get("blockers", [])
        ))
    return result


def waiver_projection_contribution(candidate):
    """Return optional projection evidence without treating warnings as authority."""
    candidate = dict(candidate or {})
    identity = candidate.get("identity_resolution") or {}
    available = (
        candidate.get("projection") is not None
        and bool(candidate.get("projection_retrieved_at"))
        and identity.get("resolution_state") in {None, "RESOLVED"}
    )
    evidence = candidate.get("projection_evidence") or {}
    return {
        "value": candidate.get("projection") if available else None,
        "state": "AVAILABLE" if available else "UNAVAILABLE",
        "warnings": list(evidence.get("blockers") or []),
    }


def wda_projection_or_none(value):
    """Decision-assistant-only: row_to_player collapses a missing projection to 0.0;
    treat 0 as unavailable here so the assistant never fabricates an upgrade signal."""
    return value or None


def waiver_trending_evidence(mode):
    """Fail-closed Sleeper trending evidence; only applicable to LIVE waiver candidates."""
    if mode != "LIVE":
        return {"state": "UNAVAILABLE", "blocker": "WAIVER_TRENDING_NOT_APPLICABLE", "add_ids": set(), "drop_ids": set()}
    try:
        adds = get_trending_adds(24, 300)
        drops = get_trending_drops(24, 300)
    except Exception:
        return {"state": "UNAVAILABLE", "blocker": "WAIVER_TRENDING_RETRIEVAL_FAILED", "add_ids": set(), "drop_ids": set()}
    if not isinstance(adds, list) or not isinstance(drops, list):
        return {"state": "UNAVAILABLE", "blocker": "WAIVER_TRENDING_DATA_INVALID", "add_ids": set(), "drop_ids": set()}
    add_ids = {str(item.get("player_id")) for item in adds if isinstance(item, dict) and item.get("player_id")}
    drop_ids = {str(item.get("player_id")) for item in drops if isinstance(item, dict) and item.get("player_id")}
    return {"state": "AVAILABLE", "blocker": None, "add_ids": add_ids, "drop_ids": drop_ids}


def wda_trending_state(player_id, trending_evidence):
    """Return 'UP'/'DOWN' only when Sleeper trending evidence directly supports it; else None."""
    trending_evidence = trending_evidence or {}
    if trending_evidence.get("state") != "AVAILABLE" or not player_id:
        return None
    pid = str(player_id)
    if pid in trending_evidence.get("add_ids", set()):
        return "UP"
    if pid in trending_evidence.get("drop_ids", set()):
        return "DOWN"
    return None


def waiver_recent_production(connection, player, season, limit=3, reader_result=None):
    """Expose only published production rows for waiver research; never calculate on read."""
    player = dict(player or {})
    player_id = player.get("opportunity_player_id") or player.get("sleeper_gsis_id") or player.get("player_id") or player.get("source_player_id")
    position = str(player.get("position") or "").upper().replace("DST", "DEF")
    if not player_id or not season:
        return {"state": "UNAVAILABLE", "rows": [], "blockers": ["PLAYER_WEEK_PRODUCTION_IDENTITY_UNAVAILABLE"]}
    result = read_player_production(connection, player_id=str(player_id), season=season, position=position, reader_result=reader_result)
    result["rows"] = list(result.get("rows") or [])[:limit] if result.get("state") == "AVAILABLE" else []
    return result


def waiver_snap_share(connection, player, season, limit=3):
    player = dict(player or {})
    player_id = player.get("opportunity_player_id") or player.get("sleeper_gsis_id") or player.get("player_id") or player.get("source_player_id")
    if not player_id or not season:
        return {"state": "UNAVAILABLE", "rows": [], "blockers": ["SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE"], "authority_state": "INFORMATIONAL_ONLY", "decision_effect": "NONE", "display_max_age_seconds": SNAP_SHARE_DISPLAY_MAX_AGE_SECONDS}
    result = read_snap_share(connection, player_id=str(player_id), season=season, limit=limit)
    result["rows"] = list(result.get("rows") or [])[:limit] if result.get("state") in {"AVAILABLE", "STALE"} else []
    result["authority_state"] = "INFORMATIONAL_ONLY"
    result["decision_effect"] = "NONE"
    result["display_max_age_seconds"] = SNAP_SHARE_DISPLAY_MAX_AGE_SECONDS
    return result


def waiver_opportunity_metrics(connection, player, season):
    player = dict(player or {})
    player_id = player.get("opportunity_player_id") or player.get("sleeper_gsis_id") or player.get("player_id") or player.get("source_player_id")
    if not player_id or not season:
        return {"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_PLAYER_IDENTITY_UNAVAILABLE"]}
    result = read_player_opportunity(connection, player_id=str(player_id), season=season)
    result["rows"] = list(result.get("rows") or [])[-3:] if result.get("state") == "AVAILABLE" else []
    return result


def _waiver_health_state(value):
    normalized = " ".join(str(value or "").strip().upper().replace("-", " ").split())
    if normalized in {"HEALTHY / NOT LISTED", "NOT LISTED"}:
        return None
    if normalized in {"INJURED RESERVE", "INJURED RESERVE DESIGNATED FOR RETURN"}:
        normalized = "IR"
    return normalize_health(normalized)


def _waiver_candidate_health(catalog_record, retrieved_at, identity_resolved):
    unavailable = {
        "injury_status": None,
        "injury_source": None,
        "health_status_available": False,
        "health_freshness_state": "UNAVAILABLE",
        "health_age_seconds": None,
        "health_blocker": "WAIVER_HEALTH_STATUS_UNAVAILABLE",
    }
    if not identity_resolved:
        return {**unavailable, "health_blocker": "WAIVER_HEALTH_IDENTITY_UNAVAILABLE"}
    if not isinstance(catalog_record, dict):
        return unavailable
    supplied = [
        value for value in (catalog_record.get("injury_status"), catalog_record.get("status"))
        if value not in (None, "", "Unknown", "UNKNOWN")
    ]
    if not supplied:
        return unavailable
    states = [_waiver_health_state(value) for value in supplied]
    if any(state is None for state in states):
        return {**unavailable, "health_blocker": "WAIVER_HEALTH_STATUS_UNSUPPORTED"}
    if len(set(states)) != 1:
        return {**unavailable, "health_blocker": "WAIVER_HEALTH_STATUS_CONTRADICTORY"}
    try:
        freshness = health_freshness_from_report_date(retrieved_at)
    except (TypeError, ValueError, OverflowError):
        return {**unavailable, "health_blocker": "WAIVER_HEALTH_RETRIEVAL_TIME_UNAVAILABLE"}
    raw_status = next(
        (value for value in (catalog_record.get("injury_status"), catalog_record.get("status")) if _waiver_health_state(value)),
        None,
    )
    return {
        "injury_status": raw_status,
        "injury_source": "Sleeper API",
        "health_status_available": True,
        "health_fetched_at": retrieved_at,
        "injury_updated_at": retrieved_at,
        "health_freshness_state": freshness["freshness_state"],
        "health_age_seconds": freshness["age"],
        "health_blocker": None if freshness["freshness_state"] == "FRESH" else "WAIVER_HEALTH_NOT_FRESH",
    }


def waiver_candidate_recommendation_state(candidate, ranking_confidence):
    """Assign a presentation disposition without turning preliminary evidence into authority."""
    candidate = dict(candidate or {})
    health_state = _waiver_health_state(candidate.get("injury_status")) if candidate.get("health_status_available") is True else None
    blockers = []
    if candidate.get("health_status_available") is not True or candidate.get("injury_source") != "Sleeper API" or not candidate.get("health_fetched_at"):
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append(candidate.get("health_blocker") or "WAIVER_HEALTH_EVIDENCE_UNAVAILABLE")
    elif candidate.get("health_freshness_state") != "FRESH":
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append(candidate.get("health_blocker") or "WAIVER_HEALTH_NOT_FRESH")
    elif health_state is None:
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append("WAIVER_HEALTH_STATUS_UNSUPPORTED")
    elif health_state != "HEALTHY":
        disposition = "HEALTH_BLOCKED"
        state = "NON_ACTIONABLE_HEALTH"
        blockers.append("WAIVER_HEALTH_NOT_ACTIONABLE")
    elif candidate.get("ownership_state") != "VERIFIED" or candidate.get("eligibility_state") != "VERIFIED":
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append("WAIVER_OWNERSHIP_OR_ELIGIBILITY_UNVERIFIED")
    elif not isinstance(candidate.get("player_id"), str) or not candidate.get("player_id") or (candidate.get("identity_resolution") or {}).get("resolution_state") != "RESOLVED":
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append("WAIVER_CANDIDATE_IDENTITY_UNRESOLVED")
    elif not any(
        isinstance(candidate.get(field), dict)
        and candidate[field].get("state") == "AVAILABLE"
        and candidate[field].get("rows")
        for field in ("recent_production", "opportunity_metrics", "snap_share")
    ) and not (candidate.get("evidence_context") or {}).get("roster_fit", {}).get("state") == "AVAILABLE" and not (
        wda_projection_or_none(candidate.get("projection")) is not None
        and candidate.get("projection_retrieved_at")
    ):
        disposition = "HEALTH_BLOCKED"
        state = "HEALTH_UNVERIFIED"
        blockers.append("WAIVER_CANDIDATE_EVIDENCE_UNAVAILABLE")
    else:
        disposition = "PRELIMINARY_SUGGESTION"
        state = "PRELIMINARY_SUGGESTION"
    if disposition == "PRELIMINARY_SUGGESTION" and ranking_confidence != "VERIFIED":
        blockers.append("WAIVER_RANKING_SOURCE_UNVERIFIED")
    if (
        disposition == "HEALTH_BLOCKED"
        and candidate.get("health_blocker") == "WAIVER_HEALTH_STATUS_UNAVAILABLE"
        and candidate.get("ownership_state") == "VERIFIED"
        and candidate.get("eligibility_state") == "VERIFIED"
        and candidate.get("player_id")
        and (candidate.get("identity_resolution") or {}).get("resolution_state") == "RESOLVED"
    ):
        disposition = "MONITOR"
    return {
        "candidate_disposition": disposition,
        "recommendation_state": state,
        "recommendation_blockers": list(dict.fromkeys(blockers)),
        "normalized_health_state": health_state or "HEALTH_UNVERIFIED",
    }


def attach_waiver_opportunity_identity(candidates, catalog, nflverse_records, nflverse_lineage, identity_source=None):
    """Add only provider-resolved GSIS IDs to waiver candidates; never name-match."""
    candidates = [dict(candidate) for candidate in candidates or []]
    if not candidates or not nflverse_records or not nflverse_lineage:
        return candidates
    source_mappings = {
        str(item.get("source_player_id")): item
        for item in (identity_source or {}).get("mappings") or []
        if item.get("source_player_id")
    }
    sleeper_records = []
    source_mapping_by_player = {}
    for candidate in candidates:
        player_id = str(candidate.get("player_id") or "")
        raw = dict((catalog or {}).get(player_id) or {})
        source_mapping = source_mappings.get(player_id)
        if not raw.get("gsis_id") and not raw.get("espn_id") and source_mapping:
            source_mapping_by_player[player_id] = source_mapping
            if source_mapping.get("state") == "RESOLVED" and source_mapping.get("gsis_id"):
                raw["gsis_id"] = source_mapping["gsis_id"]
        sleeper_records.append({
            "source_player_id": player_id,
            "gsis_id": raw.get("gsis_id"),
            "espn_id": raw.get("espn_id"),
        })
    crosswalk = resolve_gsis_crosswalk(
        sleeper_records,
        nflverse_records,
        sleeper_lineage={"source": "sleeper.players.nfl", "source_authority": "sleeper", "artifact_id": "players.nfl", "version": "live-catalog", "retrieved_at": "waiver-route", "coverage_state": "COMPLETE"},
        nflverse_lineage=nflverse_lineage,
        requested_source_player_ids=[row["source_player_id"] for row in sleeper_records if row["source_player_id"]],
    )
    mappings = {str(item.get("source_player_id")): item for item in crosswalk.get("mappings") or []}
    for candidate in candidates:
        mapping = mappings.get(str(candidate.get("player_id"))) or {}
        if mapping.get("state") == "RESOLVED":
            candidate["opportunity_player_id"] = mapping.get("opportunity_player_id")
            candidate["opportunity_identity_state"] = "RESOLVED"
            candidate["opportunity_identity_method"] = mapping.get("resolution_authority")
            if str(candidate.get("player_id")) in source_mapping_by_player:
                candidate["opportunity_identity_method"] = "dynastyprocess_gsis_id"
                candidate["opportunity_identity_lineage"] = {
                    "identity_source": dict((identity_source or {}).get("lineage") or {}),
                    "nflverse": dict(nflverse_lineage),
                }
        elif str(candidate.get("player_id")) in source_mapping_by_player:
            source_mapping = source_mapping_by_player[str(candidate.get("player_id"))]
            if source_mapping.get("state") in {"AMBIGUOUS", "CONTRADICTORY"}:
                candidate.pop("opportunity_player_id", None)
                candidate["opportunity_identity_state"] = source_mapping["state"]
                candidate["opportunity_identity_blockers"] = [source_mapping.get("blocker") or "DYNASTYPROCESS_IDENTITY_UNAVAILABLE"]
            elif source_mapping.get("state") == "UNRESOLVED":
                candidate["opportunity_identity_state"] = "UNRESOLVED"
                candidate["opportunity_identity_blockers"] = [source_mapping.get("blocker") or "DYNASTYPROCESS_GSIS_ID_UNAVAILABLE"]
        else:
            candidate.setdefault("opportunity_identity_state", mapping.get("state", "UNRESOLVED"))
            candidate.setdefault("opportunity_identity_blockers", mapping.get("blockers", ["GSIS_IDENTITY_MISSING"]))
    return candidates


def resolve_espn_news_identity(player, nflverse_records, nflverse_lineage=None):
    """Resolve ESPN news identity from direct Sleeper ID or unique GSIS crosswalk only."""
    player = dict(player or {})
    direct = str(player.get("sleeper_espn_id") or "").strip()
    if direct:
        return {"state": "RESOLVED", "espn_id": direct, "method": "SLEEPER_CATALOG_ESPN_ID", "blockers": []}
    lineage = dict(nflverse_lineage or {})
    if (
        player.get("opportunity_identity_state") != "RESOLVED"
        or lineage.get("source_authority") != "automated:nflverse"
        or not lineage.get("retrieved_at")
        or lineage.get("coverage_state") != "COMPLETE"
    ):
        return {"state": "UNAVAILABLE", "espn_id": None, "method": None, "blockers": ["ESPN_NEWS_IDENTITY_CROSSWALK_UNVERIFIED"]}
    gsis_id = str(player.get("opportunity_player_id") or "").strip()
    if not gsis_id:
        return {"state": "UNAVAILABLE", "espn_id": None, "method": None, "blockers": ["ESPN_NEWS_GSIS_ID_UNAVAILABLE"]}
    matches = [
        str(row.get("espn_id") or "").strip()
        for row in nflverse_records or []
        if str(row.get("gsis_id") or "").strip() == gsis_id and str(row.get("espn_id") or "").strip()
    ]
    if len(matches) != 1:
        blocker = "ESPN_NEWS_IDENTITY_AMBIGUOUS" if matches else "ESPN_NEWS_IDENTITY_CROSSWALK_MISSING"
        return {"state": "UNAVAILABLE", "espn_id": None, "method": None, "blockers": [blocker]}
    return {"state": "RESOLVED", "espn_id": matches[0], "method": "NFLVERSE_UNIQUE_GSIS_ESPN_CROSSWALK", "blockers": []}


COMPARISON_BLOCKED_IDENTITY_STATES = {"AMBIGUOUS", "CONTRADICTORY", "BLOCKED"}


def waiver_player_comparison(candidate):
    """Informational position-aware comparison from already-read opportunity evidence; never alters order, FAAB, or confidence."""
    candidate = dict(candidate or {})
    identity_state = candidate.get("opportunity_identity_state") or "UNRESOLVED"
    identity_blockers = list(candidate.get("opportunity_identity_blockers") or [])
    if identity_state == "RESOLVED" and candidate.get("opportunity_player_id"):
        reader = candidate.get("opportunity_metrics") or {"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_EVIDENCE_UNAVAILABLE"]}
    elif identity_state in COMPARISON_BLOCKED_IDENTITY_STATES:
        reader = {"state": "BLOCKED", "rows": [], "blockers": identity_blockers or ["PLAYER_COMPARISON_IDENTITY_AMBIGUOUS"]}
    else:
        reader = {"state": "UNAVAILABLE", "rows": [], "blockers": identity_blockers or ["PLAYER_COMPARISON_IDENTITY_UNRESOLVED"]}
    comparison = build_waiver_player_comparison(reader, position=candidate.get("position"))
    comparison["comparison_identity"] = {
        "state": identity_state,
        "opportunity_player_id": candidate.get("opportunity_player_id") if identity_state == "RESOLVED" else None,
        "method": candidate.get("opportunity_identity_method"),
    }
    return comparison


def waiver_roster_comparison(candidate, rostered_player, *, allow_cross_position=False):
    result = {"state": "UNAVAILABLE", "decision_effect": "INFORMATIONAL_ONLY", "weeks": [], "candidate_average": None, "roster_average": None, "difference": None, "reason": "No matching supported Full-PPR weeks are available for both players."}
    if candidate.get("position") != rostered_player.get("position") and not allow_cross_position:
        return {**result, "reason": "These players do not share a position."}
    observations = []
    for player in (candidate, rostered_player):
        production = player.get("recent_production") or {}
        if production.get("state") != "AVAILABLE":
            return result
        by_week = {}
        for row in production.get("rows") or []:
            season, week = row.get("season"), row.get("week")
            value = row.get("fantasy_points_ppr")
            if not isinstance(season, int) or not isinstance(week, int) or row.get("scoring_format") != "FULL_PPR" or row.get("freshness_state") not in {"FRESH", "AGING"}:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                continue
            key = (season, week)
            if key in by_week:
                return {**result, "reason": "Duplicate production observations prevent a reliable comparison."}
            by_week[key] = {
                "value": value,
                "freshness_state": row.get("freshness_state"),
                "source": row.get("source"),
                "source_authority": row.get("source_authority"),
                "retrieved_at": row.get("retrieved_at"),
                "calculation_version": row.get("calculation_version"),
            }
        observations.append(by_week)
    weeks = sorted(set(observations[0]) & set(observations[1]))[-3:]
    if not weeks:
        return result
    candidate_average = sum(observations[0][week]["value"] for week in weeks) / len(weeks)
    roster_average = sum(observations[1][week]["value"] for week in weeks) / len(weeks)
    freshness_states = sorted({observations[player_index][week]["freshness_state"] for player_index in (0, 1) for week in weeks})
    sources = sorted({observations[player_index][week]["source"] for player_index in (0, 1) for week in weeks if observations[player_index][week].get("source")})
    retrieval_times = sorted({observations[player_index][week]["retrieved_at"] for player_index in (0, 1) for week in weeks if observations[player_index][week].get("retrieved_at")})
    return {
        **result,
        "state": "PRELIMINARY",
        "weeks": [{"season": season, "week": week} for season, week in weeks],
        "candidate_average": round(candidate_average, 2),
        "roster_average": round(roster_average, 2),
        "difference": round(candidate_average - roster_average, 2),
        "latest_difference": round(observations[0][weeks[-1]]["value"] - observations[1][weeks[-1]]["value"], 2),
        "candidate_wins": sum(observations[0][week]["value"] > observations[1][week]["value"] for week in weeks),
        "freshness_states": freshness_states,
        "source_authorities": sorted({observations[player_index][week]["source_authority"] for player_index in (0, 1) for week in weeks if observations[player_index][week].get("source_authority")}),
        "sources": sources,
        "retrieved_at": retrieval_times,
        "calculation_versions": sorted({observations[player_index][week]["calculation_version"] for player_index in (0, 1) for week in weeks if observations[player_index][week].get("calculation_version")}),
        "reason": "Observed Full-PPR production over matching weeks; not a forecast or an authoritative ADD/DROP conclusion.",
    }


def waiver_faab_balance(league, users, rosters):
    result = {"state": "UNAVAILABLE", "source": "Sleeper API", "remaining": None, "budget": None, "spent": None, "reason": "Owner FAAB settings are missing or ambiguous."}
    if not isinstance(league, dict) or not isinstance(users, list) or not isinstance(rosters, list):
        return result
    settings = league.get("settings") or {}
    if settings.get("waiver_type") != 2:
        return {**result, "state": "NOT_APPLICABLE", "reason": "The league is not verified as FAAB-based."}
    owners = [user for user in users if isinstance(user, dict) and user.get("is_owner") is True and user.get("user_id")]
    if len(owners) != 1:
        return result
    matches = [roster for roster in rosters if isinstance(roster, dict) and str(roster.get("owner_id")) == str(owners[0]["user_id"])]
    if len(matches) != 1:
        return result
    budget = settings.get("waiver_budget")
    spent = (matches[0].get("settings") or {}).get("waiver_budget_used")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in (budget, spent)) or spent > budget:
        return {**result, "reason": "Sleeper budget or spending is missing or inconsistent."}
    return {**result, "state": "AVAILABLE", "budget": budget, "spent": spent, "remaining": budget - spent, "roster_id": matches[0].get("roster_id"), "retrieved_at": datetime.now(timezone.utc).isoformat(), "reason": "Current Sleeper league budget minus this owner's roster spending."}


def waiver_provisional_bid(guidance, balance, is_starter):
    result = {"state": "UNAVAILABLE", "low": None, "high": None, "reason": "Neither horizon supports reviewing an add; no bid is suggested."}
    actions = [((guidance.get(horizon) or {}).get("action")) for horizon in ("this_week", "rest_of_season")]
    if guidance.get("authority") != "PROVISIONAL" or "REVIEW_ADD" not in actions:
        return result
    if balance.get("state") != "AVAILABLE" or not isinstance(balance.get("remaining"), int) or isinstance(balance.get("remaining"), bool):
        return {**result, "reason": "A live owner FAAB balance is not verified; no budget is assumed."}
    remaining = balance["remaining"]
    if remaining <= 0:
        return {**result, "reason": "No FAAB balance remains; paid bid guidance is unavailable."}
    if is_starter is None:
        return {**result, "reason": "Starter or bench role is unverified; no spending category is assigned."}
    low_pct, high_pct = (5, 10) if is_starter is True and actions.count("REVIEW_ADD") == 2 else (3, 5) if is_starter is True else (1, 3)
    return {"state": "PROVISIONAL", "low": min(remaining, ceil(remaining * low_pct / 100)), "high": min(remaining, ceil(remaining * high_pct / 100)), "percentage_low": low_pct, "percentage_high": high_pct, "remaining": remaining, "reason": f"Conservative {'starter-replacement' if is_starter else 'bench-depth'} spending band: {low_pct}-{high_pct}% of remaining FAAB, rounded up to whole units. Not a projected winning bid."}


def waiver_move_guidance(candidate, rostered_player):
    comparison = waiver_roster_comparison(candidate, rostered_player)
    evidence = candidate.get("evidence_context") or {}
    unavailable = {"action": "MONITOR", "reason": comparison["reason"]}
    guidance = {
        "schema_version": "waiver-move-guidance.v1",
        "authority": "PROVISIONAL",
        "this_week": dict(unavailable),
        "rest_of_season": {"action": "MONITOR", "reason": "Expected role and duration are unavailable; historical production is not a rest-of-season forecast."},
        "comparison": comparison,
        "drop_review": "No drop suggestion is supported.",
        "faab": None,
        "faab_reason": "Exact bids need a verified remaining budget and a supported bid-value model.",
        "limitations": ["Recent production is not a forecast.", "Matchup, future role, opportunity duration, and playoff outlook are not modeled."],
        "lineup_scope": "Starter replacement review" if rostered_player.get("is_starter") is True else "Bench-depth review; starter impact is not established" if rostered_player.get("is_starter") is False else "Starter or bench role is unverified",
    }
    if (
        candidate.get("recommendation_state") not in {"PRELIMINARY_SUGGESTION", "ACTIONABLE"}
        or not candidate.get("player_id") or not rostered_player.get("player_id")
        or candidate.get("player_id") == rostered_player.get("player_id")
        or candidate.get("position") != rostered_player.get("position")
        or evidence.get("ownership_state") != "VERIFIED"
        or evidence.get("eligibility_state") != "VERIFIED"
        or evidence.get("health_state") != "HEALTHY"
        or evidence.get("health_freshness_state") != "FRESH"
        or evidence.get("health_source") != "Sleeper API"
    ):
        blocked = {"action": "MONITOR", "reason": "Current availability, healthy status, identity, or position is not verified for this comparison."}
        guidance.update(this_week=dict(blocked), rest_of_season=dict(blocked))
        return guidance
    if rostered_player.get("is_starter") is True and rostered_player.get("health_state") in {"OUT", "IR"} and rostered_player.get("health_freshness_state") == "FRESH":
        guidance["this_week"] = {"action": "REVIEW_ADD", "reason": f"{rostered_player.get('player')} is a current starter marked {rostered_player['health_state']}; review this healthy same-position replacement before lineup lock."}
    if comparison["state"] != "PRELIMINARY":
        return guidance
    sample = len(comparison["weeks"])
    latest_edge = comparison["latest_difference"] > 0
    wins = comparison["candidate_wins"]
    positive_edge = comparison["difference"] > 0
    if guidance["this_week"]["action"] != "REVIEW_ADD":
        if sample < 2:
            guidance["this_week"] = {"action": "MONITOR", "reason": "Only one matching week is available; this-week replacement advice needs at least two."}
        elif positive_edge and latest_edge:
            guidance["this_week"] = {"action": "REVIEW_ADD", "reason": f"Higher average production across {sample} matching weeks and a latest-week edge support reviewing this replacement. Confirm this week's matchup and role first."}
        elif not positive_edge:
            guidance["this_week"] = {"action": "KEEP", "reason": "Recent matched production does not support replacing the selected player this week."}
        else:
            guidance["this_week"] = {"action": "MONITOR", "reason": "The average favors the candidate, but the latest matched week does not; wait for a clearer short-term signal."}
    guidance["rest_of_season"] = {"action": "MONITOR", "reason": "Expected role and duration are unavailable; historical production is not a rest-of-season forecast."}
    if rostered_player.get("is_starter") is not True:
        guidance["this_week"] = {"action": "MONITOR", "reason": "A bench-depth comparison alone does not establish a starting-lineup upgrade this week."}
    if guidance["this_week"]["action"] == "REVIEW_ADD":
        guidance["drop_review"] = "No drop is supported without complete roster coverage and an authoritative player-value comparison."
    return guidance


def waiver_acquisition_evaluation(candidate, team_needs, league_settings, guidance=None, balance=None):
    """Evaluate roster-specific fit without treating ordinal player ranks as acquisition value."""
    candidate = dict(candidate or {})
    position = str(candidate.get("position") or "").upper().replace("DST", "DEF")
    evidence = candidate.get("evidence_context") or {}
    settings = dict(league_settings or {})
    needs = dict(team_needs or {})
    guidance = dict(guidance or {})
    balance = dict(balance or {})
    available = (
        candidate.get("recommendation_state") == "PRELIMINARY_SUGGESTION"
        and candidate.get("candidate_disposition") == "PRELIMINARY_SUGGESTION"
        and candidate.get("player_id")
        and evidence.get("ownership_state") == "VERIFIED"
        and evidence.get("eligibility_state") == "VERIFIED"
        and evidence.get("health_state") == "HEALTHY"
        and evidence.get("health_freshness_state") == "FRESH"
        and evidence.get("health_source") == "Sleeper API"
    )
    direct_need = dict(needs.get(position) or {})
    flex_need = dict(needs.get("FLEX") or {})
    flex_eligible = position in (settings.get("flex_eligible_positions") or [])
    need = direct_need if direct_need.get("state") == "AVAILABLE" else {}
    if flex_eligible and flex_need.get("state") == "AVAILABLE" and flex_need.get("starter_shortage", 0) > (need.get("starter_shortage") or 0):
        need = flex_need
    has_starter_gap = need.get("state") == "AVAILABLE" and (need.get("starter_shortage") or 0) > 0
    has_depth_gap = need.get("state") == "AVAILABLE" and (need.get("depth_shortage") or 0) > 0
    comparison = guidance.get("comparison") or {}
    comparison_weeks = comparison.get("weeks") or []
    meaningful_comparison = (
        comparison.get("state") == "PRELIMINARY"
        and isinstance(comparison.get("difference"), (int, float))
        and comparison.get("difference") > 0
        and len(comparison_weeks) >= 2
        and isinstance(comparison.get("latest_difference"), (int, float))
        and comparison.get("latest_difference") > 0
        and (comparison.get("candidate_wins") or 0) > len(comparison_weeks) / 2
    )
    what_changed = ((candidate.get("player_comparison") or {}).get("what_changed") or {})
    relevant_direction_fields = {
        "RB": {"carries", "carry_share", "targets", "target_share", "touch_share", "rushing_yards", "receptions"},
        "WR": {"targets", "target_share", "route_participation", "receptions", "receiving_yards", "touch_share"},
        "TE": {"targets", "target_share", "route_participation", "receptions", "receiving_yards", "touch_share"},
        "QB": {"passing_yards", "passing_tds", "targets", "rushing_yards", "carries"},
    }.get(position, set())
    current_opportunity_rows = (candidate.get("opportunity_metrics") or {}).get("rows") or []
    directional_signal = (
        what_changed.get("state") == "AVAILABLE"
        and any(row.get("freshness_state") in {"FRESH", "AGING"} for row in current_opportunity_rows)
        and any(
            str(change.get("direction") or "").upper() in {"UP", "INCREASED", "INCREASING"}
            and str(change.get("field") or "").lower() in relevant_direction_fields
            for change in what_changed.get("changes") or []
        )
    )
    evidence_relevance = "MEANINGFUL_COMPARISON" if meaningful_comparison else "DIRECTIONAL_SIGNAL" if directional_signal else "SCREENING_ONLY"
    blockers = []
    if not available:
        blockers.extend(candidate.get("recommendation_blockers") or ["WAIVER_CANDIDATE_NOT_VERIFIED_AVAILABLE"])
    if need.get("state") != "AVAILABLE":
        blockers.extend(need.get("blockers") or ["TEAM_NEEDS_UNAVAILABLE"])
    if not settings or settings.get("state") != "AVAILABLE":
        blockers.append(settings.get("blocker") or "LEAGUE_ROSTER_SETTINGS_UNAVAILABLE")
    if not available:
        action = "NO_RECOMMENDATION"
        horizon = "UNAVAILABLE"
        would_start = "UNAVAILABLE"
        impact = "Candidate availability or identity is not verified."
    elif evidence_relevance == "SCREENING_ONLY":
        action = "NO_RECOMMENDATION"
        horizon = "UNAVAILABLE"
        would_start = "UNCERTAIN" if need.get("state") == "AVAILABLE" else "UNAVAILABLE"
        impact = "Team need, health, eligibility, projection, or snap-share alone is screening evidence; no candidate-specific upgrade signal is available."
    elif has_starter_gap and settings.get("full_ppr") is True:
        action = "CONSIDER"
        horizon = "IMMEDIATE"
        would_start = "YES"
        impact = f"Could fill a supported {need.get('position')} starter-slot shortage; no points improvement is projected."
    elif has_starter_gap:
        action = "CONSIDER"
        horizon = "UNAVAILABLE"
        would_start = "UNCERTAIN"
        impact = f"A {need.get('position')} starter-slot shortage is supported, but Full-PPR settings are unavailable to authorize this acquisition horizon."
    elif has_depth_gap:
        action = "CONSIDER"
        horizon = "UNAVAILABLE"
        would_start = "UNCERTAIN"
        impact = "Addresses a supported depth need; starting-lineup impact is not established."
    else:
        action = "MONITOR"
        horizon = "UNAVAILABLE"
        would_start = "UNCERTAIN" if need.get("state") == "AVAILABLE" else "UNAVAILABLE"
        impact = "No supported open starting slot or depth shortage is established for this position."
    if has_starter_gap and settings.get("full_ppr") is not True:
        blockers.append("FULL_PPR_SETTINGS_UNAVAILABLE")
    if horizon == "IMMEDIATE" and need.get("position") == "FLEX":
        faab_category = "FLEX_CHALLENGER"
    elif horizon == "IMMEDIATE" and (guidance.get("this_week") or {}).get("action") == "REVIEW_ADD":
        faab_category = "SHORT_TERM_REPLACEMENT"
    elif horizon == "IMMEDIATE":
        faab_category = "IMMEDIATE_STARTER"
    elif has_depth_gap:
        faab_category = "DEPTH_ADDITION"
    elif action == "STASH":
        faab_category = "SPECULATIVE_STASH"
    else:
        faab_category = "UNAVAILABLE"
    provisional_bid = guidance.get("provisional_bid") or {}
    if action != "ADD":
        faab = {"state": "NO_BID", "category": "NONE", "low": 0, "high": 0, "remaining": balance.get("remaining") if balance.get("state") == "AVAILABLE" else None, "rationale": f"No bid is suggested for {action}."}
    elif provisional_bid.get("state") == "PROVISIONAL" and balance.get("state") == "AVAILABLE":
        faab = {
            "state": "PROVISIONAL",
            "category": faab_category,
            "low": provisional_bid.get("low"),
            "high": provisional_bid.get("high"),
            "remaining": balance.get("remaining"),
            "rationale": ("Acquisition category is unavailable; " if faab_category == "UNAVAILABLE" else "") + (provisional_bid.get("reason") or "Existing provisional heuristic."),
        }
    else:
        faab = {"state": "UNAVAILABLE", "category": faab_category, "low": None, "high": None, "remaining": balance.get("remaining") if balance.get("state") == "AVAILABLE" else None,
                "rationale": provisional_bid.get("reason") or "No supported valuation and live-budget combination is available."}
    reasons = []
    if need.get("state") == "AVAILABLE" and evidence_relevance != "SCREENING_ONLY":
        reasons.extend(need.get("drivers") or [])
    if comparison.get("state") == "PRELIMINARY":
        reasons.append(comparison.get("reason") or "Observed matching Full-PPR production is available; this is not a forecast.")
    if evidence.get("opportunity", {}).get("state") == "AVAILABLE":
        reasons.append("Current opportunity evidence is available for context only.")
    risks = ["Expected role and acquisition duration are unavailable.", "Historical production and ordinal consensus ranks do not forecast lineup gain."]
    if not comparison or comparison.get("state") != "PRELIMINARY":
        risks.append("No supported candidate-to-roster production comparison is available.")
    return {
        "schema_version": "waiver-acquisition-evaluation.v1",
        "candidate_id": candidate.get("player_id"),
        "candidate": candidate.get("player"),
        "position": position or None,
        "availability": "VERIFIED_AVAILABLE" if available else "BLOCKED",
        "roster_need": need.get("position") or position or None,
        "roster_fit": impact,
        "horizon": horizon,
        "horizon_blocker": "EXPECTED_ROLE_AND_DURATION_UNAVAILABLE" if horizon != "IMMEDIATE" else None,
        "action": action,
        "evidence_relevance": evidence_relevance,
        "would_start": would_start,
        "affected_slot": need.get("position") if horizon == "IMMEDIATE" else None,
        "suggested_drop": {"state": "UNAVAILABLE", "player": None, "reason": "Complete roster coverage and an authoritative drop-value comparison are unavailable."},
        "reasons": reasons,
        "risks": risks,
        "evidence_level": "PRELIMINARY" if available and need.get("state") == "AVAILABLE" else "INSUFFICIENT",
        "confidence_rationale": "Preliminary roster-fit evidence only; no projected gain, role duration, or authoritative transaction model is available." if available else "Candidate availability is not sufficiently verified for a roster-specific recommendation.",
        "faab": faab,
        "blockers": list(dict.fromkeys(blockers)),
        "freshness": {"health": evidence.get("health_freshness_state", "UNAVAILABLE"), "opportunity": (candidate.get("opportunity_metrics") or {}).get("state", "UNAVAILABLE")},
        "limitations": list(guidance.get("limitations") or []) + ["Expected role and duration are unavailable."],
        "sort_group": 0 if horizon == "IMMEDIATE" else 1 if action == "CONSIDER" else 2,
    }


def waiver_selected_player_comparison(selected_player, candidate, team_needs, league_settings, faab_balance=None, roster_coverage_complete=False, roster=None, season=None, focus="all"):
    """Build a preliminary, selected-player-specific add/hold/monitor result."""
    selected_player = dict(selected_player or {})
    candidate = dict(candidate or {})
    selected_id = str(selected_player.get("source_player_id") or selected_player.get("player_id") or "")
    candidate_id = str(candidate.get("player_id") or "")
    selected_position = str(selected_player.get("position") or "").upper().replace("DST", "DEF")
    candidate_position = str(candidate.get("position") or "").upper().replace("DST", "DEF")
    evidence = candidate.get("evidence_context") or {}
    settings = dict(league_settings or {})
    needs = dict(team_needs or {})
    selected_need = dict(needs.get(selected_position) or {})
    blockers = []
    missing = ["expected role", "acquisition duration", "player news"]
    comparison = {"state": "UNAVAILABLE", "decision_effect": "INFORMATIONAL_ONLY", "weeks": [], "reason": "No matching supported Full-PPR weeks are available for both players."}
    reasons = []
    concerns = []
    if not selected_id or not selected_position:
        blockers.append("SELECTED_ROSTER_PLAYER_IDENTITY_UNAVAILABLE")
    if not roster_coverage_complete:
        blockers.append("WAIVER_ROSTER_COVERAGE_INCOMPLETE")
    identity = candidate.get("identity_resolution") or {}
    if identity.get("resolution_state") != "RESOLVED":
        blockers.append(identity.get("blocker") or "WAIVER_CANDIDATE_IDENTITY_UNRESOLVED")
    if evidence.get("ownership_state") != "VERIFIED":
        blockers.append("WAIVER_CANDIDATE_OWNERSHIP_UNVERIFIED")
    if evidence.get("eligibility_state") != "VERIFIED":
        blockers.append("WAIVER_CANDIDATE_ELIGIBILITY_UNVERIFIED")
    if candidate.get("candidate_disposition") != "PRELIMINARY_SUGGESTION" or evidence.get("health_state") != "HEALTHY" or evidence.get("health_freshness_state") != "FRESH":
        blockers.extend(candidate.get("recommendation_blockers") or ["WAIVER_CANDIDATE_NOT_VERIFIED_HEALTHY"])
    same_position = bool(selected_position and candidate_position == selected_position)
    flex_positions = settings.get("flex_eligible_positions") or []
    selected_slot = str(selected_player.get("sleeper_lineup_slot") or selected_player.get("lineup_slot") or "").upper()
    flex_need = dict(needs.get("FLEX") or {})
    flex_slots = int((settings.get("starter_slots") or {}).get("FLEX") or flex_need.get("required_slots") or flex_need.get("starter_shortage") or 0)
    selected_is_starter = selected_player.get("is_starter", selected_player.get("sleeper_current_starter"))
    selected_flex_role = selected_slot in {"FLEX", "W/R/T", "WR/RB/TE", "WRRB_FLEX", "REC_FLEX"} or (selected_is_starter is False and flex_slots > 0)
    candidate_can_compete = same_position or (
        candidate_position in flex_positions
        and selected_position in flex_positions
        and flex_need.get("state") == "AVAILABLE"
        and flex_slots > 0
        and selected_flex_role
    )
    if not candidate_can_compete:
        blockers.append("CANDIDATE_POSITION_NOT_RELEVANT_TO_SELECTED_PLAYER")

    safety_blocked = bool(blockers)
    decision = "NO_ACTIONABLE_UPGRADE"
    summary = {"state": "UNAVAILABLE", "reason": "No current evidence supports a selected-player comparison."}
    roster_effect = "No roster change is supported."
    suggested_drop = {"state": "UNAVAILABLE", "player_id": None, "player": None, "reason": "No safe ADD/DROP conclusion is supported."}
    freshness = {"candidate_production": (candidate.get("recent_production") or {}).get("state", "UNAVAILABLE"), "selected_production": (selected_player.get("recent_production") or {}).get("state", "UNAVAILABLE")}
    for label, player in (("candidate", candidate), ("selected player", selected_player)):
        for signal in ("recent_production", "opportunity_metrics", "snap_share"):
            payload = player.get(signal) or {}
            if payload.get("state") in {"BLOCKED", "STALE", "UNAVAILABLE", "UNSUPPORTED"}:
                missing.extend(f"{label} {signal}: {blocker}" for blocker in payload.get("blockers") or [])

    if not safety_blocked and same_position:
        comparison = waiver_roster_comparison(candidate, selected_player)
        if comparison.get("state") == "PRELIMINARY":
            sample = len(comparison.get("weeks") or [])
            difference = comparison.get("difference")
            latest_difference = comparison.get("latest_difference")
            summary = {
                "state": "PRELIMINARY",
                "candidate_average": comparison.get("candidate_average"),
                "selected_average": comparison.get("roster_average"),
                "difference": difference,
                "candidate_wins": comparison.get("candidate_wins"),
                "weeks": list(comparison.get("weeks") or []),
                "sample_size": sample,
                "freshness_states": list(comparison.get("freshness_states") or []),
                "source_authorities": list(comparison.get("source_authorities") or []),
                "sources": list(comparison.get("sources") or []),
                "retrieved_at": list(comparison.get("retrieved_at") or []),
                "calculation_versions": list(comparison.get("calculation_versions") or []),
                "disclosure": "Historical evidence, not a forecast.",
            }
            if difference is not None and difference <= 0:
                decision = "HOLD"
                roster_effect = "Supported matched production does not favor replacing the selected player."
                reasons.append("The selected player matched or exceeded the candidate's observed Full-PPR average.")
            elif sample < 2 or latest_difference is None or latest_difference <= 0 or (comparison.get("candidate_wins") or 0) <= sample / 2:
                decision = "MONITOR"
                roster_effect = "The observed edge is too limited or inconsistent across matched weeks for an ADD/DROP conclusion."
                reasons.append("The candidate has a positive observed average edge, but the sample, latest matched week, or win count does not support a move.")
            else:
                current_count = sum(1 for player in (roster or []) if str(player.get("position") or "").upper().replace("DST", "DEF") == selected_position)
                required = int(selected_need.get("required_starters") or 0)
                depth_target = int(selected_need.get("depth_target") or required)
                remaining_count = current_count - 1
                drop_safe = (
                    selected_player.get("sleeper_current_starter") is not True
                    and remaining_count >= required
                    and remaining_count >= depth_target
                    and selected_need.get("state") == "AVAILABLE"
                )
                if drop_safe:
                    decision = "ADD"
                    roster_effect = f"Adds a {candidate_position} and removes one bench {selected_position}; supported required-starter and depth coverage remain intact."
                    suggested_drop = {"state": "PRELIMINARY", "player_id": selected_id, "player": selected_player.get("player"), "reason": "Selected bench player is the direct same-position comparison; roster coverage remains at or above supported starter and depth targets."}
                    reasons.append("Candidate observed a higher average across at least two matching weeks and also led in the latest matched week.")
                else:
                    decision = "HOLD"
                    roster_effect = "Keep the selected player: candidate has an observed edge, but removing this starter or reducing supported coverage is unsafe."
                    reasons.append("The candidate has a positive matched Full-PPR edge, but the selected player is a current starter or dropping him would breach supported coverage.")
                    concerns.append("Roster safety prevents dropping the selected player for this candidate.")
        else:
            candidate_usage = candidate.get("opportunity_metrics") or {}
            selected_usage = selected_player.get("opportunity_metrics") or {}
            candidate_usage_rows = candidate_usage.get("rows") or []
            selected_usage_rows = selected_usage.get("rows") or []
            selected_usage_by_week = {
                (row.get("season"), row.get("week")): row
                for row in selected_usage_rows
                if row.get("freshness_state") in {"FRESH", "AGING"}
            }
            relevant_metrics = ("carry_share", "touch_share", "target_share") if selected_position == "RB" else ("target_share", "route_participation", "touch_share")
            usage_pair = next((
                (row, selected_usage_by_week[(row.get("season"), row.get("week"))])
                for row in sorted(candidate_usage_rows, key=lambda item: (item.get("season") or 0, item.get("week") or 0), reverse=True)
                if row.get("freshness_state") in {"FRESH", "AGING"}
                and (row.get("season"), row.get("week")) in selected_usage_by_week
                and any(
                    isinstance(row.get(metric), (int, float)) and not isinstance(row.get(metric), bool)
                    and isinstance(selected_usage_by_week[(row.get("season"), row.get("week"))].get(metric), (int, float))
                    and not isinstance(selected_usage_by_week[(row.get("season"), row.get("week"))].get(metric), bool)
                    for metric in relevant_metrics
                )
            ), None)
            if usage_pair:
                candidate_row, selected_row = usage_pair
                deltas = {
                    metric: float(candidate_row[metric]) - float(selected_row[metric])
                    for metric in relevant_metrics
                    if isinstance(candidate_row.get(metric), (int, float)) and not isinstance(candidate_row.get(metric), bool)
                    and isinstance(selected_row.get(metric), (int, float)) and not isinstance(selected_row.get(metric), bool)
                }
                positive = {metric: delta for metric, delta in deltas.items() if delta > 0}
                negative = {metric: delta for metric, delta in deltas.items() if delta < 0}
                summary = {"state": "PRELIMINARY", "metric": "matched_position_opportunity", "week": candidate_row.get("week"), "season": candidate_row.get("season"), "candidate": {metric: candidate_row.get(metric) for metric in deltas}, "selected": {metric: selected_row.get(metric) for metric in deltas}, "delta": deltas, "sample_size": 1, "freshness": "FRESH_OR_AGING", "disclosure": "Matched position-specific opportunity context; historical usage, not a points forecast."}
                if positive and not negative:
                    decision = "MONITOR"
                    roster_effect = "Candidate has a positive matched position-specific opportunity signal; production comparison is unavailable."
                    reasons.append("Current matched opportunity evidence directionally favors the candidate: " + ", ".join(sorted(positive)) + ".")
                elif negative and not positive:
                    decision = "HOLD"
                    roster_effect = "Selected player has equal or better matched position-specific opportunity on the observed metrics."
                    reasons.append("Current matched opportunity evidence does not favor the candidate.")
                elif positive and negative:
                    decision = "MONITOR"
                    roster_effect = "Matched opportunity evidence is mixed and does not support an ADD/DROP conclusion."
                    reasons.append("Position-specific usage signals conflict in the same matched week.")
                else:
                    summary["state"] = "SCREENING_ONLY"
            elif decision == "NO_ACTIONABLE_UPGRADE":
                summary = {"state": "SCREENING_ONLY", "reason": "Snap share without matched Full-PPR production or position-relevant workload is screening-only evidence.", "disclosure": "No candidate-specific directional or scoring comparison is available."}
                concerns.append("Freshness-qualified production and position-relevant workload comparison are unavailable.")
            if decision == "NO_ACTIONABLE_UPGRADE":
                candidate_changes = ((candidate.get("player_comparison") or {}).get("what_changed") or {})
                selected_changes = ((selected_player.get("player_comparison") or {}).get("what_changed") or {})
                relevant_change_fields = {"targets", "target_share", "carries", "carry_share", "touch_share", "receptions", "route_participation", "receiving_yards", "rushing_yards"} if selected_position in {"RB", "WR", "TE"} else set()
                directional_changes = [
                    change for change in candidate_changes.get("changes") or []
                    if str(change.get("direction") or "").upper() in {"UP", "INCREASED", "INCREASING"}
                    and str(change.get("field") or "").lower() in relevant_change_fields
                ] if candidate_changes.get("state") == "AVAILABLE" else []
                if directional_changes:
                    decision = "MONITOR"
                    roster_effect = "Candidate has a current positive position-relevant opportunity change; selected-player production comparison remains unavailable."
                    summary = {
                        "state": "PARTIAL",
                        "disclosure": "Candidate-specific position-relevant What Changed context only; no direct points advantage or role forecast is calculated.",
                        "candidate_changes": directional_changes,
                        "selected_changes": list(selected_changes.get("changes") or []),
                    }
                    reasons.extend(
                        f"Candidate: {change.get('display') or change.get('label')}"
                        for change in directional_changes
                        if change.get("display") or change.get("label")
                    )

    if not safety_blocked and not same_position:
        comparison = waiver_roster_comparison(candidate, selected_player, allow_cross_position=True)
        if comparison.get("state") == "PRELIMINARY":
            sample = len(comparison.get("weeks") or [])
            difference = comparison.get("difference")
            latest_difference = comparison.get("latest_difference")
            summary = {
                "state": "PRELIMINARY",
                "candidate_average": comparison.get("candidate_average"),
                "selected_average": comparison.get("roster_average"),
                "difference": difference,
                "candidate_wins": comparison.get("candidate_wins"),
                "weeks": list(comparison.get("weeks") or []),
                "sample_size": sample,
                "freshness_states": list(comparison.get("freshness_states") or []),
                "source_authorities": list(comparison.get("source_authorities") or []),
                "sources": list(comparison.get("sources") or []),
                "retrieved_at": list(comparison.get("retrieved_at") or []),
                "calculation_versions": list(comparison.get("calculation_versions") or []),
                "disclosure": "Matched Full-PPR scoring across supported FLEX positions; historical evidence, not a forecast.",
            }
            if difference is not None and difference <= 0:
                decision = "HOLD"
                roster_effect = "The selected player matched or exceeded the FLEX candidate's observed Full-PPR average."
                reasons.append("Matched Full-PPR production favors the selected player over this FLEX candidate.")
            elif sample >= 2 and latest_difference is not None and latest_difference > 0 and (comparison.get("candidate_wins") or 0) > sample / 2:
                current_count = sum(1 for player in (roster or []) if str(player.get("position") or "").upper().replace("DST", "DEF") == selected_position)
                required = int(selected_need.get("required_starters") or 0)
                depth_target = int(selected_need.get("depth_target") or required)
                drop_safe = selected_player.get("sleeper_current_starter") is not True and current_count - 1 >= required and current_count - 1 >= depth_target and selected_need.get("state") == "AVAILABLE"
                decision = "ADD" if drop_safe else "HOLD"
                roster_effect = "The FLEX candidate has a consistent matched Full-PPR edge." if drop_safe else "Keep the selected player: FLEX replacement value is indicated, but removing this starter or reducing supported coverage is unsafe."
                if drop_safe:
                    suggested_drop = {"state": "PRELIMINARY", "player_id": selected_id, "player": selected_player.get("player"), "reason": "Selected bench player is the direct Full-PPR comparison and required position/depth coverage remains intact."}
                    reasons.append("Candidate led the selected player across a majority of matched Full-PPR weeks and the latest week.")
                else:
                    concerns.append("Removing the selected player would reduce supported position or starter coverage.")
            else:
                decision = "MONITOR"
                roster_effect = "A FLEX candidate has a positive matched Full-PPR signal, but the sample or latest-week edge is insufficient for ADD."
                reasons.append("Matched Full-PPR evidence provides a candidate-specific positive signal, but not enough to support a move.")
        else:
            decision = "NO_ACTIONABLE_UPGRADE"
            summary = {"state": "SCREENING_ONLY", "reason": "FLEX eligibility and snap share alone do not establish greater fantasy value.", "disclosure": "No direct cross-position points comparison is available."}
            roster_effect = "No cross-position FLEX candidate has a current overlapping Full-PPR comparison."
            concerns.append("FLEX eligibility or snap share alone is screening-only evidence.")
    if focus == "rest_of_season" and decision == "ADD":
        decision = "MONITOR"
        suggested_drop = {"state": "UNAVAILABLE", "player_id": None, "player": None, "reason": "Expected role and acquisition duration are unavailable for a season-long ADD/DROP conclusion."}
        roster_effect = "Historical comparison supports an immediate review only; season-long role and duration are not verified."
        reasons.append("The selected focus is rest of season, but expected role and duration are unavailable.")
    if safety_blocked:
        decision = "BLOCKED"
        concerns.extend(blockers)
    if decision != "ADD":
        faab = {"state": "NO_BID", "low": 0, "high": 0, "category": "NONE", "rationale": f"No bid is suggested for {decision}."}
    else:
        selected_is_starter = selected_player.get("sleeper_current_starter", selected_player.get("is_starter"))
        bid_guidance = {
            "authority": "PROVISIONAL",
            "this_week": {"action": "REVIEW_ADD"},
            "rest_of_season": {"action": "MONITOR"},
        }
        provisional = waiver_provisional_bid(bid_guidance, faab_balance or {}, selected_is_starter)
        faab_category = "FLEX_CHALLENGER" if candidate_position != selected_position else "DEPTH_ADDITION"
        faab = {"state": provisional.get("state", "UNAVAILABLE"), "low": provisional.get("low"), "high": provisional.get("high"), "remaining": (faab_balance or {}).get("remaining"), "category": faab_category, "rationale": provisional.get("reason") or "Existing provisional FAAB guidance is unavailable."}
    if not reasons and decision == "NO_ACTIONABLE_UPGRADE":
        reasons.append("No fresh, comparable evidence supports changing this selected player.")
    if not concerns:
        concerns.append("Expected role, acquisition duration, and current player news are unavailable.")
    if freshness["candidate_production"] != "AVAILABLE" or freshness["selected_production"] != "AVAILABLE":
        missing.append("fresh overlapping Full-PPR production")
    if summary.get("state") == "SCREENING_ONLY":
        relevance_class = "SCREENING_ONLY"
    elif summary.get("state") == "PRELIMINARY" and summary.get("candidate_average") is not None and summary.get("selected_average") is not None:
        relevance_class = "MEANINGFUL_COMPARISON"
    elif summary.get("metric") == "matched_position_opportunity" or (summary.get("state") == "PARTIAL" and summary.get("candidate_changes")):
        relevance_class = "DIRECTIONAL_SIGNAL"
    else:
        relevance_class = "INSUFFICIENT"
    rank_horizon = "rest_of_season" if focus == "rest_of_season" else "this_week"
    consensus_rank = (candidate.get("source_rankings") or {}).get(rank_horizon)
    secondary_context = {
        "consensus_rank": consensus_rank.get("ecr") if isinstance(consensus_rank, dict) else None,
        "source_date": consensus_rank.get("source_date") if isinstance(consensus_rank, dict) else None,
        "decision_effect": "INFORMATIONAL_ONLY",
    }
    return {
        "schema_version": "selected-waiver-comparison.v1",
        "selected_player_id": selected_id or None,
        "selected_player": selected_player.get("player"),
        "selected_position": selected_position or None,
        "candidate_id": candidate_id or None,
        "candidate": candidate.get("player"),
        "candidate_position": candidate_position or None,
        "decision": decision,
        "relevance_class": relevance_class,
        "evidence_level": "PRELIMINARY" if summary.get("state") in {"PRELIMINARY", "PARTIAL"} else "INSUFFICIENT",
        "roster_effect": roster_effect,
        "comparison_summary": summary,
        "depth_chart_context": {
            "selected_player": selected_player.get("sleeper_depth_chart") or {"state": "UNAVAILABLE", "reason": "Sleeper depth-chart fields are unavailable."},
            "candidate": candidate.get("sleeper_depth_chart") or {"state": "UNAVAILABLE", "reason": "Sleeper depth-chart fields are unavailable."},
            "decision_effect": "SCREENING_ONLY",
        },
        "news_context": {
            "selected_player": selected_player.get("player_news") or {"state": "UNAVAILABLE", "articles": [], "reason": "No ESPN athlete-ID-linked news item is available."},
            "candidate": candidate.get("player_news") or {"state": "UNAVAILABLE", "articles": [], "reason": "No ESPN athlete-ID-linked news item is available."},
            "freshness_state": "UNVERIFIED",
            "decision_effect": "INFORMATIONAL_ONLY",
        },
        "secondary_context": secondary_context,
        "reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "concerns": list(dict.fromkeys(concerns)),
        "suggested_drop": suggested_drop,
        "faab": faab,
        "confidence_rationale": "Historical or usage evidence supports only a preliminary comparison; no forecast or role-duration model is available." if summary.get("state") in {"PRELIMINARY", "PARTIAL"} else "Insufficient current comparison evidence for a safe move.",
        "missing_evidence": list(dict.fromkeys(missing)),
        "blockers": list(dict.fromkeys(blockers)),
    }


def waiver_candidate_context(candidate, roster, team_needs, ranking_confidence):
    """Build display-only context from already-authoritative waiver inputs."""
    candidate = dict(candidate or {})
    position = str(candidate.get("position") or "").upper().replace("DST", "DEF")
    ownership_state = candidate.get("ownership_state") or "UNAVAILABLE"
    eligibility_state = candidate.get("eligibility_state") or "UNAVAILABLE"
    health_is_current = (
        candidate.get("health_status_available") is True
        and candidate.get("injury_source") == "Sleeper API"
        and bool(candidate.get("health_fetched_at"))
        and candidate.get("health_freshness_state") == "FRESH"
    )
    supported_health = _waiver_health_state(candidate.get("injury_status")) if health_is_current else None
    health_state = supported_health or "UNAVAILABLE"
    identity_state = candidate.get("opportunity_identity_state") or (candidate.get("identity_resolution") or {}).get("resolution_state")
    need = dict((team_needs or {}).get(position) or {})
    if need.get("state") == "AVAILABLE":
        strategic_need = need.get("strategic_need")
        roster_fit = {
            "state": "AVAILABLE",
            "label": "addresses an active need" if strategic_need == "ADD_STARTER" else "improves depth" if strategic_need == "ADD_DEPTH" else "speculative depth only",
            "reason": (need.get("drivers") or ["Shared roster need is satisfied; review as speculative depth."])[0],
        }
    else:
        roster_fit = {"state": "BLOCKED", "label": "Roster fit unavailable", "reason": "Roster fit unavailable because league-settings evidence is unavailable."}

    candidate_projection = candidate.get("projection")
    comparable = [
        player for player in (roster or [])
        if str(player.get("position") or "").upper().replace("DST", "DEF") == position
        and player.get("projection") is not None
    ]
    if candidate_projection is not None and comparable:
        drop = min(comparable, key=lambda player: (player.get("projection"), player.get("player") or ""))
        suggested_drop = {
            "state": "INFORMATIONAL_ONLY",
            "player": drop.get("player"),
            "reason": "Projection-only same-position comparison; no authoritative drop-value model is used.",
        }
    else:
        suggested_drop = {"state": "UNAVAILABLE", "reason": "Suggested drop unavailable because no supported drop-value comparison exists.", "prerequisite": "AUTHORITY_CONTRACT_REQUIRED"}

    recent = candidate.get("recent_production") or {}
    confidence = "limited evidence: candidate production is unavailable"
    if recent.get("state") == "AVAILABLE":
        confidence = "preliminary observed production evidence; not a forecast"
    risk = []
    if recent.get("state") != "AVAILABLE":
        risk.append("missing recent production")
    if not risk:
        risk.append("no additional evidence-backed risk identified")
    snap = candidate.get("snap_share") or {}
    usage = candidate.get("opportunity_metrics") or {}
    usage_rows = usage.get("rows") or []
    snap_rows = snap.get("rows") or []
    usage_row = usage_rows[-1] if usage.get("state") == "AVAILABLE" and usage_rows else None
    prior_usage_row = usage_rows[-2] if usage.get("state") == "AVAILABLE" and len(usage_rows) > 1 else None
    snap_row = snap_rows[0] if snap.get("state") == "AVAILABLE" and snap_rows else None
    prior_snap_row = snap_rows[1] if snap.get("state") == "AVAILABLE" and len(snap_rows) > 1 else None
    strength = opportunity_strength(usage_row=usage_row, snap_row=snap_row)
    stability = usage_stability(current_usage=usage_row, prior_usage=prior_usage_row, current_snap=snap_row, prior_snap=prior_snap_row)
    if stability.get("state") == "INSUFFICIENT_EVIDENCE" and (usage_row or snap_row):
        stability["reason"] = "One supported week is available. A second published week is required for usage stability and trend."
    trend = opportunity_trend(strength=strength, stability=stability)
    if identity_state in {"AMBIGUOUS", "CONFLICTING", "BLOCKED"}:
        context_state = "BLOCKED"
        context_reason = "Identity evidence is blocked or contradictory; no source evidence is consumed."
    elif not candidate.get("opportunity_player_id"):
        non_opportunity_evidence = (
            roster_fit.get("state") == "AVAILABLE"
            or candidate.get("projection") is not None
            or bool(candidate.get("projection_retrieved_at"))
            or candidate.get("health_status_available") is True
            or candidate.get("injury_status") not in (None, "", "Unknown", "Healthy / Not listed")
        )
        context_state = "PARTIAL_CONTEXT" if non_opportunity_evidence else "IDENTITY_LIMITED"
        context_reason = (
            "Ownership, eligibility, roster fit, or projection evidence is available; opportunity evidence remains unavailable because no deterministic GSIS identity is available."
            if non_opportunity_evidence else
            "Opportunity evidence unavailable for this source because no deterministic GSIS identity is available."
        )
    elif usage.get("state") == "AVAILABLE":
        context_state = "FULL_CONTEXT"
        context_reason = "Supported identity and published opportunity evidence are available."
    elif candidate.get("projection") is not None or recent.get("state") == "AVAILABLE":
        context_state = "PARTIAL_CONTEXT"
        context_reason = "Useful roster, projection, or production evidence is available; published opportunity evidence is unavailable."
    else:
        context_state = "SOURCE_LIMITED"
        context_reason = "Identity resolves, but no published opportunity source row is available."
    if usage_row:
        snap_text = " Snap share: %s." % ((snap.get("rows") or [{}])[-1].get("snap_share")) if snap.get("state") == "AVAILABLE" else " Snap share unavailable."
        opportunity = {"state": "AVAILABLE", "reason": "Targets: %s; carries: %s; target share: %s; carry share: %s; touch share: %s.%s" % (usage_row.get("targets"), usage_row.get("carries"), usage_row.get("target_share"), usage_row.get("carry_share"), usage_row.get("touch_share"), snap_text)}
    else:
        opportunity = {"state": "UNAVAILABLE", "reason": "Opportunity context unavailable because no candidate-linked published usage row exists."}
    observed_weeks = sorted({row.get("week") for row in (usage.get("rows") or []) + (snap.get("rows") or []) if row.get("week") is not None})
    if len(observed_weeks) >= 2:
        evidence_coverage = {"state": "AVAILABLE", "label": "Two-week comparison available", "weeks": observed_weeks[-2:]}
    elif len(observed_weeks) == 1:
        evidence_coverage = {"state": "PARTIAL", "label": "Week %s evidence available; one observation only" % observed_weeks[0], "weeks": observed_weeks}
    else:
        evidence_coverage = {"state": "UNAVAILABLE", "label": "No candidate-linked usage observations available", "weeks": []}
    if candidate.get("recommendation_state") != "ACTIONABLE":
        suggested_drop = {
            "state": "UNAVAILABLE",
            "reason": "No supported ADD/DROP conclusion is available because candidate health or waiver ranking authority is blocked.",
        }
    return {
        "ownership_state": ownership_state,
        "eligibility_state": eligibility_state,
        "health_state": health_state,
        "health_source": candidate.get("injury_source") if candidate.get("health_status_available") is True else "UNAVAILABLE",
        "health_freshness_state": candidate.get("health_freshness_state") or "UNAVAILABLE" if candidate.get("health_status_available") is True else "UNAVAILABLE",
        "health_blocker": candidate.get("health_blocker") if not supported_health else None,
        "health_freshness_state": candidate.get("health_freshness_state", "UNAVAILABLE"),
        "health_blocker": candidate.get("health_blocker"),
        "recommendation_state": candidate.get("recommendation_state", "HEALTH_UNVERIFIED"),
        "recommendation_blockers": list(candidate.get("recommendation_blockers") or []),
        "projection_source": "local player projection" if candidate.get("projection") is not None else "UNAVAILABLE",
        "roster_fit": roster_fit,
        "snap_share": snap,
        "opportunity_strength": strength,
        "usage_stability": stability,
        "opportunity_trend": trend,
        "context_state": context_state,
        "context_reason": context_reason,
        "evidence_gaps": ["Second published week required for usage stability and trend"] if stability.get("state") == "INSUFFICIENT_EVIDENCE" and (usage_row or snap_row) else [],
        "suggested_drop": suggested_drop,
        "opportunity": opportunity,
        "evidence_coverage": evidence_coverage,
        "role": {"state": "UNAVAILABLE", "reason": "Role classification unavailable because no verified role contract is published."},
        "duration": {"state": "UNAVAILABLE", "reason": "Opportunity duration unavailable because no verified duration source exists.", "prerequisite": "EXTERNAL_SOURCE_REQUIRED"},
        "confidence": confidence,
        "risk": risk,
        "news": {"state": "UNAVAILABLE", "reason": "Latest news unavailable because no verified player-news source is configured.", "prerequisite": "EXTERNAL_SOURCE_REQUIRED"},
        "ranking": {"state": "UNVERIFIED", "reason": "Waiver ranking source is unverified; candidate order remains informational.", "prerequisite": "AUTHORITY_CONTRACT_REQUIRED"},
        "projection_retrieved_at": candidate.get("projection_retrieved_at"),
    }


def _stable_lineup_identity(player):
    value = str(player.get("source_player_id") or player.get("local_player_id") or "").strip()
    return value or None


def _normalize_lineup_slot(value):
    slot = str(value or "").upper()
    return "FLEX" if slot in {"W/R/T", "WR/RB/TE", "FLEX"} else slot


def build_lineup_reconciliation(roster, recommended_starters, decisions=None):
    """Compare Sleeper's current starters with the recommended lineup by stable identity; read-only."""
    def unavailable(blocker, current=()):
        return {"state": "UNAVAILABLE", "blocker": blocker, "current": list(current), "recommended": [], "changes": [], "changed_recommended": []}

    current_starters = sorted(
        (player for player in roster or [] if player.get("sleeper_current_starter") and player.get("sleeper_lineup_slot")),
        key=lambda player: (player.get("sleeper_lineup_index") is None, player.get("sleeper_lineup_index") or 0),
    )
    if not current_starters:
        return unavailable("CURRENT_LINEUP_UNAVAILABLE")
    occurrences = {}
    current = []
    for player in current_starters:
        slot = _normalize_lineup_slot(player.get("sleeper_lineup_slot"))
        if slot in {"RB", "WR"}:
            occurrences[slot] = occurrences.get(slot, 0) + 1
            slot = f"{slot}{occurrences[slot]}"
        current.append({
            "slot": slot,
            "player": player.get("player"),
            "player_id": _stable_lineup_identity(player),
            "position": player.get("position"),
            "injury_status": player.get("injury_status") or "Unknown",
        })
    if any(row["player_id"] is None for row in current):
        return unavailable("CURRENT_LINEUP_IDENTITY_UNAVAILABLE", current)
    recommended = [
        {"slot": player.get("slot"), "player": player.get("player"), "player_id": _stable_lineup_identity(player), "position": player.get("position"), "player_data": player}
        for player in recommended_starters or []
        if not player.get("vacant")
    ]
    if any(row["player_id"] is None for row in recommended):
        return unavailable("RECOMMENDED_LINEUP_IDENTITY_UNAVAILABLE", current)
    current_by_slot = {row["slot"]: row for row in current}
    if any(row["slot"] not in current_by_slot for row in recommended):
        return unavailable("CURRENT_LINEUP_INCOMPLETE", current)
    current_ids = {row["player_id"] for row in current}
    decision_by_slot = {item.get("slot"): item for item in (decisions or [])}
    changes = []
    for row in recommended:
        # Slot swaps among players already starting are not pending changes in Sleeper.
        if row["player_id"] in current_ids:
            continue
        existing = current_by_slot[row["slot"]]
        slot_decision = decision_by_slot.get(row["slot"]) or {}
        recommended_player = {**row["player_data"], "replaced_current": existing["player"], "change_action": "FLEX" if slot_decision.get("decision") == "FLEX" else "START"}
        changes.append({
            "slot": row["slot"],
            "current": existing["player"],
            "current_id": existing["player_id"],
            "recommended": row["player"],
            "recommended_id": row["player_id"],
            "authority": slot_decision.get("decision") or "START",
            "recommended_player": recommended_player,
            "reason": slot_decision.get("reason") or row["player_data"].get("reason"),
            "watch_item": next(iter(row["player_data"].get("evidence_gaps") or []), None),
            "confidence": slot_decision.get("confidence") if slot_decision.get("confidence") and slot_decision.get("confidence_rationale") else None,
        })
    return {"state": "AVAILABLE", "blocker": None, "current": current, "recommended": recommended, "changes": changes, "changed_recommended": [change["recommended_player"] for change in changes]}


def build_recommended_bench(roster, recommended_starters):
    """Return the roster minus every recommended starter, or None when starter identity is unverified."""
    starter_ids = {_stable_lineup_identity(player) for player in recommended_starters or () if not player.get("vacant")}
    if None in starter_ids:
        return None
    bench = [dict(player) for player in (roster or ()) if _stable_lineup_identity(player) not in starter_ids]
    bench.sort(key=sort_key)
    for index, player in enumerate(bench, 1):
        player["bench_order"] = index
        player["decision"] = decision(player, "SIT")
        player.setdefault("confidence", {"label": "UNAVAILABLE", "score": "Unavailable"})
    return bench


def attach_preliminary_matchup_display(starters):
    """Copy shared matchup evidence onto starters for display only; never alters decisions."""
    displayed = []
    for starter in starters or []:
        starter = dict(starter)
        evidence = (starter.get("lineup_evidence") or {}).get("matchup") or (starter.get("weekly_evidence") or {}).get("matchup") or {}
        starter["matchup_rank_authoritative"] = bool(evidence.get("authoritative"))
        if not starter.get("vacant") and evidence.get("matchup_signal") and evidence.get("evidence_level") in {"PRELIMINARY", "ESTABLISHED"}:
            starter.update(
                matchup_signal=evidence["matchup_signal"],
                evidence_level=evidence["evidence_level"],
                sample_games=evidence.get("sample_size"),
                freshness=evidence.get("freshness_state") or "UNAVAILABLE",
                matchup_recommendation_impact=evidence.get("recommendation_impact") or "NONE",
                matchup_blockers=list(evidence.get("blockers") or []),
            )
        displayed.append(starter)
    return displayed


def create_owner_operations_blueprint(
    get_db_connection,
    get_league,
    get_users,
    get_rosters,
    get_all_players,
    normalize_player_name,
):
    bp = Blueprint("owner_ops", __name__)

    def data_context(cur):
        cur.execute(
            """
            SELECT state_value
            FROM application_state
            WHERE state_key = 'active_sandbox'
            """
        )
        row = cur.fetchone()
        state = row[0] if row else None
        if state and state.get("mode") == "MOCK" and state.get("draft_id"):
            return {"mode": "MOCK", "draft_id": int(state["draft_id"])}
        return {"mode": "LIVE", "draft_id": None}

    def row_to_player(row, projection_retrieved_at=None, local_player_id=None):
        return {
            "player": row[0],
            "position": (row[1] or "NA").upper().replace("DST", "DEF"),
            "nfl_team": row[2] or "FA",
            "rank": row[3],
            "projection": float(row[4] or 0),
            "tier": row[5],
            "adp": float(row[6]) if row[6] is not None else None,
            "bye_week": row[7],
            "injury_status": row[8] or "Healthy / Not listed",
            "pick_no": row[9] if len(row) > 9 else None,
            "round": row[10] if len(row) > 10 else None,
            "projection_retrieved_at": projection_retrieved_at,
            "local_player_id": local_player_id,
        }

    def mock_roster(cur, draft_id, draft_slot=None):
        if draft_slot is None:
            cur.execute("SELECT draft_position FROM mock_drafts WHERE id = %s", (draft_id,))
            found = cur.fetchone()
            draft_slot = found[0] if found else 5
        cur.execute(
            """
            SELECT
                mp.player_name,
                UPPER(mp.position),
                mp.nfl_team,
                mp.overall_rank,
                p.projected_points,
                p.tier,
                p.adp,
                p.bye_week,
                p.injury_status,
                mp.pick_no,
                mp.round_num,
                p.projection_retrieved_at
            FROM mock_picks mp
            LEFT JOIN players p ON p.player_name = mp.player_name
            WHERE mp.draft_id = %s
              AND mp.draft_slot = %s
            ORDER BY mp.pick_no
            """,
            (draft_id, draft_slot),
        )
        return [row_to_player(row, row[11] if len(row) > 11 else None) for row in cur.fetchall()]

    def live_roster(cur):
        league_result = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", ""))
        users_result = get_users(current_app.config.get("SLEEPER_LEAGUE_ID", ""))
        rosters_result = get_rosters(current_app.config.get("SLEEPER_LEAGUE_ID", ""))
        catalog_result = get_all_players()
        league = league_result or {}
        users = users_result or []
        rosters = rosters_result or []
        all_players = catalog_result or {}
        sleeper_retrieved_at = datetime.now(timezone.utc).isoformat()
        waiver_snapshot = {"league": league_result, "users": users_result, "rosters": rosters_result, "catalog": catalog_result, "retrieved_at": sleeper_retrieved_at}
        league = {**league, "owner_faab_balance": waiver_faab_balance(league, users, rosters)}
        owner_ids = {
            str(user.get("user_id"))
            for user in users
            if user.get("is_owner") is True
        }
        owner_roster = next(
            (r for r in rosters if str(r.get("owner_id") or "") in owner_ids),
            None,
        )
        if not owner_roster:
            return [], league, all_players, waiver_snapshot
        player_ids = [str(pid) for pid in (owner_roster.get("players") or [])]
        sleeper_starters = [str(pid) for pid in (owner_roster.get("starters") or [])]
        roster_positions = [slot for slot in (league.get("roster_positions") or []) if str(slot).upper() not in {"BN", "BENCH"}]
        sleeper_slots = {player_id: str(roster_positions[index]) for index, player_id in enumerate(sleeper_starters) if index < len(roster_positions)}
        sleeper_slot_indexes = {player_id: index for index, player_id in enumerate(sleeper_starters) if index < len(roster_positions)}
        local_names = []
        for pid in player_ids:
            raw = all_players.get(pid) or {}
            name = raw.get("full_name") or " ".join(
                part for part in (raw.get("first_name"), raw.get("last_name")) if part
            )
            if name:
                local_names.append((pid, name, raw.get("position"), raw.get("team"), raw.get("injury_status") or raw.get("status")))
        result = []
        for sleeper_player_id, name, position, team, raw_status in local_names:
            catalog_record = all_players.get(sleeper_player_id) or {}
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status,
                       projection_retrieved_at, id
                FROM players
                WHERE REGEXP_REPLACE(LOWER(player_name), '[^a-z0-9]', '', 'g') = %s
                LIMIT 1
                """,
                (normalize_player_name(name),),
            )
            row = cur.fetchone()
            if not row:
                normalized_name = normalize_player_name(name)
                cur.execute(
                    """
                    SELECT player_name, UPPER(position), nfl_team, ranking,
                           projected_points, tier, adp, bye_week, injury_status,
                           projection_retrieved_at, id
                    FROM players
                    WHERE REGEXP_REPLACE(LOWER(player_name), '[^a-z0-9]', '', 'g') LIKE %s
                    ORDER BY LENGTH(player_name)
                    LIMIT 1
                    """,
                    (f"{normalized_name}%",),
                )
                row = cur.fetchone()
            if row:
                player=row_to_player(row, row[9] if len(row) > 9 else None, row[10] if len(row) > 10 else None)
                player["source_player_id"] = sleeper_player_id
                player["sleeper_current_starter"] = sleeper_player_id in sleeper_starters
                player["sleeper_lineup_slot"] = sleeper_slots.get(sleeper_player_id)
                player["sleeper_lineup_index"] = sleeper_slot_indexes.get(sleeper_player_id)
                player["sleeper_gsis_id"] = catalog_record.get("gsis_id")
                player["sleeper_espn_id"] = catalog_record.get("espn_id")
                player["sleeper_depth_chart_position"] = catalog_record.get("depth_chart_position")
                player["sleeper_depth_chart_order"] = catalog_record.get("depth_chart_order")
                player["sleeper_news_updated"] = catalog_record.get("news_updated")
                player["sleeper_metadata_retrieved_at"] = sleeper_retrieved_at
                player["sleeper_metadata_coverage_state"] = "COMPLETE"
                player["normalized_name"] = normalize_player_name(name)
                player["identity_match_method"] = "UNIQUE_NORMALIZED_NAME"
                player["identity_state"] = "RESOLVED"
                if raw_status:
                    player["injury_status"] = raw_status
                    player["injury_source"] = "Sleeper API"
                    player["health_fetched_at"] = sleeper_retrieved_at
                    player["injury_updated_at"] = sleeper_retrieved_at
                    player["health_status_available"] = True
                else:
                    player["injury_status"] = "Unknown"
                    player["injury_source"] = "Sleeper API"
                    player["health_status_available"] = False
                player["ownership"] = "ROSTERED"
                player["ownership_source"] = "Sleeper API"
                player["roster_updated_at"] = sleeper_retrieved_at
                player["roster_source"] = "Sleeper API"
                result.append(player)
            else:
                player = {
                    "player": name,
                    "position": (position or "NA").upper().replace("DST", "DEF"),
                    "nfl_team": team or "FA",
                    "rank": None,
                    "projection": 0.0,
                    "tier": None,
                    "adp": None,
                    "bye_week": None,
                    "injury_status": raw_status or "Unknown",
                    "injury_source": "Sleeper API",
                    "pick_no": None,
                    "round": None,
                }
                player["injury_source"] = "Sleeper API"
                player["source_player_id"] = sleeper_player_id
                player["sleeper_current_starter"] = sleeper_player_id in sleeper_starters
                player["sleeper_lineup_slot"] = sleeper_slots.get(sleeper_player_id)
                player["sleeper_lineup_index"] = sleeper_slot_indexes.get(sleeper_player_id)
                player["sleeper_gsis_id"] = catalog_record.get("gsis_id")
                player["sleeper_espn_id"] = catalog_record.get("espn_id")
                player["sleeper_depth_chart_position"] = catalog_record.get("depth_chart_position")
                player["sleeper_depth_chart_order"] = catalog_record.get("depth_chart_order")
                player["sleeper_news_updated"] = catalog_record.get("news_updated")
                player["sleeper_metadata_retrieved_at"] = sleeper_retrieved_at
                player["sleeper_metadata_coverage_state"] = "COMPLETE"
                player["normalized_name"] = normalize_player_name(name)
                player["identity_match_method"] = "LOCAL_PLAYER_UNAVAILABLE"
                player["identity_state"] = "UNRESOLVED"
                player["health_status_available"] = player["injury_status"] != "Unknown"
                player["ownership"] = "ROSTERED"
                player["ownership_source"] = "Sleeper API"
                player["roster_updated_at"] = sleeper_retrieved_at
                player["roster_source"] = "Sleeper API"
                if player["health_status_available"]:
                    player["health_fetched_at"] = sleeper_retrieved_at
                    player["injury_updated_at"] = sleeper_retrieved_at
                result.append(player)
        return result, league, all_players, waiver_snapshot

    def current_roster(cur, *, verify_live_week=False, include_waiver_snapshot=False):
        context = data_context(cur)
        season = 2026
        if context["mode"] == "MOCK":
            cur.execute(
                "SELECT draft_name, strategy, draft_position FROM mock_drafts WHERE id = %s",
                (context["draft_id"],),
            )
            row = cur.fetchone()
            roster = mock_roster(cur, context["draft_id"], row[2] if row else 5)
            week = current_week(cur)
            roster = enrich_players(cur, roster, week)
            metadata = {
                "team_name": "My Mock Team",
                "league_name": "Season Sandbox",
                "strategy": row[1] if row else "WR_HEAVY",
                "draft_name": row[0] if row else f"Mock #{context['draft_id']}",
                "season": season,
                "week": week,
                "shared_facts": shared_league_facts({}, source="Season Sandbox", blocker="LIVE_LEAGUE_FACTS_NOT_APPLICABLE"),
            }
            return (context, roster, metadata, None) if include_waiver_snapshot else (context, roster, metadata)
        roster, league, sleeper_catalog, waiver_snapshot = live_roster(cur)
        week_authority = None
        if verify_live_week:
            acquire_week = current_app.config.get("WEEK_AUTHORITY_ACQUIRER")
            try:
                week_authority = acquire_week(season) if acquire_week else build_authoritative_week_contract(season=season, blockers=["WEEK_AUTHORITY_ACQUISITION_UNAVAILABLE"])
            except Exception:
                week_authority = build_authoritative_week_contract(season=season, blockers=["WEEK_AUTHORITY_ACQUISITION_FAILED"])
            week = week_authority.get("week") if week_authority.get("authoritative") else None
        else:
            week = current_week(cur)
        roster = enrich_players(cur, roster, week, season=season, allow_local_weekly_data=True, allow_local_health_fallback=False, require_automated_weekly_evidence=True)
        metadata = {
            "team_name": "DiE-HaRd-9eRs-FaN",
            "league_name": league.get("name") or "Fantasy Intelligence Champions League",
            "strategy": "LIVE",
            "draft_name": None,
            "season": season,
            "week": week,
            "sleeper_catalog": sleeper_catalog,
            "week_authority": week_authority,
            "faab_balance": league.get("owner_faab_balance"),
            "shared_facts": shared_league_facts(league),
        }
        return (context, roster, metadata, waiver_snapshot) if include_waiver_snapshot else (context, roster, metadata)

    def roster_analysis(roster, vacancies):
        counts = {pos: sum(1 for p in roster if p["position"] == pos) for pos in POSITIONS}
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        needs = []
        grades = {}
        for pos in POSITIONS:
            count = counts[pos]
            target = targets[pos]
            ratio = count / target if target else 1
            grades[pos] = "A" if ratio >= 1 else "B" if ratio >= .75 else "C" if ratio >= .5 else "F"
            if count < target:
                needs.append(f"Add {pos} depth: {count} rostered, target {target}.")
        for slot in vacancies:
            message = f"Fill vacant {slot} starter slot before Week 1."
            if message not in needs:
                needs.insert(0, message)
        injured = [p for p in roster if str(p["injury_status"]).lower() not in {"healthy / not listed", "healthy", "none", ""}]
        if injured:
            needs.append(f"Monitor {len(injured)} player(s) with an injury designation.")
        score = sum(min(counts[p] / targets[p], 1) for p in POSITIONS) / len(POSITIONS) * 100
        overall = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"
        return counts, grades, needs, overall, round(score)

    def waiver_pool_with_evidence(cur, context, roster, limit=40, live_snapshot=None):
        roster_names = {p["player"] for p in roster}
        if context["mode"] == "MOCK":
            cur.execute(
                """
                SELECT p.player_name, UPPER(p.position), p.nfl_team, p.ranking,
                       p.projected_points, p.tier, p.adp, p.bye_week, p.injury_status
                FROM players p
                WHERE UPPER(p.position) IN ('QB','RB','WR','TE','K','DEF')
                  AND NOT EXISTS (
                      SELECT 1 FROM mock_picks mp
                      WHERE mp.draft_id = %s AND mp.player_name = p.player_name
                  )
                ORDER BY p.ranking NULLS LAST
                LIMIT %s
                """,
                (context["draft_id"], limit),
            )
        elif context["mode"] == "LIVE":
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF')
                ORDER BY ranking NULLS LAST
                """
            )
        else:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF')
                ORDER BY ranking NULLS LAST
                LIMIT %s
                """,
                (max(120, (limit or 40) * 3),),
            )
        rows = [row_to_player(tuple(row) + (None, None)) for row in cur.fetchall()]
        if context["mode"] != "LIVE":
            candidates = [{**row, "player_id": normalize_player_name(row["player"])} for row in rows if row["player"] not in roster_names][:limit]
            return evaluate_waiver_availability(
                candidates,
                waiver_evidence_contract(domain="waiver ownership", source="Season Sandbox", freshness_state="BLOCKED", completeness_state="UNKNOWN", blocker="WAIVER_LIVE_OWNERSHIP_REQUIRED"),
                waiver_evidence_contract(domain="waiver eligibility", source="Season Sandbox", freshness_state="BLOCKED", completeness_state="UNKNOWN", blocker="WAIVER_LIVE_ELIGIBILITY_REQUIRED"),
            )
        return _live_waiver_evidence(rows, current_app.config.get("SLEEPER_LEAGUE_ID", ""), get_league, get_rosters, get_all_players, normalize_player_name, limit, snapshot=live_snapshot)

    def _live_waiver_evidence(rows, league_id, league_fetcher, roster_fetcher, catalog_fetcher, name_normalizer, limit=40, snapshot=None):
        retrieved_at = datetime.now(timezone.utc).isoformat()
        if snapshot is not None:
            league = snapshot.get("league")
            all_rosters = snapshot.get("rosters")
            catalog = snapshot.get("catalog")
        else:
            try:
                league = league_fetcher(league_id)
                all_rosters = roster_fetcher(league_id)
                catalog = catalog_fetcher()
            except Exception:
                league = None
                catalog = None
                all_rosters = None
        expected_count = (league or {}).get("total_rosters") if isinstance(league, dict) else None
        coverage = waiver_roster_coverage(all_rosters, expected_count)
        catalog_ok = isinstance(catalog, dict) and bool(catalog)
        rosters_ok = isinstance(all_rosters, list) and all(
            isinstance(item, dict) and isinstance(item.get("players"), list)
            for item in all_rosters or []
        )
        ownership_blocker = None
        if catalog is None or all_rosters is None:
            ownership_blocker = "WAIVER_OWNERSHIP_RETRIEVAL_FAILED"
        elif not catalog_ok:
            ownership_blocker = "WAIVER_PLAYER_CATALOG_UNAVAILABLE"
        elif not rosters_ok:
            ownership_blocker = "WAIVER_ROSTER_DATA_INCOMPLETE"
        elif coverage["blockers"]:
            ownership_blocker = coverage["blockers"][0]
        owned_ids = {
            str(player_id)
            for item in all_rosters or []
            for player_id in item.get("players") or []
            if player_id is not None and str(player_id)
        }
        normalized_catalog_index = build_waiver_catalog_name_index(catalog, name_normalizer)
        resolutions = [
            resolve_waiver_candidate_identity(row, catalog, name_normalizer, normalized_catalog_index)
            for row in rows
        ]
        ownership_freshness = waiver_ownership_freshness(
            source_record_time=None,
            retrieved_at=retrieved_at,
            source="Sleeper API",
        )
        ownership = waiver_evidence_contract(
            domain="waiver ownership",
            league_id=league_id,
            source="Sleeper API",
            source_record_time=None,
            retrieved_at=retrieved_at,
            age=ownership_freshness["age"],
            freshness_threshold_id=ownership_freshness["freshness_threshold_id"],
            freshness_state=ownership_freshness["freshness_state"],
            completeness_state="COMPLETE" if not ownership_blocker else "INCOMPLETE",
            blocker=ownership_blocker or ownership_freshness["blocker"],
            recommendation_impact="BLOCKED",
            expected_active_roster_count=coverage["expected_active_roster_count"],
            observed_active_roster_count=coverage["observed_active_roster_count"],
            unique_owned_player_ids=owned_ids,
            require_roster_coverage=True,
        )
        candidates = []
        for row, resolution in zip(rows, resolutions):
            resolved_player_id = resolution.get("resolved_player_id")
            catalog_record = (catalog or {}).get(str(resolved_player_id)) if resolved_player_id else None
            candidate_health = _waiver_candidate_health(
                catalog_record,
                retrieved_at,
                resolution.get("resolution_state") == "RESOLVED",
            )
            candidates.append({
                **row,
                **candidate_health,
                "player_id": resolved_player_id,
                "opportunity_player_id": (catalog_record or {}).get("gsis_id"),
                "sleeper_espn_id": (catalog_record or {}).get("espn_id"),
                "sleeper_depth_chart_position": (catalog_record or {}).get("depth_chart_position"),
                "sleeper_depth_chart_order": (catalog_record or {}).get("depth_chart_order"),
                "sleeper_news_updated": (catalog_record or {}).get("news_updated"),
                "sleeper_catalog_retrieved_at": (snapshot or {}).get("retrieved_at") or retrieved_at,
                "identity_resolution": resolution,
            })
        nflverse_identity_rows = current_app.config.get("NFLVERSE_PLAYER_METADATA")
        nflverse_identity_lineage = current_app.config.get("NFLVERSE_PLAYER_METADATA_LINEAGE")
        if nflverse_identity_rows is None and not current_app.testing:
            metadata = acquire_nflverse_player_metadata()
            if metadata["state"] == "AVAILABLE":
                nflverse_identity_rows = metadata["rows"]
                nflverse_identity_lineage = metadata["lineage"]
        identity_source = current_app.config.get("DYNASTYPROCESS_IDENTITY_SOURCE")
        needs_supplemental_identity = any(
            not (catalog or {}).get(str(candidate.get("player_id") or ""), {}).get("gsis_id")
            and not (catalog or {}).get(str(candidate.get("player_id") or ""), {}).get("espn_id")
            for candidate in candidates
        )
        if identity_source is None and needs_supplemental_identity and not current_app.testing:
            identity_source = acquire_dynastyprocess_identity_source()
        candidates = attach_waiver_opportunity_identity(
            candidates,
            catalog,
            nflverse_identity_rows,
            nflverse_identity_lineage,
            identity_source=identity_source,
        )
        for candidate in candidates:
            news_identity = resolve_espn_news_identity(candidate, nflverse_identity_rows, nflverse_identity_lineage)
            candidate["espn_news_identity"] = news_identity
            candidate["espn_news_id"] = news_identity.get("espn_id")
        supported_positions = {
            str(position).upper().replace("DST", "DEF")
            for position in (league or {}).get("roster_positions") or []
            if str(position).upper().replace("DST", "DEF") in POSITIONS
        }
        availability = derived_waiver_availability(
            league_id=league_id,
            ownership={**ownership, "owned_player_ids": owned_ids},
            supported_player_ids=(catalog or {}).keys(),
            supported_positions=supported_positions,
            candidates=candidates,
            identity_diagnostics={
                "total_source_candidates": len(candidates),
                "directly_resolved_count": sum(
                    item["resolution_method"] == "DIRECT_SLEEPER_ID" for item in resolutions
                ),
                "uniquely_canonical_resolved_count": sum(
                    item["resolution_method"] == "UNIQUE_CANONICAL_MATCH" for item in resolutions
                ),
                "unresolved_count": sum(item["resolution_state"] == "UNRESOLVED" for item in resolutions),
                "ambiguous_count": sum(item["resolution_state"] == "AMBIGUOUS" for item in resolutions),
                "conflicting_count": sum(item["resolution_state"] == "CONFLICTING" for item in resolutions),
                "unsupported_count": sum(item["resolution_state"] == "UNSUPPORTED" for item in resolutions),
            },
        )
        result = evaluate_waiver_availability(
            candidates,
            {**ownership, "owned_player_ids": owned_ids},
            availability,
        )
        result["resolved_roster_production_ids"] = {
            str(candidate["player_id"]): candidate["opportunity_player_id"]
            for candidate in candidates
            if candidate.get("player_id") in owned_ids
            and candidate.get("opportunity_identity_state") == "RESOLVED"
            and candidate.get("opportunity_player_id")
        }
        result["resolved_roster_espn_ids"] = {
            str(candidate["player_id"]): candidate["espn_news_id"]
            for candidate in candidates
            if candidate.get("player_id") in owned_ids
            and candidate.get("opportunity_identity_state") == "RESOLVED"
            and candidate.get("espn_news_id")
        }
        result["candidates"] = result["candidates"][:limit]
        decision_evidence = weekly_evidence_contract(
            domain="waiver ranking inputs", source=None, freshness_state="UNAVAILABLE", completeness_state="UNAVAILABLE",
            blocker="WAIVER_RANKING_SOURCE_UNVERIFIED", fallback_used="local player projections/rankings",
            recommendation_impact="Waiver candidates use locally supplied projections/rankings; automated ranking source is unverified.",
        )
        result["decision_evidence"] = decision_evidence
        if not decision_evidence["authoritative"]:
            # Ownership and eligibility are already fail-closed above (see
            # evaluate_waiver_availability). Ranking source is informational:
            # surface it as a visible warning instead of re-blocking
            # already-verified, fresh, complete waiver candidates.
            result["warnings"] = list(dict.fromkeys([*(result.get("warnings") or []), decision_evidence["blocker"]]))
            result["ranking_confidence"] = "UNVERIFIED"
        else:
            result["ranking_confidence"] = "VERIFIED"
        availability["identity_diagnostics"].update(
            rostered_exclusion_count=sum(
                item.get("resolved_player_id") in owned_ids
                for item in resolutions
                if item.get("resolved_player_id")
            ),
            verified_unrostered_count=len(result["candidates"]),
            published_count=len(result["candidates"]),
        )
        return result

    def waiver_pool(cur, context, roster, limit=40):
        return waiver_pool_with_evidence(cur, context, roster, limit)["candidates"]

    def faab_recommendations(pool, counts):
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        recs = []
        for player in pool:
            need = max(0, targets.get(player["position"], 1) - counts.get(player["position"], 0))
            rank_value = max(0, 110 - (player["rank"] or 110))
            tier_value = max(0, 7 - (player["tier"] or 7)) * 5
            score = rank_value + tier_value + need * 20
            bid = max(0, min(35, round(score / 6)))
            if player["position"] in {"K", "DEF"}:
                bid = min(bid, 3)
            projection_info = waiver_projection_contribution(player)
            projection_contribution = projection_info["value"]
            recs.append({**player, "priority_score": round(score, 1), "faab": bid, "bid_low": max(0, bid - 3), "bid_high": min(40, bid + 4), "need": need, "projection_contribution": projection_contribution, "projection_contribution_state": projection_info["state"], "projection_warnings": projection_info["warnings"]})
        return sorted(recs, key=lambda p: (-p["priority_score"], -(p["projection_contribution"] if p["projection_contribution"] is not None else float("-inf")), p["rank"] or 9999))

    def other_mock_teams(cur, draft_id):
        cur.execute(
            """
            SELECT DISTINCT draft_slot, team_name
            FROM mock_picks
            WHERE draft_id = %s
            ORDER BY draft_slot
            """,
            (draft_id,),
        )
        return [{"slot": row[0], "name": row[1]} for row in cur.fetchall()]

    @bp.route("/team")
    def team_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur, verify_live_week=True)
            preliminary_matchup_context = build_preliminary_matchup_context(
                current_app.config.get("PRELIMINARY_MATCHUP_EVIDENCE"),
                roster=roster,
            )
            opportunity_view = build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE"))
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, _, overall, score = roster_analysis(roster, vacancies)
            league_payload = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or {} if context["mode"] == "LIVE" else {}
            league_settings = league_settings_contract(league_payload, source="Sleeper API" if context["mode"] == "LIVE" else "Season Sandbox", blocker=None if context["mode"] == "LIVE" else "LIVE_LEAGUE_SETTINGS_NOT_APPLICABLE")
            team_needs = team_needs_contract(roster, league_settings)
            needs = build_team_needs_summary(team_needs)
            if context["mode"] == "LIVE":
                fetched_at = next((player.get("health_fetched_at") for player in roster if player.get("health_fetched_at")), None)
                if fetched_at and any(player.get("health_status_available") for player in roster):
                    health_meta = health_freshness_from_report_date(fetched_at)
                    health_source = "Sleeper API"
                else:
                    health_meta = {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}
                    health_source = "Sleeper API"
            else:
                health_meta = {"freshness_state": "UNAVAILABLE", "last_verified": None, "age": None}
                health_source = "Season Sandbox"
            team_health = team_health_contract(roster, source=health_source, **health_meta)
            team_accuracy = build_team_accuracy_contract(roster, starters, league_settings, team_needs, team_health)
            nflverse_records = current_app.config.get("NFLVERSE_PLAYER_METADATA")
            nflverse_lineage = current_app.config.get("NFLVERSE_PLAYER_METADATA_LINEAGE")
            if nflverse_records is None and not current_app.testing:
                metadata = acquire_nflverse_player_metadata()
                if metadata["state"] == "AVAILABLE":
                    nflverse_records = metadata["rows"]
                    nflverse_lineage = metadata["lineage"]
            opportunity_changes = build_team_opportunity_changes(
                conn,
                roster,
                season=meta.get("season"),
                week=meta.get("week"),
                nflverse_records=nflverse_records,
                nflverse_lineage=nflverse_lineage,
                sleeper_records=meta.get("sleeper_catalog"),
            )
        finally:
            cur.close(); conn.close()
        weekly_defaults = {
            "weekly_baseline": 0.0, "matchup_modifier": 0.0,
            "injury_multiplier": 1.0, "weekly_score": None,
            "is_bye": False, "bye_week": None, "opponent": None,
            "home_away": None, "game_time_pacific": None,
            "matchup_rank": None, "injury_status": "Unknown", "vacant": False,
        }
        for player in [*starters, *bench]:
            for key, value in weekly_defaults.items(): player.setdefault(key, value)
        health_source = team_health.get("source") or ("Sleeper" if context["mode"] == "LIVE" else "Season Sandbox")
        health_freshness = team_health.get("freshness_state") or "UNAVAILABLE"
        apply_player_health_to_recommendations(
            starters,
            source=health_source,
            freshness_state=health_freshness,
            blocker=(team_health.get("blocker") if team_health.get("state") == "BLOCKED" else None),
        )
        for player in [*starters, *bench]:
            player["weekly_value_state"] = "AVAILABLE" if player.get("weekly_score") is not None else "UNAVAILABLE"
            gaps = player.get("evidence_gaps") or []
            player["health_shared_only"] = team_health.get("state") != "AVAILABLE" and not any(
                gap not in {"HEALTH_UNAVAILABLE", "HEALTH_BLOCKED", "HEALTH_EVIDENCE_STALE", "HEALTH_REFRESH_FAILED", "TEAM_HEALTH_UNAVAILABLE", "TEAM_HEALTH_STALE"}
                for gap in gaps
            )
        current_sleeper_starters = [player for player in roster if player.get("sleeper_current_starter")]
        team_priority_action = build_team_priority_action(starters, team_needs, team_health, team_accuracy, current_starters=current_sleeper_starters)
        team_accuracy["recommendation_impact"] = team_priority_action["action"]
        team_trust = build_team_trust_summary(team_accuracy, team_health, starters, bench)
        bench_decisions = build_bench_decisions(starters, bench)
        bench_plan = build_bench_plan(bench_decisions)
        weekly_risks = build_weekly_risks(starters, team_needs, team_health, team_accuracy, current_starters=current_sleeper_starters)
        roster_outlook = build_roster_outlook(team_needs, team_health)
        lineup_intelligence = build_lineup_intelligence(roster, current_starters=current_sleeper_starters)
        decisions_by_slot = {d.get("slot"): d for d in lineup_intelligence.get("start_sit_decisions", [])}
        lineup_reconciliation = build_lineup_reconciliation(roster, lineup_intelligence.get("starters"), lineup_intelligence.get("start_sit_decisions"))
        displayed_bench = build_recommended_bench(roster, lineup_intelligence.get("starters"))
        if displayed_bench is not None:
            lineup_intelligence["bench"] = displayed_bench
        lineup_intelligence["changed_recommended"] = lineup_reconciliation.get("changed_recommended", [])
        if lineup_reconciliation.get("changes"):
            lineup_intelligence["verdict"].update(status="ACTION REQUIRED", action=f"{len(lineup_reconciliation['changes'])} lineup changes recommended", why="Review the supported lineup changes before lineup lock.")
        lineup_snapshot = build_lineup_snapshot(starters, bench_decisions, current_starters=current_sleeper_starters, lineup_changes=lineup_reconciliation.get("changes"))
        lineup_intelligence["starters"] = attach_preliminary_matchup_display(lineup_intelligence.get("starters"))
        if context["mode"] == "LIVE" and lineup_reconciliation.get("changes"):
            provider_projections = build_changed_slot_projections(
                roster,
                lineup_reconciliation["changes"],
                season=meta.get("season"),
                week=meta.get("week"),
            )
            for change in lineup_reconciliation["changes"]:
                change["provider_projection"] = provider_projections.get(change.get("slot"), {})
        return render_template("team.html", title="My Team", context=context, roster=roster, meta=meta, starters=starters, bench=bench, total=total, vacancies=vacancies, counts=counts, grades=grades, needs=needs, overall=overall, roster_score=score, league_settings=league_settings, team_needs=team_needs, team_health=team_health, team_accuracy=team_accuracy, team_priority_action=team_priority_action, team_trust=team_trust, bench_decisions=bench_decisions, bench_plan=bench_plan, lineup_snapshot=lineup_snapshot, weekly_risks=weekly_risks, roster_outlook=roster_outlook, lineup_intelligence=lineup_intelligence, decisions_by_slot=decisions_by_slot, preliminary_matchup_context=preliminary_matchup_context, opportunity_view=opportunity_view, opportunity_changes=opportunity_changes, lineup_reconciliation=lineup_reconciliation)

    @bp.route("/lineup")
    def lineup_page():
        return redirect(url_for("owner_ops.team_page") + "#lineup", code=302)

    @bp.route("/waivers")
    @bp.route("/waivers", methods=["GET", "POST"])
    def waivers_page():
        rankings_path = current_app.instance_path + "/dynastyprocess-rankings.json"
        requested_selected_player_id = request.args.get("player_id")
        selected_focus = request.args.get("focus", "all")
        if selected_focus not in {"all", "this_week", "rest_of_season"}:
            selected_focus = "all"
        if request.method == "POST":
            try:
                nfl_state = get_nfl_state()
            except Exception:
                nfl_state = {}
            refresh_rankings(rankings_path, nfl_state, force=True)
            return redirect(url_for("owner_ops.waivers_page"))
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta, waiver_snapshot = current_roster(cur, include_waiver_snapshot=True)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool_evidence = waiver_pool_with_evidence(cur, context, roster, limit=None, live_snapshot=waiver_snapshot)
            ranking_confidence = pool_evidence.get("ranking_confidence", "UNVERIFIED")
            source_candidates = []
            for candidate in pool_evidence.get("candidates") or []:
                item = dict(candidate)
                item["ownership_state"] = "VERIFIED" if pool_evidence.get("allowed") else "UNAVAILABLE"
                item["eligibility_state"] = "VERIFIED" if pool_evidence.get("allowed") else "UNAVAILABLE"
                item["candidate_publication_state"] = "PUBLISHED" if pool_evidence.get("allowed") else "BLOCKED"
                source_candidates.append(item)
            league_payload = ((waiver_snapshot or {}).get("league") or {}) if context["mode"] == "LIVE" else {}
            league_settings = league_settings_contract(league_payload, source="Sleeper API" if context["mode"] == "LIVE" else "Season Sandbox", blocker=None if context["mode"] == "LIVE" else "LIVE_LEAGUE_SETTINGS_NOT_APPLICABLE")
            team_needs = team_needs_contract(roster, league_settings)
            for player in roster:
                player_id = str(player.get("source_player_id") or player.get("player_id") or "")
                resolved_production_id = (pool_evidence.get("resolved_roster_production_ids") or {}).get(player_id)
                if resolved_production_id:
                    player["opportunity_player_id"] = resolved_production_id
                    player["opportunity_identity_state"] = "RESOLVED"
                    player["opportunity_identity_method"] = "WAIVER_ROSTER_IDENTITY_CROSSWALK"
                else:
                    player["opportunity_identity_state"] = "UNRESOLVED"
                resolved_espn_id = (pool_evidence.get("resolved_roster_espn_ids") or {}).get(player_id)
                if resolved_espn_id and not player.get("sleeper_espn_id"):
                    player["sleeper_espn_id"] = resolved_espn_id
                    player["sleeper_espn_identity_method"] = "NFLVERSE_UNIQUE_GSIS_ESPN_CROSSWALK"
                player["opportunity_metrics"] = waiver_opportunity_metrics(conn, player, meta.get("season"))
                player["recent_production"] = waiver_recent_production(
                    conn, player, meta.get("season"), reader_result=player["opportunity_metrics"],
                )
                player["snap_share"] = waiver_snap_share(conn, player, meta.get("season"))
                player["player_comparison"] = waiver_player_comparison(player)
            actionable_candidates = []
            preliminary_suggestions = []
            monitor_candidates = []
            health_excluded_count = 0
            health_excluded_reasons = {}
            health_source_states = {}
            for candidate in source_candidates:
                candidate["opportunity_metrics"] = waiver_opportunity_metrics(conn, candidate, meta.get("season"))
                candidate["recent_production"] = waiver_recent_production(
                    conn, candidate, meta.get("season"), reader_result=candidate["opportunity_metrics"],
                )
                candidate["snap_share"] = waiver_snap_share(conn, candidate, meta.get("season"))
                candidate["evidence_context"] = waiver_candidate_context(candidate, roster, team_needs, ranking_confidence)
                candidate.update(waiver_candidate_recommendation_state(candidate, ranking_confidence))
                if candidate["candidate_disposition"] == "HEALTH_BLOCKED":
                    health_excluded_count += 1
                    for reason in candidate.get("recommendation_blockers") or ["WAIVER_HEALTH_UNVERIFIED"]:
                        health_excluded_reasons[reason] = health_excluded_reasons.get(reason, 0) + 1
                    freshness = candidate.get("health_freshness_state") or "UNAVAILABLE"
                    source = candidate.get("injury_source") or "UNAVAILABLE"
                    source_freshness = f"{source} / {freshness}"
                    health_source_states[source_freshness] = health_source_states.get(source_freshness, 0) + 1
                    continue
                if candidate["candidate_disposition"] == "MONITOR":
                    candidate.update(rank=None, priority_score=None, tier=None, faab=None, bid_low=None, bid_high=None)
                    candidate["faab_state"] = "UNAVAILABLE"
                    monitor_candidates.append(candidate)
                    continue
                candidate["recommendation_state"] = "PRELIMINARY_SUGGESTION"
                candidate.update(rank=None, priority_score=None, tier=None, faab=None, bid_low=None, bid_high=None)
                candidate["faab_state"] = "UNAVAILABLE"
                if ranking_confidence != "VERIFIED":
                    candidate["faab_blockers"] = ["WAIVER_RANKING_SOURCE_UNVERIFIED"]
                candidate["preliminary_review_order"] = len(preliminary_suggestions) + 1
                preliminary_suggestions.append(candidate)
            recommendations = faab_recommendations(actionable_candidates, counts)[:25] if actionable_candidates else []
            pool_evidence["health_excluded_diagnostics"] = {
                "excluded_count": health_excluded_count,
                "reason_counts": health_excluded_reasons,
                "source_freshness_counts": health_source_states,
            }
            display_candidates = [*recommendations, *preliminary_suggestions, *monitor_candidates]
            for candidate in display_candidates:
                candidate["evidence_context"] = waiver_candidate_context(candidate, roster, team_needs, pool_evidence.get("ranking_confidence"))
                candidate["player_comparison"] = waiver_player_comparison(candidate)
            opportunity_rows = [
                row
                for candidate in display_candidates
                for row in ((candidate.get("opportunity_metrics") or {}).get("rows") or [])
            ]
            fresh_opportunity_count = sum(
                (candidate.get("opportunity_metrics") or {}).get("state") == "AVAILABLE"
                and any(row.get("freshness_state") in {"FRESH", "AGING"} for row in ((candidate.get("opportunity_metrics") or {}).get("rows") or []))
                for candidate in display_candidates
            )
            stale_opportunity_rows = [row for row in opportunity_rows if row.get("freshness_state") == "STALE"]
            if fresh_opportunity_count:
                waiver_opportunity_status = {
                    "state": "PRELIMINARY",
                    "impact": "Current published opportunity evidence is available for research only; it does not authorize ranking, FAAB, or ADD/DROP conclusions.",
                    "candidate_count": fresh_opportunity_count,
                }
            elif stale_opportunity_rows:
                waiver_opportunity_status = {
                    "state": "STALE",
                    "impact": "Published opportunity evidence is stale and is not presented as current.",
                    "blocker": "OPPORTUNITY_DATA_STALE",
                }
            else:
                waiver_opportunity_status = {
                    "state": "UNAVAILABLE",
                    "impact": "No current candidate-linked published opportunity row is available for this cohort.",
                    "blocker": next((blocker for candidate in display_candidates for blocker in ((candidate.get("opportunity_metrics") or {}).get("blockers") or [])), "OPPORTUNITY_READER_NO_ROWS"),
                }
        finally:
            cur.close(); conn.close()
        # row_to_player collapses a missing projected_points value to 0.0; treat 0 as
        # "no supported projection" here so the assistant never fabricates an upgrade signal.
        trending_evidence = waiver_trending_evidence(context.get("mode"))
        wda_roster = [{
            "player_id": str(player.get("source_player_id") or player.get("player_id") or ""),
            "player": player.get("player"),
            "position": player.get("position"),
            "team": player.get("nfl_team"),
            "identity_state": player.get("identity_state"),
            "espn_id": player.get("sleeper_espn_id"),
            "espn_news_identity": {"state": "RESOLVED" if player.get("sleeper_espn_id") else "UNAVAILABLE", "method": player.get("sleeper_espn_identity_method") or ("SLEEPER_CATALOG_ESPN_ID" if player.get("sleeper_espn_id") else None)},
            "depth_chart_position": player.get("sleeper_depth_chart_position"),
            "depth_chart_order": player.get("sleeper_depth_chart_order"),
            "news_updated": player.get("sleeper_news_updated"),
            "catalog_retrieved_at": player.get("sleeper_metadata_retrieved_at"),
            "projection": wda_projection_or_none(player.get("projection")),
            "projection_retrieved_at": player.get("projection_retrieved_at"),
            "trending": wda_trending_state(player.get("source_player_id"), trending_evidence),
            "recent_production": player.get("recent_production", {"state": "UNAVAILABLE", "rows": []}),
            "opportunity_metrics": player.get("opportunity_metrics", {"state": "UNAVAILABLE", "rows": []}),
            "snap_share": player.get("snap_share", {"state": "UNAVAILABLE", "rows": []}),
            "player_comparison": player.get("player_comparison", {}),
            "is_starter": player.get("sleeper_current_starter"),
            "lineup_slot": player.get("sleeper_lineup_slot"),
            "health_state": _waiver_health_state(player.get("injury_status")) if player.get("health_status_available") is True and player.get("injury_source") == "Sleeper API" else None,
            "health_freshness_state": health_freshness_from_report_date(player.get("health_fetched_at"))["freshness_state"] if player.get("health_status_available") is True else "UNAVAILABLE",
        } for player in roster if player.get("source_player_id") or player.get("player_id")]
        move_checker_candidates = [candidate for candidate in preliminary_suggestions if candidate.get("candidate_disposition") == "PRELIMINARY_SUGGESTION"]
        wda_candidates = [{
            "player_id": str(candidate.get("player_id") or ""),
            "player": candidate.get("player"),
            "position": candidate.get("position"),
            "team": candidate.get("nfl_team"),
            "identity_resolution": candidate.get("identity_resolution", {}),
            "espn_id": candidate.get("espn_news_id") or candidate.get("sleeper_espn_id"),
            "espn_news_identity": candidate.get("espn_news_identity") or {"state": "UNAVAILABLE", "method": None},
            "depth_chart_position": candidate.get("sleeper_depth_chart_position"),
            "depth_chart_order": candidate.get("sleeper_depth_chart_order"),
            "catalog_retrieved_at": candidate.get("sleeper_catalog_retrieved_at"),
            "sleeper_news_updated": candidate.get("sleeper_news_updated"),
            "flex_eligible_positions": list(league_settings.get("flex_eligible_positions") or []),
            "projection": wda_projection_or_none(candidate.get("projection")),
            "projection_retrieved_at": candidate.get("projection_retrieved_at"),
            "need": candidate.get("need"),
            "recommendation_state": candidate.get("recommendation_state"),
            "candidate_disposition": candidate.get("candidate_disposition"),
            "recommendation_blockers": candidate.get("recommendation_blockers", []),
            "trending": wda_trending_state(candidate.get("player_id"), trending_evidence),
            "recent_production": candidate.get("recent_production", {"state": "UNAVAILABLE", "rows": []}),
            "opportunity_metrics": candidate.get("opportunity_metrics", {"state": "UNAVAILABLE", "rows": []}),
            "snap_share": candidate.get("snap_share", {"state": "UNAVAILABLE", "rows": []}),
            "player_comparison": candidate.get("player_comparison", {}),
            "evidence_context": candidate.get("evidence_context", {}),
        } for candidate in move_checker_candidates]
        for candidate in wda_candidates:
            candidate["roster_comparisons"] = {
                player["player_id"]: waiver_roster_comparison(candidate, player)
                for player in wda_roster if player.get("position") == candidate.get("position")
            }
            candidate["roster_guidance"] = {}
            for player in wda_roster:
                if player.get("position") != candidate.get("position"):
                    continue
                guidance = waiver_move_guidance(candidate, player)
                guidance["provisional_bid"] = waiver_provisional_bid(guidance, meta.get("faab_balance") or {}, player.get("is_starter"))
                candidate["roster_guidance"][player["player_id"]] = guidance
            starter_reviews = [
                player for player in wda_roster
                if player.get("position") == candidate.get("position")
                and player.get("is_starter") is True
                and candidate["roster_guidance"][player["player_id"]]["this_week"]["action"] == "REVIEW_ADD"
            ]
            starter_reviews.sort(key=lambda player: (
                player.get("health_state") in {"OUT", "IR"} and player.get("health_freshness_state") == "FRESH",
                candidate["roster_guidance"][player["player_id"]]["comparison"].get("difference") or 0,
            ), reverse=True)
            for player in wda_roster:
                guidance = candidate["roster_guidance"].get(player["player_id"])
                if not guidance:
                    continue
                baseline = player if player.get("is_starter") is True else starter_reviews[0] if starter_reviews else None
                if baseline:
                    starter_guidance = candidate["roster_guidance"][baseline["player_id"]]
                    guidance["this_week"] = dict(starter_guidance["this_week"])
                    guidance["weekly_comparison"] = starter_guidance["comparison"]
                    guidance["weekly_baseline_player"] = baseline["player"]
                    guidance["lineup_scope"] = f"Current starter comparison against {baseline['player']}"
                    if player.get("is_starter") is False and guidance["this_week"]["action"] == "REVIEW_ADD":
                        guidance["drop_review"] = f"Consider {player['player']} as a bench-drop option only if a roster slot is needed; verify role and bye-week coverage before dropping."
                guidance["provisional_bid"] = waiver_provisional_bid(guidance, meta.get("faab_balance") or {}, True if baseline and guidance["this_week"]["action"] == "REVIEW_ADD" else player.get("is_starter"))
        rankings = current_app.config.get("DYNASTYPROCESS_RANKINGS")
        if rankings is None and not current_app.testing and context.get("mode") == "LIVE":
            try:
                nfl_state = get_nfl_state()
            except Exception:
                nfl_state = {}
            rankings = read_cached_rankings(rankings_path, nfl_state, sleeper_catalog=meta.get("sleeper_catalog"))
            if rankings.get("cache_missing"):
                rankings = refresh_rankings(rankings_path, nfl_state, sleeper_catalog=meta.get("sleeper_catalog"))
        rankings = rankings or {"source": "FantasyPros consensus via DynastyProcess", "horizons": {}, "refresh_error": "Current ranking evidence is unavailable."}
        for candidate in wda_candidates:
            candidate["source_rankings"] = {horizon: (rankings.get("horizons", {}).get(horizon, {}).get("ranks", {}) or {}).get(candidate["player_id"]) for horizon in ("this_week", "rest_of_season")}
            preferred_player = next((player for player in wda_roster if player.get("position") == candidate.get("position") and player.get("is_starter") is True), None)
            if preferred_player is None:
                preferred_player = next((player for player in wda_roster if player.get("position") == candidate.get("position")), None)
            selected_guidance = candidate["roster_guidance"].get(preferred_player["player_id"], {}) if preferred_player else {}
            candidate["acquisition_evaluation"] = waiver_acquisition_evaluation(
                candidate, team_needs, league_settings, selected_guidance, meta.get("faab_balance") or {},
            )
        candidate_evaluations = {candidate["player_id"]: candidate["acquisition_evaluation"] for candidate in wda_candidates}
        for candidate in preliminary_suggestions:
            candidate["acquisition_evaluation"] = candidate_evaluations.get(str(candidate.get("player_id")))
        wda_candidates.sort(key=lambda candidate: (candidate["acquisition_evaluation"]["sort_group"], candidate.get("player") or "", candidate["player_id"]))
        preliminary_suggestions.sort(key=lambda candidate: ((candidate.get("acquisition_evaluation") or {}).get("sort_group", 3), candidate.get("player") or "", str(candidate.get("player_id") or "")))
        default_position = next((candidate.get("position") for candidate in preliminary_suggestions if candidate.get("position")), None)
        selected_player = next((player for player in wda_roster if requested_selected_player_id and player.get("player_id") == str(requested_selected_player_id)), None)
        if not requested_selected_player_id:
            selected_player = next((player for player in wda_roster if player.get("position") == default_position), None) or next(iter(wda_roster), None)
        selected_player_id = selected_player.get("player_id") if selected_player else None
        selected_context = {
            "player_id": selected_player_id or requested_selected_player_id,
            "player": selected_player.get("player") if selected_player else None,
            "position": selected_player.get("position") if selected_player else None,
            "focus": selected_focus,
            "is_starter": selected_player.get("is_starter") if selected_player else None,
            "lineup_slot": selected_player.get("lineup_slot") if selected_player else None,
            "valid": selected_player is not None,
        }
        pagewide_news_candidates = [
            candidate for candidate in preliminary_suggestions
            if (candidate.get("acquisition_evaluation") or {}).get("evidence_relevance") in {"MEANINGFUL_COMPARISON", "DIRECTIONAL_SIGNAL"}
            and (candidate.get("acquisition_evaluation") or {}).get("action") in {"ADD", "CONSIDER", "STASH", "MONITOR"}
        ][:3]
        def sleeper_depth_context(player):
            depth_position = player.get("depth_chart_position") or player.get("sleeper_depth_chart_position")
            depth_order = player.get("depth_chart_order") or player.get("sleeper_depth_chart_order")
            available = depth_position not in (None, "") or isinstance(depth_order, int) and not isinstance(depth_order, bool)
            return {
                "state": "AVAILABLE" if available else "UNAVAILABLE",
                "position": depth_position,
                "order": depth_order if isinstance(depth_order, int) and not isinstance(depth_order, bool) else None,
                "team": player.get("team") or player.get("nfl_team"),
                "source": "Sleeper player catalog",
                "retrieved_at": player.get("catalog_retrieved_at") or player.get("sleeper_catalog_retrieved_at") or player.get("sleeper_metadata_retrieved_at"),
                "authority_state": "SCREENING_ONLY",
                "decision_effect": "SCREENING_ONLY",
                "reason": "Current catalog depth-chart listing; not an expected-role or duration claim." if available else "Sleeper depth-chart fields are unavailable for this player.",
            }
        selected_comparisons = []
        if selected_player:
            selected_comparison_player = {**selected_player, "sleeper_current_starter": selected_player.get("is_starter")}
            relevant_candidates = []
            flex_positions = league_settings.get("flex_eligible_positions") or []
            selected_position = str(selected_player.get("position") or "").upper().replace("DST", "DEF")
            selected_slot = str(selected_player.get("lineup_slot") or "").upper()
            flex_need = dict(team_needs.get("FLEX") or {})
            flex_slots = int((league_settings.get("starter_slots") or {}).get("FLEX") or flex_need.get("required_slots") or flex_need.get("starter_shortage") or 0)
            selected_flex_role = selected_slot in {"FLEX", "W/R/T", "WR/RB/TE", "WRRB_FLEX", "REC_FLEX"} or (selected_player.get("is_starter") is False and flex_slots > 0)
            relevant_candidates = [
                candidate for candidate in wda_candidates
                if candidate.get("position") == selected_position
                or (candidate.get("position") in flex_positions and selected_position in flex_positions and flex_need.get("state") == "AVAILABLE" and flex_slots > 0 and selected_flex_role)
            ]
            espn_ids = [selected_player.get("espn_id"), *(candidate.get("espn_id") for candidate in relevant_candidates), *(candidate.get("espn_news_id") or candidate.get("sleeper_espn_id") for candidate in pagewide_news_candidates)]
            news_feed = read_espn_nfl_news() if any(espn_ids) else None
            selected_comparison_player["sleeper_depth_chart"] = sleeper_depth_context(selected_player)
            selected_comparison_player["player_news"] = news_for_espn_player(news_feed, selected_player.get("espn_id"))
            selected_comparison_player["player_news"]["identity_method"] = (selected_player.get("espn_news_identity") or {}).get("method") or ("SLEEPER_CATALOG_ESPN_ID" if selected_player.get("espn_id") else None)
            selected_context["depth_chart"] = selected_comparison_player["sleeper_depth_chart"]
            selected_context["news"] = selected_comparison_player["player_news"]
            wda_candidate_by_id = {candidate.get("player_id"): candidate for candidate in wda_candidates}
            for pagewide_candidate in pagewide_news_candidates:
                pagewide_candidate["sleeper_depth_chart"] = sleeper_depth_context(pagewide_candidate)
                pagewide_candidate["player_news"] = news_for_espn_player(news_feed, pagewide_candidate.get("espn_news_id") or pagewide_candidate.get("sleeper_espn_id"))
                pagewide_candidate["player_news"]["identity_method"] = (pagewide_candidate.get("espn_news_identity") or {}).get("method")
                client_candidate = wda_candidate_by_id.get(str(pagewide_candidate.get("player_id") or ""))
                if client_candidate is not None:
                    client_candidate["sleeper_depth_chart"] = pagewide_candidate["sleeper_depth_chart"]
                    client_candidate["player_news"] = pagewide_candidate["player_news"]
            for candidate in relevant_candidates:
                candidate["sleeper_depth_chart"] = sleeper_depth_context(candidate)
                candidate["player_news"] = news_for_espn_player(news_feed, candidate.get("espn_id"))
                candidate["player_news"]["identity_method"] = (candidate.get("espn_news_identity") or {}).get("method")
                candidate["selected_comparison"] = waiver_selected_player_comparison(
                    selected_comparison_player,
                    candidate,
                    team_needs,
                    league_settings,
                    meta.get("faab_balance") or {},
                    roster_coverage_complete=pool_evidence.get("allowed") is True,
                    roster=roster,
                    season=meta.get("season"),
                    focus=selected_focus,
                )
            decision_order = {"ADD": 0, "MONITOR": 1, "HOLD": 2, "BLOCKED": 3, "NO_ACTIONABLE_UPGRADE": 4}
            relevant_candidates.sort(key=lambda candidate: (
                decision_order.get((candidate.get("selected_comparison") or {}).get("decision"), 5),
                -float((candidate.get("selected_comparison") or {}).get("comparison_summary", {}).get("difference") or 0),
                -int((candidate.get("selected_comparison") or {}).get("comparison_summary", {}).get("sample_size") or 0),
                candidate.get("player") or "",
                candidate.get("player_id") or "",
            ))
            selected_comparisons = [
                candidate for candidate in relevant_candidates
                if (candidate.get("selected_comparison") or {}).get("decision") in {"ADD", "HOLD", "MONITOR"}
                and (candidate.get("selected_comparison") or {}).get("relevance_class") in {"MEANINGFUL_COMPARISON", "DIRECTIONAL_SIGNAL"}
            ][:5]
        screened_reason_counts = {}
        selected_comparison_ids = {candidate.get("player_id") for candidate in selected_comparisons}
        relevant_ids = {candidate.get("player_id") for candidate in relevant_candidates} if selected_player else set()
        for candidate in wda_candidates:
            evaluation = candidate.get("selected_comparison") or {}
            if candidate.get("player_id") in selected_comparison_ids:
                continue
            if evaluation.get("decision") == "BLOCKED":
                reason = "identity or ownership blocked"
            elif any("STALE" in str(blocker) or "EXPIRED" in str(blocker) for blocker in evaluation.get("blockers") or []) or (candidate.get("recent_production") or {}).get("state") in {"STALE", "BLOCKED"}:
                reason = "stale evidence"
            elif evaluation.get("relevance_class") == "SCREENING_ONLY":
                reason = "screening evidence only"
            elif candidate.get("player_id") not in relevant_ids:
                reason = "cross-position comparison unsupported for selected role"
            else:
                reason = "no current production comparison or directional opportunity signal"
            screened_reason_counts[reason] = screened_reason_counts.get(reason, 0) + 1
        selected_screened_summary = {
            "count": len(wda_candidates) - len(selected_comparisons),
            "reason_counts": screened_reason_counts,
        }
        if selected_comparisons:
            selected_result = selected_comparisons[0]["selected_comparison"]
        else:
            selected_blockers = list(pool_evidence.get("blockers") or []) if not pool_evidence.get("allowed") else []
            if requested_selected_player_id and not selected_player:
                selected_blockers.append("SELECTED_ROSTER_PLAYER_ID_NOT_FOUND")
            no_safe_move = bool(selected_blockers)
            selected_result = {
                "schema_version": "selected-waiver-comparison.v1",
                "selected_player_id": selected_context["player_id"],
                "selected_player": selected_context["player"],
                "selected_position": selected_context["position"],
                "candidate_id": None,
                "candidate": None,
                "decision": "BLOCKED" if no_safe_move else "NO_ACTIONABLE_UPGRADE",
                "evidence_level": "INSUFFICIENT",
                "roster_effect": "Evaluation is blocked by safety evidence." if no_safe_move else "No available player has enough current candidate-specific evidence to support an upgrade over the selected player.",
                "comparison_summary": {"state": "BLOCKED" if no_safe_move else "UNAVAILABLE", "reason": "Safety-critical identity, ownership, eligibility, or roster evidence is blocked." if no_safe_move else "No candidate clears the selected-player relevance gate."},
                "reasons": ["No eligible comparison candidate is available for this selected roster player."] if no_safe_move else ["Available candidates have screening-only or insufficient evidence; none distinguishes a supported upgrade."],
                "concerns": ["Identity, ownership, eligibility, or roster coverage evidence may be incomplete."],
                "suggested_drop": {"state": "UNAVAILABLE", "player_id": None, "player": None, "reason": "No selected-player drop is supported."},
                "depth_chart_context": {"selected_player": selected_context.get("depth_chart") or {"state": "UNAVAILABLE"}, "candidate": {"state": "UNAVAILABLE"}, "decision_effect": "SCREENING_ONLY"},
                "news_context": {"selected_player": selected_context.get("news") or {"state": "UNAVAILABLE", "articles": []}, "candidate": {"state": "UNAVAILABLE", "articles": []}, "freshness_state": "UNVERIFIED", "decision_effect": "INFORMATIONAL_ONLY"},
                "faab": {"state": "NO_BID", "low": 0, "high": 0, "category": "NONE", "rationale": "No bid is suggested for NO_ACTIONABLE_UPGRADE."},
                "confidence_rationale": "Safety evidence prevents comparison." if no_safe_move else "Eligibility and availability may be supported, but no candidate-specific value signal clears the relevance gate.",
                "missing_evidence": ["fresh overlapping Full-PPR production", "position-relevant directional opportunity evidence"],
                "blockers": selected_blockers if no_safe_move else [],
            }
        return render_template("waivers.html", title="Waiver and FAAB Center", context=context, meta=meta, recommendations=recommendations, preliminary_suggestions=preliminary_suggestions, monitor_candidates=monitor_candidates, health_excluded_diagnostics=pool_evidence["health_excluded_diagnostics"], waiver_opportunity_status=waiver_opportunity_status, needs=needs, vacancies=vacancies, faab_budget=(meta.get("faab_balance") or {}).get("remaining"), faab_balance=meta.get("faab_balance") or {}, ranking_source=rankings, waiver_evidence=pool_evidence, opportunity_view=build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE")), roster=roster, grades=grades, counts=counts, wda_roster=wda_roster, wda_candidates=selected_comparisons, selected_player=selected_context, selected_focus=selected_focus, selected_result=selected_result, selected_comparisons=selected_comparisons, selected_screened_summary=selected_screened_summary, trending_evidence_state=trending_evidence.get("state"))

    @bp.route("/trades")
    def trades_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            scenario=(current_app.config.get("TRADE_SCENARIO") or request.args.get("trade_scenario")) if current_app.testing else None
            if scenario:
                from services.trade_scenarios import build_trade_scenario
                trade_intelligence=build_trade_scenario(scenario)
                trade_target_center=build_trade_target_center(trade_intelligence)
                return render_template("trades.html",title="Trade Target Center",context={"mode":"SCENARIO"},meta={"team_name":"Controlled Team"},teams=[trade_intelligence["partner"]],target_slot=trade_intelligence["partner"].get("slot"),trade_intelligence=trade_intelligence,trade_target_center=trade_target_center)
            context, roster, meta = current_roster(cur)
            teams=[]; target_roster=[]; partner={}
            target_slot=request.args.get("team",type=int)
            if context["mode"] == "MOCK":
                teams=[t for t in other_mock_teams(cur,context["draft_id"]) if t["name"] != "My Mock Team"]
                partner=next((t for t in teams if t["slot"]==target_slot),{})
                if target_slot:target_roster=mock_roster(cur,context["draft_id"],target_slot);target_roster=enrich_players(cur,target_roster,current_week(cur))
            else:
                league_id=current_app.config.get("SLEEPER_LEAGUE_ID","")
                users=get_users(league_id) or [];sleep_rosters=get_rosters(league_id) or [];catalog=get_all_players() or {}
                sleeper_retrieved_at=datetime.now(timezone.utc).isoformat()
                users_by_id={str(u.get("user_id")):u for u in users};owner_ids={str(u.get("user_id")) for u in users if u.get("is_owner") is True}
                for item in sleep_rosters:
                    rid=int(item.get("roster_id") or 0);oid=str(item.get("owner_id") or "")
                    if oid in owner_ids:continue
                    user=users_by_id.get(oid,{}) or {};metadata=user.get("metadata") or {};name=metadata.get("team_name") or user.get("display_name") or f"Roster {rid}"
                    teams.append({"slot":rid,"name":name})
                    if target_slot==rid:
                        partner={"slot":rid,"name":name};raw=[]
                        for pid in item.get("players") or []:
                            data=catalog.get(str(pid),{}) or {};full=data.get("full_name") or " ".join(x for x in (data.get("first_name"),data.get("last_name")) if x)
                            if not full:continue
                            cur.execute("SELECT player_name,UPPER(position),nfl_team,ranking,projected_points,tier,adp,bye_week,injury_status,projection_retrieved_at,id FROM players WHERE REGEXP_REPLACE(REGEXP_REPLACE(LOWER(player_name),'[^a-z0-9]','','g'),'(jr|sr|ii|iii|iv|il|ill)$','','g')=%s LIMIT 1",(normalize_player_name(full),))
                            row=cur.fetchone()
                            player=row_to_player(row,row[9] if len(row)>9 else None,row[10] if len(row)>10 else None) if row else {"player":full,"position":str(data.get("position") or "NA").upper().replace("DST","DEF"),"nfl_team":data.get("team") or "FA","rank":None,"projection":None,"tier":None,"adp":None,"bye_week":None,"injury_status":"Unknown","pick_no":None,"round":None,"projection_retrieved_at":None,"local_player_id":None}
                            player["source_player_id"]=str(pid);player["normalized_name"]=normalize_player_name(full);player["identity_match_method"]="UNIQUE_NORMALIZED_NAME" if row else "LOCAL_PLAYER_UNAVAILABLE";player["identity_state"]="RESOLVED" if row else "UNRESOLVED"
                            player["roster_updated_at"]=sleeper_retrieved_at;player["roster_source"]="Sleeper API"
                            status=data.get("injury_status") or data.get("status")
                            player["injury_source"]="Sleeper API";player["health_status_available"]=bool(status)
                            if status:
                                player["injury_status"]=status;player["health_fetched_at"]=sleeper_retrieved_at;player["injury_updated_at"]=sleeper_retrieved_at
                            raw.append(player)
                        target_roster=enrich_players(cur,raw,current_week(cur))
            trade_intelligence=build_trade_intelligence(
                roster,
                target_roster,
                partner,
            )
            trade_target_center=build_trade_target_center(trade_intelligence)
        finally:
            cur.close();conn.close()
        return render_template("trades.html",title="Trade Target Center",context=context,meta=meta,teams=teams,target_slot=target_slot,trade_intelligence=trade_intelligence,trade_target_center=trade_target_center,opportunity_view=build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE")))

    @bp.route("/gm")
    def gm_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool_evidence = waiver_pool_with_evidence(cur, context, roster, limit=20)
            waivers = faab_recommendations(pool_evidence["candidates"], counts)[:5]
            lineup_intelligence = build_lineup_intelligence(roster)
            matchup_intelligence = build_matchup_intelligence(roster, lineup_intelligence.get("starters"))
            extra_actions = []
            for vacancy in vacancies:
                extra_actions.append(build_action(action_id=f"roster:vacancy:{vacancy}", category="lineup", title=f"Fill {vacancy}", action=f"Fill vacant {vacancy} starter slot", reason="A vacant starter slot has a zero-point baseline until filled.", urgency="CRITICAL", confidence={"label":"HIGH","score":100}, risk_reduction=100, source="roster_analysis", metadata={"slot":vacancy}))
            for index, need in enumerate(needs[:5], 1):
                extra_actions.append(build_action(action_id=f"team-health:{index}", category="waiver", title="Address roster need", action=need, reason=need, urgency="HIGH", confidence={"label":"MEDIUM","score":70}, risk_reduction=50, source="roster_analysis"))
            extra_actions.extend(build_gm_waiver_watch_actions(waivers, pool_evidence.get("ranking_confidence")))
            incomplete = [p for p in roster if p.get("evidence_gaps")]
            if incomplete:
                extra_actions.append(build_action(action_id="data-integrity:weekly-evidence", category="matchup", title="Resolve weekly evidence", action=f"Resolve weekly evidence for {len(incomplete)} roster player(s)", reason="Schedule, bye, health, or matchup evidence is incomplete.", urgency="CRITICAL", confidence={"label":"LOW","score":0}, evidence_complete=False, blockers=sorted({gap for p in incomplete for gap in p.get("evidence_gaps",[])}), source="weekly_intelligence"))
            for index, player in enumerate(matchup_intelligence.get("favorable_matchups",[])[:3],1):
                extra_actions.append(build_action(action_id=f"matchup:{index}:{player['player']}", category="matchup", title=f"Exploit {player['player']} matchup", action=f"Prioritize {player['player']} against {player.get('opponent') or 'TBD'}", reason=f"Supplied matchup modifier is {player['matchup_modifier']:+.1%}.", urgency="MEDIUM", confidence=player.get("confidence"), expected_points_gain=max(0.0,player["weekly_score"]-player["weekly_baseline"]), evidence_complete=not player.get("evidence_gaps"), blockers=player.get("evidence_gaps") or (), source="matchup_intelligence", metadata={"position":player.get("position"),"matchup_rank":player.get("matchup_rank")}))
            decision_ranking = build_decision_ranking(lineup_intelligence=lineup_intelligence, extra_actions=extra_actions, limit=12)
        finally:
            cur.close(); conn.close()
        return render_template("gm.html", title="Weekly Command Center", context=context, meta=meta, overall=overall, roster_score=score, total=total, vacancies=vacancies, waivers=waivers, waiver_evidence=pool_evidence, roster=roster, lineup_intelligence=lineup_intelligence, decision_ranking=decision_ranking, matchup_intelligence=matchup_intelligence)

    return bp
