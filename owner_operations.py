from __future__ import annotations

from datetime import datetime, timezone
from math import ceil, isfinite

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from weekly_intelligence import enrich_players, current_week, upcoming_byes, normalize_team
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
from services.schedule_bye_evidence import team_bye_evidence, team_game_context
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
    if normalized == "NOT APPLICABLE":
        return "HEALTHY"
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
    if str(catalog_record.get("position") or "").upper() in {"DEF", "DST"} and not any(catalog_record.get(key) for key in ("injury_status", "status")):
        freshness = health_freshness_from_report_date(retrieved_at)
        return {**unavailable, "injury_status": "Not applicable", "injury_source": "Sleeper API", "health_status_available": True,
                "health_fetched_at": retrieved_at, "injury_updated_at": retrieved_at, "health_freshness_state": freshness["freshness_state"],
                "health_age_seconds": freshness["age"], "health_blocker": None if freshness["freshness_state"] == "FRESH" else "WAIVER_HEALTH_NOT_FRESH"}
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


WAIVER_VALUE_BASIS_ID = "waiver-value-pareto.v1"
WAIVER_POSITION_VALUE_FIELDS = {
    "QB": ("fantasy_points_ppr", "passing_yards", "passing_tds", "passing_interceptions", "carries", "rushing_yards", "snap_share"),
    "RB": ("fantasy_points_ppr", "carry_share", "carries", "target_share", "targets", "red_zone_share", "snap_share"),
    "WR": ("fantasy_points_ppr", "target_share", "targets", "route_participation", "red_zone_share", "snap_share"),
    "TE": ("fantasy_points_ppr", "route_participation", "target_share", "targets", "red_zone_share", "snap_share"),
}
WAIVER_POSITION_USAGE_FIELDS = {
    "QB": {"carries", "snap_share"},
    "RB": {"carry_share", "carries", "target_share", "targets", "red_zone_share", "snap_share"},
    "WR": {"target_share", "targets", "route_participation", "red_zone_share", "snap_share"},
    "TE": {"target_share", "targets", "route_participation", "red_zone_share", "snap_share"},
}
WAIVER_PRODUCTION_VALUE_FIELDS = (
    "passing_yards", "passing_tds", "passing_interceptions", "rushing_yards",
)
WAIVER_VALUE_LABELS = {
    "fantasy_points_ppr": "Full-PPR points",
    "carry_share": "carry share",
    "carries": "carries",
    "target_share": "target share",
    "targets": "targets",
    "route_participation": "route participation",
    "red_zone_share": "red-zone share",
    "snap_share": "snap share",
    "rushing_yards": "rushing yards",
    "passing_yards": "passing yards",
    "passing_tds": "passing touchdowns",
    "passing_interceptions": "interceptions",
}


def waiver_value_ranking(candidates, *, position, season, current_week, need):
    """Rank only by Pareto dominance across fresh shared-week production and usage; never score missing evidence."""
    position = str(position or "").upper().replace("DST", "DEF")
    fields = WAIVER_POSITION_VALUE_FIELDS.get(position)
    candidates = list(candidates or [])
    missing_by_id = {}
    weekly_by_id = {}
    for candidate in candidates:
        player_id = str(candidate.get("player_id") or "")
        evidence = candidate.get("evidence_context") or {}
        missing = []
        if not isinstance(season, int) or isinstance(season, bool) or not isinstance(current_week, int) or isinstance(current_week, bool):
            missing.append("verified season and current week")
        if not player_id or candidate.get("candidate_disposition") != "PRELIMINARY_SUGGESTION":
            missing.append("verified available player identity")
        identity = candidate.get("identity_resolution") or {}
        if identity.get("resolution_state") != "RESOLVED":
            missing.append("resolved player identity")
        if evidence.get("ownership_state") != "VERIFIED":
            missing.append("verified unrostered status")
        if evidence.get("eligibility_state") != "VERIFIED":
            missing.append("verified league eligibility")
        if evidence.get("health_state") != "HEALTHY" or evidence.get("health_freshness_state") != "FRESH" or evidence.get("health_source") != "Sleeper API":
            missing.append("fresh verified healthy status")
        if evidence.get("opportunity_identity_state") != "RESOLVED" and candidate.get("opportunity_identity_state") != "RESOLVED":
            missing.append("exact production/usage identity")
        if (need or {}).get("starter_shortage", 0) > 0:
            game = candidate.get("waiver_game_context") or {}
            bye = candidate.get("waiver_bye_evidence") or {}
            if (
                game.get("game_context_state") != "AVAILABLE"
                or game.get("week") != current_week
                or bye.get("authoritative") is not True
                or bye.get("freshness_state") != "FRESH"
                or bye.get("is_current_week_bye") is not False
            ):
                missing.append("verified current-week schedule and non-bye status for a starter replacement")
        metrics = candidate.get("opportunity_metrics") or {}
        production = candidate.get("recent_production") or {}
        production_by_week = {
            row.get("week"): row
            for row in (production.get("rows") or [])
            if row.get("season") == season
            and isinstance(row.get("week"), int)
            and row.get("freshness_state") == "FRESH"
        }
        if metrics.get("state") != "AVAILABLE":
            missing.append("fresh published production and usage rows")
        rows = {}
        if metrics.get("state") == "AVAILABLE":
            for row in metrics.get("rows") or []:
                week = row.get("week")
                if (
                    row.get("season") == season
                    and isinstance(week, int) and not isinstance(week, bool)
                    and isinstance(current_week, int) and 0 < week < current_week
                    and row.get("freshness_state") == "FRESH"
                ):
                    merged = dict(row)
                    production_row = production_by_week.get(week)
                    if production_row:
                        merged.update({
                            field: production_row.get(field)
                            for field in WAIVER_PRODUCTION_VALUE_FIELDS
                            if production_row.get(field) is not None
                        })
                    rows[week] = merged
        if len(rows) < 2:
            missing.append("at least two fresh completed weeks")
        missing_by_id[player_id] = list(dict.fromkeys(missing))
        weekly_by_id[player_id] = rows

    shared_weeks = set.intersection(*(set(rows) for rows in weekly_by_id.values())) if weekly_by_id and all(weekly_by_id.values()) else set()
    if len(shared_weeks) < 2:
        missing_reason = "two or more matching fresh completed weeks across the available alternatives"
        for missing in missing_by_id.values():
            if missing_reason not in missing:
                missing.append(missing_reason)
    common_fields = []
    if fields and len(shared_weeks) >= 2:
        for field in fields:
            if all(
                isinstance(weekly_by_id[str(candidate.get("player_id") or "")][week].get(field), (int, float))
                and not isinstance(weekly_by_id[str(candidate.get("player_id") or "")][week].get(field), bool)
                for candidate in candidates for week in shared_weeks
            ):
                common_fields.append(field)
    has_usage = bool(set(common_fields) & WAIVER_POSITION_USAGE_FIELDS.get(position, set()))
    if not fields:
        shared_reason = "A current positional projection or rank is unavailable"
    elif "fantasy_points_ppr" not in common_fields or not has_usage:
        shared_reason = "Matching recent production and position-relevant usage across these alternatives are unavailable"
    else:
        shared_reason = None

    values = {}
    if shared_reason is None and not any(missing_by_id.values()):
        selected_weeks = sorted(shared_weeks)[-3:]
        for candidate in candidates:
            player_id = str(candidate.get("player_id") or "")
            values[player_id] = {
                field: sum(float(weekly_by_id[player_id][week][field]) for week in selected_weeks) / len(selected_weeks)
                for field in common_fields
            }
    ranks = {}
    if values:
        remaining = set(values)
        rank = 1
        while remaining:
            frontier = {
                player_id for player_id in remaining
                if not any(
                    other != player_id
                    and all(values[other][field] >= values[player_id][field] for field in common_fields)
                    and any(values[other][field] > values[player_id][field] for field in common_fields)
                    for other in remaining
                )
            }
            for player_id in frontier:
                ranks[player_id] = rank
            remaining -= frontier
            rank += len(frontier)

    grouped = {}
    for player in candidates:
        player_id = str(player.get("player_id") or "")
        grouped.setdefault(ranks.get(player_id), []).append(player_id)
    results = {}
    for candidate in candidates:
        player_id = str(candidate.get("player_id") or "")
        player_missing = list(missing_by_id.get(player_id) or [])
        rank = ranks.get(player_id)
        rank_group = grouped.get(rank, []) if rank is not None else []
        rank_tie = len(rank_group) > 1 and all(values[player_id] == values[rank_group[0]] for player_id in rank_group[1:])
        incomparable = len(rank_group) > 1 and not rank_tie
        positive = []
        if rank is not None and not rank_tie and not incomparable:
            for field in common_fields:
                better = sum(values[player_id][field] > values[other][field] for other in values if other != player_id)
                if better:
                    positive.append(f"Higher {WAIVER_VALUE_LABELS[field]} than {better} comparable option(s)")
        stats = [
            {"field": field, "label": WAIVER_VALUE_LABELS[field], "value": round(values[player_id][field], 3)}
            for field in common_fields if player_id in values
        ]
        state = "RANKED" if rank is not None else "INSUFFICIENT_EVIDENCE"
        if rank is not None and rank_tie:
            state = "TIED"
        elif rank is not None and incomparable:
            state = "INCOMPARABLE"
        results[player_id] = {
            "schema_version": WAIVER_VALUE_BASIS_ID,
            "state": state,
            "position": position,
            "position_rank": rank,
            "recommendation": "TIED" if rank_tie else "NO_CLEAR_WINNER" if incomparable else "CONSIDER" if rank == 1 else "FALLBACK" if rank else "PASS",
            "roster_need": dict(need or {}),
            "shared_weeks": sorted(shared_weeks)[-3:] if rank is not None else [],
            "statistics_used": stats,
            "positive_reasons": positive[:3],
            "risks": (
                ["Alternatives have different supported strengths; no single option is better across all compared statistics."]
                if incomparable else ["Historical production and usage are not a forecast."]
            ) if rank is not None else ["No ranking advantage is inferred from missing data."],
            "missing_important_statistics": list(dict.fromkeys(player_missing + ([shared_reason] if shared_reason else []))),
            "alternatives": [other for other in values if other != player_id],
            "basis_id": WAIVER_VALUE_BASIS_ID,
            "disclosure": "Position-specific Pareto comparison of matching fresh completed-week Full-PPR production and published usage; no weighted score or forecast.",
        }
    return results


