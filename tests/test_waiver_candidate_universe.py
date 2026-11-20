"""Focused tests for the W2 waiver candidate universe (services/waiver_candidate_universe.py)."""
from datetime import datetime, timedelta, timezone

import pytest

from services.waiver_candidate_universe import (
    build_waiver_candidate_universe,
    candidate_universe_funnel,
    explain_catalog_player,
    find_catalog_players,
)

NOW = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)
LEAGUE = {"total_rosters": 2, "roster_positions": ["QB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"]}


def normalize(value):
    return "".join(character for character in str(value or "").lower() if character.isalnum())


def record(player_id, name, position, team="KC", *, active=True, status="Active", injury=None, **extra):
    first, _, last = name.partition(" ")
    return {"player_id": player_id, "full_name": name, "first_name": first, "last_name": last, "position": position, "team": team,
            "active": active, "status": status, "injury_status": injury, "fantasy_positions": [position], **extra}


def defense(team, first, last, position="DEF"):
    return {"player_id": team, "first_name": first, "last_name": last, "position": position, "team": team, "active": True, "fantasy_positions": ["DEF"], "injury_status": None}


def rosters(mine=(), other=(), **extra_fields):
    return [{"roster_id": 1, "owner_id": "me", "players": list(mine), "starters": [], **extra_fields},
            {"roster_id": 2, "owner_id": "them", "players": list(other), "starters": []}]


def build(catalog, *, roster_list=None, league=LEAGUE, local_rows=None, retrieved_at=NOW, **kwargs):
    return build_waiver_candidate_universe(catalog=catalog, rosters=rosters() if roster_list is None else roster_list, league=league, league_id="L1",
                                           retrieved_at=retrieved_at.isoformat() if retrieved_at else None, now=NOW, local_rows=local_rows,
                                           name_normalizer=normalize, **kwargs)


def candidate_ids(universe):
    return [candidate["player_id"] for candidate in universe["candidates"]]


def test_current_sleeper_player_without_a_local_row_is_discovered_by_exact_id():
    universe = build({"9001": record("9001", "Rookie Receiver", "WR", "MIA")}, local_rows=[{"player": "Old Veteran", "position": "WR", "nfl_team": "DAL"}])
    candidate = universe["candidates"][0]
    assert universe["universe_state"] == "AVAILABLE" and universe["uses_local_players_table_for_discovery"] is False
    assert (candidate["player_id"], candidate["player"], candidate["position"], candidate["nfl_team"]) == ("9001", "Rookie Receiver", "WR", "MIA")
    assert candidate["identity_resolution"]["resolution_method"] == "DIRECT_SLEEPER_ID" and candidate["identity_resolution"]["resolved_player_id"] == "9001"
    assert candidate["candidate_discovery"]["local_lineage"]["state"] == "NO_LOCAL_ROW" and universe["counts"]["sleeper_only_candidates"] == 1
    assert (candidate["projection"], candidate["rank"], candidate["tier"]) == (None, None, None)
    assert candidate["candidate_discovery"]["acquisition_state"] == "UNKNOWN" and universe["acquisition"]["state"] == "UNKNOWN"


def test_players_on_any_league_roster_including_reserve_and_taxi_are_excluded():
    catalog = {player_id: record(player_id, f"Player {player_id}", "RB") for player_id in ("1", "2", "3", "4", "5")}
    universe = build(catalog, roster_list=rosters(mine=["1"], other=["2"], reserve=["3"], taxi=["4"]))
    assert candidate_ids(universe) == ["5"]
    assert {player_id: universe["stage_by_player"][player_id] for player_id in "1234"} == dict.fromkeys("1234", "ROSTERED")
    assert universe["counts"]["rostered"] == 4 and universe["ownership"]["owned_player_ids"] == {"1", "2", "3", "4"}


@pytest.mark.parametrize("roster_list,league,retrieved_at,blocker", [
    (None, LEAGUE, NOW, "WAIVER_OWNERSHIP_RETRIEVAL_FAILED"),
    (rosters(), {**LEAGUE, "total_rosters": 3}, NOW, "WAIVER_ROSTER_COVERAGE_INCOMPLETE"),
    ([{"roster_id": 1, "players": None}, {"roster_id": 2, "players": []}], LEAGUE, NOW, "WAIVER_ROSTER_DATA_INCOMPLETE"),
    (rosters(), LEAGUE, NOW - timedelta(hours=2), "WAIVER_OWNERSHIP_STALE"),
])
def test_unavailable_incomplete_or_stale_ownership_blocks_publication(roster_list, league, retrieved_at, blocker):
    catalog = {"7": record("7", "Free Agent WR", "WR")}
    universe = build_waiver_candidate_universe(catalog=catalog, rosters=roster_list, league=league, league_id="L1", retrieved_at=retrieved_at.isoformat(), now=NOW)
    assert universe["universe_state"] == "BLOCKED" and universe["blockers"] == [blocker] and universe["candidates"] == []
    assert universe["ownership"]["allowed"] is False and universe["stage_by_player"]["7"] == "AVAILABILITY_UNVERIFIED"
    assert explain_catalog_player(universe, catalog, "7")["state"] == "AVAILABILITY UNVERIFIED"


