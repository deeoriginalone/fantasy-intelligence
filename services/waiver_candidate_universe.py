"""W2 waiver candidate universe: decide which players can enter the waiver decision pipeline.

Pure and read-only. Discovery starts from Sleeper's current NFL player catalog keyed by exact Sleeper player ID
(never by name), keeps the six supported fantasy positions by Sleeper's primary position, removes every player on
any roster in the active league, and classifies the rest with Sleeper's own activity and NFL-team facts. The stale
local ``players`` table never decides who is discovered; when supplied it is lineage-only diagnostic context.

Availability stays fail-closed: when the catalog is unusable, or league ownership is stale, incomplete, or
contradictory, no candidate is published and nothing falls back to a local pool. Health, ranking, and roster
decisions are applied downstream by their existing contracts; this module never ranks, values, or submits anything.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence

from services.team_codes import canonical_team
from services.ux_evidence import (
    build_waiver_catalog_name_index,
    resolve_waiver_candidate_identity,
    waiver_evidence_contract,
    waiver_ownership_freshness,
    waiver_roster_coverage,
)
from services.waiver_roster_decision import SLOT_POSITIONS, consensus_rank, normalize_position, ranking_horizon_summary, ros_player_value

CONTRACT_ID = "waiver.candidate_universe.v1"
CATALOG_SOURCE = "Sleeper API /players/nfl"
SUPPORTED_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
NON_STARTER_SLOTS = {"BN", "BENCH", "IR", "TAXI"}
ROSTER_ID_FIELDS = ("players", "reserve", "taxi", "starters")
STAGES = (
    "CATALOG_RECORD_MALFORMED", "UNSUPPORTED_POSITION", "ROSTERED", "AVAILABILITY_UNVERIFIED", "POSITION_NOT_IN_LEAGUE",
    "IDENTITY_BLOCKED", "INACTIVE", "NO_NFL_TEAM", "ACTIVITY_UNKNOWN", "CANDIDATE",
)
FANTASY_STAGES = STAGES[2:]
ACTIVITY_BY_STAGE = {"CANDIDATE": "ACTIVE", "INACTIVE": "INACTIVE", "NO_NFL_TEAM": "INACTIVE", "ACTIVITY_UNKNOWN": "UNKNOWN",
                     "IDENTITY_BLOCKED": "BLOCKED", "CATALOG_RECORD_MALFORMED": "BLOCKED"}
CANDIDATE_TRACE = ("SLEEPER_CATALOG", "SUPPORTED_POSITION", "UNROSTERED_IN_LEAGUE", "LEAGUE_POSITION", "EXACT_SLEEPER_IDENTITY", "ACTIVE_ON_NFL_TEAM")
ACQUISITION_UNKNOWN_REASON = ("Sleeper's public API publishes no per-player waiver or free-agent status and no supported transaction-timing "
                              "contract exists, so waiver versus free-agent state is not determined.")
PROVIDER_TIMESTAMP_NOTE = "Sleeper's catalog response carries no provider timestamp; retrieved_at is this request's retrieval time."
HEALTH_GROUPS = ("healthy_eligible", "questionable_monitor_only", "health_non_actionable", "health_unverified")


def normalize_position(value: Any) -> str:
    value = str(value or "").strip().upper()
    return "DEF" if value == "DST" else value


def catalog_player_name(record: Mapping[str, Any] | None) -> str | None:
    record = record or {}
    name = str(record.get("full_name") or "").strip()
    if not name:
        name = " ".join(str(record.get(key) or "").strip() for key in ("first_name", "last_name") if str(record.get(key) or "").strip())
    return name or None


def lookup_key(value: Any) -> str:
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def league_positions(league: Mapping[str, Any] | None) -> set[str]:
    """Supported positions with at least one starting slot, including flex-eligible positions."""
    positions: set[str] = set()
    for slot in (league or {}).get("roster_positions") or []:
        slot = str(slot).strip().upper()
        if slot not in NON_STARTER_SLOTS:
            positions.update(SLOT_POSITIONS.get(slot, ()))
    return {position for position in positions if position in SUPPORTED_POSITIONS}


def _catalog_blocker(catalog: Any) -> str | None:
    if catalog is None:
        return "WAIVER_PLAYER_CATALOG_RETRIEVAL_FAILED"
    if not isinstance(catalog, Mapping) or not catalog:
        return "WAIVER_PLAYER_CATALOG_UNAVAILABLE"
    if not any(isinstance(record, Mapping) and normalize_position(record.get("position")) in SUPPORTED_POSITIONS for record in catalog.values()):
        return "WAIVER_PLAYER_CATALOG_NO_SUPPORTED_PLAYERS"
    return None


def league_ownership(*, league: Any, rosters: Any, league_id: Any = None, retrieved_at: Any = None, catalog_blocker: str | None = None,
                     now: Any = None) -> dict[str, Any]:
    """Current active-league ownership; any missing, incomplete, stale, or contradictory evidence blocks publication."""
    expected = league.get("total_rosters") if isinstance(league, Mapping) else None
    coverage = waiver_roster_coverage(rosters, expected)
    rosters_ok = isinstance(rosters, list) and all(isinstance(item, Mapping) and isinstance(item.get("players"), list) for item in rosters)
    holders: dict[str, list[str | None]] = {}
    for item in rosters if isinstance(rosters, list) else []:
        if not isinstance(item, Mapping):
            continue
        roster_id = None if item.get("roster_id") in (None, "") else str(item.get("roster_id"))
        roster_player_ids = {str(value).strip() for field in ROSTER_ID_FIELDS for value in item.get(field) or [] if value is not None}
        for player_id in roster_player_ids - {"", "0"}:
            holders.setdefault(player_id, []).append(roster_id)
    duplicates = sorted(player_id for player_id, rosters_holding in holders.items() if len(rosters_holding) > 1)
    if rosters is None:
        blocker = "WAIVER_OWNERSHIP_RETRIEVAL_FAILED"
    elif catalog_blocker:
        blocker = catalog_blocker
    elif not rosters_ok:
        blocker = "WAIVER_ROSTER_DATA_INCOMPLETE"
    elif coverage["blockers"]:
        blocker = coverage["blockers"][0]
    else:
        blocker = None
    freshness = waiver_ownership_freshness(source_record_time=None, retrieved_at=retrieved_at, source="Sleeper API", now=now)
    contract = waiver_evidence_contract(
        domain="waiver ownership", league_id=league_id, source="Sleeper API", source_record_time=None, retrieved_at=retrieved_at,
        age=freshness["age"], freshness_threshold_id=freshness["freshness_threshold_id"], freshness_state=freshness["freshness_state"],
        completeness_state="COMPLETE" if not blocker else "INCOMPLETE", blocker=blocker or freshness["blocker"], recommendation_impact="BLOCKED",
        expected_active_roster_count=coverage["expected_active_roster_count"], observed_active_roster_count=coverage["observed_active_roster_count"],
        unique_owned_player_ids=holders, duplicate_conflicts=duplicates, require_roster_coverage=True,
    )
    contract.update(owned_player_ids=set(holders), roster_holders=holders, roster_coverage=coverage)
    return contract


def local_lineage_index(local_rows: Sequence[Mapping[str, Any]] | None, catalog: Mapping[str, Any] | None,
                        name_normalizer: Callable[[Any], str] | None) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    """Map Sleeper IDs to the stale local preseason row the pre-W2 name resolver used; lineage only, never identity."""
    summary = {"local_rows": 0, "prior_resolved": 0, "prior_conflicting": 0, "prior_ambiguous": 0, "prior_unresolved": 0, "prior_unsupported": 0}
    index: dict[str, dict[str, Any]] = {}
    if not local_rows or not isinstance(catalog, Mapping) or name_normalizer is None:
        return index, summary
    name_index = build_waiver_catalog_name_index(catalog, name_normalizer)
    for row in local_rows:
        summary["local_rows"] += 1
        prior = resolve_waiver_candidate_identity({"player": row.get("player"), "position": row.get("position"), "nfl_team": row.get("nfl_team")},
                                                  catalog, name_normalizer, name_index)
        state = prior["resolution_state"]
        key = f"prior_{state.lower()}"
        summary[key] = summary.get(key, 0) + 1
        matches = name_index.get(name_normalizer(row.get("player") or ""), [])
        if len(matches) == 1:
            index.setdefault(matches[0][0], {
                "local_player": row.get("player"), "local_position": normalize_position(row.get("position")) or None, "local_team": row.get("nfl_team"),
                "prior_resolution_state": state, "conflicting_fields": list(prior.get("conflicting_fields") or []),
                "match_method": "UNIQUE_NORMALIZED_NAME", "decision_effect": "LINEAGE_ONLY",
            })
    return index, summary


def classify_catalog_entry(player_id: Any, record: Any, *, holders: Mapping[str, Any], my_player_ids: set[str] | frozenset[str] = frozenset(),
                           ownership_allowed: bool, positions: set[str] | frozenset[str]) -> dict[str, Any]:
    """Place one Sleeper catalog record in exactly one discovery stage using only Sleeper facts and league ownership."""
    pid = str(player_id or "").strip()
    rostered = bool(pid) and pid in holders
    if not isinstance(record, Mapping) or not pid or str(record.get("player_id") or pid).strip() != pid:
        return {"player_id": pid or None, "player": None, "position": None, "team": None, "stage": "CATALOG_RECORD_MALFORMED", "activity_state": "BLOCKED",
                "rostered": rostered, "rostered_by_me": rostered and pid in my_player_ids}
    position = normalize_position(record.get("position"))
    team_raw = str(record.get("team") or "").strip().upper()
    team = canonical_team(team_raw)
    name = catalog_player_name(record)
    entry = {
        "player_id": pid, "player": name, "position": position or None, "team": team or team_raw or None,
        "sleeper_status": record.get("status"), "injury_status": record.get("injury_status"), "active": record.get("active"),
        "fantasy_positions": [normalize_position(value) for value in record.get("fantasy_positions") or [] if value],
        "rostered": rostered, "rostered_by_me": rostered and pid in my_player_ids,
    }
    if position not in SUPPORTED_POSITIONS:
        stage = "UNSUPPORTED_POSITION"
    elif rostered:
        stage = "ROSTERED"
    elif not ownership_allowed:
        stage = "AVAILABILITY_UNVERIFIED"
    elif position not in positions:
        stage = "POSITION_NOT_IN_LEAGUE"
    elif not name or (team_raw and team is None):
        stage = "IDENTITY_BLOCKED"
    elif record.get("active") is False:
        stage = "INACTIVE"
    elif record.get("active") is not True:
        stage = "ACTIVITY_UNKNOWN"
    elif team is None:
        stage = "NO_NFL_TEAM"
    else:
        stage = "CANDIDATE"
    entry["stage"] = stage
    entry["activity_state"] = ACTIVITY_BY_STAGE.get(stage)
    return entry


def _lineage_view(local: Mapping[str, Any] | None, entry: Mapping[str, Any]) -> dict[str, Any]:
    if not local:
        return {"state": "NO_LOCAL_ROW", "decision_effect": "LINEAGE_ONLY",
                "note": "No local preseason row resolves to this player; discovered from Sleeper's current catalog only."}
    state = "PRIOR_POOL_RESOLVED" if local["prior_resolution_state"] == "RESOLVED" else "PRIOR_POOL_UNPUBLISHABLE"
    conflicts = list(local.get("conflicting_fields") or [])
    note = (f"Stale local row lists {local.get('local_team') or 'no team'} {local.get('local_position') or ''}".strip()
            + f"; current Sleeper facts ({entry['team']} {entry['position']}) are used." if conflicts else "Local preseason row agrees with current Sleeper team and position.")
    return {**local, "state": state, "note": note}


def _candidate(entry: Mapping[str, Any], record: Mapping[str, Any], *, retrieved_at: Any, lineage: Mapping[str, Any]) -> dict[str, Any]:
    pid, name, position, team = entry["player_id"], entry["player"], entry["position"], entry["team"]
    identity = {
        "input_reference": name, "input_player_id": pid, "resolved_player_id": pid, "resolution_state": "RESOLVED", "resolution_method": "DIRECT_SLEEPER_ID",
        "candidate_name": name, "candidate_team": team, "candidate_position": position, "catalog_name": name, "catalog_team": team, "catalog_position": position,
        "corroborating_fields": [], "conflicting_fields": [], "candidate_source": "Sleeper player catalog", "catalog_source": "Sleeper player catalog",
        "completeness_state": "COMPLETE", "blocker": None, "recommendation_impact": "AVAILABLE",
    }
    return {
        "player_id": pid, "player": name, "position": position, "nfl_team": team,
        # Stale local preseason values are never attached to Sleeper-discovered candidates.
        "rank": None, "projection": None, "tier": None, "adp": None, "bye_week": None, "pick_no": None, "round": None,
        "projection_retrieved_at": None, "local_player_id": None,
        "opportunity_player_id": record.get("gsis_id") or None,
        "sleeper_espn_id": record.get("espn_id"),
        "sleeper_depth_chart_position": record.get("depth_chart_position"),
        "sleeper_depth_chart_order": record.get("depth_chart_order"),
        "sleeper_news_updated": record.get("news_updated"),
        "sleeper_catalog_retrieved_at": retrieved_at,
        "identity_resolution": identity,
        "candidate_discovery": {
            "contract_id": CONTRACT_ID, "source": CATALOG_SOURCE, "stage": "CANDIDATE", "trace": list(CANDIDATE_TRACE), "activity_state": "ACTIVE",
            "sleeper_status": entry.get("sleeper_status"), "sleeper_injury_status": entry.get("injury_status"), "fantasy_positions": entry.get("fantasy_positions") or [],
            "acquisition_state": "UNKNOWN", "local_lineage": _lineage_view(lineage.get(pid), entry),
        },
    }


def _blank_counts() -> dict[str, Any]:
    counts = {stage.lower(): 0 for stage in STAGES}
    counts.update(catalog_entries=0, fantasy_relevant=0, candidates_by_position={position: 0 for position in SUPPORTED_POSITIONS},
                  sleeper_only_candidates=0, prior_pool_candidates=0, local_conflicts_overridden=0, owned_ids_not_in_catalog=0)
    return counts


def build_waiver_candidate_universe(*, catalog: Any, rosters: Any, league: Any, league_id: Any = None, retrieved_at: Any = None,
                                    my_player_ids: Iterable[Any] = (), local_rows: Sequence[Mapping[str, Any]] | None = None,
                                    name_normalizer: Callable[[Any], str] | None = None, now: Any = None) -> dict[str, Any]:
    """Return the waiver.candidate_universe.v1 contract: discovered candidates, stage classifications, and reconcilable counts."""
    catalog_blocker = _catalog_blocker(catalog)
    positions = league_positions(league if isinstance(league, Mapping) else {})
    ownership = league_ownership(league=league, rosters=rosters, league_id=league_id, retrieved_at=retrieved_at, catalog_blocker=catalog_blocker, now=now)
    mine = {str(value) for value in my_player_ids or [] if value not in (None, "")}
    counts = _blank_counts()
    candidates: list[dict[str, Any]] = []
    stage_by_player: dict[str, str] = {}
    lineage_summary = local_lineage_index(None, None, None)[1]
    if not catalog_blocker:
        lineage, lineage_summary = local_lineage_index(local_rows, catalog, name_normalizer)
        holders = ownership["roster_holders"]
        counts["catalog_entries"] = len(catalog)
        for player_id, record in catalog.items():
            entry = classify_catalog_entry(player_id, record, holders=holders, my_player_ids=mine, ownership_allowed=ownership["allowed"], positions=positions)
            counts[entry["stage"].lower()] += 1
            if entry["player_id"]:
                stage_by_player[entry["player_id"]] = entry["stage"]
            if entry["stage"] == "CANDIDATE":
                candidate = _candidate(entry, record, retrieved_at=retrieved_at, lineage=lineage)
                candidates.append(candidate)
                counts["candidates_by_position"][candidate["position"]] += 1
                lineage_state = candidate["candidate_discovery"]["local_lineage"]["state"]
                counts["prior_pool_candidates" if lineage_state == "PRIOR_POOL_RESOLVED" else "sleeper_only_candidates"] += 1
                counts["local_conflicts_overridden"] += bool(candidate["candidate_discovery"]["local_lineage"].get("conflicting_fields"))
        counts["fantasy_relevant"] = sum(counts[stage.lower()] for stage in FANTASY_STAGES)
        counts["owned_ids_not_in_catalog"] = sum(1 for player_id in holders if player_id not in catalog)
    candidates.sort(key=lambda item: (SUPPORTED_POSITIONS.index(item["position"]), str(item["player"] or "").casefold(), item["player_id"]))
    position_blocker = None if positions else "WAIVER_ROSTER_POSITION_RULES_UNAVAILABLE"
    ownership_blocker = None if ownership["allowed"] else ownership.get("blocker") or "WAIVER_OWNERSHIP_UNVERIFIED"
    blockers = list(dict.fromkeys(blocker for blocker in (catalog_blocker, ownership_blocker, position_blocker) if blocker))
    reconciliation = {
        "catalog": counts["catalog_entries"] == counts["catalog_record_malformed"] + counts["unsupported_position"] + counts["fantasy_relevant"],
        "fantasy_relevant": counts["fantasy_relevant"] == sum(counts[stage.lower()] for stage in FANTASY_STAGES),
        "candidates": counts["candidate"] == len(candidates) == sum(counts["candidates_by_position"].values()) == counts["sleeper_only_candidates"] + counts["prior_pool_candidates"],
    }
    return {
        "contract_id": CONTRACT_ID, "universe_state": "BLOCKED" if blockers else "AVAILABLE", "blockers": blockers, "source": CATALOG_SOURCE,
        "retrieval": {"retrieved_at": retrieved_at, "provider_timestamp": None, "note": PROVIDER_TIMESTAMP_NOTE},
        "completeness_state": "COMPLETE" if not blockers else "INCOMPLETE", "ownership": ownership, "league_positions": sorted(positions, key=SUPPORTED_POSITIONS.index),
        "candidates": candidates if not blockers else [], "stage_by_player": stage_by_player, "counts": counts, "reconciliation": reconciliation,
        "reconciles": all(reconciliation.values()), "local_lineage": {**lineage_summary, "decision_effect": "LINEAGE_ONLY",
                                                                       "role": "Diagnostic only: the local preseason table no longer controls discovery."},
        "acquisition": {"state": "UNKNOWN", "reason": ACQUISITION_UNKNOWN_REASON},
        "uses_local_players_table_for_discovery": False, "decision_effect": "DISCOVERY_ONLY",
    }


def candidate_health_group(candidate: Mapping[str, Any]) -> str:
    """Map an evaluated candidate's existing W1 health disposition to one universe health group."""
    if candidate.get("candidate_disposition") == "PRELIMINARY_SUGGESTION":
        return "healthy_eligible"
    if candidate.get("recommendation_state") == "NON_ACTIONABLE_HEALTH":
        return "questionable_monitor_only" if candidate.get("normalized_health_state") == "QUESTIONABLE" else "health_non_actionable"
    return "health_unverified"


