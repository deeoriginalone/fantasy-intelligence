"""Focused tests for the W1 waiver roster decision engine (services/waiver_roster_decision.py)."""
import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from services.team_codes import CANONICAL_TEAMS
from services.team_needs import league_settings_contract, team_needs_contract
from services.waiver_roster_decision import (NO_SAFE_DROP_REASON, ROS_UNAVAILABLE_LABEL, build_manager_plan, build_waiver_roster_decision, compare_ros_values,
                                             player_value_context, replacement_context, ros_materiality, ros_player_value, selected_player_priority)

SEASON, WEEK = 2026, 11
NOW = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)
RECORDED = (NOW - timedelta(hours=2)).isoformat()


def week_evidence(byes=(), locked_games=()):
    """Bye rows for all 32 teams plus one game per playing team; locked games kicked off an hour ago."""
    bye_rows = [{"season": SEASON, "team": team, "bye_week": WEEK if team in byes else 5, "source": "automated:nflverse-schedules:derived-bye:test",
                 "source_recorded_at": RECORDED, "retrieved_at": RECORDED} for team in sorted(CANONICAL_TEAMS)]

    def game(home, away, kickoff):
        return {"season": SEASON, "week": WEEK, "home_team": home, "away_team": away, "game_time_utc": kickoff.isoformat(),
                "source": "automated:nflverse-schedules:games.csv.gz:sha256:test", "source_recorded_at": RECORDED, "retrieved_at": RECORDED}

    in_locked = {team for pair in locked_games for team in pair}
    playing = [team for team in sorted(CANONICAL_TEAMS) if team not in byes and team not in in_locked]
    schedule = [game(home, away, NOW - timedelta(hours=1)) for home, away in locked_games]
    schedule += [game(home, away, NOW + timedelta(days=1)) for home, away in zip(playing[0::2], playing[1::2])]
    return schedule, bye_rows


def rank(position, ecr, horizon="this_week", **overrides):
    row = {"position": position, "ecr": ecr, "horizon": horizon, "scoring": "PPR", "season": SEASON, "week": WEEK if horizon == "this_week" else None,
           "source_age_seconds": 3600, "source_date": "2026-11-14", "expert_best_rank": ecr - 1, "expert_worst_rank": ecr + 1}
    return {**row, **overrides}


def ros(position, ecr):
    return rank(position, ecr, horizon="rest_of_season")


def player(player_id, position, team, *, starter=True, index=None, health="HEALTHY", reserve=False):
    return {"player_id": player_id, "player": player_id, "position": position, "team": team, "is_starter": starter, "lineup_index": index,
            "lineup_slot": position if starter else None, "reserve": reserve, "taxi": False, "health_state": health, "health_freshness_state": "FRESH"}


def candidate(player_id, position, team, *, health="HEALTHY", identity="RESOLVED"):
    return {"player_id": player_id, "player": player_id, "position": position, "team": team, "identity_state": identity, "ownership_state": "VERIFIED",
            "eligibility_state": "VERIFIED", "health_state": health, "health_freshness_state": "FRESH", "health_source": "Sleeper API"}


def decide(roster, candidates, *, this_week=None, rest_of_season=None, slots=("WR",), capacity=None, full_ppr=True, byes=(), locked_games=(),
           empty_slots=(), **overrides):
    schedule, bye_rows = week_evidence(byes, locked_games)
    rankings = {"horizons": {
        "this_week": {"state": "AVAILABLE" if this_week else "UNAVAILABLE", "max_age_seconds": 172800, "ranks": dict(this_week or {})},
        "rest_of_season": {"state": "AVAILABLE" if rest_of_season else "UNAVAILABLE", "max_age_seconds": 604800, "ranks": dict(rest_of_season or {})},
    }}
    settings = league_settings_contract({"roster_positions": [*slots, "BN", "BN"], "scoring_settings": {"rec": 1 if full_ppr else 0.5}})
    args = dict(roster=roster, candidates=candidates, rankings=rankings, league_settings=settings, season=SEASON, week=WEEK, schedule_rows=schedule,
                bye_rows=bye_rows, now=NOW, pool_allowed=True, empty_required_slots=None if empty_slots is None else list(empty_slots),
                roster_capacity=capacity if capacity is not None else sum(1 for item in roster if not item["reserve"]),
                faab_balance={"state": "AVAILABLE", "remaining": 41, "budget": 100}, schedule_max_age_seconds=86400)
    args.update(overrides)
    return build_waiver_roster_decision(**args)


def one_wr_starter(**overrides):
    return decide([player("wr-start", "WR", "KC", index=0)], [candidate("wr-free", "WR", "DEN")], capacity=2, **overrides)


@pytest.mark.parametrize("candidate_rank,urgency,verdict", [
    (rank("WR", 10), "MATERIAL", "ACT"),
    (rank("WR", 10, expert_worst_rank=35), "OPTIONAL", "OPTIONAL"),
    (rank("WR", 10, expert_best_rank=None, expert_worst_rank=None), "OPTIONAL", "OPTIONAL"),
])
def test_better_ranked_candidate_with_open_spot_is_an_add_and_materiality_sets_urgency(candidate_rank, urgency, verdict):
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30), "wr-free": candidate_rank})
    move = result["moves"][0]
    assert (move["decision"], move["kind"], move["urgency"]) == ("ADD", "CURRENT_WEEK_UPGRADE", urgency)
    assert move["add"]["player_id"] == "wr-free" and move["over"]["player_id"] == "wr-start" and move["drop"] is None
    assert (move["state_label"], move["drop_state"], move["drop_safety"]["state"]) == ("ADD — OPEN ROSTER SPOT", "NOT_REQUIRED", "NOT_REQUIRED")
    assert result["verdict"]["state"] == verdict and result["verdict"]["save_faab"] is False
    if urgency == "OPTIONAL" and candidate_rank["expert_worst_rank"]:
        assert move["materiality_text"].startswith("CLOSE CALL")


def test_full_roster_drops_lowest_rest_of_season_same_position_bench_player():
    roster = [player("wr-start", "WR", "KC", index=0), player("wr-bench-a", "WR", "BUF", starter=False), player("wr-bench-b", "WR", "CIN", starter=False),
              player("wr-stud", "WR", "LAR", starter=False)]
    this_week = {"wr-start": rank("WR", 30), "wr-free": rank("WR", 10), "wr-bench-a": rank("WR", 40), "wr-bench-b": rank("WR", 50)}
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week=this_week,
                    rest_of_season={"wr-free": ros("WR", 20), "wr-bench-a": ros("WR", 60), "wr-bench-b": ros("WR", 45), "wr-stud": ros("WR", 5)})
    move = result["moves"][0]
    assert (move["decision"], move["drop_state"]) == ("ADD_DROP", "VERIFIED")
    assert (move["drop"]["player_id"], move["drop"]["basis"], move["drop"]["role"]) == ("wr-bench-a", "rest_of_season", "BENCH")
    assert ROS_UNAVAILABLE_LABEL not in move["disclosures"]
    assert (move["state_label"], move["drop_safety"]["state"], move["value_combination"]) == ("ADD + DROP", "SUPPORTED", "A_BOTH")
    assert move["drop"]["reason"] == ("wr-bench-a is your weakest releasable WR for the rest of the season (WR ROS ECR 60.0 vs 20.0; expert ranges 59–61 vs 19–21 "
                                      "do not overlap); every starting slot, including FLEX, can still be filled this week and for the rest of the season.")
    assert move["rest_of_season"]["text"] == "wr-free ranks ahead of wr-bench-a for the rest of the season (WR ROS ECR 20.0 vs 60.0; lower is better)."
    assert move["impact"] == "Current-week upgrade over wr-start; rest-of-season value clearly improves over wr-bench-a, who is released"
    assert (result["verdict"]["state"], result["verdict"]["counts"]["executable"]) == ("ACT", 1)
    status = result["ros_value"]["drop_status"]
    assert (status["wr-bench-a"]["state"], status["wr-start"]["state"]) == ("SAFE", "PROTECTED")
    assert status["wr-bench-b"] == {"state": "PROTECTED", "reason": "The only available WR with a better fresh rest-of-season rank (wr-free) is already a recommended add, "
                                                                    "so releasing him as well would give up rest-of-season value."}
    assert status["wr-stud"] == {"state": "PROTECTED", "reason": "No available WR has a better fresh rest-of-season rank than his WR ROS ECR 5.0, so releasing him would give up rest-of-season value."}


def test_roster_ahead_of_every_ranked_candidate_holds_and_passes():
    result = one_wr_starter(this_week={"wr-start": rank("WR", 8), "wr-free": rank("WR", 25)}, rest_of_season={"wr-start": ros("WR", 5), "wr-free": ros("WR", 40)})
    assert result["moves"] == [] and result["positions"]["WR"]["status"] == "HOLD" and result["hold_positions"] == ["WR"]
    assert result["verdict"]["state"] == "PASS" and result["verdict"]["save_faab_text"] == "Save FAAB."


def test_unranked_candidate_cannot_prove_an_upgrade():
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30)})
    assert result["moves"] == [] and result["positions"]["WR"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["positions"]["WR"]["reason"] == "No available WR has a current consensus rank to compare."


def test_unranked_starter_cannot_be_shown_worse_than_a_ranked_candidate():
    result = one_wr_starter(this_week={"wr-free": rank("WR", 10)})
    summary = result["positions"]["WR"]
    assert result["moves"] == [] and summary["status"] == "INSUFFICIENT_EVIDENCE" and summary["unranked_starters"] == ["wr-start"]
    assert summary["reason"].startswith("wr-start has no current consensus rank")


@pytest.mark.parametrize("stale_field", [{"source_age_seconds": 172801}, {"week": WEEK - 1}, {"scoring": "STD"}])
def test_stale_wrong_week_or_non_ppr_candidate_rank_is_treated_as_unranked(stale_field):
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10, **stale_field)})
    summary = result["positions"]["WR"]
    assert result["moves"] == [] and summary["status"] == "INSUFFICIENT_EVIDENCE"
    assert (summary["ranked_candidates"], summary["unranked_candidates"]) == (0, 1)


def test_league_not_verified_as_full_ppr_cannot_use_ppr_ranks():
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}, full_ppr=False)
    assert result["moves"] == [] and result["verdict"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "not verified as Full PPR" in result["verdict"]["reasons"][0]


@pytest.mark.parametrize("evidence", [{"byes": ("DEN", "SEA")}, {"locked_games": (("DEN", "LV"),)}])
def test_candidate_on_bye_or_already_kicked_off_is_not_a_current_week_add(evidence):
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}, **evidence)
    assert result["moves"] == [] and result["positions"]["WR"]["status"] == "HOLD"
    assert result["positions"]["WR"]["reason"] == "No verified, healthy, unlocked WR with a current game is available this week."