@pytest.mark.parametrize("roster_list,blocker", [
    ([{"roster_id": 1, "players": ["1"]}, {"roster_id": 1, "players": []}], "WAIVER_DUPLICATE_ROSTER_IDS"),
    (rosters(mine=["1"], other=["1"]), "WAIVER_DUPLICATE_OWNERSHIP"),
])
def test_duplicate_roster_or_ownership_data_fails_closed(roster_list, blocker):
    universe = build({"1": record("1", "Shared WR", "WR"), "2": record("2", "Free WR", "WR")}, roster_list=roster_list)
    assert universe["universe_state"] == "BLOCKED" and universe["blockers"] == [blocker] and universe["candidates"] == []


@pytest.mark.parametrize("position,expected", [("QB", "QB"), ("RB", "RB"), ("WR", "WR"), ("TE", "TE"), ("K", "K"), ("DEF", "DEF"), ("DST", "DEF")])
def test_each_supported_fantasy_position_reaches_the_universe(position, expected):
    catalog = {"SEA": defense("SEA", "Seattle", "Seahawks", position)} if expected == "DEF" else {"100": record("100", "Candidate Player", position)}
    candidate = build(catalog)["candidates"][0]
    assert candidate["position"] == expected
    if expected == "DEF":
        assert (candidate["player_id"], candidate["player"], candidate["nfl_team"]) == ("SEA", "Seattle Seahawks", "SEA")


def test_unsupported_positions_are_excluded_but_counted_and_explained():
    catalog = {"1": record("1", "Line Backer", "LB"), "2": record("2", "Guard Man", "OL"), "3": record("3", "Punt Guy", "P", fantasy_positions=["K", "P"]),
               "4": record("4", "Full Back", "FB", fantasy_positions=["RB"]), "5": {"player_id": "5", "full_name": "No Position", "active": True}, "6": record("6", "Real Back", "RB")}
    universe = build(catalog)
    assert candidate_ids(universe) == ["6"] and universe["counts"]["unsupported_position"] == 5
    explanation = explain_catalog_player(universe, catalog, "4")
    assert explanation["state"] == "UNSUPPORTED POSITION" and "Sleeper fantasy positions: RB" in explanation["message"]


def test_exact_sleeper_id_controls_identity_for_players_who_share_a_name():
    catalog = {"11": record("11", "Mike Williams", "WR", "NYJ"), "22": record("22", "Mike Williams", "WR", "LAC")}
    universe = build(catalog, local_rows=[{"player": "Mike Williams", "position": "WR", "nfl_team": "NYJ"}])
    assert [(candidate["player_id"], candidate["nfl_team"]) for candidate in universe["candidates"]] == [("11", "NYJ"), ("22", "LAC")]
    assert {candidate["candidate_discovery"]["local_lineage"]["state"] for candidate in universe["candidates"]} == {"NO_LOCAL_ROW"}
    assert universe["local_lineage"]["prior_ambiguous"] == 1 and find_catalog_players(catalog, "mike williams") == ["11", "22"]


def test_stale_local_team_and_position_never_override_current_sleeper_facts():
    catalog = {"30": record("30", "Traded Receiver", "WR", "PHI"), "31": record("31", "Moved Back", "WR", "SF"), "32": record("32", "Steady Tight End", "TE", "GB")}
    local_rows = [{"player": "Traded Receiver", "position": "WR", "nfl_team": "DAL"}, {"player": "Moved Back", "position": "RB", "nfl_team": "SF"},
                  {"player": "Steady Tight End", "position": "TE", "nfl_team": "GB"}]
    universe = build(catalog, local_rows=local_rows)
    by_id = {candidate["player_id"]: candidate for candidate in universe["candidates"]}
    traded, moved, steady = (by_id[player_id]["candidate_discovery"]["local_lineage"] for player_id in ("30", "31", "32"))
    assert (by_id["30"]["nfl_team"], traded["local_team"], traded["conflicting_fields"], traded["state"]) == ("PHI", "DAL", ["team"], "PRIOR_POOL_UNPUBLISHABLE")
    assert traded["note"] == "Stale local row lists DAL WR; current Sleeper facts (PHI WR) are used."
    assert (by_id["31"]["position"], moved["local_position"], moved["conflicting_fields"]) == ("WR", "RB", ["position"])
    assert steady["state"] == "PRIOR_POOL_RESOLVED" and steady["decision_effect"] == "LINEAGE_ONLY"
    counts = universe["counts"]
    assert (counts["local_conflicts_overridden"], counts["sleeper_only_candidates"], counts["prior_pool_candidates"]) == (2, 2, 1)