def waiver_consensus_ranking(candidates, *, horizon, horizon_data, position, season=None, current_week=None):
    """Rank safety-screened candidates by fresh current FantasyPros positional ECR."""
    position = str(position or "").upper().replace("DST", "DEF")
    horizon_data = horizon_data or {}
    ranks = horizon_data.get("ranks") or {}
    diagnostics = horizon_data.get("diagnostics") or []
    page_names = {"QB": "qb", "RB": "ppr-rb", "WR": "ppr-wr", "TE": "ppr-te", "K": "k", "DEF": "dst"}

    def normalized_name(value):
        return "".join(character for character in str(value or "").casefold() if character.isalnum())

    def candidate_diagnostic(candidate):
        name = normalized_name(candidate.get("player"))
        return next(
            (
                row for row in diagnostics
                if normalized_name(row.get("player")) == name
                and str(row.get("page") or "").lower() == page_names.get(position)
            ),
            None,
        )

    def candidate_reason(candidate):
        evidence = candidate.get("evidence_context") or {}
        if evidence.get("ownership_state") != "VERIFIED":
            return "Ownership is not verified."
        if evidence.get("eligibility_state") != "VERIFIED":
            return "League position eligibility is not verified."
        if (candidate.get("identity_resolution") or {}).get("resolution_state") != "RESOLVED":
            return "Player identity is not resolved."
        if evidence.get("health_state") != "HEALTHY" or evidence.get("health_freshness_state") != "FRESH" or evidence.get("health_source") != "Sleeper API":
            return "Fresh healthy status is not verified."
        if str(candidate.get("position") or "").upper().replace("DST", "DEF") != position:
            return "Candidate position does not match this ranking group."
        diagnostic = candidate_diagnostic(candidate)
        if diagnostic:
            reason = str(diagnostic.get("reason") or "")
            if "stale" in reason.casefold():
                return "Consensus rank is stale."
            return f"Consensus rank could not be verified: {reason or 'source row failed validation'}."
        if horizon_data.get("state") != "AVAILABLE":
            return f"No fresh {horizon.replace('_', ' ')} consensus ranks are available."
        if rank_row := ranks.get(str(candidate.get("player_id") or "")):
            age = rank_row.get("source_age_seconds")
            maximum_age = horizon_data.get("max_age_seconds")
            if not isinstance(age, (int, float)) or not isinstance(maximum_age, (int, float)) or age < 0 or age > maximum_age:
                return "Consensus rank freshness is stale or could not be verified."
            if rank_row.get("horizon") != horizon or rank_row.get("position") != position or rank_row.get("scoring") != "PPR":
                return "Consensus rank does not match the requested position, scoring, or horizon."
            if rank_row.get("season") != season or horizon == "this_week" and rank_row.get("week") != current_week:
                return "Consensus rank is for a different season or week."
        return f"No fresh {horizon.replace('_', ' ')} positional consensus rank is published for this player."

    ranked = []
    results = {}
    for candidate in candidates or []:
        player_id = str(candidate.get("player_id") or "")
        evidence = candidate.get("evidence_context") or {}
        position_rank = str(candidate.get("position") or "").upper().replace("DST", "DEF")
        rank_row = ranks.get(player_id)
        valid = (
            candidate.get("candidate_disposition") == "PRELIMINARY_SUGGESTION"
            and evidence.get("ownership_state") == "VERIFIED"
            and evidence.get("eligibility_state") == "VERIFIED"
            and evidence.get("health_state") == "HEALTHY"
            and evidence.get("health_freshness_state") == "FRESH"
            and evidence.get("health_source") == "Sleeper API"
            and (candidate.get("identity_resolution") or {}).get("resolution_state") == "RESOLVED"
            and position_rank == position
            and isinstance(rank_row, dict)
            and str(rank_row.get("position") or "").upper().replace("DST", "DEF") == position
            and rank_row.get("horizon") == horizon
            and rank_row.get("scoring") == "PPR"
            and rank_row.get("season") == season
            and (horizon != "this_week" or rank_row.get("week") == current_week)
            and isinstance(rank_row.get("source_age_seconds"), (int, float))
            and isinstance(horizon_data.get("max_age_seconds"), (int, float))
            and 0 <= rank_row["source_age_seconds"] <= horizon_data["max_age_seconds"]
            and isinstance(rank_row.get("ecr"), (int, float))
            and not isinstance(rank_row.get("ecr"), bool)
            and isfinite(float(rank_row["ecr"]))
            and float(rank_row["ecr"]) > 0
        )
        if valid:
            ranked.append((float(rank_row["ecr"]), candidate))
        else:
            diagnostic = candidate_diagnostic(candidate)
            diagnostic_reason = str((diagnostic or {}).get("reason") or "")
            results[player_id] = {
                "state": "UNRANKED",
                "position": position,
                "position_rank": None,
                "recommendation": "CONSIDER",
                "horizon": horizon,
                "rank": None,
                "source": horizon_data.get("source", "FantasyPros consensus via DynastyProcess"),
                "freshness_state": "STALE" if "stale" in diagnostic_reason.casefold() or "future-dated" in diagnostic_reason.casefold() else "UNAVAILABLE",
                "source_date": (diagnostic or {}).get("source_date"),
                "reason": candidate_reason(candidate),
                "basis_id": "waiver-consensus-ecr.v1",
            }
    ranked.sort(key=lambda item: (item[0], str(item[1].get("player") or "").casefold(), str(item[1].get("player_id") or "")))
    for index, (ecr, candidate) in enumerate(ranked):
        player_id = str(candidate.get("player_id") or "")
        rank_row = ranks[player_id]
        tied_ahead = sum(1 for other_ecr, _ in ranked if other_ecr < ecr)
        tie_count = sum(1 for other_ecr, _ in ranked if other_ecr == ecr)
        results[player_id] = {
            "state": "TIED" if tie_count > 1 else "RANKED",
            "position": position,
            "position_rank": tied_ahead + 1,
            "recommendation": "TIED" if tie_count > 1 else "CONSIDER" if tied_ahead == 0 else "FALLBACK",
            "horizon": horizon,
            "rank": ecr,
            "source": rank_row.get("source") or horizon_data.get("source", "FantasyPros consensus via DynastyProcess"),
            "source_date": rank_row.get("source_date"),
            "source_age_seconds": rank_row.get("source_age_seconds"),
            "freshness_state": "FRESH",
            "identity_method": rank_row.get("identity_method"),
            "roster_need": {},
            "reason": "Lower current positional consensus rank." if tied_ahead == 0 else "Ranked behind a lower current positional consensus rank.",
            "basis_id": "waiver-consensus-ecr.v1",
        }
    return results