def test_starter_on_bye_with_playable_bench_coverage_needs_no_waiver_move():
    roster = [player("k-start", "K", "MIN", index=0), player("k-bench", "K", "KC", starter=False)]
    result = decide(roster, [candidate("k-free", "K", "DEN")], this_week={"k-start": rank("K", 5), "k-bench": rank("K", 12), "k-free": rank("K", 20)},
                    slots=("K",), byes=("MIN", "SEA"))
    assert result["moves"] == [] and result["verdict"]["state"] == "PASS"
    assert [(note["slot"], note["player_id"], note["replaces"]) for note in result["lineup_notes"]] == [("K", "k-bench", "k-start")]
    assert result["lineup_notes"][0]["note"].endswith("no waiver move is needed.")


def test_starter_on_bye_without_coverage_is_a_required_must_fill():
    candidates = [candidate("k-alt", "K", "BUF"), candidate("k-free", "K", "DEN")]
    result = decide([player("k-start", "K", "MIN", index=0)], candidates, this_week={"k-start": rank("K", 5), "k-free": rank("K", 12), "k-alt": rank("K", 18)},
                    slots=("K",), byes=("MIN", "SEA"), capacity=2)
    move = result["moves"][0]
    assert (move["kind"], move["urgency"], move["decision"], move["trigger"]) == ("MUST_FILL", "REQUIRED", "ADD", "BYE")
    assert move["add"]["player_id"] == "k-free" and move["slot_player"]["player_id"] == "k-start"
    assert result["verdict"]["state"] == "ACT"


def test_empty_required_slot_is_a_must_fill_only_when_sleeper_reports_it():
    roster = [player("wr-start", "WR", "KC", index=0), player("wr-bench", "WR", "BUF", starter=False)]
    ranks = {"wr-start": rank("WR", 30), "k-free": rank("K", 10)}
    reported = decide(roster, [candidate("k-free", "K", "DEN")], this_week=ranks, slots=("WR", "K"), empty_slots=("K",), capacity=3)
    move = reported["moves"][0]
    assert (move["kind"], move["trigger"], move["decision"], move["add"]["player_id"]) == ("MUST_FILL", "EMPTY_SLOT", "ADD", "k-free")
    unreported = decide(roster, [candidate("k-free", "K", "DEN")], this_week=ranks, slots=("WR", "K"), empty_slots=None, capacity=3)
    assert unreported["moves"] == [] and unreported["positions"]["K"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_upgrade_without_a_verified_safe_drop_is_monitor_with_reason():
    roster = [player("wr-start", "WR", "KC", index=0), player("rb-bench", "RB", "BUF", starter=False)]
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)})
    move = result["moves"][0]
    assert (move["decision"], move["reason"], move["drop"], move["drop_state"]) == ("MONITOR", NO_SAFE_DROP_REASON, None, "UNVERIFIED")
    assert "rest-of-season value is unavailable" in move["monitor_detail"]
    assert result["verdict"]["state"] == "OPTIONAL"


def test_only_bench_coverage_player_is_never_the_drop():
    roster = [player("k-start", "K", "MIN", index=0), player("k-bench", "K", "KC", starter=False)]
    result = decide(roster, [candidate("k-free", "K", "DEN")], this_week={"k-start": rank("K", 5), "k-bench": rank("K", 20), "k-free": rank("K", 12)},
                    rest_of_season={"k-bench": ros("K", 30), "k-free": ros("K", 10)}, slots=("K",), byes=("MIN", "SEA"))
    move = result["moves"][0]
    assert (move["kind"], move["over"]["player_id"], move["decision"], move["drop"]) == ("CURRENT_WEEK_UPGRADE", "k-bench", "MONITOR", None)
    assert move["monitor_detail"] == "k-bench is protected: Covers the K slot this week for k-start (verified bye)."
    assert (move["drop_blocker"], result["ros_value"]["drop_status"]["k-bench"]["state"]) == ("PROTECTED", "PROTECTED")


def test_reserve_player_does_not_consume_an_active_roster_spot_or_become_a_drop():
    roster = [player("wr-start", "WR", "KC", index=0), player("wr-ir", "WR", "BUF", starter=False, health="IR", reserve=True)]
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}, capacity=2)
    assert (result["moves"][0]["decision"], result["moves"][0]["drop"]) == ("ADD", None)


def test_reserve_and_taxi_players_do_not_satisfy_team_depth_needs():
    settings = league_settings_contract({"roster_positions": ["RB", "BN"], "scoring_settings": {"rec": 1}})
    needs = team_needs_contract([{"position": "RB"}, {"position": "RB", "sleeper_reserve": True}, {"position": "RB", "sleeper_taxi": True}], settings)
    assert (needs["RB"]["rostered"], needs["RB"]["depth_shortage"]) == (1, 3)


def test_unverified_ownership_blocks_every_position_and_move():
    result = one_wr_starter(this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}, pool_allowed=False, pool_blockers=["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"])
    assert result["verdict"]["state"] == "BLOCKED" and result["moves"] == [] and result["blockers"] == ["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"]
    assert {summary["status"] for summary in result["positions"].values()} == {"BLOCKED"}


def test_unverified_roster_identity_blocks_and_unresolved_candidate_is_excluded():
    ranks = {"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}
    blocked = decide([player("wr-start", "WR", "KC", index=0), player("", "WR", "BUF", starter=False)], [candidate("wr-free", "WR", "DEN")], this_week=ranks)
    assert blocked["verdict"]["state"] == "BLOCKED" and blocked["blockers"] == ["WAIVER_ROSTER_IDENTITY_UNVERIFIED"]
    excluded = decide([player("wr-start", "WR", "KC", index=0)], [candidate("wr-free", "WR", "DEN", identity="AMBIGUOUS")], this_week=ranks, capacity=2)
    assert excluded["moves"] == [] and excluded["positions"]["WR"]["ranked_candidates"] == 0


def test_pass_requires_a_completed_comparison_and_is_distinct_from_insufficient_evidence():
    passed = one_wr_starter(this_week={"wr-start": rank("WR", 8), "wr-free": rank("WR", 25)}, rest_of_season={"wr-start": ros("WR", 5), "wr-free": ros("WR", 40)})
    no_ranks = one_wr_starter(this_week=None)
    no_week = one_wr_starter(this_week={"wr-start": rank("WR", 8), "wr-free": rank("WR", 25)}, week=None)
    assert (passed["verdict"]["state"], passed["verdict"]["save_faab"]) == ("PASS", True)
    for result in (no_ranks, no_week):
        assert (result["verdict"]["state"], result["verdict"]["save_faab"], result["moves"]) == ("INSUFFICIENT_EVIDENCE", False, [])
    assert no_ranks["verdict"]["reasons"] == ["No fresh current-week consensus ranks are available."]
    assert no_week["blockers"] == ["CURRENT_WEEK_UNVERIFIED"]


def test_rest_of_season_unavailable_keeps_the_current_week_upgrade_but_never_verifies_a_drop():
    roster = [player("wr-start", "WR", "KC", index=0), player("wr-bench", "WR", "BUF", starter=False)]
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week={"wr-start": rank("WR", 30), "wr-bench": rank("WR", 45), "wr-free": rank("WR", 10)})
    move = result["moves"][0]
    assert (move["kind"], move["decision"], move["drop"], move["drop_blocker"]) == ("CURRENT_WEEK_UPGRADE", "MONITOR", None, "ROS_VALUE_UNAVAILABLE")
    assert (move["state_label"], move["reason"], move["drop_safety"]["state"]) == ("MONITOR — ROS VALUE UNAVAILABLE", NO_SAFE_DROP_REASON, "NOT_SUPPORTED")
    assert move["monitor_detail"].startswith("A safe release cannot be verified because rest-of-season value is unavailable")
    assert move["current_week"]["text"] == "wr-free ECR 10.0 vs wr-start ECR 30.0: wr-free is stronger this week."
    assert (move["value_combination"], result["verdict"]["state"]) == ("D_CURRENT_WEEK_ONLY", "OPTIONAL")
    assert ROS_UNAVAILABLE_LABEL in move["disclosures"] and result["rest_of_season"]["label"] == ROS_UNAVAILABLE_LABEL
    assert result["ros_value"]["drop_status"]["wr-bench"]["state"] == "UNVERIFIED"


def test_unranked_candidate_is_disclosed_rather_than_ranked_below_the_roster():
    result = decide([player("wr-start", "WR", "KC", index=0)], [candidate("wr-ranked", "WR", "DEN"), candidate("wr-unranked", "WR", "BUF")],
                    this_week={"wr-start": rank("WR", 8), "wr-ranked": rank("WR", 25)}, capacity=2)
    summary = result["positions"]["WR"]
    assert summary["status"] == "HOLD" and summary["reason"] == "Your WR starter(s) rank ahead of every ranked available WR this week."
    assert summary["rank_disclosure"] == "1 ranked candidate(s) compared; 1 additional player(s) were unranked and were not used to prove superiority."


def test_must_fill_leads_with_the_ranked_subset_and_discloses_unranked_options():
    candidates = [candidate("k-a", "K", "BUF"), candidate("k-ranked", "K", "DEN"), candidate("k-b", "K", "CIN")]
    result = decide([player("k-start", "K", "MIN", index=0)], candidates, this_week={"k-start": rank("K", 5), "k-ranked": rank("K", 14)},
                    slots=("K",), byes=("MIN", "SEA"), capacity=2)
    move = result["moves"][0]
    assert move["add"]["player_id"] == "k-ranked" and [backup["player_id"] for backup in move["fallbacks"]] == ["k-a", "k-b"]
    assert "1 ranked option(s) ordered by current consensus; 2 unranked option(s) follow and were not used to prove superiority." in move["disclosures"]


def test_upgrade_fallbacks_are_the_next_better_ranked_alternatives_in_rank_order():
    ecrs = {"DEN": 22, "BUF": 12, "CIN": 18, "CLE": 40, "DAL": 15, "DET": 20}
    candidates = [candidate(f"wr-{ecr}", "WR", team) for team, ecr in ecrs.items()]
    this_week = {"wr-start": rank("WR", 30), **{f"wr-{ecr}": rank("WR", ecr) for ecr in ecrs.values()}}
    move = decide([player("wr-start", "WR", "KC", index=0)], candidates, this_week=this_week, capacity=2)["moves"][0]
    assert move["add"]["player_id"] == "wr-12" and [backup["player_id"] for backup in move["fallbacks"]] == ["wr-15", "wr-18", "wr-20"]