def test_inactive_no_team_and_unknown_activity_players_are_retained_not_deleted():
    catalog = {"40": record("40", "Unsigned Veteran", "RB", None), "41": record("41", "Retired Passer", "QB", None, active=False, status="Inactive"),
               "42": {**record("42", "Mystery Kicker", "K"), "active": None}, "43": record("43", "Injured Starter", "QB", "BAL", status="Inactive", injury="IR")}
    universe = build(catalog)
    assert candidate_ids(universe) == ["43"]
    assert {player_id: universe["stage_by_player"][player_id] for player_id in ("40", "41", "42")} == {"40": "NO_NFL_TEAM", "41": "INACTIVE", "42": "ACTIVITY_UNKNOWN"}
    no_team = explain_catalog_player(universe, catalog, "40")
    assert no_team["state"] == "NO CURRENT NFL TEAM" and no_team["message"].startswith("Available in this league")
    assert no_team["details"]["ownership"] == "VERIFIED_UNROSTERED" and no_team["details"]["activity_state"] == "INACTIVE"
    assert explain_catalog_player(universe, catalog, "41")["state"] == "INACTIVE" and explain_catalog_player(universe, catalog, "42")["state"] == "ACTIVITY UNKNOWN"


def test_counts_reconcile_across_every_discovery_stage():
    catalog = {"1": record("1", "Owned Back", "RB"), "2": record("2", "Free Back", "RB"), "3": record("3", "Edge Rusher", "DE"), "4": record("4", "Gone Guy", "WR", None, active=False),
               "5": record("5", "Street Free", "TE", None), "6": "malformed", "7": {**record("7", "Wrong Key", "WR"), "player_id": "8"}, "SF": defense("SF", "San Francisco", "49ers")}
    universe = build(catalog, roster_list=rosters(mine=["1"]))
    counts = universe["counts"]
    assert universe["reconciles"] is True and all(universe["reconciliation"].values())
    assert (counts["catalog_entries"], counts["catalog_record_malformed"], counts["unsupported_position"], counts["fantasy_relevant"]) == (8, 2, 1, 5)
    assert (counts["rostered"], counts["inactive"], counts["no_nfl_team"], counts["candidate"]) == (1, 1, 1, 2)
    assert counts["candidates_by_position"] == {"QB": 0, "RB": 1, "WR": 0, "TE": 0, "K": 0, "DEF": 1}


def test_no_discovery_cap_hides_supported_players():
    catalog = {str(index): record(str(index), f"Depth Receiver {index:04d}", "WR", "CHI") for index in range(1500)}
    universe = build(catalog)
    assert len(universe["candidates"]) == universe["counts"]["candidate"] == 1500


def test_defense_identity_ownership_and_dst_alias_stay_exact():
    catalog = {"SF": defense("SF", "San Francisco", "49ers"), "SEA": defense("SEA", "Seattle", "Seahawks"), "LAR": defense("LAR", "Los Angeles", "Rams", "DST")}
    universe = build(catalog, roster_list=rosters(other=["SF"]))
    assert [(candidate["player_id"], candidate["position"], candidate["nfl_team"]) for candidate in universe["candidates"]] == [("LAR", "DEF", "LAR"), ("SEA", "DEF", "SEA")]
    assert universe["stage_by_player"]["SF"] == "ROSTERED" and explain_catalog_player(universe, catalog, "SF")["message"] == "Rostered by another team in this league; not available."


@pytest.mark.parametrize("catalog,blocker", [
    (None, "WAIVER_PLAYER_CATALOG_RETRIEVAL_FAILED"),
    ({}, "WAIVER_PLAYER_CATALOG_UNAVAILABLE"),
    ({"1": record("1", "Only Lineman", "OT")}, "WAIVER_PLAYER_CATALOG_NO_SUPPORTED_PLAYERS"),
])
def test_unusable_catalog_blocks_without_falling_back_to_the_local_pool(catalog, blocker):
    universe = build(catalog, local_rows=[{"player": "Preseason Star", "position": "WR", "nfl_team": "DAL"}])
    assert universe["universe_state"] == "BLOCKED" and blocker in universe["blockers"] and universe["candidates"] == []
    assert universe["ownership"]["allowed"] is False and universe["local_lineage"]["local_rows"] == 0
    assert universe["uses_local_players_table_for_discovery"] is False