def waiver_bid_estimates(candidate, faab_balance):
    """Keep the value and winning-bid contracts unavailable until their required valuation/market evidence exists."""
    balance = faab_balance or {}
    return {
        "value_based_bid": {"state": "UNAVAILABLE", "amount": None, "range": None, "reason": "No verified player-value-to-FAAB model using role duration and projected lineup impact is available."},
        "estimated_winning_bid": {"state": "UNAVAILABLE", "amount": None, "range": None, "reason": "Historical winning and losing bids, candidate-specific competitor demand, and league bidding behavior are unavailable."},
        "maximum_bid": {"state": "UNAVAILABLE", "amount": None, "range": None, "remaining_faab": balance.get("remaining") if balance.get("state") == "AVAILABLE" else None, "reason": "A maximum requires a supported value-based bid; none is available."},
        "market_demand": {"state": "UNAVAILABLE", "likely_competitors": [], "reason": "Current competitor needs and bid history are not covered by a validated league-market reader."},
    }


def sleeper_empty_required_slots(starters, roster_positions):
    """Starter slots Sleeper reports empty ("0"); None when the lineup shape contradicts the league slots."""
    slots = [str(slot).upper().replace("DST", "DEF") for slot in (roster_positions or []) if str(slot).upper() not in {"BN", "BENCH"}]
    starters = [str(pid) for pid in (starters or [])]
    if not slots or len(starters) != len(slots):
        return None
    return [slot for slot, pid in zip(slots, starters) if pid in {"0", "", "None"}]


def read_week_schedule_rows(cur, season, week):
    if not isinstance(week, int):
        return []
    cur.execute("SELECT home_team, away_team, game_time_pacific, source, source_recorded_at, retrieved_at FROM nfl_schedule WHERE season=%s AND week=%s", (season, week))
    return [dict(zip(("home_team", "away_team", "game_time_pacific", "source", "source_recorded_at", "retrieved_at"), row)) for row in cur.fetchall() or []]


SLOT_FILL_FAAB_CONTRACT_ID = "waiver.slot_fill_faab.v1"


def slot_fill_faab(position, balance, *, one_week_rental, equivalent_alternatives=0):
    """Conservative spending guardrail for a mandatory K/DEF slot fill; not an expected winning bid."""
    label = "PROVISIONAL SLOT-FILL FAAB"
    base = {"label": label, "contract_id": SLOT_FILL_FAAB_CONTRACT_ID, "evidence_level": "PRELIMINARY", "category": "SLOT_FILL", "recommended": None, "low": None, "high": None,
            "percent_of_remaining": None, "remaining": None, "budget": None, "posture": None, "rationale": None, "low_label": "minimum", "high_label": "maximum recommended"}
    balance = balance or {}
    remaining, budget, min_bid = balance.get("remaining"), balance.get("budget"), balance.get("min_bid")
    ints = all(isinstance(v, int) and not isinstance(v, bool) for v in (remaining, min_bid))
    if position not in {"K", "DEF"}:
        return {**base, "state": "UNAVAILABLE", "reason": "Slot-fill FAAB applies only to K and DEF."}
    if balance.get("state") != "AVAILABLE" or not ints or remaining < 0 or min_bid < 0 or (isinstance(budget, int) and remaining > budget):
        return {**base, "state": "UNAVAILABLE", "reason": "FAAB budget or league minimum bid is unavailable or inconsistent; no amount is suggested."}
    if remaining < max(1, min_bid):
        return {**base, "state": "UNAVAILABLE", "reason": "Remaining FAAB cannot cover the smallest positive bid."}
    percent = 2 if position == "DEF" and equivalent_alternatives < 2 else 1
    recommended = min(remaining, max(min_bid, 1, int(remaining * percent / 100 + 0.5)))
    high = min(remaining, max(recommended, int(remaining * 3 / 100)))
    rental = "one-week" if one_week_rental else "slot-fill"
    return {**base, "state": "PROVISIONAL", "recommended": recommended, "low": min_bid, "high": high, "percent_of_remaining": round(recommended / remaining * 100, 1),
            "remaining": remaining, "budget": budget if isinstance(budget, int) else None, "posture": "CONSERVATIVE_ONE_WEEK_RENTAL" if one_week_rental else "CONSERVATIVE_SLOT_FILL",
            "rationale": f"About {percent}% of ${remaining} remaining for a {rental} {position} replacement"
                         + (f" with {equivalent_alternatives} verified equivalent alternative(s)" if equivalent_alternatives else "")
                         + ". A spending guardrail, not a likely winning bid.",
            "limitations": ["Not an expected winning bid or market forecast.", "Other managers' demand and bids are unknown.", "No multi-week or rest-of-season value is established."]}


def read_season_bye_rows(cur, season):
    cur.execute("SELECT team, bye_week, source, source_recorded_at, retrieved_at, imported_at FROM bye_weeks WHERE season=%s", (season,))
    return [dict(zip(("team", "bye_week", "source", "source_recorded_at", "retrieved_at", "imported_at"), row)) for row in cur.fetchall() or []]