def candidate_universe_funnel(universe: Mapping[str, Any] | None, *, published_candidates: Sequence[Mapping[str, Any]], rankings: Mapping[str, Any] | None,
                              full_ppr: bool, season: Any, week: Any) -> dict[str, Any]:
    """Reconcile discovered candidates through publication, health, provider identity, fresh current-week rank, and rest-of-season rank."""
    universe = universe or {}
    discovered = len(universe.get("candidates") or [])
    published = [dict(candidate) for candidate in published_candidates or []]
    health = {group: 0 for group in HEALTH_GROUPS}
    this_week = ((rankings or {}).get("horizons") or {}).get("this_week") or {}
    ranks_usable = full_ppr is True and this_week.get("state") == "AVAILABLE" and bool(this_week.get("ranks"))
    ros_summary = ranking_horizon_summary(rankings, "rest_of_season", full_ppr=full_ppr)
    ros = {"state": ros_summary["state"], "source_date": ros_summary["source_date"], "freshness_state": ros_summary["freshness_state"],
           "ranked": 0, "unranked": 0, "materiality_capable": 0, "by_position": {}, "states": {}}
    ranked = ranked_healthy = provider_resolved = 0
    for candidate in published:
        group = candidate_health_group(candidate)
        health[group] += 1
        rank = consensus_rank(this_week, candidate.get("player_id"), position=candidate.get("position"), horizon="this_week", season=season, week=week) if ranks_usable else {"state": "UNRANKED"}
        if rank["state"] == "RANKED":
            ranked += 1
            ranked_healthy += group == "healthy_eligible"
        provider_resolved += candidate.get("opportunity_identity_state") == "RESOLVED"
        # A missing rest-of-season rank or crosswalk only labels the player; it never removes him from the universe.
        ros_view = ros_player_value(ros_summary, rankings, candidate.get("player_id"), candidate.get("position"), season=season)
        ros_state = ros_view["evidence_state"]
        ros["states"][ros_state] = ros["states"].get(ros_state, 0) + 1
        bucket = ros["by_position"].setdefault(normalize_position(candidate.get("position")), {"ranked": 0, "unranked": 0, "materiality_capable": 0})
        bucket["ranked" if ros_state == "RANKED" else "unranked"] += 1
        ros["ranked" if ros_state == "RANKED" else "unranked"] += 1
        capable = ros_view["range_state"] == "VALID"
        bucket["materiality_capable"] += capable
        ros["materiality_capable"] += capable
    counts = {
        "discovered": discovered, "published": len(published), "not_published": discovered - len(published), "health": health,
        "ranked": ranked, "unranked": len(published) - ranked, "ranked_healthy_eligible": ranked_healthy,
        "provider_identity_resolved": provider_resolved, "provider_identity_unavailable": len(published) - provider_resolved,
        "ranking_state": "AVAILABLE" if ranks_usable else "UNAVAILABLE", "ros": ros,
    }
    counts["reconciles"] = (
        sum(health.values()) == len(published) == counts["ranked"] + counts["unranked"]
        == counts["provider_identity_resolved"] + counts["provider_identity_unavailable"] == ros["ranked"] + ros["unranked"]
        and counts["published"] + counts["not_published"] == discovered
    )
    return counts