def rank_row(player_id_position, ecr, **overrides):
    return {"position": player_id_position, "ecr": ecr, "horizon": "this_week", "scoring": "PPR", "season": 2026, "week": 11, "source_age_seconds": 3600, **overrides}


def test_funnel_reconciles_health_groups_provider_identity_and_fresh_rank_validity():
    universe = build({str(index): record(str(index), f"Funnel Player {index}", "WR") for index in range(1, 7)})
    published = [
        {"player_id": "1", "position": "WR", "candidate_disposition": "PRELIMINARY_SUGGESTION", "opportunity_identity_state": "RESOLVED"},
        {"player_id": "2", "position": "WR", "candidate_disposition": "HEALTH_BLOCKED", "recommendation_state": "NON_ACTIONABLE_HEALTH", "normalized_health_state": "QUESTIONABLE"},
        {"player_id": "3", "position": "WR", "candidate_disposition": "HEALTH_BLOCKED", "recommendation_state": "NON_ACTIONABLE_HEALTH", "normalized_health_state": "OUT"},
        {"player_id": "4", "position": "WR", "candidate_disposition": "MONITOR", "recommendation_state": "HEALTH_UNVERIFIED"},
        {"player_id": "5", "position": "WR", "candidate_disposition": "PRELIMINARY_SUGGESTION"},
        {"player_id": "6", "position": "WR", "candidate_disposition": "PRELIMINARY_SUGGESTION"},
    ]
    ranks = {"1": rank_row("WR", 10), "2": rank_row("WR", 12, source_age_seconds=999999), "3": rank_row("WR", 14, week=10), "4": rank_row("WR", 16, scoring="STD"), "6": rank_row("WR", 20)}
    rankings = {"horizons": {"this_week": {"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": ranks}}}
    funnel = candidate_universe_funnel(universe, published_candidates=published, rankings=rankings, full_ppr=True, season=2026, week=11)
    assert funnel["health"] == {"healthy_eligible": 3, "questionable_monitor_only": 1, "health_non_actionable": 1, "health_unverified": 1}
    assert (funnel["ranked"], funnel["unranked"], funnel["ranked_healthy_eligible"]) == (2, 4, 2)
    assert (funnel["provider_identity_resolved"], funnel["provider_identity_unavailable"], funnel["reconciles"]) == (1, 5, True)
    not_full_ppr = candidate_universe_funnel(universe, published_candidates=published, rankings=rankings, full_ppr=False, season=2026, week=11)
    assert (not_full_ppr["ranked"], not_full_ppr["ranking_state"]) == (0, "UNAVAILABLE")


def test_missing_ros_rank_or_crosswalk_labels_a_candidate_without_removing_him():
    universe = build({"1": record("1", "Ranked Receiver", "WR"), "2": record("2", "Unmapped Rookie", "WR", "MIA"), "3": record("3", "Plain Unranked", "TE")})
    published = [{"player_id": player_id, "position": position, "candidate_disposition": "PRELIMINARY_SUGGESTION"} for player_id, position in (("1", "WR"), ("2", "WR"), ("3", "TE"))]
    ros = {**rank_row("WR", 20), "horizon": "rest_of_season", "week": None, "source_date": "2026-11-14"}
    unmapped = {"reason": "PROVIDER_ID_ABSENT_FROM_CROSSWALK", "crosswalk_matches": [], "investigation_candidates": [{"player_id": "2"}]}
    rankings = {"horizons": {"rest_of_season": {"state": "AVAILABLE", "max_age_seconds": 604800, "ranks": {"1": ros}, "diagnostics": [unmapped]}}}
    funnel = candidate_universe_funnel(universe, published_candidates=published, rankings=rankings, full_ppr=True, season=2026, week=11)
    assert sorted(candidate_ids(universe)) == ["1", "2", "3"] and (funnel["published"], funnel["reconciles"]) == (3, True)
    assert (funnel["ros"]["state"], funnel["ros"]["ranked"], funnel["ros"]["unranked"]) == ("AVAILABLE", 1, 2)
    assert funnel["ros"]["states"] == {"RANKED": 1, "IDENTITY_UNRESOLVED": 1, "UNRANKED": 1}
    assert funnel["ros"]["by_position"] == {"WR": {"ranked": 1, "unranked": 1, "materiality_capable": 0}, "TE": {"ranked": 0, "unranked": 1, "materiality_capable": 0}}