def waiver_mandatory_slot_trigger(selected_player, position, settings, need, bye_evidence=None):
    """Verified reason a required starter slot cannot be played this week, or None."""
    slots = (settings or {}).get("starter_slots") or {}
    if (settings or {}).get("state") != "AVAILABLE" or not position or int(slots.get(position) or 0) < 1 or (need or {}).get("state") != "AVAILABLE":
        return None
    if int((need or {}).get("starter_shortage") or 0) > 0:
        return {"reason": "EMPTY_REQUIRED_SLOT", "detail": f"A required {position} starter slot is empty on the verified roster."}
    starter = selected_player.get("sleeper_current_starter", selected_player.get("is_starter")) is True
    slot = str(selected_player.get("sleeper_lineup_slot") or selected_player.get("lineup_slot") or "").upper()
    empty_slots = selected_player.get("empty_required_slots")
    slot_empty = isinstance(empty_slots, list) and position in empty_slots and not starter and int((need or {}).get("rostered") or 0) <= int(slots.get(position) or 0)
    if not slot_empty and (not starter or slot in {"FLEX", "W/R/T", "WR/RB/TE", "WRRB_FLEX", "REC_FLEX", "BN"}):
        return None
    role = f"a current {position} starter" if starter else f"the only rostered {position} with the required {position} lineup slot empty"
    bye = bye_evidence or {}
    team = str(selected_player.get("team") or selected_player.get("nfl_team") or "").upper()
    if bye.get("authoritative") is True and bye.get("is_current_week_bye") is True and team and bye.get("team") == team:
        return {"reason": "BYE_WEEK", "detail": f"{selected_player.get('player')} is {role} and {team} is on its bye in week {bye.get('bye_week')}."}
    if selected_player.get("health_state") in {"OUT", "IR"} and selected_player.get("health_freshness_state") == "FRESH":
        return {"reason": "UNUSABLE_HEALTH", "detail": f"{selected_player.get('player')} is {role} with a fresh {selected_player['health_state']} status."}
    return None