STAGE_EXPLANATIONS = {
    "CATALOG_RECORD_MALFORMED": ("IDENTITY EVIDENCE MISSING", "Sleeper's catalog record for this player is malformed, so no identity can be verified."),
    "UNSUPPORTED_POSITION": ("UNSUPPORTED POSITION", "Sleeper lists a primary position outside QB, RB, WR, TE, K and DEF, so waivers do not evaluate this player."),
    "AVAILABILITY_UNVERIFIED": ("AVAILABILITY UNVERIFIED", "League ownership could not be verified, so no player is treated as available."),
    "POSITION_NOT_IN_LEAGUE": ("POSITION NOT IN LEAGUE", "This league has no lineup slot for the player's position."),
    "IDENTITY_BLOCKED": ("IDENTITY EVIDENCE MISSING", "Sleeper's record lacks a name or lists an unrecognized NFL team, so identity cannot be verified."),
    "INACTIVE": ("INACTIVE", "Available in this league, but Sleeper lists the player as inactive; not a current-week option."),
    "NO_NFL_TEAM": ("NO CURRENT NFL TEAM", "Available in this league, but Sleeper lists no current NFL team, so he has no game this week; not a current-week option."),
    "ACTIVITY_UNKNOWN": ("ACTIVITY UNKNOWN", "Available in this league, but Sleeper did not supply an activity flag; not a current-week option."),
    "CANDIDATE": ("AVAILABLE", "Available in this league and checked as a current waiver candidate."),
}