def test_one_bench_player_is_never_the_drop_for_two_moves():
    roster = [player("wr-start", "WR", "KC", index=0), player("wr-bench", "WR", "BUF", starter=False)]
    result = decide(roster, [candidate("wr-free", "WR", "DEN"), candidate("wr-stash", "WR", "CIN")],
                    this_week={"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)},
                    rest_of_season={"wr-bench": ros("WR", 80), "wr-free": ros("WR", 20), "wr-stash": ros("WR", 40)})
    first, second = result["moves"]
    assert (first["kind"], first["decision"], first["drop"]["player_id"]) == ("CURRENT_WEEK_UPGRADE", "ADD_DROP", "wr-bench")
    assert (second["kind"], second["add"]["player_id"], second["decision"], second["drop"], second["reason"]) == ("DEPTH_UPGRADE", "wr-stash", "MONITOR", None, NO_SAFE_DROP_REASON)
    assert (second["drop_blocker"], second["monitor_detail"]) == ("DROP_ALREADY_USED", "wr-bench is already the drop for a higher-priority move.")


def test_questionable_candidate_is_monitor_only_even_when_ranked_ahead():
    result = decide([player("wr-start", "WR", "KC", index=0)], [candidate("wr-q", "WR", "DEN", health="QUESTIONABLE")],
                    this_week={"wr-start": rank("WR", 30), "wr-q": rank("WR", 10)}, capacity=2)
    move = result["moves"][0]
    assert (move["decision"], move["reason"], move["add"]["health_state"]) == ("MONITOR", "HEALTH DESIGNATION PREVENTS A SUPPORTED ADD.", "QUESTIONABLE")
    assert result["verdict"]["state"] == "OPTIONAL"


# W3: fresh rest-of-season value and safe drop decisions.

def full_wr_roster(*bench):
    return [player("wr-start", "WR", "KC", index=0), *bench]


WR_UPGRADE = {"wr-start": rank("WR", 30), "wr-free": rank("WR", 10)}


def test_stale_rest_of_season_source_is_never_drop_authority():
    def stale(ecr):
        return rank("WR", ecr, horizon="rest_of_season", source_age_seconds=752400, source_date="2026-11-07")

    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": stale(40), "wr-bench": stale(90), "wr-free": stale(20)})
    move = result["moves"][0]
    assert (result["rest_of_season"]["state"], result["rest_of_season"]["label"]) == ("STALE", ROS_UNAVAILABLE_LABEL)
    assert result["rest_of_season"]["reason"].startswith("The newest rest-of-season consensus was published 2026-11-07, 8 days 17 hours ago; the limit is 7 days.")
    assert (move["decision"], move["state_label"], move["drop_blocker"]) == ("MONITOR", "MONITOR — ROS VALUE UNAVAILABLE", "ROS_VALUE_UNAVAILABLE")
    assert (result["ros_value"]["candidates"]["wr-free"]["evidence_state"], result["ros_value"]["candidates"]["wr-free"]["ros_ecr"]) == ("STALE", None)


@pytest.mark.parametrize("starter_ros,decision,drop,blocker,combination", [
    (15, "MONITOR", None, "ROSTER_ROS_STRONGER", "B_SHORT_TERM"),
    (45, "ADD_DROP", "wr-start", None, "A_BOTH"),
])
def test_replaced_starter_is_released_only_when_fresh_ros_supports_it(starter_ros, decision, drop, blocker, combination):
    result = decide(full_wr_roster(player("rb-bench", "RB", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": ros("WR", starter_ros), "wr-free": ros("WR", 30), "rb-bench": ros("RB", 90)})
    move = result["moves"][0]
    assert (move["decision"], (move["drop"] or {}).get("player_id"), move["drop_blocker"], move["value_combination"]) == (decision, drop, blocker, combination)
    assert move["current_week"]["text"] == "wr-free ECR 10.0 vs wr-start ECR 30.0: wr-free is stronger this week."
    if drop:
        assert (move["drop"]["role"], move["impact"]) == ("REPLACED_STARTER", "Current-week and clear rest-of-season upgrade over wr-start")
    else:
        assert move["monitor_detail"] == ("wr-start ranks ahead of wr-free for the rest of the season (WR ROS ECR 15.0 vs 30.0; lower is better). "
                                          "The current-week edge is short-term, so wr-start is kept.")
        assert move["impact"] == "Short-term current-week edge only; wr-start keeps more rest-of-season value"


def test_roster_player_without_a_ros_rank_is_never_released():
    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": ros("WR", 10), "wr-free": ros("WR", 20)})
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"], move["state_label"]) == ("MONITOR", None, "ROSTER_ROS_UNRANKED", "MONITOR — NO SAFE DROP VERIFIED")
    assert move["monitor_detail"].startswith("wr-bench has no fresh rest-of-season rank (unranked).")
    assert result["ros_value"]["drop_status"]["wr-bench"] == {"state": "UNVERIFIED", "reason": "No fresh rest-of-season rank (unranked), so releasing him cannot be verified."}


def test_candidate_without_a_ros_rank_is_unranked_and_cannot_justify_a_drop():
    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": ros("WR", 20), "wr-bench": ros("WR", 70)})
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"]) == ("MONITOR", None, "CANDIDATE_ROS_UNRANKED")
    assert move["monitor_detail"] == "wr-free has no fresh rest-of-season rank (unranked), so releasing a roster player for him cannot be verified."
    value = result["ros_value"]["candidates"]["wr-free"]
    assert (value["evidence_state"], value["ros_ecr"], value["blocker"]) == ("UNRANKED", None, "NO_ROS_RANK")


@pytest.mark.parametrize("hold,reason", [({"reserve": True, "health_state": "IR"}, "On IR (reserve)"), ({"taxi": True}, "On the taxi squad")])
def test_reserve_and_taxi_players_are_never_the_active_drop(hold, reason):
    stash = {**player("wr-stash", "WR", "CIN", starter=False), **hold}
    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False), stash), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": ros("WR", 10), "wr-free": ros("WR", 20), "wr-bench": ros("WR", 50), "wr-stash": ros("WR", 99)}, capacity=2)
    assert (result["moves"][0]["decision"], result["moves"][0]["drop"]["player_id"]) == ("ADD_DROP", "wr-bench")
    status = result["ros_value"]["drop_status"]["wr-stash"]
    assert status["state"] == "PROTECTED" and status["reason"].startswith(reason)


def test_only_the_bench_player_covering_a_required_slot_is_protected():
    roster = [player("rb-out", "RB", "KC", index=0, health="OUT"), player("rb-cover", "RB", "BUF", starter=False), player("rb-spare", "RB", "CIN", starter=False)]
    kwargs = dict(slots=("RB",), this_week={"rb-cover": rank("RB", 20), "rb-spare": rank("RB", 40), "rb-free": rank("RB", 30)},
                  rest_of_season={"rb-out": ros("RB", 10), "rb-cover": ros("RB", 50), "rb-spare": ros("RB", 60), "rb-free": ros("RB", 25)})
    result = decide(roster, [candidate("rb-free", "RB", "DEN")], **kwargs)
    move = result["moves"][0]
    assert (move["kind"], move["decision"], move["drop"]["player_id"]) == ("DEPTH_UPGRADE", "ADD_DROP", "rb-spare")
    assert result["ros_value"]["drop_status"]["rb-cover"] == {"state": "PROTECTED", "reason": "Covers the RB slot this week for rb-out (injury)."}
    sole = decide(roster[:2], [candidate("rb-free", "RB", "DEN")], **kwargs)
    assert sole["moves"] == [] and sole["ros_value"]["drop_status"]["rb-cover"]["state"] == "PROTECTED"


@pytest.mark.parametrize("health,protected", [("QUESTIONABLE", True), ("DOUBTFUL", True), ("HEALTHY", False)])
def test_backup_for_a_questionable_or_doubtful_starter_is_protected(health, protected):
    roster = [player("rb-start", "RB", "KC", index=0, health=health), player("rb-backup", "RB", "BUF", starter=False)]
    result = decide(roster, [candidate("rb-free", "RB", "DEN")], slots=("RB",),
                    this_week={"rb-start": rank("RB", 20), "rb-backup": rank("RB", 35), "rb-free": rank("RB", 25)},
                    rest_of_season={"rb-start": ros("RB", 10), "rb-backup": ros("RB", 70), "rb-free": ros("RB", 30)})
    status = result["ros_value"]["drop_status"]["rb-backup"]
    if protected:
        assert result["moves"] == [] and status == {"state": "PROTECTED", "reason": f"Backup for rb-start ({health.title()}) at RB this week."}
    else:
        assert (result["moves"][0]["kind"], result["moves"][0]["drop"]["player_id"], status["state"]) == ("DEPTH_UPGRADE", "rb-backup", "SAFE")


def test_player_whose_game_has_kicked_off_is_never_released():
    roster = full_wr_roster(player("wr-locked", "WR", "BUF", starter=False), player("wr-open", "WR", "CIN", starter=False))
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE, locked_games=(("BUF", "MIA"),),
                    rest_of_season={"wr-start": ros("WR", 5), "wr-free": ros("WR", 20), "wr-locked": ros("WR", 90), "wr-open": ros("WR", 50)})
    assert (result["moves"][0]["decision"], result["moves"][0]["drop"]["player_id"]) == ("ADD_DROP", "wr-open")
    assert result["ros_value"]["drop_status"]["wr-locked"] == {"state": "PROTECTED", "reason": "His game has already kicked off this week, so his roster spot is locked."}


def test_full_roster_without_a_same_position_release_stays_monitor():
    roster = full_wr_roster(player("wr-bench", "WR", "BUF", starter=False))
    result = decide(roster, [candidate("k-free", "K", "DEN")], slots=("WR", "K"), empty_slots=("K",), this_week={"wr-start": rank("WR", 30), "k-free": rank("K", 10)},
                    rest_of_season={"wr-bench": ros("WR", 99), "k-free": ros("K", 3)})
    move = result["moves"][0]
    assert (move["kind"], move["decision"], move["drop"], move["drop_blocker"]) == ("MUST_FILL", "MONITOR", None, "NO_SAME_POSITION_RELEASE")
    assert move["monitor_detail"] == ("No K on your active roster can be released for k-free. A release at a different position was checked: "
                                      "wr-bench (WR) — WR depth would fall to 1, below the supported target of 4.")
    assert (move["state_label"], result["verdict"]["state"], result["verdict"]["counts"]["executable"]) == ("MONITOR — NO SAFE DROP VERIFIED", "ACT", 0)


def test_same_position_ros_comparison_is_ordinal_and_lower_is_better():
    candidate_value = {"position": "RB", "evidence_state": "RANKED", "ros_ecr": 31.0}
    roster_value = {"position": "RB", "evidence_state": "RANKED", "ros_ecr": 62.0}
    assert compare_ros_values(candidate_value, roster_value, candidate_name="Candidate", roster_name="Roster RB") == {
        "state": "CANDIDATE_BETTER", "candidate_ecr": 31.0, "roster_ecr": 62.0,
        "reason": "Candidate ranks ahead of Roster RB for the rest of the season (RB ROS ECR 31.0 vs 62.0; lower is better)."}
    assert compare_ros_values(roster_value, candidate_value, candidate_name="Roster RB", roster_name="Candidate")["state"] == "ROSTER_BETTER"
    assert compare_ros_values(candidate_value, dict(candidate_value), candidate_name="a", roster_name="b")["state"] == "TIED"


@pytest.mark.parametrize("candidate_position,other_position", [("RB", "WR"), ("WR", "TE")])
def test_ros_ranks_are_never_compared_across_positions(candidate_position, other_position):
    comparison = compare_ros_values({"position": candidate_position, "evidence_state": "RANKED", "ros_ecr": 25.0},
                                    {"position": other_position, "evidence_state": "RANKED", "ros_ecr": 40.0}, candidate_name="a", roster_name="b")
    assert comparison["state"] == "NOT_COMPARABLE" and "candidate_ecr" not in comparison
    roster = [player("start", candidate_position, "KC", index=0), player("other", other_position, "BUF", starter=False)]
    result = decide(roster, [candidate("free", candidate_position, "DEN")], slots=(candidate_position,),
                    this_week={"start": rank(candidate_position, 30), "free": rank(candidate_position, 10)},
                    rest_of_season={"start": ros(candidate_position, 5), "free": ros(candidate_position, 25), "other": ros(other_position, 40)})
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"]) == ("MONITOR", None, "ROSTER_ROS_STRONGER")
    assert "other" not in move["monitor_detail"] and result["ros_value"]["roster"]["other"]["position"] == other_position


def test_flex_coverage_can_protect_a_player_but_never_compares_positions():
    roster = full_wr_roster(player("te-start", "TE", "BUF", index=1), {**player("rb-flex", "RB", "MIN", index=2), "lineup_slot": "FLEX"},
                            player("te-bench", "TE", "CIN", starter=False))
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], slots=("WR", "TE", "FLEX"), byes=("MIN", "SEA"),
                    this_week={**WR_UPGRADE, "te-start": rank("TE", 8), "te-bench": rank("TE", 20)},
                    rest_of_season={"wr-start": ros("WR", 12), "wr-free": ros("WR", 25), "te-start": ros("TE", 5), "te-bench": ros("TE", 40), "rb-flex": ros("RB", 20)})
    move = result["moves"][0]
    assert (move["position"], move["decision"], move["drop"], move["drop_blocker"]) == ("WR", "MONITOR", None, "ROSTER_ROS_STRONGER")
    assert "te-bench" not in move["monitor_detail"]
    assert result["ros_value"]["drop_status"]["te-bench"] == {"state": "PROTECTED", "reason": "Covers the FLEX slot this week for rb-flex (verified bye)."}
    assert [(note["slot"], note["player_id"]) for note in result["lineup_notes"]] == [("FLEX", "te-bench")]