def waiver_selected_player_comparison(selected_player, candidate, team_needs, league_settings, faab_balance=None, roster_coverage_complete=False, roster=None, season=None, focus="all", bye_evidence=None, candidate_bye_evidence=None, candidate_game_context=None, roster_capacity=None, equivalent_alternatives=0):
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
    usage_not_applicable = selected_position in {"K", "DEF"}
    if usage_not_applicable:
        missing.append("production and opportunity comparison: NOT_APPLICABLE for K/DEF")
    for label, player in (("candidate", candidate), ("selected player", selected_player)):
        for signal in ("recent_production", "opportunity_metrics", "snap_share"):
            if usage_not_applicable:
                continue
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
    slot_trigger = None
    if decision == "NO_ACTIONABLE_UPGRADE" and not safety_blocked and same_position:
        slot_trigger = waiver_mandatory_slot_trigger(selected_player, selected_position, settings, selected_need, bye_evidence)
        cbye = candidate_bye_evidence or {}
        if slot_trigger and not (cbye.get("authoritative") is True and cbye.get("is_current_week_bye") is False):
            slot_trigger = None
            missing.append("candidate bye week: not verified as playing this week")
        gctx = candidate_game_context or {}
        if slot_trigger and not (gctx.get("game_context_state") == "AVAILABLE" and gctx.get("opponent") and gctx.get("team") == normalize_team(candidate.get("team") or candidate.get("nfl_team"))):
            slot_trigger = None
            missing.append(f"candidate week matchup: {gctx.get('blocker') or 'SCHEDULE_CONTEXT_UNAVAILABLE'}")
        if slot_trigger:
            decision = "PRELIMINARY_RECOMMENDATION"
            summary = {"state": "SLOT_FILL", "reason": slot_trigger["detail"], "disclosure": "Slot-fill need is verified; no upgrade comparison is claimed."}
            roster_effect = f"Fill the {selected_position} starter slot; this is a preliminary slot-fill recommendation, not a verified upgrade."
            reasons.append(slot_trigger["detail"])
            suggested_drop = {"state": "UNAVAILABLE", "player_id": None, "player": None, "reason": "No authoritative drop is established; see the conditional drop for this claim."}
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
    if not usage_not_applicable and (freshness["candidate_production"] != "AVAILABLE" or freshness["selected_production"] != "AVAILABLE"):
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
    result = {
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
    if bye_evidence and selected_position in {"K", "DEF"}:
        result["bye_evidence"] = dict(bye_evidence)
    if slot_trigger and decision == "PRELIMINARY_RECOMMENDATION":
        bye = bye_evidence or {}
        bye_used = slot_trigger["reason"] == "BYE_WEEK"
        result.update(
            authority="PRELIMINARY", evidence_level="PRELIMINARY", relevance_class="SLOT_FILL",
            decision_basis="MANDATORY_STARTER_SLOT", slot_trigger=slot_trigger["reason"],
            manager_reason=slot_trigger["detail"] + f" Review {candidate.get('player')} as a verified available {candidate_position} before lineup lock.",
            disclosure="PRELIMINARY: ownership, eligibility, health, and roster need are verified. No upgrade comparison, waiver rank, FAAB bid, or drop is established.",
            evidence_used=["Verified candidate ownership", "Verified candidate eligibility", "Fresh healthy candidate status", "Verified roster and league starter slots", slot_trigger["detail"]],
            recommendation_impact="Useful for filling a required starter slot; it does not authorize an upgrade, ranking, bid, or drop.",
            bye_evidence=bye if bye_used else None,
            confidence_rationale="Slot-fill need is verified; no confidence score is calculated.",
        )
        result["missing_evidence"] = list(dict.fromkeys([*result["missing_evidence"], "authoritative upgrade comparison"]))
        week = (candidate_game_context or {}).get("week")
        rental = ({"status": "ONE_WEEK_RENTAL", "reason": f"Fills the required Week {week} slot. Reevaluate after the bye."} if bye_used
                  else {"status": "NOT_ESTABLISHED", "reason": "Multi-week value is not established; reevaluate next week."})
        position_count = sum(1 for player in (roster or []) if str(player.get("position") or "").upper().replace("DST", "DEF") == selected_position)
        required_slots = int(selected_need.get("required_starters") or 0)
        full = (len(roster or []) >= roster_capacity) if isinstance(roster_capacity, int) and roster else None
        drop_ok = bool(selected_id) and selected_position == candidate_position and required_slots >= 1 and position_count >= 1 and full is True
        result.update(
            candidate_team=normalize_team(candidate.get("team") or candidate.get("nfl_team")), candidate_position=candidate_position, week=week,
            game_context=dict(candidate_game_context), candidate_bye_state=(candidate_bye_evidence or {}).get("freshness_state"), rental=rental,
            equivalent_alternatives=equivalent_alternatives,
            faab=slot_fill_faab(selected_position, faab_balance, one_week_rental=bye_used, equivalent_alternatives=equivalent_alternatives),
            conditional_drop=({"state": "CONDITIONAL", "label": "CONDITIONAL DROP FOR THIS CLAIM", "player_id": selected_id, "player": selected_player.get("player"), "position": selected_position,
                               "roster_full": full,
                               "reason": f"Drop {selected_player.get('player')} only if roster construction requires the corresponding move"
                                         + (f" (roster is full at {len(roster)} of {roster_capacity})" if full else "")
                                         + f"; the {selected_position} count stays at {position_count}. This is not an automatic transaction."}
                              if drop_ok else {"state": "UNAVAILABLE", "reason": "Roster construction does not verify a safe same-position drop."}),
        )
    return result

def waiver_slot_fill_inputs(team, season, week, bye_rows, schedule_rows):
    team = normalize_team(team)
    return (team_bye_evidence(bye_rows, season=season, team=team, week=week),
            team_game_context(schedule_rows, season=season, week=week, team=team, normalize=normalize_team))


def build_waiver_plan(wda_roster, wda_candidates, team_needs, league_settings, faab_balance, roster, season, week, bye_rows, schedule_rows, roster_capacity=None):
    """Action-first K/DEF mandatory-slot plan; arithmetic totals count each primary claim once and never fallbacks."""
    problems = []
    for position in ("K", "DEF"):
        for player in (p for p in wda_roster if str(p.get("position") or "").upper().replace("DST", "DEF") == position):
            bye = team_bye_evidence(bye_rows, season=season, team=normalize_team(player.get("team")), week=week)
            trigger = waiver_mandatory_slot_trigger(player, position, league_settings, (team_needs or {}).get(position), bye)
            if not trigger:
                continue
            same = [c for c in wda_candidates if str(c.get("position") or "").upper().replace("DST", "DEF") == position]
            eligible = [c for c in same if (lambda b, g: b.get("authoritative") is True and b.get("is_current_week_bye") is False and g.get("game_context_state") == "AVAILABLE")(
                *waiver_slot_fill_inputs(c.get("team"), season, week, bye_rows, schedule_rows))]
            claims = []
            for candidate in eligible:
                cbye, gctx = waiver_slot_fill_inputs(candidate.get("team"), season, week, bye_rows, schedule_rows)
                result = waiver_selected_player_comparison(player, candidate, team_needs, league_settings, faab_balance, True, roster, season, "all", bye_evidence=bye,
                                                           candidate_bye_evidence=cbye, candidate_game_context=gctx, roster_capacity=roster_capacity,
                                                           equivalent_alternatives=len(eligible) - 1)
                if result.get("decision") == "PRELIMINARY_RECOMMENDATION":
                    result["waiver_value_result"] = candidate.get("waiver_value_result") or {}
                    claims.append(result)
            candidate_by_id = {str(item.get("player_id") or ""): item for item in same}
            claims.sort(key=lambda result: (
                (candidate_by_id.get(str(result.get("candidate_id") or ""), {}).get("waiver_value_result") or {}).get("position_rank") or 999,
                (candidate_by_id.get(str(result.get("candidate_id") or ""), {}).get("waiver_value_result") or {}).get("rank") or float("inf"),
                str(result.get("candidate") or "").casefold(),
                str(result.get("candidate_id") or ""),
            ))
            has_current_rank = any(
                (candidate_by_id.get(str(result.get("candidate_id") or ""), {}).get("waiver_value_result") or {}).get("rank") is not None
                for result in claims
            )
            problems.append({"need": trigger["reason"], "detail": trigger["detail"], "position": position, "selected_player": player.get("player"), "selected_player_id": player.get("player_id"),
                             "selected_team": normalize_team(player.get("team")), "claims": claims[:4], "fallback_count": max(0, min(len(claims), 4) - 1), "candidates_considered": len(same),
                             "ordering": "CURRENT_CONSENSUS_RANK" if claims and has_current_rank else "VERIFIED_EQUIVALENT_OPTIONS" if claims else None,
                             "ordering_note": (
                                 "Ordered by fresh current positional consensus rank; unranked candidates follow ranked candidates. Tied or unranked options use stable display order."
                                 if has_current_rank else
                                 "Verified equivalent slot-fill options: no fresh consensus rank distinguishes these players; the display order is stable, not a quality ranking."
                             )})
    for index, problem in enumerate(problems, 1):
        problem["priority"] = index
        problem["state"] = "PRELIMINARY" if problem["claims"] else "NO_SUPPORTED_CLAIM"
        if not problem["claims"]:
            problem["blocker"] = "No verified available candidate with an authoritative current-week matchup and non-bye status."
    primaries = [p["claims"][0]["faab"] for p in problems if p["claims"]]
    amounts = [f.get("recommended") for f in primaries]
    remaining = (faab_balance or {}).get("remaining")
    total = sum(amounts) if amounts and all(isinstance(a, int) for a in amounts) else None
    return {"state": "PLAN" if any(p["claims"] for p in problems) else ("NO_SUPPORTED_CLAIM" if problems else "PASS"), "week": week, "problems": problems,
            "pass_reason": None if problems else "No verified mandatory K/DEF slot problem exists this week.",
            "faab_remaining": remaining if isinstance(remaining, int) else None, "faab_budget": (faab_balance or {}).get("budget"),
            "total_recommended_faab": total, "projected_remaining_faab": (remaining - total) if total is not None and isinstance(remaining, int) else None,
            "total_note": "Arithmetic across displayed primary claims only; fallbacks are mutually exclusive and not counted. Not a prediction that any claim wins."}


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
        empty_slots = sleeper_empty_required_slots(owner_roster.get("starters"), league.get("roster_positions"))
        for roster_player in result:
            roster_player["sleeper_empty_required_slots"] = empty_slots
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
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF','DST')
                ORDER BY ranking NULLS LAST
                """
            )
        else:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF','DST')
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
        candidate_outcomes = []
        for candidate in candidates:
            player_id = str(candidate.get("player_id") or "")
            position = str(candidate.get("position") or "").upper().replace("DST", "DEF")
            identity = candidate.get("identity_resolution") or {}
            if identity.get("resolution_state") != "RESOLVED":
                message = "Identity could not be verified."
            elif not ownership.get("allowed") or availability.get("freshness_state") not in {"FRESH", "AGING"}:
                message = "Current availability could not be verified."
            elif player_id in owned_ids:
                message = "Already rostered."
            elif position not in supported_positions:
                message = "Position is not eligible in this league."
            elif player_id not in availability.get("eligible_player_ids", set()):
                message = "Identity or eligibility could not be verified."
            elif candidate.get("health_freshness_state") == "STALE":
                message = "Current health information is stale."
            elif candidate.get("health_status_available") is not True:
                message = "Health could not be verified."
            elif candidate.get("health_freshness_state") != "FRESH":
                message = "Current health information could not be verified as current."
            elif _waiver_health_state(candidate.get("injury_status")) != "HEALTHY":
                message = "Current health status does not support an add."
            else:
                message = "Available; current player-specific comparison is needed."
            candidate_outcomes.append({
                "player_id": player_id or None,
                "player": candidate.get("player") or candidate.get("name"),
                "team": candidate.get("nfl_team") or candidate.get("team"),
                "position": position or None,
                "message": message,
                "state": "AVAILABLE" if message.startswith("Available;") else "NOT_AVAILABLE_OR_UNVERIFIED",
                "details": {
                    "identity": identity.get("resolution_state"),
                    "health": candidate.get("health_freshness_state"),
                    "health_status": candidate.get("injury_status"),
                },
            })
        result = evaluate_waiver_availability(
            candidates,
            {**ownership, "owned_player_ids": owned_ids},
            availability,
        )
        result["candidate_outcomes"] = candidate_outcomes
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
        requested_explanation_name = request.args.get("explain_player", "").strip()
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
            context, roster, meta, waiver_snapshot = current_roster(cur, verify_live_week=True, include_waiver_snapshot=True)
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
            bye_rows = read_season_bye_rows(cur, meta.get("season"))
            schedule_rows = read_week_schedule_rows(cur, meta.get("season"), meta.get("week"))
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
            waiver_candidate_outcomes = list(pool_evidence.get("candidate_outcomes") or [])
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
                    candidate_blockers = candidate.get("recommendation_blockers") or []
                    if "WAIVER_CANDIDATE_EVIDENCE_UNAVAILABLE" in candidate_blockers:
                        health_message = "Available, but there is not enough current player evidence to compare."
                    elif "WAIVER_CANDIDATE_IDENTITY_UNRESOLVED" in candidate_blockers:
                        health_message = "Identity could not be verified."
                    elif "WAIVER_OWNERSHIP_OR_ELIGIBILITY_UNVERIFIED" in candidate_blockers:
                        health_message = "Current availability or position eligibility could not be verified."
                    elif candidate.get("health_freshness_state") == "STALE" or "WAIVER_HEALTH_NOT_FRESH" in candidate_blockers:
                        health_message = "Current health information is stale."
                    elif "WAIVER_HEALTH_NOT_ACTIONABLE" in candidate_blockers:
                        health_message = "Current health status does not support an add."
                    else:
                        health_message = "Health could not be verified."
                    waiver_candidate_outcomes.append({
                        "player_id": candidate.get("player_id"),
                        "player": candidate.get("player"),
                        "team": candidate.get("nfl_team"),
                        "position": candidate.get("position"),
                        "message": health_message,
                        "details": {"blockers": list(candidate.get("recommendation_blockers") or [])},
                    })
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
                    waiver_candidate_outcomes.append({
                        "player_id": candidate.get("player_id"),
                        "player": candidate.get("player"),
                        "team": candidate.get("nfl_team"),
                        "position": candidate.get("position"),
                        "message": "Health could not be verified.",
                        "details": {"blockers": list(candidate.get("recommendation_blockers") or [])},
                    })
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
            "empty_required_slots": player.get("sleeper_empty_required_slots"),
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
        ranking_horizon = "rest_of_season" if selected_focus == "rest_of_season" else "this_week"
        ranking_horizon_data = dict(rankings.get("horizons", {}).get(ranking_horizon, {}))
        ranking_horizon_data["source"] = rankings.get("source", "FantasyPros consensus via DynastyProcess")
        for candidate in [*wda_candidates, *preliminary_suggestions]:
            candidate["source_rankings"] = {
                horizon: (rankings.get("horizons", {}).get(horizon, {}).get("ranks", {}) or {}).get(str(candidate.get("player_id") or ""))
                for horizon in ("this_week", "rest_of_season")
            }
            candidate["waiver_rank_horizon"] = ranking_horizon
            preferred_player = next((player for player in wda_roster if player.get("position") == candidate.get("position") and player.get("is_starter") is True), None)
            if preferred_player is None:
                preferred_player = next((player for player in wda_roster if player.get("position") == candidate.get("position")), None)
            if candidate in wda_candidates:
                selected_guidance = candidate["roster_guidance"].get(preferred_player["player_id"], {}) if preferred_player else {}
                candidate["acquisition_evaluation"] = waiver_acquisition_evaluation(
                    candidate, team_needs, league_settings, selected_guidance, meta.get("faab_balance") or {},
                )
        candidate_evaluations = {candidate["player_id"]: candidate["acquisition_evaluation"] for candidate in wda_candidates}
        for candidate in preliminary_suggestions:
            candidate["acquisition_evaluation"] = candidate_evaluations.get(str(candidate.get("player_id")))
        wda_candidates.sort(key=lambda candidate: (candidate["acquisition_evaluation"]["sort_group"], candidate.get("player") or "", candidate["player_id"]))
        preliminary_suggestions.sort(key=lambda candidate: ((candidate.get("acquisition_evaluation") or {}).get("sort_group", 3), candidate.get("player") or "", str(candidate.get("player_id") or "")))
        for position in ("QB", "RB", "WR", "TE", "K", "DEF"):
            position_candidates = [
                candidate for candidate in preliminary_suggestions
                if str(candidate.get("position") or "").upper().replace("DST", "DEF") == position
            ]
            for candidate in position_candidates:
                candidate["waiver_bye_evidence"], candidate["waiver_game_context"] = waiver_slot_fill_inputs(
                    candidate.get("nfl_team"), meta.get("season"), meta.get("week"), bye_rows, schedule_rows,
                )
            historical_results = waiver_value_ranking(
                position_candidates,
                position=position,
                season=meta.get("season"),
                current_week=meta.get("week"),
                need=team_needs.get(position),
            )
            consensus_results = waiver_consensus_ranking(
                position_candidates,
                horizon=ranking_horizon,
                horizon_data=ranking_horizon_data,
                position=position,
                season=meta.get("season"),
                current_week=meta.get("week"),
            )
            for candidate in position_candidates:
                candidate_id = str(candidate.get("player_id") or "")
                candidate["waiver_value_result"] = consensus_results.get(candidate_id, {
                    "state": "UNRANKED",
                    "position": position,
                    "position_rank": None,
                    "recommendation": "CONSIDER",
                    "horizon": ranking_horizon,
                    "rank": None,
                    "source": rankings.get("source", "FantasyPros consensus via DynastyProcess"),
                    "freshness_state": "UNAVAILABLE",
                    "reason": "No current consensus rank was resolved for this candidate.",
                    "basis_id": "waiver-consensus-ecr.v1",
                })
                candidate["waiver_supporting_evidence"] = historical_results.get(candidate_id, {})
                candidate["waiver_bid_estimates"] = waiver_bid_estimates(candidate, meta.get("faab_balance") or {})
        preliminary_by_id = {str(candidate.get("player_id") or ""): candidate for candidate in preliminary_suggestions}
        for candidate in wda_candidates:
            ranked_candidate = preliminary_by_id.get(str(candidate.get("player_id") or ""))
            if ranked_candidate:
                candidate["waiver_value_result"] = ranked_candidate.get("waiver_value_result")
                candidate["waiver_supporting_evidence"] = ranked_candidate.get("waiver_supporting_evidence")
                candidate["waiver_bid_estimates"] = ranked_candidate.get("waiver_bid_estimates")
        preliminary_suggestions.sort(key=lambda candidate: (
            (candidate.get("acquisition_evaluation") or {}).get("sort_group", 3),
            str(candidate.get("position") or ""),
            candidate.get("waiver_value_result", {}).get("position_rank") or 999,
            candidate.get("waiver_value_result", {}).get("rank") or float("inf"),
            str(candidate.get("player") or "").casefold(),
            str(candidate.get("player_id") or ""),
        ))
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
        faab_inputs = {**(meta.get("faab_balance") or {}), "min_bid": ((league_payload or {}).get("settings") or {}).get("waiver_bid_min")}
        roster_capacity = len((league_payload or {}).get("roster_positions") or []) or None
        waiver_plan = build_waiver_plan(wda_roster, wda_candidates, team_needs, league_settings, faab_inputs, roster, meta.get("season"), meta.get("week"), bye_rows, schedule_rows, roster_capacity)
        selected_comparisons = []
        client_wda_candidates = []
        selected_bye_evidence = team_bye_evidence(bye_rows, season=meta.get("season"), team=normalize_team(selected_player.get("team")), week=meta.get("week")) if selected_player else None
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
            client_wda_candidates = relevant_candidates[:5]
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
                    faab_inputs,
                    roster_coverage_complete=pool_evidence.get("allowed") is True,
                    roster=roster,
                    season=meta.get("season"),
                    focus=selected_focus,
                    bye_evidence=selected_bye_evidence,
                    candidate_bye_evidence=waiver_slot_fill_inputs(candidate.get("team"), meta.get("season"), meta.get("week"), bye_rows, schedule_rows)[0],
                    candidate_game_context=waiver_slot_fill_inputs(candidate.get("team"), meta.get("season"), meta.get("week"), bye_rows, schedule_rows)[1],
                    roster_capacity=roster_capacity,
                    equivalent_alternatives=max(0, next((len(problem["claims"]) for problem in waiver_plan["problems"] if problem["selected_player_id"] == selected_player.get("player_id")), 0) - 1),
                )
            decision_order = {"ADD": 0, "PRELIMINARY_RECOMMENDATION": 1, "MONITOR": 2, "HOLD": 3, "BLOCKED": 4, "NO_ACTIONABLE_UPGRADE": 5}
            relevant_candidates.sort(key=lambda candidate: (
                decision_order.get((candidate.get("selected_comparison") or {}).get("decision"), 5),
                -float((candidate.get("selected_comparison") or {}).get("comparison_summary", {}).get("difference") or 0),
                -int((candidate.get("selected_comparison") or {}).get("comparison_summary", {}).get("sample_size") or 0),
                candidate.get("player") or "",
                candidate.get("player_id") or "",
            ))
            selected_comparisons = [
                candidate for candidate in relevant_candidates
                if (candidate.get("selected_comparison") or {}).get("decision") in {"ADD", "HOLD", "MONITOR", "PRELIMINARY_RECOMMENDATION"}
                and (candidate.get("selected_comparison") or {}).get("relevance_class") in {"MEANINGFUL_COMPARISON", "DIRECTIONAL_SIGNAL", "SLOT_FILL"}
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
        candidate_outcomes_by_id = {
            str(outcome.get("player_id")): outcome
            for outcome in waiver_candidate_outcomes
            if outcome.get("player_id")
        }
        for candidate in preliminary_suggestions:
            player_id = str(candidate.get("player_id") or "")
            evaluation = candidate.get("acquisition_evaluation") or {}
            value_result = candidate.get("waiver_value_result") or {}
            rank_text = "current-week" if value_result.get("horizon") == "this_week" else "rest-of-season"
            if value_result.get("state") == "TIED":
                message = f"Available; tied at {rank_text} consensus rank {value_result.get('rank'):g}."
            elif value_result.get("state") == "RANKED":
                message = f"Available; {rank_text} positional consensus rank {value_result.get('rank'):g} (position #{value_result.get('position_rank')})."
            else:
                message = f"Available, but unranked for {rank_text}: {value_result.get('reason') or 'consensus rank unavailable'}"
            roster_match = next((player for player in roster if str(player.get("source_player_id") or player.get("player_id") or "") == player_id), None)
            opportunity = candidate.get("opportunity_metrics") or {}
            support = candidate.get("waiver_supporting_evidence") or {}
            candidate_outcomes_by_id[player_id] = {
                "player_id": player_id,
                "player": candidate.get("player"),
                "team": candidate.get("nfl_team"),
                "position": candidate.get("position"),
                "message": message,
                "details": {
                    "recommendation_blockers": list(candidate.get("recommendation_blockers") or []),
                    "evidence_relevance": evaluation.get("evidence_relevance"),
                    "waiver_value": value_result,
                    "rankings": candidate.get("source_rankings") or {},
                    "ranking_horizon": ranking_horizon,
                    "rank_source": rankings.get("source", "FantasyPros consensus via DynastyProcess"),
                    "roster_fit": team_needs.get(str(candidate.get("position") or "").upper().replace("DST", "DEF"), {}),
                    "supporting_evidence": support,
                    "ownership": "VERIFIED_UNROSTERED" if roster_match is None else "ROSTERED",
                    "identity": candidate.get("identity_resolution") or {},
                    "health": {
                        "state": (candidate.get("evidence_context") or {}).get("health_state"),
                        "freshness": (candidate.get("evidence_context") or {}).get("health_freshness_state"),
                    },
                    "opportunity_state": opportunity.get("state"),
                    "bid_estimates": candidate.get("waiver_bid_estimates") or {},
                },
            }
        for candidate in monitor_candidates:
            player_id = str(candidate.get("player_id") or "")
            candidate_outcomes_by_id[player_id] = {
                "player_id": player_id,
                "player": candidate.get("player"),
                "team": candidate.get("nfl_team"),
                "position": candidate.get("position"),
                "message": "Health could not be verified.",
                "details": {"recommendation_blockers": list(candidate.get("recommendation_blockers") or [])},
            }
        waiver_candidate_outcomes = sorted(
            candidate_outcomes_by_id.values(),
            key=lambda outcome: (
                str(outcome.get("player") or "").casefold(),
                str(outcome.get("player_id") or ""),
            ),
        )
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
                **({"bye_evidence": selected_bye_evidence} if selected_bye_evidence and selected_context["position"] in {"K", "DEF"} else {}),
                "blockers": selected_blockers if no_safe_move else [],
            }
        candidate_by_id = {
            str(candidate.get("player_id") or ""): candidate
            for candidate in preliminary_suggestions
        }
        manager_position_sections = []
        for position in ("QB", "RB", "WR", "TE", "K", "DEF"):
            need = dict(team_needs.get(position) or {})
            plan_problem = next(
                (problem for problem in waiver_plan.get("problems") or [] if problem.get("position") == position),
                None,
            )
            options = []
            if plan_problem and plan_problem.get("claims"):
                for claim in plan_problem["claims"]:
                    candidate = candidate_by_id.get(str(claim.get("candidate_id") or ""), {})
                    options.append({
                        "candidate": candidate,
                        "claim": claim,
                        "value": candidate.get("waiver_value_result") or {},
                        "game_context": claim.get("game_context") or {},
                        "bye_evidence": claim.get("candidate_bye_evidence") or {},
                    })
            else:
                for candidate in preliminary_suggestions:
                    if str(candidate.get("position") or "").upper().replace("DST", "DEF") != position:
                        continue
                    bye_evidence, game_context = waiver_slot_fill_inputs(
                        candidate.get("nfl_team"), meta.get("season"), meta.get("week"), bye_rows, schedule_rows,
                    )
                    options.append({
                        "candidate": candidate,
                        "claim": None,
                        "value": candidate.get("waiver_value_result") or {},
                        "game_context": candidate.get("waiver_game_context") or game_context,
                        "bye_evidence": candidate.get("waiver_bye_evidence") or bye_evidence,
                    })
            options.sort(key=lambda option: (
                option.get("value", {}).get("position_rank") or 999,
                option.get("value", {}).get("rank") or float("inf"),
                str((option.get("candidate") or {}).get("player") or "").casefold(),
                str((option.get("candidate") or {}).get("player_id") or ""),
            ))
            all_ranked = bool(options) and all(option.get("value", {}).get("state") in {"RANKED", "TIED"} for option in options)
            unique_top = (
                len(options) > 1
                and all_ranked
                and options[0].get("value", {}).get("state") == "RANKED"
                and options[0].get("value", {}).get("position_rank") == 1
                and all(option.get("value", {}).get("rank") != options[0].get("value", {}).get("rank") for option in options[1:])
            )
            if need.get("state") != "AVAILABLE":
                need_message = "Roster need could not be verified."
            elif plan_problem and plan_problem.get("claims"):
                need_message = plan_problem.get("detail") or plan_problem.get("need") or "A verified one-week starter slot needs coverage."
            elif need.get("starter_shortage", 0):
                need_message = f"{need['starter_shortage']} required {position} starter slot(s) need filling."
            elif need.get("depth_shortage", 0):
                need_message = f"Roster depth is below the supported {position} target."
            else:
                need_message = f"No current {position} starter or depth shortage is verified."
            if plan_problem and plan_problem.get("claims"):
                label = "SLOT-FILL OPTION"
                explanation = (
                    f"This fills a verified one-week starter need and has the best fresh current consensus rank ({options[0]['value'].get('rank'):g}) among these options."
                    if unique_top else
                    "This fills a verified one-week starter need; available consensus ranks do not establish that it is better than the alternatives."
                )
            elif unique_top:
                label = "BEST SUPPORTED OPTION"
                explanation = f"Fresh {ranking_horizon.replace('_', ' ')} positional consensus ranks this player ahead of the available alternatives."
            elif options:
                label = "PLAYERS TO CONSIDER"
                explanation = "These are available options. Any shown current consensus ranks are supported; unranked or tied players are not separated by player-value evidence."
            else:
                label = "PASS"
                explanation = (
                    "Current availability could not be verified."
                    if pool_evidence and not pool_evidence.get("allowed")
                    else "No verified available players at this position."
                )
            manager_position_sections.append({
                "position": position,
                "need": need,
                "need_message": need_message,
                "label": label,
                "explanation": explanation,
                "options": options[:3],
                "more_options": options[3:],
                "available_count": len(options),
                "priority_need": need.get("strategic_need") == "ADD_STARTER",
            })
        manager_more_available = [
            option
            for section in manager_position_sections
            for option in section["more_options"]
        ][:12]
        explanation_key = " ".join(requested_explanation_name.split()).casefold()
        requested_outcomes = [
            outcome for outcome in waiver_candidate_outcomes
            if requested_explanation_name
            and " ".join(str(outcome.get("player") or "").split()).casefold() == explanation_key
        ]
        if requested_explanation_name and not requested_outcomes:
            normalized_query = "".join(character for character in explanation_key if character.isalnum())
            roster_match = next(
                (
                    player for player in roster
                    if "".join(character for character in str(player.get("player") or "").casefold() if character.isalnum()) == normalized_query
                ),
                None,
            )
            catalog_match = next(
                (
                    (str(player_id), player)
                    for player_id, player in (meta.get("sleeper_catalog") or {}).items()
                    if "".join(
                        character for character in str(player.get("full_name") or " ".join(str(player.get(key) or "") for key in ("first_name", "last_name"))).casefold()
                        if character.isalnum()
                    ) == normalized_query
                ),
                None,
            )
            if roster_match:
                requested_outcomes = [{
                    "player_id": str(roster_match.get("source_player_id") or roster_match.get("player_id") or ""),
                    "player": roster_match.get("player"),
                    "team": roster_match.get("nfl_team"),
                    "position": roster_match.get("position"),
                    "message": "Already rostered; not an available waiver candidate.",
                    "details": {"ownership": "ROSTERED", "identity": "RESOLVED", "health": {"state": roster_match.get("health_state"), "freshness": roster_match.get("health_freshness_state")}},
                }]
            else:
                catalog_player = catalog_match[1] if catalog_match else {}
                requested_outcomes = [{
                    "player_id": catalog_match[0] if catalog_match else None,
                    "player": str(catalog_player.get("full_name") or " ".join(str(catalog_player.get(key) or "") for key in ("first_name", "last_name"))).strip() or requested_explanation_name,
                    "team": catalog_player.get("team"),
                    "position": catalog_player.get("position"),
                    "message": "Not in the evaluated candidate pool; current waiver ownership, health, and rank could not be checked.",
                    "details": {
                        "ownership": "NOT_EVALUATED",
                        "identity": "CATALOG_MATCH" if catalog_match else "UNRESOLVED",
                        "health": {"state": catalog_player.get("injury_status") or "NOT_EVALUATED", "freshness": "UNAVAILABLE"},
                        "rankings": {},
                        "ranking_horizon": ranking_horizon,
                        "rank_source": rankings.get("source", "FantasyPros consensus via DynastyProcess"),
                        "roster_fit": team_needs.get(str(catalog_player.get("position") or "").upper().replace("DST", "DEF"), {}),
                        "supporting_evidence": {},
                    },
                }]
        for outcome in requested_outcomes:
            details = outcome.setdefault("details", {})
            player_id = str(outcome.get("player_id") or "")
            outcome_name = "".join(character for character in str(outcome.get("player") or "").casefold() if character.isalnum())
            candidate = next(
                (
                    item for item in source_candidates
                    if str(item.get("player_id") or "") == player_id
                    or "".join(character for character in str(item.get("player") or "").casefold() if character.isalnum()) == outcome_name
                ),
                None,
            )
            candidate = candidate or next((item for item in preliminary_suggestions if str(item.get("player_id") or "") == player_id), None)
            roster_match = next(
                (
                    player for player in roster
                    if str(player.get("source_player_id") or player.get("player_id") or "") == player_id
                    or "".join(character for character in str(player.get("player") or "").casefold() if character.isalnum()) == outcome_name
                ),
                None,
            )
            rank_lookup_id = str(
                (candidate or {}).get("player_id")
                or (roster_match or {}).get("source_player_id")
                or (roster_match or {}).get("player_id")
                or player_id
            )
            current_rank = (rankings.get("horizons", {}).get("this_week", {}).get("ranks", {}) or {}).get(rank_lookup_id)
            ros_rank = (rankings.get("horizons", {}).get("rest_of_season", {}).get("ranks", {}) or {}).get(rank_lookup_id)
            if candidate:
                details["ownership"] = "ROSTERED" if roster_match or str(outcome.get("message") or "").startswith("Already rostered") else "VERIFIED_UNROSTERED"
                details["identity"] = candidate.get("identity_resolution") or {"resolution_state": "UNRESOLVED"}
                context_evidence = candidate.get("evidence_context") or {}
                details["health"] = {"state": context_evidence.get("health_state"), "freshness": context_evidence.get("health_freshness_state")}
                details.setdefault("supporting_evidence", candidate.get("waiver_supporting_evidence") or {})
                details.setdefault("waiver_value", candidate.get("waiver_value_result") or {})
            elif roster_match:
                details["ownership"] = "ROSTERED"
                details["identity"] = {"resolution_state": "RESOLVED"}
                details["health"] = {"state": roster_match.get("health_state"), "freshness": roster_match.get("health_freshness_state")}
                details.setdefault("supporting_evidence", {})
            details.setdefault("rankings", {"this_week": current_rank, "rest_of_season": ros_rank})
            if str(outcome.get("message") or "").startswith("Already rostered"):
                details["ownership"] = "ROSTERED"
            else:
                details.setdefault("ownership", "ROSTERED" if roster_match else "NOT_EVALUATED")
            if isinstance(details.get("identity"), str):
                details["identity"] = {"resolution_state": details["identity"]}
            elif not isinstance(details.get("identity"), dict):
                details["identity"] = {"resolution_state": "RESOLVED" if roster_match else "UNRESOLVED"}
            if isinstance(details.get("health"), str):
                health_status = details.get("health_status")
                details["health"] = {
                    "state": _waiver_health_state(health_status) if health_status else "NOT_EVALUATED",
                    "freshness": details["health"],
                }
            elif not isinstance(details.get("health"), dict):
                details["health"] = {
                    "state": roster_match.get("health_state") if roster_match else "NOT_EVALUATED",
                    "freshness": roster_match.get("health_freshness_state") if roster_match else "UNAVAILABLE",
                }
            details.setdefault("ranking_horizon", ranking_horizon)
            details.setdefault("rank_source", rankings.get("source", "FantasyPros consensus via DynastyProcess"))
            details.setdefault("roster_fit", team_needs.get(str(outcome.get("position") or "").upper().replace("DST", "DEF"), {}))
            details.setdefault("final_rank", (details.get("waiver_value") or {}).get("position_rank"))
            details.setdefault(
                "final_rank_reason",
                (details.get("waiver_value") or {}).get("reason")
                or ("Not ranked because this player is already rostered." if roster_match else outcome.get("message")),
            )
        return render_template("waivers.html", title="Waiver and FAAB Center", context=context, meta=meta, recommendations=recommendations, preliminary_suggestions=preliminary_suggestions, monitor_candidates=monitor_candidates, health_excluded_diagnostics=pool_evidence["health_excluded_diagnostics"], waiver_candidate_outcomes=requested_outcomes, waiver_explain_player=requested_explanation_name, waiver_position_sections=manager_position_sections, waiver_more_available=manager_more_available, waiver_team_needs=team_needs, waiver_opportunity_status=waiver_opportunity_status, needs=needs, vacancies=vacancies, faab_budget=(meta.get("faab_balance") or {}).get("remaining"), faab_balance=meta.get("faab_balance") or {}, ranking_source=rankings, waiver_evidence=pool_evidence, opportunity_view=build_opportunity_view(current_app.config.get("OPPORTUNITY_EVIDENCE")), roster=roster, grades=grades, counts=counts, wda_roster=wda_roster, wda_candidates=client_wda_candidates, waiver_plan=waiver_plan, selected_player=selected_context, selected_focus=selected_focus, selected_result=selected_result, selected_comparisons=selected_comparisons, selected_screened_summary=selected_screened_summary, trending_evidence_state=trending_evidence.get("state"))

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