def explain_catalog_player(universe: Mapping[str, Any] | None, catalog: Mapping[str, Any] | None, player_id: Any, *, my_player_ids: Iterable[Any] = ()) -> dict[str, Any]:
    """Player-specific lookup explanation from the universe classification of one exact Sleeper ID."""
    universe = universe or {}
    catalog = catalog if isinstance(catalog, Mapping) else {}
    pid = str(player_id or "")
    record = catalog.get(pid)
    ownership = universe.get("ownership") or {}
    entry = classify_catalog_entry(pid, record, holders=ownership.get("roster_holders") or {}, my_player_ids={str(value) for value in my_player_ids or []},
                                   ownership_allowed=ownership.get("allowed") is True, positions=set(universe.get("league_positions") or []))
    stage = universe.get("stage_by_player", {}).get(pid, entry["stage"])
    if entry.get("rostered"):
        label = "ROSTERED"
        message = "Already rostered; not an available waiver candidate." if entry.get("rostered_by_me") else "Rostered by another team in this league; not available."
    else:
        label, message = STAGE_EXPLANATIONS.get(stage, ("AVAILABILITY UNVERIFIED", "Current availability could not be verified."))
    if stage == "UNSUPPORTED_POSITION" and entry.get("fantasy_positions"):
        message += f" Sleeper fantasy positions: {', '.join(entry['fantasy_positions'])}; only the primary position is evaluated."
    return {
        "player_id": pid or None, "player": entry.get("player"), "team": entry.get("team"), "position": entry.get("position"), "message": message,
        "state": label,
        "details": {
            "ownership": "ROSTERED" if entry.get("rostered") else "UNVERIFIED" if stage == "AVAILABILITY_UNVERIFIED" or not ownership.get("allowed") else "VERIFIED_UNROSTERED",
            "identity": {"resolution_state": "RESOLVED" if stage not in {"CATALOG_RECORD_MALFORMED", "IDENTITY_BLOCKED"} else "BLOCKED", "resolution_method": "DIRECT_SLEEPER_ID"},
            "discovery_stage": stage, "discovery_state": label, "activity_state": entry.get("activity_state"),
            "sleeper_status": entry.get("sleeper_status"), "sleeper_injury_status": entry.get("injury_status"), "sleeper_active": entry.get("active"),
            "fantasy_positions": entry.get("fantasy_positions") or [], "acquisition_state": "UNKNOWN", "source": CATALOG_SOURCE,
        },
    }


def find_catalog_players(catalog: Mapping[str, Any] | None, query: Any) -> list[str]:
    """Exact Sleeper IDs whose current catalog name matches a manager's search text (alphanumeric, case-insensitive)."""
    key = lookup_key(query)
    if not key or not isinstance(catalog, Mapping):
        return []
    return sorted(str(player_id) for player_id, record in catalog.items() if isinstance(record, Mapping) and lookup_key(catalog_player_name(record)) == key)