@pytest.mark.parametrize("occupant_ros,decision,drop,blocker", [
    (None, "MONITOR", None, "ROS_VALUE_UNAVAILABLE"),
    (20, "ADD_DROP", "k-start", None),
    (2, "MONITOR", None, "ROSTER_ROS_STRONGER"),
])
def test_kicker_slot_fill_stays_required_and_releases_the_bye_kicker_only_with_ros_support(occupant_ros, decision, drop, blocker):
    rest_of_season = None if occupant_ros is None else {"k-start": ros("K", occupant_ros), "k-free": ros("K", 8), "k-alt": ros("K", 4)}
    result = decide([player("k-start", "K", "MIN", index=0)], [candidate("k-alt", "K", "BUF"), candidate("k-free", "K", "DEN")], slots=("K",), byes=("MIN", "SEA"),
                    this_week={"k-start": rank("K", 5), "k-free": rank("K", 12), "k-alt": rank("K", 18)}, rest_of_season=rest_of_season)
    move = result["moves"][0]
    assert (move["kind"], move["urgency"], move["add"]["player_id"], [backup["player_id"] for backup in move["fallbacks"]]) == ("MUST_FILL", "REQUIRED", "k-free", ["k-alt"])
    assert (move["decision"], (move["drop"] or {}).get("player_id"), move["drop_blocker"]) == (decision, drop, blocker)
    assert (result["verdict"]["state"], result["verdict"]["counts"]["executable"]) == ("ACT", 1 if drop else 0)
    if drop:
        assert move["drop"]["role"] == "SLOT_OCCUPANT"
    elif blocker == "ROSTER_ROS_STRONGER":
        assert move["monitor_detail"].endswith("The slot fill is short-term, so k-start is kept.")


def test_current_week_hold_coexists_with_an_optional_ros_depth_upgrade():
    roster = [player("rb-start", "RB", "KC", index=0), player("rb-bench", "RB", "BUF", starter=False)]
    result = decide(roster, [candidate("rb-free", "RB", "DEN")], slots=("RB",),
                    this_week={"rb-start": rank("RB", 10), "rb-bench": rank("RB", 50), "rb-free": rank("RB", 30)},
                    rest_of_season={"rb-start": ros("RB", 8), "rb-bench": ros("RB", 65), "rb-free": ros("RB", 30)})
    move = result["moves"][0]
    assert (move["kind"], move["decision"], move["drop"]["player_id"], move["value_combination"]) == ("DEPTH_UPGRADE", "ADD_DROP", "rb-bench", "C_DEPTH")
    assert (move["impact"], move["current_week"]["text"]) == ("Rest-of-season depth upgrade (bench); your current-week lineup is unchanged",
                                                               "Bench depth move: your current-week lineup is unchanged.")
    assert (result["positions"]["RB"]["status"], result["hold_positions"], result["verdict"]["state"]) == ("HOLD", ["RB"], "OPTIONAL")


def test_pass_without_fresh_ros_is_not_a_full_pass_and_withholds_save_faab():
    week = {"wr-start": rank("WR", 8), "wr-free": rank("WR", 25)}
    fresh = one_wr_starter(this_week=week, rest_of_season={"wr-start": ros("WR", 5), "wr-free": ros("WR", 40)})
    missing = one_wr_starter(this_week=week)
    assert fresh["verdict"]["state"] == missing["verdict"]["state"] == "PASS"
    assert (fresh["verdict"]["save_faab"], fresh["verdict"]["save_faab_text"], fresh["rest_of_season"]["label"]) == (True, "Save FAAB.", None)
    assert "not evaluated" not in fresh["verdict"]["detail"]
    assert (missing["verdict"]["save_faab"], missing["verdict"]["save_faab_text"], missing["rest_of_season"]["label"]) == (False, None, ROS_UNAVAILABLE_LABEL)
    assert missing["verdict"]["detail"].endswith("Rest-of-season depth upgrades were not evaluated because rest-of-season value is unavailable; "
                                                 "refresh it before deciding to save FAAB.")


def test_fresh_ros_never_turns_missing_current_week_evidence_into_a_pass():
    result = one_wr_starter(this_week=None, rest_of_season={"wr-start": ros("WR", 5), "wr-free": ros("WR", 40)})
    assert (result["verdict"]["state"], result["verdict"]["save_faab"], result["moves"]) == ("INSUFFICIENT_EVIDENCE", False, [])
    assert result["rest_of_season"]["state"] == "AVAILABLE"


def test_blocked_ownership_withholds_every_move_even_with_fresh_ros():
    result = one_wr_starter(this_week=WR_UPGRADE, rest_of_season={"wr-start": ros("WR", 40), "wr-free": ros("WR", 5)},
                            pool_allowed=False, pool_blockers=["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"])
    assert (result["verdict"]["state"], result["moves"], result["ros_value"]["drop_status"]) == ("BLOCKED", [], {})


def test_ros_value_never_erases_a_questionable_designation():
    roster = full_wr_roster(player("wr-bench", "WR", "BUF", starter=False))
    result = decide(roster, [candidate("wr-q", "WR", "DEN", health="QUESTIONABLE")], this_week={"wr-start": rank("WR", 30), "wr-q": rank("WR", 10)},
                    rest_of_season={"wr-start": ros("WR", 40), "wr-bench": ros("WR", 90), "wr-q": ros("WR", 5)})
    assert [move["kind"] for move in result["moves"]] == ["CURRENT_WEEK_UPGRADE"]
    move = result["moves"][0]
    assert (move["decision"], move["state_label"], move["drop"], move["drop_safety"]["state"]) == ("MONITOR", "MONITOR — HEALTH DESIGNATION", None, "NOT_EVALUATED")
    assert (move["add"]["health_state"], move["add"]["ros_value"]["evidence_state"]) == ("QUESTIONABLE", "RANKED")


def test_each_release_is_checked_after_the_higher_priority_moves():
    unverified_flex = {**player("flex-start", "RB", "KC", index=0), "lineup_slot": "FLEX", "health_freshness_state": "STALE"}
    roster = [unverified_flex, player("rb-bench", "RB", "BUF", starter=False), player("wr-bench", "WR", "CIN", starter=False)]
    result = decide(roster, [candidate("rb-free", "RB", "MIN"), candidate("wr-free", "WR", "SEA")], slots=("FLEX",), byes=("MIN", "SEA"),
                    this_week={"flex-start": rank("RB", 20), "rb-bench": rank("RB", 40), "wr-bench": rank("WR", 50)},
                    rest_of_season={"flex-start": ros("RB", 10), "rb-bench": ros("RB", 60), "wr-bench": ros("WR", 70), "rb-free": ros("RB", 30), "wr-free": ros("WR", 35)})
    first, second = result["moves"]
    reason = "Releasing wr-bench after the higher-priority moves would leave fewer starting slots covered this week (bye, injury, or kickoff lock)."
    assert (first["kind"], first["decision"], first["drop"]["player_id"]) == ("DEPTH_UPGRADE", "ADD_DROP", "rb-bench")
    assert (second["position"], second["decision"], second["drop"], second["drop_blocker"], second["monitor_detail"]) == ("WR", "MONITOR", None, "LINEUP_COVERAGE", reason)
    assert result["ros_value"]["drop_status"]["wr-bench"] == {"state": "PROTECTED", "reason": reason}


def test_ros_rows_without_a_verifiable_source_date_never_authorize_a_drop():
    def undated(ecr):
        return rank("WR", ecr, horizon="rest_of_season", source_date=None)

    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": undated(40), "wr-bench": undated(90), "wr-free": undated(20)})
    move = result["moves"][0]
    assert (result["rest_of_season"]["state"], result["rest_of_season"]["blocker"]) == ("BLOCKED", "SOURCE_FRESHNESS_UNVERIFIED")
    assert (move["decision"], move["drop"], move["drop_blocker"]) == ("MONITOR", None, "ROS_VALUE_UNAVAILABLE")
    rankings = {"horizons": {"rest_of_season": {"max_age_seconds": 604800, "ranks": {"wr-free": undated(20)}}}}
    value = ros_player_value({"state": "AVAILABLE"}, rankings, "wr-free", "WR", season=SEASON)
    assert (value["evidence_state"], value["blocker"], value["ros_ecr"]) == ("BLOCKED", "ROS_SOURCE_DATE_MISSING", None)


def test_drop_status_judges_a_release_with_its_replacement_not_as_a_bare_removal():
    unverified = {**player("wr-b", "WR", "BUF", index=1), "health_freshness_state": "STALE"}
    roster = [player("wr-a", "WR", "KC", index=0), unverified, player("wr-c", "WR", "CIN", starter=False)]
    result = decide(roster, [candidate("wr-s1", "WR", "DEN"), candidate("wr-s2", "WR", "LAR")], slots=("WR", "WR"), capacity=4,
                    this_week={"wr-a": rank("WR", 10), "wr-b": rank("WR", 20), "wr-c": rank("WR", 50), "wr-s1": rank("WR", 60), "wr-s2": rank("WR", 70)},
                    rest_of_season={"wr-a": ros("WR", 5), "wr-b": ros("WR", 8), "wr-c": ros("WR", 50), "wr-s1": ros("WR", 10), "wr-s2": ros("WR", 15)})
    assert [(move["kind"], move["decision"], move["add"]["player_id"]) for move in result["moves"]] == [("DEPTH_UPGRADE", "ADD", "wr-s1")]
    assert result["ros_value"]["drop_status"]["wr-c"] == {
        "state": "SAFE", "reason": "Releasable: available wr-s2 is clearly ahead of him for the rest of the season (WR ROS ECR 15.0 vs 50.0; expert ranges 14–16 vs "
                                   "49–51 do not overlap) and the lineup stays covered; no current move uses this release."}


def test_questionable_flex_starter_keeps_a_backup_at_each_eligible_position():
    roster = [{**player("flex-q", "WR", "KC", index=0, health="QUESTIONABLE"), "lineup_slot": "FLEX"},
              player("rb-bench", "RB", "BUF", starter=False), player("te-bench", "TE", "CIN", starter=False)]
    result = decide(roster, [candidate("rb-free", "RB", "DEN")], slots=("FLEX",),
                    this_week={"flex-q": rank("WR", 20), "rb-bench": rank("RB", 10), "te-bench": rank("TE", 5), "rb-free": rank("RB", 30)},
                    rest_of_season={"flex-q": ros("WR", 10), "rb-bench": ros("RB", 60), "te-bench": ros("TE", 8), "rb-free": ros("RB", 25)})
    reason = "Backup for flex-q (Questionable) at FLEX this week."
    assert result["ros_value"]["protected"] == {"rb-bench": reason, "te-bench": reason}
    assert result["moves"] == [] and result["ros_value"]["drop_status"]["rb-bench"] == {"state": "PROTECTED", "reason": reason}


# W4: material rest-of-season edge and positional replacement context.

FORBIDDEN_VALUE_UNITS = re.compile(r"\b(points?|pts|vor|value score)\b|%|\$")


def rosr(position, ecr, best, worst, **overrides):
    return rank(position, ecr, horizon="rest_of_season", expert_best_rank=best, expert_worst_rank=worst, **overrides)


def value(position, ecr, best=None, worst=None, *, evidence_state="RANKED", range_state=None):
    return {"player_id": f"{position}-{ecr}", "position": position, "evidence_state": evidence_state, "ros_ecr": ecr, "expert_best_rank": best,
            "expert_worst_rank": worst, "expert_rank_sd": None, "range_state": range_state or ("VALID" if best is not None else "MISSING")}


@pytest.mark.parametrize("candidate_value,roster_value,state,separation,effect", [
    (value("K", 3.1, 2, 5), value("K", 10.8, 8, 16), "CLEAR_EDGE", "NON_OVERLAPPING", "SUPPORTS_RELEASE"),
    (value("K", 10.3, 5, 15), value("K", 10.8, 8, 16), "CLOSE_CALL", "OVERLAPPING", "DOES_NOT_SUPPORT_RELEASE"),
    (value("DEF", 6.3, 3, 9), value("DEF", 15.0, 11, 18), "CLEAR_EDGE", "NON_OVERLAPPING", "SUPPORTS_RELEASE"),
    (value("DEF", 11.2, 6, 17), value("DEF", 11.3, 4, 18), "CLOSE_CALL", "OVERLAPPING", "DOES_NOT_SUPPORT_RELEASE"),
    (value("TE", 13.8, 13, 15), value("TE", 21.8, 15, 28), "CLOSE_CALL", "OVERLAPPING", "DOES_NOT_SUPPORT_RELEASE"),
    (value("RB", 20.0, 15, 25), value("RB", 21.0, 15, 25), "CLOSE_CALL", "OVERLAPPING", "DOES_NOT_SUPPORT_RELEASE"),
    (value("RB", 20.0, 15, 25), value("RB", 20.0, 16, 24), "TIED", "OVERLAPPING", "DOES_NOT_SUPPORT_RELEASE"),
    (value("WR", 30.0, 25, 35), value("WR", 10.0, 8, 12), "ROSTER_BETTER", "NON_OVERLAPPING", "KEEP_ROSTER_PLAYER"),
    (value("WR", 12.0), value("WR", 30.0, 25, 35), "UNVERIFIED", "UNVERIFIED", "DOES_NOT_SUPPORT_RELEASE"),
    (value("WR", 12.0, range_state="INVALID"), value("WR", 30.0, 25, 35), "UNVERIFIED", "UNVERIFIED", "DOES_NOT_SUPPORT_RELEASE"),
    (value("WR", 12.0, evidence_state="STALE", range_state="NOT_RANKED"), value("WR", 30.0, 25, 35), "UNVERIFIED", "UNVERIFIED", "DOES_NOT_SUPPORT_RELEASE"),
    (value("RB", 25.0, 20, 30), value("WR", 40.0, 35, 45), "NOT_COMPARABLE", "NOT_APPLICABLE", "NOT_APPLICABLE"),
    (value("WR", 25.0, 20, 30), value("TE", 40.0, 35, 45), "NOT_COMPARABLE", "NOT_APPLICABLE", "NOT_APPLICABLE"),
])
def test_ros_materiality_needs_non_overlapping_expert_ranges_at_one_position(candidate_value, roster_value, state, separation, effect):
    result = ros_materiality(candidate_value, roster_value, candidate_name="cand", roster_name="mine")
    assert (result["contract_id"], result["state"], result["separation"], result["decision_effect"]) == ("waiver.ros_materiality.v1", state, separation, effect)
    assert not FORBIDDEN_VALUE_UNITS.search(" ".join((result["reason"], result["summary"], result["label"])).lower())


def test_close_call_explanation_names_both_expert_ranges():
    result = ros_materiality(value("K", 10.3, 5, 15), value("K", 10.8, 8, 16), candidate_name="Tyler Bass", roster_name="Jake Bates")
    assert result["reason"] == ("Tyler Bass ranks ahead of Jake Bates for the rest of the season (K ROS ECR 10.3 vs 10.8; lower is better), but their expert ranges "
                                "overlap (Tyler Bass 5–15 vs Jake Bates 8–16), so the edge is a close call.")
    assert result["summary"] == "Expert ranges overlap (Tyler Bass 5–15 vs Jake Bates 8–16), so the rest-of-season edge is a close call, not a clear upgrade."


def test_tiny_kicker_ros_edge_never_releases_the_starter_but_a_clear_edge_does():
    roster = [player("k-bates", "K", "DET", index=0)]
    week = {"k-bates": rank("K", 10.0, expert_best_rank=7, expert_worst_rank=12), "k-bass": rank("K", 3.7, expert_best_rank=2, expert_worst_rank=5),
            "k-little": rank("K", 4.7, expert_best_rank=1, expert_worst_rank=9)}
    rest = {"k-bates": rosr("K", 10.8, 8, 16), "k-bass": rosr("K", 10.3, 5, 15), "k-little": rosr("K", 3.1, 2, 5)}
    close_only = decide(roster, [candidate("k-bass", "K", "BUF")], slots=("K",), this_week=week, rest_of_season=rest)
    move = close_only["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"], move["state_label"], move["urgency"]) == ("MONITOR", None, "ROS_EDGE_NOT_MATERIAL", "MONITOR — CLOSE ROS CALL", "MATERIAL")
    assert (move["ros_materiality"]["state"], move["value_combination"], close_only["verdict"]["state"]) == ("CLOSE_CALL", "A_CLOSE_ROS", "OPTIONAL")
    assert close_only["ros_value"]["drop_status"]["k-bates"]["state"] == "PROTECTED"
    both = decide(roster, [candidate("k-bass", "K", "BUF"), candidate("k-little", "K", "JAX")], slots=("K",), this_week=week, rest_of_season=rest)
    move = both["moves"][0]
    assert (move["decision"], move["add"]["player_id"], move["drop"]["player_id"], move["drop"]["role"]) == ("ADD_DROP", "k-little", "k-bates", "REPLACED_STARTER")
    assert (move["ros_materiality"]["state"], move["urgency"], move["value_combination"]) == ("CLEAR_EDGE", "OPTIONAL", "A_BOTH")
    assert (move["passed_over"]["player_id"], move["passed_over"]["blocker"], move["passed_over"]["rank_text"]) == ("k-bass", "ROS_EDGE_NOT_MATERIAL", "K ECR 3.7")
    assert [(backup["player_id"], backup["ros_materiality"]["state"]) for backup in move["fallbacks"]] == [("k-bass", "CLOSE_CALL")]
    assert player_value_context(both, both["ros_value"]["roster"]["k-bates"], "k-bates", rostered=True)["materiality"]["state"] == "CLEAR_EDGE"


@pytest.mark.parametrize("ranges,blocker,label,status", [
    ({"wr-start": (18, 14, 22), "wr-bench": (24, 19, 30), "wr-free": (20, 15, 26)}, "ROS_EDGE_NOT_MATERIAL", "MONITOR — CLOSE ROS CALL", "PROTECTED"),
    ({"wr-start": (30, None, None), "wr-bench": (60, None, None), "wr-free": (20, None, None)}, "ROS_MATERIALITY_UNVERIFIED", "MONITOR — ROS MATERIALITY UNVERIFIED", "UNVERIFIED"),
])
def test_full_roster_release_needs_a_clear_ros_edge(ranges, blocker, label, status):
    roster = full_wr_roster(player("wr-bench", "WR", "BUF", starter=False))
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE, rest_of_season={pid: rosr("WR", *values) for pid, values in ranges.items()})
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"], move["state_label"]) == ("MONITOR", None, blocker, label)
    assert result["ros_value"]["drop_status"]["wr-bench"]["state"] == status
    assert result["ros_value"]["roster"]["wr-bench"]["evidence_state"] == "RANKED"


def test_bench_depth_is_released_before_a_clearly_beaten_starter():
    roster = full_wr_roster(player("wr-bench", "WR", "BUF", starter=False))
    result = decide(roster, [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": rosr("WR", 40, 35, 45), "wr-bench": rosr("WR", 60, 55, 66), "wr-free": rosr("WR", 20, 17, 23)})
    move = result["moves"][0]
    assert (move["decision"], move["drop"]["player_id"], move["drop"]["role"], move["ros_materiality"]["state"]) == ("ADD_DROP", "wr-bench", "BENCH", "CLEAR_EDGE")
    assert result["ros_value"]["drop_status"]["wr-start"]["state"] == "PROTECTED"


def test_close_ros_depth_comparison_is_a_hold_note_unless_a_roster_spot_is_open():
    roster = [player("rb-start", "RB", "KC", index=0), player("rb-bench", "RB", "BUF", starter=False)]
    kwargs = dict(slots=("RB",), this_week={"rb-start": rank("RB", 10), "rb-bench": rank("RB", 40), "rb-white": rank("RB", 30)},
                  rest_of_season={"rb-start": rosr("RB", 8, 6, 10), "rb-bench": rosr("RB", 42.2, 35, 47), "rb-white": rosr("RB", 35, 31, 42)})
    full = decide(roster, [candidate("rb-white", "RB", "WAS")], **kwargs)
    [note] = full["depth_notes"]
    assert (full["moves"], full["verdict"]["state"], full["verdict"]["save_faab"]) == ([], "PASS", True)
    assert (note["position"], note["state"], note["label"], note["add"]["player_id"], note["over"]["player_id"]) == ("RB", "CLOSE_CALL", "CLOSE ROS CALL", "rb-white", "rb-bench")
    assert note["text"] == ("rb-white ranks ahead of rb-bench for the rest of the season (RB ROS ECR 35.0 vs 42.2; lower is better), but their expert ranges overlap "
                            "(rb-white 31–42 vs rb-bench 35–47), so the edge is a close call. No release is recommended.")
    open_spot = decide(roster, [candidate("rb-white", "RB", "WAS")], capacity=3, **kwargs)
    move = open_spot["moves"][0]
    assert (move["kind"], move["decision"], move["drop"], move["ros_materiality"]["state"]) == ("DEPTH_UPGRADE", "ADD", None, "CLOSE_CALL")
    assert move["impact"].startswith("Rest-of-season bench add for an open roster spot, not a clear upgrade over rb-bench")


def test_unverified_ros_materiality_keeps_a_pass_from_saying_save_faab():
    roster = [player("rb-start", "RB", "KC", index=0), player("rb-bench", "RB", "BUF", starter=False)]
    result = decide(roster, [candidate("rb-free", "RB", "WAS")], slots=("RB",),
                    this_week={"rb-start": rank("RB", 10), "rb-bench": rank("RB", 40), "rb-free": rank("RB", 30)},
                    rest_of_season={"rb-start": rosr("RB", 8, 6, 10), "rb-bench": rosr("RB", 60, None, None), "rb-free": rosr("RB", 30, 25, 35)})
    [note] = result["depth_notes"]
    assert (note["state"], result["verdict"]["state"], result["verdict"]["save_faab"], result["verdict"]["save_faab_text"]) == ("UNVERIFIED", "PASS", False, None)
    assert result["verdict"]["detail"].endswith("Rest-of-season expert separation could not be verified for RB depth, so saving FAAB is not yet supported.")


def test_required_slot_fill_stays_act_even_when_options_are_comparable():
    result = decide([player("wr-start", "WR", "KC", index=0)], [candidate("k-a", "K", "DEN"), candidate("k-b", "K", "BUF")], slots=("WR", "K"), empty_slots=("K",),
                    capacity=3, this_week={"wr-start": rank("WR", 30), "k-a": rank("K", 12), "k-b": rank("K", 13)},
                    rest_of_season={"k-a": rosr("K", 12, 8, 16), "k-b": rosr("K", 12.5, 9, 17)})
    move = result["moves"][0]
    assert (move["kind"], move["urgency"], move["decision"], result["verdict"]["state"]) == ("MUST_FILL", "REQUIRED", "ADD", "ACT")


def test_required_bye_fill_stays_act_when_releasing_the_bye_kicker_is_only_a_close_call():
    result = decide([player("k-start", "K", "MIN", index=0)], [candidate("k-free", "K", "DEN")], slots=("K",), byes=("MIN", "SEA"),
                    this_week={"k-start": rank("K", 5), "k-free": rank("K", 12)}, rest_of_season={"k-start": rosr("K", 10.8, 8, 16), "k-free": rosr("K", 10.3, 5, 15)})
    move = result["moves"][0]
    assert (move["kind"], move["urgency"], move["decision"], move["drop_blocker"], result["verdict"]["state"]) == ("MUST_FILL", "REQUIRED", "MONITOR", "ROS_EDGE_NOT_MATERIAL", "ACT")


def test_replacement_context_is_positional_and_built_only_from_verified_actionable_ranked_players():
    roster = [player("k-start", "K", "MIN", index=0), player("d-start", "DEF", "KC", index=1), player("te-start", "TE", "BUF", index=2),
              player("rb-start", "RB", "CIN", index=3), player("wr-start", "WR", "DAL", index=4)]
    candidates = [candidate("k-far", "K", "NYJ"), candidate("k-c", "K", "SEA"), candidate("k-b", "K", "LAR"), candidate("k-a", "K", "DEN"),
                  candidate("k-q", "K", "ATL", health="QUESTIONABLE"), candidate("k-unranked", "K", "MIA"), candidate("k-taken", "K", "PHI"),
                  candidate("d-a", "DEF", "DET"), candidate("d-b", "DEF", "GB"), candidate("te-a", "TE", "CHI"), candidate("rb-a", "RB", "HOU")]
    positions = {"k": "K", "d": "DEF", "te": "TE", "rb": "RB", "wr": "WR"}
    week = {item["player_id"]: rank(item["position"], 1 if item["player_id"].endswith("start") else 40) for item in [*roster, *candidates]}
    week.update({"k-far": rank("K", 34), "k-c": rank("K", 36), "k-b": rank("K", 38)})  # current-week order is the reverse of the ROS order
    rest = {"k-start": rosr("K", 12, 9, 15), "d-start": rosr("DEF", 10, 8, 12), "te-start": rosr("TE", 5, 4, 6), "rb-start": rosr("RB", 20, 18, 22),
            "wr-start": rosr("WR", 20, 18, 22), "k-a": rosr("K", 10, 8, 13), "k-b": rosr("K", 13, 11, 16), "k-c": rosr("K", 14, 12, 20), "k-far": rosr("K", 30, 25, 35),
            "k-q": rosr("K", 9, 7, 11), "k-taken": rosr("K", 2, 1, 3), "d-a": rosr("DEF", 11, 9, 14), "d-b": rosr("DEF", 12, 10, 15), "te-a": rosr("TE", 20, 15, 25),
            "rb-a": rosr("RB", 21, 19, 23)}
    result = decide(roster, candidates, slots=tuple(positions.values()), this_week=week, rest_of_season=rest, owned_player_ids=["k-taken"])
    pools, contexts = result["replacement"]["positions"], result["replacement"]["players"]
    assert result["moves"] == [] and pools["K"]["counts"] == {"available": 6, "ros_ranked": 5, "ros_unranked": 1, "materiality_capable": 5, "actionable": 4,
                                                             "comparison": 4, "recommended_adds_excluded": 0, "remaining": 4}
    assert [entry["player_id"] for entry in pools["K"]["comparison"]] == ["k-a", "k-b", "k-c", "k-far"]
    assert [entry["player_id"] for entry in pools["DEF"]["comparison"]] == ["d-a", "d-b"] and pools["WR"]["comparison"] == []
    for pool in pools.values():
        counts = pool["counts"]
        assert counts["available"] == counts["ros_ranked"] + counts["ros_unranked"] and counts["comparison"] <= min(counts["actionable"], counts["materiality_capable"])
    assert (contexts["k-start"]["state"], contexts["k-start"]["comparable_count"], [entry["player_id"] for entry in contexts["k-start"]["nearest"]]) == ("STRONG", 3, ["k-a", "k-b", "k-c"])
    assert contexts["k-start"]["reason"] == "3 healthy available kickers have fresh rest-of-season expert ranges reaching k-start's (9–15)."
    assert (contexts["d-start"]["state"], contexts["d-start"]["comparable_count"]) == ("STRONG", 2)
    assert (contexts["rb-start"]["state"], contexts["rb-start"]["reason"]) == ("LIMITED", "Only rb-a (RB ROS ECR 21.0, experts 19–23) reaches rb-start's rest-of-season expert range (18–22).")
    assert contexts["te-start"]["state"] == "SCARCE"
    assert contexts["te-start"]["reason"] == "No healthy available TE reaches te-start's rest-of-season expert range (4–6); the best available is te-a (TE ROS ECR 20.0, experts 15–25)."
    assert (contexts["wr-start"]["state"], contexts["wr-start"]["comparable_count"]) == ("UNVERIFIED", None)
    lookup = player_value_context(result, result["ros_value"]["roster"]["k-start"], "k-start", rostered=True)
    assert (lookup["materiality"]["state"], lookup["materiality"]["candidate"], lookup["replacement"]["state"]) == ("CLOSE_CALL", "k-a", "STRONG")
    far = player_value_context(result, result["ros_value"]["candidates"]["k-far"], "k-far", rostered=False)
    assert (far["materiality"]["state"], far["materiality"]["roster"]) == ("ROSTER_BETTER", "k-start")
    assert not FORBIDDEN_VALUE_UNITS.search(json.dumps(result["replacement"]).lower())
    assert not re.search(r"value_score|player_value\b|vor|points", json.dumps(result).lower())


def test_replacement_reason_names_the_clearly_better_option_and_the_excluded_add():
    def entry(player_id, name, ecr, best, worst):
        return {**value("DEF", ecr, best, worst), "player_id": player_id, "player": name}

    pool = {"comparison": [entry("d-pit", "Pittsburgh Steelers", 4.0, 1, 6), entry("d-gb", "Green Bay Packers", 6.0, 3, 9)],
            "recommended_adds": [{"player_id": "d-tb", "player": "Tampa Bay Buccaneers"}]}
    context = replacement_context({**value("DEF", 9.0, 7, 12), "player_id": "d-jax"}, "Jacksonville Jaguars", pool)
    assert (context["state"], context["comparable_count"], context["clearly_ahead_count"]) == ("STRONG", 2, 1)
    assert context["reason"] == ("2 healthy available defenses have fresh rest-of-season expert ranges reaching Jacksonville Jaguars' (7–12); 1 of them, "
                                 "Pittsburgh Steelers, is clearly ahead. Excludes Tampa Bay Buccaneers, already recommended to add.")
    own = replacement_context({**value("DEF", 5.0, 2, 8), "player_id": "d-tb"}, "Tampa Bay Buccaneers", pool)
    assert own["reason"] == "2 healthy available defenses have fresh rest-of-season expert ranges reaching Tampa Bay Buccaneers' (2–8)."


def test_stale_ros_leaves_replacement_context_and_materiality_unverified():
    def stale(ecr, best, worst):
        return rosr("WR", ecr, best, worst, source_age_seconds=752400, source_date="2026-11-07")

    result = decide(full_wr_roster(player("wr-bench", "WR", "BUF", starter=False)), [candidate("wr-free", "WR", "DEN")], this_week=WR_UPGRADE,
                    rest_of_season={"wr-start": stale(40, 35, 45), "wr-bench": stale(90, 80, 99), "wr-free": stale(20, 17, 23)})
    move = result["moves"][0]
    assert (move["drop_blocker"], move["ros_materiality"], move["replacement_context"]) == ("ROS_VALUE_UNAVAILABLE", None, None)
    assert result["replacement"]["players"]["wr-bench"]["state"] == "UNVERIFIED" and result["replacement"]["positions"]["WR"]["comparison"] == []


def test_flex_coverage_never_names_a_cross_position_best_backup():
    roster = [{**player("rb-flex", "RB", "MIN", index=0), "lineup_slot": "FLEX"}, player("wr-bench", "WR", "BUF", starter=False), player("te-bench", "TE", "CIN", starter=False)]
    kwargs = dict(slots=("FLEX",), byes=("MIN", "SEA"), this_week={"rb-flex": rank("RB", 10), "wr-bench": rank("WR", 30), "te-bench": rank("TE", 5)})
    result = decide(roster, [], **kwargs)
    [note] = result["lineup_notes"]
    assert (note["player_id"], [option["player_id"] for option in note["options"]]) == (None, ["wr-bench", "te-bench"])
    assert note["note"] == ("FLEX has verified internal coverage for rb-flex from WR/TE bench options: wr-bench (WR); te-bench (TE). Consensus ranks are positional, "
                            "so no cross-position best is named; choose who starts. No waiver move is needed.")
    assert result["moves"] == [] and set(result["ros_value"]["protected"]) == {"wr-bench", "te-bench"}
    with_rb = decide([*roster, player("rb-bench", "RB", "DAL", starter=False)], [], **{**kwargs, "this_week": {**kwargs["this_week"], "rb-bench": rank("RB", 45)}})
    [note] = with_rb["lineup_notes"]
    assert (note["player_id"], note["note"]) == ("rb-bench", "Start rb-bench in the FLEX slot for rb-flex; no waiver move is needed.")


# Cross-position release (waiver.cross_position_drop.v1), the drop-candidate order, and the manager plan built on them.

FULL_SLOTS = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF")


def ros_range(position, ecr, best, worst):
    return {**ros(position, ecr), "expert_best_rank": best, "expert_worst_rank": worst}


def starters_core(flex=None):
    return [player("qb", "QB", "CIN", index=0), player("rb-1", "RB", "TEN", index=1), player("rb-2", "RB", "NYJ", index=2), player("wr-1", "WR", "DAL", index=3),
            player("wr-2", "WR", "SEA", index=4), player("te-1", "TE", "LV", index=5), {**(flex or player("wr-3", "WR", "HOU", index=6)), "lineup_slot": "FLEX"},
            player("k", "K", "JAX", index=7), player("def", "DEF", "JAX", index=8)]


def surplus_bench():
    return [player("rb-3", "RB", "MIA", starter=False), player("rb-4", "RB", "PIT", starter=False), player("rb-5", "RB", "ARI", starter=False),
            player("wr-4", "WR", "NE", starter=False), player("wr-5", "WR", "SF", starter=False)]


FREE_AGENTS = [candidate("te-free", "TE", "WAS"), candidate("te-alt", "TE", "ATL"), candidate("rb-fa-1", "RB", "DET"), candidate("rb-fa-2", "RB", "BAL"),
               candidate("rb-fa-3", "RB", "CHI"), candidate("wr-fa-1", "WR", "NO"), candidate("wr-fa-2", "WR", "CLE")]
SURPLUS_WEEK = {"qb": rank("QB", 1), "rb-1": rank("RB", 16), "rb-2": rank("RB", 15), "wr-1": rank("WR", 3), "wr-2": rank("WR", 2), "wr-3": rank("WR", 12),
                "te-1": rank("TE", 29, expert_best_rank=23, expert_worst_rank=36), "k": rank("K", 2), "def": rank("DEF", 3), "rb-3": rank("RB", 22),
                "rb-4": rank("RB", 39), "rb-5": rank("RB", 42), "wr-4": rank("WR", 17), "wr-5": rank("WR", 16), "te-free": rank("TE", 10),
                "te-alt": rank("TE", 15, expert_best_rank=13, expert_worst_rank=17)}
SURPLUS_ROS = {"qb": ros("QB", 2), "rb-1": ros_range("RB", 19, 14, 26), "rb-2": ros_range("RB", 20, 17, 25), "wr-1": ros("WR", 4), "wr-2": ros("WR", 1),
               "wr-3": ros("WR", 13), "te-1": ros_range("TE", 22, 15, 28), "k": ros("K", 3), "def": ros("DEF", 4), "rb-3": ros_range("RB", 19, 17, 21),
               "rb-4": ros_range("RB", 40, 37, 43), "rb-5": ros_range("RB", 42, 35, 47), "wr-4": ros_range("WR", 15, 15, 16), "wr-5": ros_range("WR", 28, 26, 30),
               "te-free": ros_range("TE", 14, 13, 15), "te-alt": ros_range("TE", 14.5, 11, 17), "rb-fa-1": ros_range("RB", 35, 31, 42),
               "rb-fa-2": ros_range("RB", 42, 36, 48), "rb-fa-3": ros_range("RB", 47, 40, 50), "wr-fa-1": ros_range("WR", 25, 19, 29), "wr-fa-2": ros_range("WR", 30, 25, 35)}


def surplus_league(roster=None, *, week=None, rest=None, candidates=None, **overrides):
    """A full 14-player roster: one TE (below its depth target of 2) and five RBs and five WRs (each one above its target of 4)."""
    return decide(roster or starters_core() + surplus_bench(), FREE_AGENTS if candidates is None else candidates, this_week={**SURPLUS_WEEK, **(week or {})},
                  rest_of_season={**SURPLUS_ROS, **(rest or {})} if rest is not False else None, slots=FULL_SLOTS, **overrides)


def test_te_upgrade_releases_the_most_replaceable_surplus_rb_when_no_te_can_be_released():
    result = surplus_league()
    move = result["moves"][0]
    assert (move["position"], move["kind"], move["decision"], move["state_label"]) == ("TE", "CURRENT_WEEK_UPGRADE", "ADD_DROP", "ADD + DROP — CROSS-POSITION")
    assert (move["add"]["player_id"], move["drop"]["player_id"], move["drop"]["basis"], move["drop"]["add_basis"]) == ("te-free", "rb-5", "cross_position", "VERIFIED_NEED")
    assert move["drop"]["surplus"] == {"position": "RB", "count": 5, "count_after": 4, "depth_target": 4}
    # RB is chosen over the equally eligible WR because more waiver RBs reach his expert range (3 vs 2); positional ranks are never compared.
    assert [(option["player_id"], option["blocker"], option["replacement"]["comparable_count"]) for option in move["cross_position"]["options"]] == [
        ("rb-5", None, 3), ("wr-5", None, 2)]
    assert (move["rest_of_season"]["roster"], move["ros_materiality"]["state"], move["replacement_context"]["state"]) == ("te-1", "CLOSE_CALL", "STRONG")
    assert move["value_combination"] == "CROSS_POSITION_RELEASE" and move["impact"].startswith("Current-week upgrade over te-1, who stays as TE depth")
    assert move["drop_safety"]["state"] == "SUPPORTED" and move["drop"]["reason"].endswith(
        "Every starting slot, including FLEX, can still be filled this week and for the rest of the season. Ranks are not compared across positions.")
    assert any(text.startswith("Cross-position release:") and "No same-position release was verified: te-free ranks ahead of te-1" in text for text in move["disclosures"])
    assert (result["verdict"]["state"], result["verdict"]["counts"]["executable"]) == ("ACT", 1)
    status = result["ros_value"]["drop_status"]
    assert (status["rb-5"]["state"], status["te-1"]["state"]) == ("SAFE", "PROTECTED")
    rb_view = player_value_context(result, result["ros_value"]["roster"]["rb-5"], "rb-5", rostered=True)
    assert rb_view["materiality"]["label"] == "CROSS-POSITION RELEASE" and "never on a cross-position rank comparison" in rb_view["materiality"]["reason"]


def test_te_upgrade_releases_a_clearly_beaten_bench_te_before_any_other_position():
    roster = starters_core() + surplus_bench() + [player("te-2", "TE", "KC", starter=False)]
    move = surplus_league(roster, rest={"te-2": ros_range("TE", 40, 38, 42)})["moves"][0]
    assert (move["decision"], move["state_label"], move["drop"]["player_id"], move["drop"]["basis"], move["drop"]["role"]) == (
        "ADD_DROP", "ADD + DROP", "te-2", "rest_of_season", "BENCH")
    assert "cross_position" not in move


def test_candidate_better_this_week_but_not_rest_of_season_never_releases_a_player_at_another_position():
    result = surplus_league(rest={"te-free": ros_range("TE", 25, 24, 26), "te-alt": ros_range("TE", 26, 24, 28)})
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"], move["value_combination"]) == ("MONITOR", None, "ROSTER_ROS_STRONGER", "B_SHORT_TERM")
    assert move["monitor_detail"] == ("te-1 ranks ahead of te-free for the rest of the season (TE ROS ECR 22.0 vs 25.0; lower is better). "
                                      "The current-week edge is short-term, so te-1 is kept.")
    assert [backup["claim"]["state"] for backup in move["fallbacks"]] == ["MONITOR"]
    assert result["ros_value"]["drop_status"]["rb-5"]["state"] != "SAFE" and result["verdict"]["counts"]["executable"] == 0


def rb_need_league(flex_fresh=True):
    """Three RBs (below the target of 4) and six WRs; rb-free is a rest-of-season RB upgrade on bye this week, so not a current-week one."""
    flex = {**player("wr-3", "WR", "HOU", index=6), **({} if flex_fresh else {"health_freshness_state": "STALE"})}
    roster = starters_core(flex) + [player("rb-3", "RB", "MIA", starter=False), player("wr-4", "WR", "NE", starter=False),
                                    player("wr-5", "WR", "SF", starter=False), player("wr-6", "WR", "BUF", starter=False)]
    return decide(roster, [candidate("rb-free", "RB", "MIN"), candidate("wr-fa-1", "WR", "NO"), candidate("wr-fa-2", "WR", "CLE")], slots=FULL_SLOTS,
                  byes=("MIN", "MIA", "NE", "SF"), this_week={key: SURPLUS_WEEK[key] for key in ("qb", "rb-1", "rb-2", "wr-1", "wr-2", "wr-3", "te-1", "k", "def")},
                  rest_of_season={**{key: SURPLUS_ROS[key] for key in ("qb", "rb-1", "rb-2", "wr-1", "wr-2", "wr-3", "te-1", "k", "def")},
                                  "rb-3": ros_range("RB", 45, 40, 50), "rb-free": ros_range("RB", 38, 35, 41), "wr-4": ros_range("WR", 15, 15, 16),
                                  "wr-5": ros_range("WR", 29, 27, 31), "wr-6": ros_range("WR", 30, 26, 34), "wr-fa-1": ros_range("WR", 32, 28, 36),
                                  "wr-fa-2": ros_range("WR", 35, 30, 40)})


@pytest.mark.parametrize("flex_fresh,drop", [(True, "wr-6"), (False, "wr-5")])
def test_rest_of_season_need_releases_surplus_depth_without_breaking_flex(flex_fresh, drop):
    result = rb_need_league(flex_fresh)
    [move] = result["moves"]
    assert (move["kind"], move["decision"], move["add"]["player_id"], move["drop"]["player_id"], move["drop"]["add_basis"]) == (
        "DEPTH_UPGRADE", "ADD_DROP", "rb-free", drop, "VERIFIED_NEED")
    assert move["current_week"]["text"] == "Bench depth move: your current-week lineup is unchanged."
    assert move["impact"] == f"Adds RB depth for the rest of the season while rb-3 stays; your current-week lineup is unchanged; {drop} (WR), surplus depth with strong waiver replacement, is released"
    keep = {entry["player_id"]: entry for entry in result["drop_candidates"]["players"]}
    if flex_fresh:
        assert keep["wr-5"]["state"] == "RELEASABLE"
    else:
        # wr-6 is the only bench player who can fill FLEX this week (wr-3's health is unverified and the rest are on bye), so he is kept.
        assert keep["wr-6"]["state"] == "KEEP" and "would leave fewer starting slots covered this week" in " ".join(keep["wr-6"]["reasons"])


def test_protected_and_starting_players_are_never_released_across_positions():
    questionable = player("wr-1", "WR", "DAL", index=3, health="QUESTIONABLE")
    roster = [questionable if item["player_id"] == "wr-1" else item for item in starters_core()]
    roster += [player("rb-3", "RB", "MIA", starter=False), player("rb-4", "RB", "PIT", starter=False), player("wr-4", "WR", "NE", starter=False),
               player("wr-5", "WR", "SF", starter=False), player("wr-6", "WR", "BUF", starter=False)]
    result = surplus_league(roster, week={"wr-6": rank("WR", 40)}, rest={"rb-1": ros_range("RB", 60, 55, 65), "wr-4": ros_range("WR", 27, 25, 29),
                                                                          "wr-5": ros_range("WR", 28, 26, 30), "wr-6": ros_range("WR", 15, 15, 16)})
    move = result["moves"][0]
    assert result["ros_value"]["protected"]["wr-5"] == "Backup for wr-1 (Questionable) at WR this week."
    weakest_starter = surplus_league(rest={"rb-1": ros_range("RB", 60, 55, 65)})["moves"][0]
    assert (weakest_starter["drop"]["player_id"], weakest_starter["drop"]["position"]) == ("rb-5", "RB")
    assert (move["decision"], move["drop"]["player_id"], move["drop"]["position"]) == ("ADD_DROP", "wr-4", "WR")
    assert result["ros_value"]["drop_status"]["rb-1"]["state"] == "PROTECTED" and all(option["player_id"] != "wr-5" for option in move["cross_position"]["options"])


def test_player_whose_game_has_kicked_off_is_never_released_across_positions():
    result = surplus_league(locked_games=(("ARI", "MIN"),))
    move = result["moves"][0]
    assert (move["decision"], move["drop"]["player_id"]) == ("ADD_DROP", "rb-4")
    assert result["ros_value"]["drop_status"]["rb-5"] == {"state": "PROTECTED", "reason": "His game has already kicked off this week, so his roster spot is locked."}


def test_stale_rest_of_season_evidence_never_authorizes_a_cross_position_release():
    stale = {key: {**value, "source_age_seconds": 752400, "source_date": "2026-11-07"} for key, value in SURPLUS_ROS.items()}
    result = surplus_league(rest=stale)
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"], "cross_position" in move) == ("MONITOR", None, "ROS_VALUE_UNAVAILABLE", False)
    assert {entry["state"] for entry in result["drop_candidates"]["players"]} == {"UNVERIFIED"}
    plan = build_manager_plan(result)
    assert plan["best_move"] is None and plan["headline"].startswith("MONITOR te-free") and plan["drop_candidates"] == []


def test_unverified_ownership_blocks_the_plan_and_every_release():
    result = surplus_league(pool_allowed=False, pool_blockers=["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"])
    plan = build_manager_plan(result)
    assert (result["verdict"]["state"], result["moves"], result["drop_candidates"]["players"]) == ("BLOCKED", [], [])
    assert (plan["state"], plan["best_move"], plan["blockers"]) == ("BLOCKED", None, ["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"])


def test_unranked_bench_player_is_not_treated_as_the_weakest_release():
    rest = {key: value for key, value in SURPLUS_ROS.items() if key != "rb-5"}
    result = decide(starters_core() + surplus_bench(), FREE_AGENTS, this_week=SURPLUS_WEEK, rest_of_season=rest, slots=FULL_SLOTS)
    assert result["moves"][0]["drop"]["player_id"] == "rb-4"
    entry = next(item for item in result["drop_candidates"]["players"] if item["player_id"] == "rb-5")
    assert entry["state"] == "UNVERIFIED" and entry["reasons"] == ["Not ranked here: no fresh rest-of-season rank (unranked); an unranked player is not treated as worse."]


def test_contradictory_team_needs_fail_closed_for_cross_position_releases():
    roster = starters_core() + surplus_bench()
    settings = league_settings_contract({"roster_positions": [*FULL_SLOTS, "BN", "BN"], "scoring_settings": {"rec": 1}})
    page_needs = team_needs_contract([*({"position": item["position"]} for item in roster), {"position": "RB"}], settings)
    result = surplus_league(team_needs=page_needs)
    move = result["moves"][0]
    assert result["team_needs"]["state"] == "CONTRADICTORY"
    assert (move["decision"], move["drop"], move["drop_blocker"]) == ("MONITOR", None, "ROS_EDGE_NOT_MATERIAL")
    assert "A release at a different position is not evaluated: The page's team-needs result disagrees with your active roster at RB, FLEX" in move["monitor_detail"]
    assert surplus_league(team_needs=team_needs_contract(roster, settings))["team_needs"]["state"] == "AVAILABLE"


def test_contingent_claims_are_verified_one_by_one_and_shared_with_the_move_checker():
    result = surplus_league()
    move = result["moves"][0]
    assert [(backup["player_id"], backup["claim"]["state"], (backup["claim"]["drop"] or {}).get("player_id")) for backup in move["fallbacks"]] == [("te-alt", "ADD_DROP", "rb-5")]
    checker = selected_player_priority(result, "te-1")
    assert (checker["state"], checker["role"], checker["move"]["add"]["player_id"], checker["move"]["drop"]["player_id"]) == ("IN_PRIORITY_MOVE", "REPLACED", "te-free", "rb-5")
    assert [(option["add_id"], option["state"], option["drop"]) for option in checker["options"]] == [("te-free", "ADD_DROP", "rb-5"), ("te-alt", "ADD_DROP", "rb-5")]
    assert selected_player_priority(result, "rb-5")["role"] == "DROP"
    unrelated = selected_player_priority(result, "wr-4")
    assert (unrelated["state"], unrelated["drop_candidate"]["state"]) == ("NO_PRIORITY_MOVE", "KEEP")


def test_drop_candidates_and_manager_plan_restate_the_shared_decision():
    result = surplus_league()
    order = [(entry["player_id"], entry["state"]) for entry in result["drop_candidates"]["players"]]
    assert order == [("rb-5", "VERIFIED_DROP"), ("rb-4", "RELEASABLE"), ("wr-5", "RELEASABLE"), ("rb-3", "KEEP"), ("wr-4", "KEEP")]
    assert result["team_needs"]["positions"]["TE"]["depth_status"] == "BELOW_TARGET"
    market = {"state": "AVAILABLE", "label": "MARKET HISTORY AVAILABLE", "scope_text": "Weeks 1–10",
              "budget_context": {"state": "AVAILABLE", "total": 10, "distribution": {"n": 10, "median_remaining": 81}},
              "position_summaries": {"TE": {"text": "TE (Weeks 1–10): 10 completed claims.", "contested_bids": {"text": "$9 (N=1, single observation)"},
                                            "uncontested_bids": {"text": "$0–$11, median $3 (N=9)"}}}}
    result["moves"][0]["market"] = {"lines": ["Player history: NO LEAGUE CLAIM HISTORY for te-free in Weeks 1–10.", "TE (Weeks 1–10): 10 completed claims."]}
    plan = build_manager_plan(result, market=market)
    assert (plan["state"], plan["headline"], plan["best_move"]["drop"]["basis"]) == ("ACT", "ADD te-free · DROP rb-5", "cross_position")
    assert [(claim["add"], claim["state"], claim["drop"]) for claim in plan["backup_claims"]] == [("te-alt", "ADD_DROP", "rb-5")]
    assert [entry["player_id"] for entry in plan["drop_candidates"]] == ["rb-5", "rb-4", "wr-5"]
    labels = {row["position"]: row["label"] for row in plan["positions"]}
    assert labels == {"QB": "HOLD", "RB": "SURPLUS", "WR": "SURPLUS", "TE": "UPGRADE", "K": "HOLD", "DEF": "HOLD"}
    faab = plan["faab"]
    assert (faab["remaining"], faab["league_median_remaining"], faab["value_bid"], faab["guardrail"]) == (41, 81, "VALUE-BASED BID UNAVAILABLE", None)
    assert faab["player_history"] == "Player history: NO LEAGUE CLAIM HISTORY for te-free in Weeks 1–10." and plan["submits_transactions"] is False


def test_cross_position_release_needs_strong_waiver_replacement_depth_at_the_released_position():
    result = surplus_league(candidates=[candidate("te-free", "TE", "WAS"), candidate("te-alt", "TE", "ATL"), candidate("rb-fa-1", "RB", "DET")])
    move = result["moves"][0]
    assert (move["decision"], move["drop"], move["drop_blocker"]) == ("MONITOR", None, "ROS_EDGE_NOT_MATERIAL")
    assert [(option["player_id"], option["blocker"]) for option in move["cross_position"]["options"]] == [("rb-5", "REPLACEMENT_NOT_STRONG"), ("wr-5", "REPLACEMENT_NOT_STRONG")]
    assert "A release at a different position was checked: rb-5 (RB) — replacement depth limited on waivers" in move["monitor_detail"]
