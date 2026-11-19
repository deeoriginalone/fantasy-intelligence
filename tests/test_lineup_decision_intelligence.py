from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from services.authoritative_week import build_sleeper_week_contract
from services.dynastyprocess_rankings import evaluate as evaluate_rankings
from services.lineup_decision_intelligence import CONSENSUS_UNIT, build_lineup_decision, build_slot_contract
from services.lineup_evidence import build_matchup_evidence
from services.team_needs import league_settings_contract

NOW = "2026-09-16T12:00:00+00:00"
NOW_TIME = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
FRESH_HEALTH = {"state": "AVAILABLE", "source": "Sleeper API", "freshness_state": "FRESH", "last_verified": NOW}
STANDARD_SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"]
PRELIMINARY_MATCHUP_FIELDS = {
    "matchup_rank": 12,
    "matchup_source": "automated:nflverse",
    "matchup_retrieved_at": NOW,
    "matchup_sample_threshold_id": None,
    "matchup_population": "ALL_DEFENSES_BY_POSITION",
    "matchup_directionality": "LOWER_IS_HARDER",
    "matchup_publication_lineage": {"publication_contracts": {"population": {"size": 32}}},
    "matchup_sample_size": 2,
    "matchup_source_recorded_at": NOW,
    "matchup_source_authority": "automated",
}


def settings(positions=STANDARD_SLOTS, rec=1.0):
    league = {"roster_positions": positions}
    if rec is not None:
        league["scoring_settings"] = {"rec": rec}
    return league_settings_contract(league)


def player(name, position, value=None, *, slot=None, index=None, status="Active", baseline=None, multiplier=1.0, **extra):
    row = {
        "player": name, "position": position, "source_player_id": name, "injury_status": status, "health_status_available": True,
        "opponent": "KC", "is_bye": False, "weekly_score": value, "weekly_baseline": value if baseline is None else baseline,
        "matchup_modifier": 0.0, "injury_multiplier": multiplier,
        "sleeper_current_starter": slot is not None, "sleeper_lineup_slot": slot, "sleeper_lineup_index": index,
    }
    row.update(extra)
    return row


def base_roster():
    return [
        player("QB1", "QB", 20.0, slot="QB", index=0),
        player("RB1", "RB", 12.0, slot="RB", index=1),
        player("RB2", "RB", 11.0, slot="RB", index=2),
        player("WR1", "WR", 14.0, slot="WR", index=3),
        player("WR2", "WR", 13.0, slot="WR", index=4),
        player("TE1", "TE", 9.0, slot="TE", index=5),
        player("FLEX1", "WR", 10.0, slot="FLEX", index=6),
        player("K1", "K", 7.0, slot="K", index=7),
        player("DEF1", "DEF", 6.0, slot="DEF", index=8, status=""),
        player("BENCH-RB", "RB", 8.0),
        player("BENCH-WR", "WR", 7.5),
    ]


def without_values(roster):
    return [dict(row, weekly_score=None, weekly_baseline=None) for row in roster]


def provider(player_id, ppg, freshness="FRESH", **extra):
    return {
        "state": "AVAILABLE" if freshness == "FRESH" else "PRELIMINARY", "evidence_level": "PRELIMINARY", "recommendation_impact": "INFORMATIONAL_ONLY",
        "sleeper_id": player_id, "projected_ppg": ppg, "metric_name": "Provider Full-PPR Projection", "unit": "fantasy_points_per_game",
        "source": "JerryGM jgm_baseline", "scoring_format": "ppr", "season": 2026, "week": 3, "source_record_time": NOW, "retrieved_at": NOW,
        "freshness_state": freshness, "completeness_state": "COMPLETE" if freshness == "FRESH" else "INCOMPLETE", "blockers": [],
        "attribution": "JerryGM projections.", "limitations": [], **extra,
    }


def decide(roster, **kwargs):
    kwargs.setdefault("league_settings", settings())
    kwargs.setdefault("team_health", FRESH_HEALTH)
    kwargs.setdefault("season", 2026)
    kwargs.setdefault("week", 3)
    kwargs.setdefault("game_locks", locks(roster))
    return build_lineup_decision(roster, **kwargs)


KICKOFF = "2026-09-20T17:00:00+00:00"


def locks(roster, *, locked=(), unverified=(), kickoff=KICKOFF):
    """Schedule-owned lock contracts: OPEN unless a player is listed as LOCKED or LOCK_UNVERIFIED."""
    def lock(player_id):
        if player_id in locked:
            return {"state": "LOCKED", "label": "Locked", "kickoff_utc": "2026-09-16T11:00:00+00:00", "kickoff_display": "Wed Sep 16 4:00 AM PDT",
                    "no_game": False, "blocker": None, "reason": "Kickoff has passed; Sleeper locks the player at kickoff."}
        if player_id in unverified:
            return {"state": "LOCK_UNVERIFIED", "label": "Unverified", "kickoff_utc": None, "no_game": False, "blocker": "SCHEDULE_DATA_STALE",
                    "reason": "The schedule evidence is older than its approved freshness limit; the kickoff may have changed."}
        return {"state": "OPEN", "label": "Open", "kickoff_utc": kickoff, "kickoff_display": "Sun Sep 20 10:00 AM PDT", "no_game": False, "blocker": None,
                "reason": "Kickoff Sun Sep 20 10:00 AM PDT; the player can still be moved."}
    return {"players": {str(row["source_player_id"]): lock(str(row["source_player_id"])) for row in roster if row.get("source_player_id")}}


def slot(contract, label):
    return next(decision for decision in contract["slots"] if decision["slot"] == label)


def lineup(contract):
    return {decision["slot"]: (decision["recommended"] or {}).get("player") for decision in contract["slots"]}


def best_legal_total(slots, players):
    best = None

    def search(position, used, total):
        nonlocal best
        if position == len(slots):
            best = total if best is None else max(best, total)
            return
        for row in players:
            if row["player"] not in used and row["position"] in slots[position]["eligible_positions"]:
                search(position + 1, used | {row["player"]}, total + row["weekly_score"])

    search(0, frozenset(), 0.0)
    return best


def test_slots_follow_league_roster_positions_and_configured_flex_eligibility():
    positions = ["QB", "WR", "WRRB_FLEX", "REC_FLEX", "FLEX", "FLEX", "K", "BN"]
    contract = build_slot_contract(settings(positions), mode="LIVE")
    assert [(item["slot"], item["eligible_positions"]) for item in contract["slots"]] == [
        ("QB", ["QB"]), ("WR", ["WR"]), ("W/R FLEX", ["RB", "WR"]), ("W/T FLEX", ["WR", "TE"]),
        ("FLEX1", ["RB", "WR", "TE"]), ("FLEX2", ["RB", "WR", "TE"]), ("K", ["K"]),
    ]
    roster = [player("Q", "QB", 20), player("T1", "TE", 30), player("T2", "TE", 29), player("W1", "WR", 5),
              player("R1", "RB", 4), player("R2", "RB", 3), player("W2", "WR", 2), player("KK", "K", 1)]
    result = decide(roster, league_settings=settings(positions))
    assert [decision["slot"] for decision in result["slots"]] == [item["slot"] for item in contract["slots"]]
    assert all(decision["recommended"]["position"] in decision["eligible_positions"] for decision in result["slots"])
    assert slot(result, "W/R FLEX")["recommended"]["position"] in {"RB", "WR"}
    unsupported = decide(roster, league_settings=settings(["QB", "DL", "BN"]))
    assert unsupported["state"] == "BLOCKED" and unsupported["blocker"] == "LEAGUE_SLOT_TYPE_UNSUPPORTED" and unsupported["slots"] == []


def test_flex_is_allocated_jointly_even_when_the_league_lists_flex_first():
    result = decide([player("RB-A", "RB", 9.0), player("WR-A", "WR", 10.0)], league_settings=settings(["FLEX", "WR", "BN"]))
    assert lineup(result) == {"FLEX": "RB-A", "WR": "WR-A"}
    assert result["summary"]["value_total"]["value"] == 19.0
    assert not any(decision["status"] == "VACANT" for decision in result["slots"])


def test_out_player_never_enters_the_recommended_lineup_and_out_starter_is_replaced():
    roster = base_roster()
    roster[1].update(injury_status="Out", weekly_score=25.0, weekly_baseline=25.0)
    roster.append(player("IR-WR", "WR", 30.0, status="IR"))
    result = decide(roster)
    assert {"RB1", "IR-WR"}.isdisjoint(lineup(result).values())
    decision = slot(result, "RB1")
    assert decision["status"] == "REPLACEMENT_REQUIRED" and decision["recommended"]["player"] == "BENCH-RB"
    assert decision["drivers"][0] == "HEALTH_DRIVEN"
    assert decision["decision_confidence"]["state"] == "ESTABLISHED"
    assert result["changes"][0]["start"]["player"] == "BENCH-RB" and result["changes"][0]["sit"]["player"] == "RB1"


def test_questionable_starter_degrades_only_its_own_decision():
    roster = base_roster()
    roster[3].update(injury_status="Questionable", weekly_score=13.6, weekly_baseline=16.0, injury_multiplier=0.85)
    result = decide(roster)
    watched = slot(result, "WR1")
    assert watched["recommended"]["player"] == "WR1" and watched["decision"] == "MONITOR" and watched["status"] == "AVAILABILITY_WATCH"
    assert watched["decision_confidence"]["state"] == "DEGRADED"
    assert [decision["slot"] for decision in result["attention"]] == ["WR1"]
    others = [decision for decision in result["slots"] if decision["slot"] != "WR1"]
    assert all(decision["decision"] in {"START", "FLEX"} for decision in others)
    assert all(decision["decision_confidence"]["state"] != "DEGRADED" for decision in others)


@pytest.mark.parametrize("status,reported", [("Unknown", True), ("", True), ("Healthy", False), ("Day-to-day", True)])
def test_unknown_health_is_never_treated_as_healthy(status, reported):
    roster = base_roster()
    roster[0].update(injury_status=status, health_status_available=reported)
    decision = slot(decide(roster), "QB")
    assert decision["recommended"]["health"]["state"] == "UNKNOWN" and decision["recommended"]["health"]["verified"] is False
    assert decision["recommended"]["availability"] == "UNCERTAIN" and decision["decision"] == "MONITOR"


def test_unverified_team_health_monitors_starters_without_flagging_every_slot():
    stale = {"state": "STALE", "source": "Sleeper API", "freshness_state": "STALE", "last_verified": NOW}
    result = decide(base_roster(), team_health=stale)
    assert all(decision["decision"] == "MONITOR" for decision in result["slots"] if decision["recommended"]["position"] != "DEF")
    assert not any(decision["recommended"]["health"]["verified"] for decision in result["slots"] if decision["recommended"]["position"] != "DEF")
    assert result["attention"] == []
    assert [notice["code"] for notice in result["notices"]] == ["TEAM_HEALTH_UNVERIFIED"]


def test_current_lineup_is_kept_when_no_supported_alternative_is_better():
    result = decide(base_roster())
    assert result["changes"] == [] and result["moves"] == []
    assert lineup(result) == {"QB": "QB1", "RB1": "RB1", "RB2": "RB2", "WR1": "WR1", "WR2": "WR2", "TE": "TE1", "FLEX": "FLEX1", "K": "K1", "DEF": "DEF1"}
    assert result["summary"]["action"] == "Keep your current lineup"


def test_missing_values_keep_current_starters_instead_of_rank_tiebreaks():
    roster = without_values(base_roster())
    roster[9]["rank"] = 1
    roster[1]["rank"] = 500
    result = decide(roster)
    assert result["changes"] == []
    decision = slot(result, "RB1")
    assert decision["recommended"]["player"] == "RB1" and decision["status"] == "UNRESOLVED"
    assert decision["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert decision["best_alternative"] is None and "BENCH-RB" in decision["unranked_alternatives"]
    assert result["summary"]["status"] == "REVIEW"


def test_best_alternative_is_the_best_eligible_supported_bench_player():
    roster = base_roster() + [player("OUT-RB", "RB", 30.0, status="Out"), player("NO-VALUE-RB", "RB", None)]
    decision = slot(decide(roster), "RB1")
    assert decision["best_alternative"]["player"] == "BENCH-RB"
    assert decision["edge"]["value"]["delta"] == pytest.approx(4.0)
    assert decision["unranked_alternatives"] == ["NO-VALUE-RB"]
    assert "OUT-RB" not in [item["player"] for item in decision["alternatives"]]
    assert decision["decision_confidence"]["state"] == "DEGRADED"


def test_projection_delta_is_recommended_minus_best_alternative():
    roster = base_roster()
    roster[1].update(weekly_score=12.5, weekly_baseline=12.5)
    roster[9].update(weekly_score=9.75, weekly_baseline=9.75)
    projections = {"state": "AVAILABLE", "players": {"RB1": provider("RB1", 15.0), "BENCH-RB": provider("BENCH-RB", 11.5)}, "blockers": []}
    decision = slot(decide(roster, provider_projections=projections), "RB1")
    assert decision["edge"]["value"]["delta"] == pytest.approx(2.75) and decision["projection_delta"] == pytest.approx(2.75)
    assert decision["edge"]["provider_projection"]["delta"] == pytest.approx(3.5)
    assert decision["edge"]["provider_projection"]["recommendation_impact"] == "INFORMATIONAL_ONLY"


def test_missing_weekly_value_is_never_treated_as_zero():
    roster = base_roster()
    roster[1].update(weekly_score=None, weekly_baseline=None)
    roster[9].update(weekly_score=0.5, weekly_baseline=0.5)
    result = decide(roster)
    kept = slot(result, "RB1")["recommended"]
    assert kept["player"] == "RB1" and kept["value"] == {**kept["value"], "state": "UNAVAILABLE", "value": None}
    assert result["summary"]["value_total"]["state"] == "UNAVAILABLE" and result["summary"]["value_total"]["value"] is None
    verified_zero = decide([player("Z-QB", "QB", 0.0)], league_settings=settings(["QB", "BN"]))
    assert slot(verified_zero, "QB")["recommended"]["value"]["value"] == 0.0


def test_missing_matchup_rank_is_unavailable_not_bad_or_neutral():
    decision = slot(decide(base_roster()), "RB1")
    matchup = decision["recommended"]["matchup"]
    assert matchup["state"] == "UNAVAILABLE" and matchup["rank"] is None and matchup["signal"] is None
    assert "not treated as favorable, difficult, or neutral" in matchup["label"]
    assert "MATCHUP_SUPPORTED" not in decision["drivers"]
    assert not any("Matchup" in item for item in decision["advantages"] + decision["disadvantages"])


def test_preliminary_matchup_signal_never_becomes_an_authoritative_rank():
    roster = base_roster()
    roster[3].update(PRELIMINARY_MATCHUP_FIELDS, local_player_id=4)
    roster[3]["weekly_evidence"] = {"matchup": build_matchup_evidence(roster[3], season=2026, week=3, now=NOW)}
    result = decide(roster)
    matchup = slot(result, "WR1")["recommended"]["matchup"]
    assert matchup["state"] == "PRELIMINARY" and matchup["signal"] == "21st easiest defense"
    assert matchup["rank"] is None and matchup["rank_authoritative"] is False
    assert "not an authoritative rank" in matchup["label"]
    assert lineup(result) == lineup(decide(base_roster()))
def test_projection_and_decision_confidence_stay_separate_and_provider_never_selects():
    roster = base_roster()
    withheld = {"state": "AVAILABLE", "players": {"RB1": provider("RB1", 15.0, "UNAVAILABLE"), "BENCH-RB": provider("BENCH-RB", 30.0, "UNAVAILABLE")}, "blockers": []}
    plain, informed = decide(roster), decide(roster, provider_projections=withheld)
    before, after = slot(plain, "RB1"), slot(informed, "RB1")
    assert lineup(plain) == lineup(informed) and after["decision_confidence"] == before["decision_confidence"]
    assert before["decision_confidence"]["state"] == "PRELIMINARY"
    assert before["projection_confidence"]["recommended"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "freshness threshold is unverified" in after["projection_confidence"]["recommended"]["reason"]
    assert after["edge"]["provider_projection"]["delta"] is None
    assert "freshness threshold is unverified" in after["edge"]["provider_projection"]["reason"]


def test_confidence_states_are_categorical_and_never_fabricated_percentages():
    result = decide(without_values(base_roster()))
    for decision in result["slots"]:
        assert set(decision["decision_confidence"]) == {"state", "reason"}
        assert decision["decision_confidence"]["state"] in {"INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"}
        projection = decision["projection_confidence"]["recommended"]
        assert projection["state"] == "UNAVAILABLE" and "score" not in projection
    assert result["summary"]["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "%" not in str(result["summary"]["decision_confidence"])


def test_missing_league_settings_block_the_live_recommendation():
    result = decide(base_roster(), league_settings=league_settings_contract({}))
    assert result["state"] == "BLOCKED" and result["recommended_lineup"] == [] and result["slots"] == []
    assert result["summary"]["action"] == "Lineup recommendation blocked"
    assert result["scoring_context"]["state"] == "UNAVAILABLE" and result["scoring_context"]["scoring_format"] is None


def test_missing_or_different_scoring_never_substitutes_full_ppr():
    missing = settings(rec=None)
    assert missing["scoring_format"] is None and missing["scoring_settings_state"] == "UNAVAILABLE"
    result = decide(base_roster(), league_settings=missing)
    assert result["changes"] == [] and result["value_basis"]["blockers"] == ["LEAGUE_SCORING_UNVERIFIED"]
    assert all(decision["recommended"]["value"]["value"] is None for decision in result["slots"])
    half = settings(rec=0.5)
    assert half["scoring_format"] == "Half-PPR" and settings()["scoring_format"] == "Full-PPR"
    assert decide(base_roster(), league_settings=half)["value_basis"]["blockers"] == ["LEAGUE_SCORING_NOT_FULL_PPR"]


def test_explanation_identifies_the_evidence_actually_used():
    roster = base_roster()
    roster[9].update(weekly_score=12.5, weekly_baseline=12.5)
    change = slot(decide(roster, provider_projections={"state": "AVAILABLE", "players": {"BENCH-RB": provider("BENCH-RB", 9.0)}, "blockers": []}), "FLEX")
    used = {(item["domain"], item["used_for"]) for item in change["evidence_used"]}
    assert change["status"] == "CHANGE" and change["recommended"]["player"] == "BENCH-RB"
    assert {("WEEKLY_VALUE", "SELECTION"), ("HEALTH", "AVAILABILITY"), ("LEAGUE_SLOTS", "ELIGIBILITY"), ("PROVIDER_PROJECTION", "CONTEXT_ONLY")} <= used
    assert "12.50" in change["why"] and "FLEX1" in change["why"] and change["drivers"] == ["PROJECTION_DRIVEN"]
    kept = slot(decide(without_values(base_roster())), "RB1")
    assert ("WEEKLY_VALUE", "SELECTION") not in {(item["domain"], item["used_for"]) for item in kept["evidence_used"]}
    assert "no supported evidence favors a change" in kept["why"] and kept["drivers"] == ["REDUCED_SCOPE"]


def test_what_could_change_lists_only_decision_relevant_triggers():
    roster = base_roster()
    roster[9].update(injury_status="Questionable", weekly_score=8.5, weekly_baseline=10.0, injury_multiplier=0.85, sleeper_news_updated=1763200000000)
    irrelevant = decide(roster)
    assert not any(trigger["player"] == "BENCH-RB" for decision in irrelevant["slots"] for trigger in decision["what_could_change"])
    assert not any("NEWS" in trigger["code"] for decision in irrelevant["slots"] for trigger in decision["what_could_change"])
    roster[9].update(weekly_score=9.9, weekly_baseline=11.65)
    relevant = decide(roster)
    flagged = {decision["slot"] for decision in relevant["slots"] for trigger in decision["what_could_change"] if trigger["code"] == "OFFICIAL_GAME_STATUS" and trigger["player"] == "BENCH-RB"}
    assert flagged == {"RB2", "FLEX"}
    unresolved = without_values(base_roster())
    unresolved[10]["injury_status"] = "Questionable"
    result = decide(unresolved)
    assert all(not decision["what_could_change"] for decision in result["slots"])
    assert [trigger["code"] for trigger in result["what_could_change"]] == ["WEEKLY_VALUE_AVAILABILITY"]


@pytest.mark.parametrize("positions", [STANDARD_SLOTS, ["FLEX", "RB", "WR", "TE", "BN"], ["QB", "SUPER_FLEX", "RB", "WR", "WRRB_FLEX", "BN"]])
def test_whole_lineup_optimum_matches_exhaustive_legal_assignments(positions):
    roster = [
        player("QB-A", "QB", 20.0), player("QB-B", "QB", 18.0), player("RB-A", "RB", 15.0), player("RB-B", "RB", 9.0),
        player("RB-Q", "RB", 8.5, status="Questionable", baseline=10.0, multiplier=0.85), player("WR-A", "WR", 14.0), player("WR-B", "WR", 13.0),
        player("WR-C", "WR", 12.0), player("TE-A", "TE", 9.0), player("TE-B", "TE", 6.0), player("K-A", "K", 5.0), player("D-A", "DEF", 4.0, status=""),
        player("RB-OUT", "RB", 30.0, status="Out"),
    ]
    result = decide(roster, league_settings=settings(positions))
    slots = build_slot_contract(settings(positions), mode="LIVE")["slots"]
    chosen = [decision["recommended"] for decision in result["slots"]]
    assert all(view is not None and view["position"] in decision["eligible_positions"] for view, decision in zip(chosen, result["slots"]))
    assert len({view["player"] for view in chosen}) == len(chosen) and "RB-OUT" not in {view["player"] for view in chosen}
    eligible = [row for row in roster if row["injury_status"] != "Out"]
    assert result["summary"]["value_total"]["value"] == pytest.approx(best_legal_total(slots, eligible))


def test_lineup_differences_are_deterministic():
    roster = base_roster()
    roster[1].update(injury_status="Out")
    roster[9].update(weekly_score=12.5, weekly_baseline=12.5)
    roster[10].update(weekly_score=10.5, weekly_baseline=10.5)

    def summary(contract):
        return [(change["slot"], change["verb"], (change["start"] or {}).get("player"), (change["sit"] or {}).get("player")) for change in contract["changes"]], contract["moves"], lineup(contract)

    first = summary(decide(roster))
    assert first == summary(decide(list(reversed(roster)))) == summary(decide(roster))
    assert first[0] == [("RB1", "START", "BENCH-RB", "RB1"), ("FLEX", "FLEX", "BENCH-WR", "FLEX1")]


def test_out_starter_is_covered_by_moving_a_flex_starter_instead_of_leaving_a_vacancy():
    roster = without_values([
        player("QB-A", "QB", slot="QB", index=0), player("RB-OUT", "RB", slot="RB", index=1, status="Out"),
        player("Charlie", "RB", slot="FLEX", index=2), player("Delta", "WR"),
    ])
    result = decide(roster, league_settings=settings(["QB", "RB", "FLEX", "BN", "BN"]))
    assert lineup(result) == {"QB": "QB-A", "RB": "Charlie", "FLEX": "Delta"}
    assert result["summary"]["status"] != "BLOCKED" and not {"VACANT", "BLOCKED"} & {decision["status"] for decision in result["slots"]}
    assert slot(result, "FLEX")["basis"] == "ONLY_ELIGIBLE_OPTION"
    assert "Charlie moves from FLEX to RB" in slot(result, "RB")["why"] and "Charlie moves to RB" in slot(result, "FLEX")["why"]
    assert [(move["player"], move["from"], move["to"]) for move in result["moves"]] == [("Charlie", "FLEX", "RB")]

    valued = [player("WR-OUT", "WR", 12.0, slot="WR", index=0, status="Out"), player("WR-A", "WR", 10.0, slot="FLEX", index=1), player("RB-B", "RB")]
    result = decide(valued, league_settings=settings(["WR", "FLEX", "BN"]))
    assert lineup(result) == {"WR": "WR-A", "FLEX": "RB-B"}
    assert slot(result, "FLEX")["basis"] == "ONLY_ELIGIBLE_OPTION" and result["summary"]["status"] != "BLOCKED"


def test_forced_fills_are_exact_and_open_slots_list_one_move_options():
    forced = without_values([
        player("RB-OUT", "RB", slot="RB", index=0, status="Out"), player("TE-OUT", "TE", slot="TE", index=1, status="Out"),
        player("A-RB", "RB"), player("B-TE", "TE"), player("C-RB", "RB"),
    ])
    result = decide(forced, league_settings=settings(["RB", "TE", "BN", "BN", "BN"]))
    assert lineup(result) == {"RB": None, "TE": "B-TE"}
    assert slot(result, "TE")["basis"] == "ONLY_ELIGIBLE_OPTION"
    assert [candidate["player"] for candidate in slot(result, "RB")["candidates"]] == ["A-RB", "C-RB"]

    shuffle = without_values([
        player("RB-OUT", "RB", slot="RB", index=0, status="Out"), player("W", "WR", slot="WR", index=1), player("F", "RB", slot="FLEX", index=2),
        player("X", "RB"), player("Y", "WR"),
    ])
    result = decide(shuffle, league_settings=settings(["RB", "WR", "FLEX", "BN", "BN"]))
    assert lineup(result) == {"RB": None, "WR": "W", "FLEX": "F"}
    assert [(candidate["player"], candidate["via"]) for candidate in slot(result, "RB")["candidates"]] == [("X", None), ("Y", "if F moves from FLEX to RB")]
    assert "Eligible options (X, Y (if F moves from FLEX to RB)) cannot be ranked" in slot(result, "RB")["why"]


def test_uncertain_starter_without_alternatives_is_degraded_not_established():
    result = decide([player("QB-Q", "QB", 20.0, slot="QB", index=0, status="Questionable", multiplier=0.85)], league_settings=settings(["QB", "BN"]))
    assert slot(result, "QB")["decision_confidence"]["state"] == "DEGRADED"
    assert result["summary"]["decision_confidence"]["state"] == "DEGRADED"


def test_changes_pair_each_start_with_its_own_slot_before_cross_slot_pairing():
    roster = [player("F", "WR", 4.0, slot="FLEX", index=1), player("Q2", "QB", 18.0), player("X", "RB", 10.0)]
    result = decide(roster, league_settings=settings(["QB", "FLEX", "BN", "BN"]))
    changes = [(change["slot"], (change["start"] or {}).get("player"), (change["sit"] or {}).get("player")) for change in result["changes"]]
    assert changes == [("QB", "Q2", None), ("FLEX", "X", "F")]


RANK_SLOTS = ["QB", "RB", "RB", "WR", "FLEX", "BN", "BN"]
RANKS = {"QB1": ("QB", 5.0), "RB-A": ("RB", 30.0), "RB-B": ("RB", 12.0), "FLEX-RB": ("RB", 20.0), "RB-C": ("RB", 8.0), "WR-A": ("WR", 10.0), "WR-B": ("WR", 40.0)}


def consensus(table, *, week=3, season=2026, source_date="2026-09-16", scoring="PPR", max_age=172800, diagnostics=(), **row_extra):
    """The evaluated weekly payload shape produced by services.dynastyprocess_rankings."""
    rows = {player_id: {"player_id": player_id, "position": position, "ecr": ecr, "source_date": source_date, "horizon": "this_week", "scoring": scoring,
                        "season": season, "week": week, "identity_method": "PUBLISHED_PROVIDER_CROSSWALK", "game_evidence": None, **row_extra}
            for player_id, (position, ecr) in table.items()}
    return {"source": "FantasyPros consensus via DynastyProcess", "last_successful_refresh": NOW, "refresh_error": None, "version": "a" * 40,
            "horizons": {"this_week": {"state": "AVAILABLE" if rows else "UNAVAILABLE", "ranks": rows, "diagnostics": list(diagnostics), "max_age_seconds": max_age}}}


def rank_roster(**extra_rows):
    rows = [
        player("QB1", "QB", slot="QB", index=0), player("RB-A", "RB", slot="RB", index=1), player("RB-B", "RB", slot="RB", index=2),
        player("WR-A", "WR", slot="WR", index=3), player("FLEX-RB", "RB", slot="FLEX", index=4), player("RB-C", "RB"), player("WR-B", "WR"),
    ]
    return without_values(rows + list(extra_rows.values()))


def rank_decide(roster, table=RANKS, **kwargs):
    kwargs.setdefault("league_settings", settings(RANK_SLOTS))
    kwargs.setdefault("consensus_authority", True)
    ranks = kwargs.pop("ranks", None) or consensus(table)
    return decide(roster, consensus_ranks=ranks, now=NOW_TIME, **kwargs)


def changes_of(contract):
    return [(change["slot"], (change["start"] or {}).get("player"), (change["sit"] or {}).get("player")) for change in contract["changes"]]


def test_consensus_rank_orders_same_position_starters_across_the_whole_lineup_but_never_across_positions():
    result = rank_decide(rank_roster())
    assert lineup(result) == {"QB": "QB1", "RB1": "RB-C", "RB2": "RB-B", "WR": "WR-A", "FLEX": "FLEX-RB"}
    assert changes_of(result) == [("RB1", "RB-C", "RB-A")]
    change = slot(result, "RB1")
    assert change["basis"] == "SUPPORTED_RANK" and change["primary_driver"] == "CONSENSUS_RANK_DRIVEN"
    assert change["edge"]["consensus_rank"]["delta"] == 22.0 and change["decision_confidence"]["state"] == "PRELIMINARY"
    assert "This week's RB consensus ranks RB-C 8, ahead of RB-A (30)" in change["why"]
    flex = slot(result, "FLEX")
    assert flex["status"] == "STABLE" and flex["counterpart"]["player"] == "RB-A"
    assert flex["rank_uncompared"] == [{"player": "WR-B", "reason": "different position"}]
    assert flex["decision_confidence"]["state"] == "DEGRADED"
    assert result["summary"]["action"] == "START RB-C over RB-A" and result["summary"]["decision_confidence"]["state"] == "DEGRADED"
    assert result["consensus_basis"]["state"] == "AVAILABLE" and result["consensus_basis"]["evidence_level"] == "PRELIMINARY"
    assert "never ESTABLISHED" in result["consensus_basis"]["authority"]
    assert all(decision["decision_confidence"]["state"] != "ESTABLISHED" for decision in result["slots"] if decision["basis"] == "SUPPORTED_RANK")
    cross = rank_decide(without_values([player("WR-F", "WR", slot="FLEX", index=0), player("RB-Z", "RB")]), {"WR-F": ("WR", 60.0), "RB-Z": ("RB", 1.0)},
                        league_settings=settings(["FLEX", "BN"]))
    assert lineup(cross) == {"FLEX": "WR-F"} and slot(cross, "FLEX")["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"


def test_consensus_rank_is_never_converted_into_points_or_a_weekly_value():
    result = rank_decide(rank_roster(), ranks=consensus(RANKS, r2p_pts=99.0))
    change = slot(result, "RB1")
    assert change["edge"]["value"]["state"] == "UNAVAILABLE" and change["projection_delta"] is None
    assert change["edge"]["consensus_rank"]["unit"] == CONSENSUS_UNIT
    assert result["summary"]["value_total"] == {"state": "UNAVAILABLE", "value": None, "available": 0, "required": 5}
    assert all(view["value"]["value"] is None for view in result["players"])
    assert "not projected points" in change["why"] and "99" not in change["why"]


@pytest.mark.parametrize("ranks,league,blocker", [
    (consensus(RANKS, week=2), None, "CONSENSUS_RANK_WEEK_MISMATCH"),
    (consensus(RANKS, scoring="STD"), None, "CONSENSUS_RANK_SCORING_MISMATCH"),
    (consensus(RANKS), settings(RANK_SLOTS, rec=0.5), "CONSENSUS_RANK_SCORING_MISMATCH"),
    (consensus(RANKS), settings(RANK_SLOTS, rec=None), "CONSENSUS_RANK_SCORING_UNVERIFIED"),
    (consensus(RANKS, source_date="2026-09-13"), None, "CONSENSUS_RANK_STALE"),
    (consensus(RANKS, source_date="2026-09-18"), None, "CONSENSUS_RANK_STALE"),
    (consensus(RANKS, source_date=None), None, "CONSENSUS_RANK_TIMESTAMP_UNAVAILABLE"),
    (consensus(RANKS, max_age=None), None, "CONSENSUS_RANK_FRESHNESS_UNVERIFIED"),
])
def test_wrong_week_scoring_stale_or_undated_consensus_never_influences_the_lineup(ranks, league, blocker):
    result = rank_decide(rank_roster(), ranks=ranks, **({"league_settings": league} if league else {}))
    assert result["changes"] == [] and lineup(result)["RB1"] == "RB-A"
    assert {view["consensus_rank"]["blocker"] for view in result["players"]} == {blocker}
    assert all(view["consensus_rank"]["ecr"] is None for view in result["players"])
    assert result["consensus_basis"]["state"] in {"UNAVAILABLE", "BLOCKED"}
    assert any(notice["code"].startswith("CONSENSUS_RANK_") for notice in result["notices"])


def test_missing_rank_or_projection_is_unranked_never_zero_or_worse():
    table = {key: value for key, value in RANKS.items() if key != "RB-C"}
    result = rank_decide(rank_roster(), table, provider_projections=provider_payload({"RB-A": 12.0}))
    rb_c = next(view for view in result["players"] if view["player"] == "RB-C")
    assert rb_c["consensus_rank"]["ecr"] is None and rb_c["consensus_rank"]["reason"] == "not in this week's published consensus"
    assert rb_c["value"]["value"] is None and rb_c["provider_projection"]["projected_ppg"] is None
    assert result["changes"] == [] and slot(result, "RB1")["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "RB-C (not in this week's published consensus)" in slot(result, "RB1")["edge"]["consensus_rank"]["reason"]
    assert next(row for row in result["bench"] if row["player"] == "RB-C")["consensus_rank"] is None


def provider_payload(values):
    return {"state": "AVAILABLE", "players": {player_id: provider(player_id, ppg, "UNAVAILABLE") for player_id, ppg in values.items()}, "blockers": []}


def test_provider_projection_never_selects_or_changes_confidence_and_disagreement_is_disclosed():
    table = {**RANKS, "RB-C": ("RB", 35.0)}
    plain = rank_decide(rank_roster(), table)
    disputed = rank_decide(rank_roster(), table, provider_projections=provider_payload({"RB-A": 5.0, "RB-C": 30.0}))
    assert lineup(disputed) == lineup(plain) and disputed["changes"] == plain["changes"] == []
    assert [d["decision_confidence"] for d in disputed["slots"]] == [d["decision_confidence"] for d in plain["slots"]]
    agreement = slot(disputed, "RB1")["evidence_agreement"]
    assert agreement["state"] == "DISAGREES" and agreement["recommendation_impact"] == "INFORMATIONAL_ONLY"
    assert "Sources disagree: this week's consensus rank favors RB-A, but the JerryGM provider projection favors RB-C" in agreement["label"]
    no_rank = decide(rank_roster(), league_settings=settings(RANK_SLOTS), provider_projections=provider_payload({"RB-A": 5.0, "RB-C": 30.0}))
    assert no_rank["changes"] == []


SHADOW_SCORING = {"rec": 1.0, "rec_yd": 0.1, "rush_yd": 0.1}


def shadow_payload(roster):
    """League-scorable provider lines that project every bench player (25.0) far above every starter (1.5)."""
    lines = {row["source_player_id"]: {"receptions": 1.0, "recYds": 5.0, "rushYds": 0.0} if row.get("sleeper_lineup_slot")
             else {"receptions": 10.0, "recYds": 150.0, "rushYds": 0.0} for row in roster}
    return {"state": "AVAILABLE", "blockers": [], "players": {player_id: provider(player_id, 20.0, "UNAVAILABLE", stat_line=line, data_through_week=2)
                                                              for player_id, line in lines.items()}}


def without_shadow(value):
    if isinstance(value, dict):
        return {key: without_shadow(item) for key, item in value.items() if key not in {"weekly_score_v2", "weekly_score_v2_basis", "forward_validation"}}
    if isinstance(value, list):
        return [without_shadow(item) for item in value]
    return value


@pytest.mark.parametrize("scenario", ["weekly-values", "live-without-values", "consensus-authority", "locked-and-unverified"])
def test_weekly_score_v2_shadow_evidence_never_changes_selection_or_confidence(monkeypatch, scenario):
    import services.lineup_decision_intelligence as intelligence

    real = intelligence.build_weekly_score_v2

    def inverted(projection, **kwargs):
        score = real(projection, **kwargs)
        return {**score, "state": "PRELIMINARY", "value": 100.0 - (score["value"] or 0.0), "value_range": None}

    def run(builder):
        monkeypatch.setattr(intelligence, "build_weekly_score_v2", builder)
        if scenario == "consensus-authority":
            return rank_decide(rank_roster(), provider_projections=shadow_payload(rank_roster()), scoring_settings=SHADOW_SCORING)
        roster = without_values(base_roster()) if scenario == "live-without-values" else base_roster()
        extra = {"game_locks": locks(roster, locked=("QB1",), unverified=("RB2",))} if scenario == "locked-and-unverified" else {}
        return decide(roster, provider_projections=shadow_payload(roster), scoring_settings=SHADOW_SCORING, now=NOW_TIME, **extra)

    results = {name: run(builder) for name, builder in (("real", real), ("inverted", inverted), ("absent", lambda projection, **kwargs: real(None)))}
    shadow = {(view["is_current_starter"], view["weekly_score_v2"]["value"]) for view in results["real"]["players"] if view["position"] in {"RB", "WR"}}
    assert shadow == {(True, 1.5), (False, 25.0)}
    if scenario == "live-without-values":
        assert results["real"]["changes"] == []
    compared = {name: json.dumps(without_shadow(result), sort_keys=True, default=str) for name, result in results.items()}
    assert compared["real"] == compared["inverted"] == compared["absent"]
    for result in results.values():
        assert [slot["decision_confidence"] for slot in result["slots"]] == [slot["decision_confidence"] for slot in results["real"]["slots"]]
        assert result["summary"]["decision_confidence"] == results["real"]["summary"]["decision_confidence"]
        assert [(snapshot["decision_subject"], snapshot["decision_output"]["decision"], snapshot["decision_output"]["decision_confidence"])
                for snapshot in result["forward_validation"]["snapshots"]] == [
            (snapshot["decision_subject"], snapshot["decision_output"]["decision"], snapshot["decision_output"]["decision_confidence"])
            for snapshot in results["real"]["forward_validation"]["snapshots"]]


def test_same_consensus_evidence_produces_the_same_lineup_in_any_roster_order():
    def snapshot(contract):
        return lineup(contract), changes_of(contract), [(d["slot"], d["status"], d["decision_confidence"]["state"]) for d in contract["slots"]]

    assert snapshot(rank_decide(rank_roster())) == snapshot(rank_decide(list(reversed(rank_roster())))) == snapshot(rank_decide(rank_roster()))


def test_out_player_cannot_start_regardless_of_rank_or_projection():
    roster = rank_roster(out=player("RB-OUT", "RB", status="Out"))
    result = rank_decide(roster, {**RANKS, "RB-OUT": ("RB", 1.0)}, provider_projections=provider_payload({"RB-OUT": 40.0}))
    assert "RB-OUT" not in lineup(result).values()
    assert next(view for view in result["players"] if view["player"] == "RB-OUT")["availability"] == "UNAVAILABLE"


def test_consensus_fills_an_open_slot_only_when_every_option_is_ranked_at_one_position():
    roster = without_values([player("QB1", "QB", slot="QB", index=0), player("RB-OUT", "RB", slot="RB", index=1, status="Out"),
                             player("WR-A", "WR", slot="WR", index=2), player("RB-X", "RB"), player("RB-Y", "RB")])
    table = {"RB-X": ("RB", 10.0), "RB-Y": ("RB", 25.0)}
    result = rank_decide(roster, table, league_settings=settings(["QB", "RB", "WR", "BN", "BN", "BN"]))
    replacement = slot(result, "RB")
    assert replacement["recommended"]["player"] == "RB-X" and replacement["status"] == "REPLACEMENT_REQUIRED"
    assert replacement["drivers"] == ["HEALTH_DRIVEN", "CONSENSUS_RANK_DRIVEN"] and replacement["decision_confidence"]["state"] == "PRELIMINARY"
    assert changes_of(result) == [("RB", "RB-X", "RB-OUT")]
    tied = rank_decide(roster, {"RB-X": ("RB", 10.0), "RB-Y": ("RB", 10.0)}, league_settings=settings(["QB", "RB", "WR", "BN", "BN", "BN"]))
    assert slot(tied, "RB")["recommended"] is None and slot(tied, "RB")["status"] == "REPLACEMENT_REQUIRED"
    unranked = rank_decide(roster + without_values([player("RB-Z", "RB")]), table, league_settings=settings(["QB", "RB", "WR", "BN", "BN", "BN", "BN"]))
    assert slot(unranked, "RB")["recommended"] is None
    assert [candidate["player"] for candidate in slot(unranked, "RB")["candidates"]] == ["RB-X", "RB-Y", "RB-Z"]


def test_ties_keep_the_current_starter_with_insufficient_evidence():
    result = rank_decide(rank_roster(), {**RANKS, "RB-C": ("RB", 30.0)})
    assert result["changes"] == [] and lineup(result)["RB1"] == "RB-A"
    assert slot(result, "RB1")["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "tied" in slot(result, "RB1")["decision_confidence"]["reason"]


def started(*player_ids):
    return [{"reason": "Game already started", "classification": "CONFIRMED_STARTED_GAME", "crosswalk_matches": [{"sleeper_id": player_id}]} for player_id in player_ids]


def test_starters_whose_games_started_are_pinned_and_never_moved_or_replaced():
    roster = without_values([player("X", "RB", slot="RB", index=0, status="Out"), player("W1", "WR", slot="WR", index=1),
                             player("A", "RB", slot="FLEX", index=2), player("B", "RB"), player("W2", "WR")])
    table = {"B": ("RB", 10.0), "W1": ("WR", 5.0), "W2": ("WR", 30.0)}
    result = rank_decide(roster, ranks=consensus(table), league_settings=settings(["RB", "WR", "FLEX", "BN", "BN"]), game_locks=locks(roster, locked=("X", "A")))
    assert lineup(result) == {"RB": "X", "WR": "W1", "FLEX": "A"} and result["changes"] == [] and result["moves"] == []
    assert [slot(result, label)["status"] for label in ("RB", "FLEX")] == ["LOCKED", "LOCKED"] and result["summary"]["locked_count"] == 2
    assert slot(result, "RB")["decision"] == "MONITOR" and "listed Out" in slot(result, "RB")["why"]
    assert slot(result, "RB")["decision_confidence"]["state"] == "NOT_APPLICABLE"
    valued_roster = [player("A", "RB", 5.0, slot="RB", index=0), player("B", "RB", 10.0)]
    valued = decide(valued_roster, league_settings=settings(["RB", "BN"]), game_locks=locks(valued_roster, locked=("A",)), now=NOW_TIME)
    assert lineup(valued) == {"RB": "A"} and valued["changes"] == [] and slot(valued, "RB")["status"] == "LOCKED"


def test_consensus_started_game_evidence_never_locks_a_player():
    roster = without_values([player("A", "RB", slot="RB", index=0), player("B", "RB")])
    result = rank_decide(roster, ranks=consensus({"B": ("RB", 10.0)}, diagnostics=started("A", "B")), league_settings=settings(["RB", "BN"]))
    assert {view["player"]: (view["lock"]["state"], view["availability"]) for view in result["players"]} == {"A": ("OPEN", "AVAILABLE"), "B": ("OPEN", "AVAILABLE")}
    assert slot(result, "RB")["status"] != "LOCKED" and result["summary"]["locked_count"] == 0
    assert (result["lock_summary"]["locked_count"], result["lock_summary"]["open_count"], result["lock_summary"]["week_state"]) == (0, 2, "PRE_KICKOFF")


def test_open_slot_options_are_rebuilt_after_rank_swaps():
    roster = without_values([player("X", "RB", slot="RB", index=0, status="Out"), player("A", "RB", slot="RB", index=1), player("B", "RB"), player("D", "RB")])
    result = rank_decide(roster, {"A": ("RB", 20.0), "B": ("RB", 10.0)}, league_settings=settings(["RB", "RB", "BN", "BN", "BN"]))
    assert changes_of(result) == [("RB1", None, "X"), ("RB2", "B", "A")]
    assert [candidate["player"] for candidate in slot(result, "RB1")["candidates"]] == ["A", "D"]
    assert "Eligible options (A, D)" in slot(result, "RB1")["why"]
    hop = without_values([player("X", "RB", slot="RB", index=0, status="Out"), player("A", "RB", slot="FLEX", index=1), player("B", "RB"), player("W", "WR")])
    moved = rank_decide(hop, {"A": ("RB", 20.0), "B": ("RB", 10.0)}, league_settings=settings(["RB", "FLEX", "BN", "BN", "BN"]))
    assert lineup(moved)["FLEX"] == "B"
    assert [(candidate["player"], candidate["via"]) for candidate in slot(moved, "RB")["candidates"]] == [("A", None), ("W", "if B moves from FLEX to RB")]


def test_rank_tier_never_compares_players_who_have_a_weekly_value():
    result = rank_decide([player("A", "RB", slot="RB", index=0), player("B", "RB", 10.0)], {"A": ("RB", 20.0), "B": ("RB", 5.0)}, league_settings=settings(["RB", "BN"]))
    assert result["changes"] == [] and slot(result, "RB")["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert slot(result, "RB")["rank_uncompared"] == [{"player": "B", "reason": "has a weekly value; ranks and values are not mixed"}]
    roster = without_values([player("R0", "RB", slot="RB", index=0), player("A", "RB", slot="FLEX", index=1), player("B", "RB")]) + [player("W", "WR", 8.0)]
    flex = slot(rank_decide(roster, {"R0": ("RB", 2.0), "A": ("RB", 5.0), "B": ("RB", 10.0), "W": ("WR", 3.0)}, league_settings=settings(["RB", "FLEX", "BN", "BN"])), "FLEX")
    assert flex["status"] == "STABLE" and flex["best_alternative"]["player"] == "B"
    assert {"player": "W", "reason": "different position"} in flex["rank_uncompared"]


def test_tied_bench_players_leave_the_slot_for_the_manager_instead_of_an_id_tiebreak():
    roster = without_values([player("A", "RB", slot="RB", index=0), player("B", "RB"), player("C", "RB")])
    result = rank_decide(roster, {"A": ("RB", 20.0), "B": ("RB", 10.0), "C": ("RB", 10.0)}, league_settings=settings(["RB", "BN", "BN", "BN"]))
    decision = slot(result, "RB")
    assert decision["recommended"] is None and decision["status"] == "SELECTION_UNRESOLVED"
    assert [candidate["player"] for candidate in decision["candidates"]] == ["B", "C"] and changes_of(result) == [("RB", None, "A")]
    assert "ranks B, C equally (RB 10) as the best options for RB, ahead of A (RB 20)" in decision["why"]
    assert "equally" in decision["decision_confidence"]["reason"]
    assert changes_of(rank_decide(list(reversed(roster)), {"A": ("RB", 20.0), "B": ("RB", 10.0), "C": ("RB", 10.0)}, league_settings=settings(["RB", "BN", "BN", "BN"]))) == changes_of(result)


def test_ranking_owner_payload_joins_by_exact_sleeper_id_current_week_and_kickoff_locks():
    now = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
    state = {"season": "2026", "week": 4, "season_type": "regular", "season_start_date": "2026-09-10"}
    later, earlier = (str((now + delta).timestamp()) for delta in (timedelta(days=1), timedelta(hours=-2)))
    identities = [{"fantasypros_id": f"fp-{key}", "sleeper_id": f"s-{key}", "position": position} for key, position in (("q", "QB"), ("1", "RB"), ("2", "RB"), ("3", "RB"))]
    weekly = [{"page": page, "fantasypros_id": f"fp-{key}", "ecr": ecr, "scrape_date": "2026-10-03", "player_game_kickoff_ts": kickoff}
              for key, page, ecr, kickoff in (("q", "qb", "4", earlier), ("1", "ppr-rb", "30", later), ("2", "ppr-rb", "10", later), ("3", "ppr-rb", "5", earlier))]
    snapshot = {"artifacts": {"db_playerids.csv": {"rows": identities}, "fp_latest_weekly.csv": {"rows": weekly}, "db_fpecr_latest.csv": {"rows": []}},
                "last_successful_refresh": now.isoformat(), "source": "FantasyPros consensus via DynastyProcess"}
    ranks = {**evaluate_rankings(snapshot, state, now), "last_successful_refresh": now.isoformat()}
    roster = without_values([
        player("Starter QB", "QB", slot="QB", index=0, source_player_id="s-q"), player("Starter RB", "RB", slot="RB", index=1, source_player_id="s-1"),
        player("Bench RB", "RB", source_player_id="s-2"), player("Started RB", "RB", source_player_id="s-3"), player("Unmapped RB", "RB", source_player_id="s-9"),
    ])
    # Kickoff locks come from the schedule; the consensus feed's own kickoff only withholds its rank.
    schedule_locks = locks(roster, locked=("s-q", "s-3"))
    result = build_lineup_decision(roster, league_settings=settings(["QB", "RB", "BN", "BN", "BN"]), team_health=FRESH_HEALTH, season=2026, week=4, consensus_ranks=ranks, now=now,
                                   game_locks=schedule_locks, consensus_authority=True)
    assert changes_of(result) == [("RB", "Bench RB", "Starter RB")]
    views = {view["player"]: view for view in result["players"]}
    assert views["Bench RB"]["consensus_rank"].items() >= {"ecr": 10.0, "source_date": "2026-10-03", "identity_method": "PUBLISHED_PROVIDER_CROSSWALK", "retrieved_at": now.isoformat()}.items()
    assert views["Started RB"]["availability_reason"] == "GAME_LOCKED" and views["Started RB"]["consensus_rank"]["blocker"] == "CONSENSUS_RANK_GAME_STARTED"
    assert views["Unmapped RB"]["consensus_rank"]["blocker"] == "CONSENSUS_RANK_NOT_PUBLISHED"
    assert slot(result, "QB")["status"] == "LOCKED" and slot(result, "QB")["decision_confidence"]["state"] == "NOT_APPLICABLE"
    assert [entry["player"] for entry in result["lock_summary"]["locked_players"]] == ["Started RB", "Starter QB"]
    wrong_week = build_lineup_decision(roster, league_settings=settings(["QB", "RB", "BN", "BN", "BN"]), team_health=FRESH_HEALTH, season=2026, week=5, consensus_ranks=ranks, now=now,
                                       game_locks=schedule_locks, consensus_authority=True)
    assert wrong_week["changes"] == []


class RouteCursor:
    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class RouteConnection:
    def cursor(self):
        return RouteCursor()

    def close(self):
        pass


def fresh_schedule(teams=("KC",), opponent="BUF", *, kickoff_in=timedelta(days=2)):
    """Automated nflverse schedule rows recorded an hour ago with a future kickoff."""
    now = datetime.now(timezone.utc)
    return [{"home_team": team, "away_team": opponent, "game_time_utc": now + kickoff_in, "game_time_pacific": None,
             "source": "automated:nflverse-schedules:games.csv.gz:sha256:fixture", "source_recorded_at": now - timedelta(hours=1),
             "retrieved_at": now - timedelta(hours=1)} for team in teams]


def render_team_route(monkeypatch, *, weekly, statuses=None, league=None, provider_fetcher=None, starters=("1", "2", "3"), consensus=None, schedule=None, schedule_max_age="604800",
                      teams=None):
    from flask import Flask
    import owner_operations

    statuses = statuses or {}
    names = {"1": ("Alpha QB", "QB"), "2": ("Bravo RB", "RB"), "3": ("Charlie WR", "WR"), "4": ("Delta RB", "RB")}
    catalog = {pid: {"full_name": name, "position": position, "team": (teams or {}).get(pid, "KC"), "status": statuses.get(name, "Active")}
               for pid, (name, position) in names.items()}
    league = league if league is not None else {"name": "Controlled", "roster_positions": ["QB", "RB", "FLEX", "BN"], "scoring_settings": {"rec": 1.0}}
    schedule = fresh_schedule() if schedule is None else schedule
    captured = {}
    real_render = owner_operations.render_template

    def capture(name, **kwargs):
        captured.update(kwargs)
        return real_render(name, **kwargs)

    def enrich(cur, roster, week, **kwargs):
        return [{**row, "opponent": "BUF", "is_bye": False, "weekly_score": weekly.get(row["player"]), "weekly_baseline": weekly.get(row["player"]), "matchup_modifier": 0.0, "injury_multiplier": 1.0} for row in roster]

    monkeypatch.setattr(owner_operations, "render_template", capture)
    monkeypatch.setattr(owner_operations, "enrich_players", enrich)
    monkeypatch.setattr(owner_operations, "build_team_opportunity_changes", lambda *args, **kwargs: {"state": "UNAVAILABLE", "players": [], "blockers": [], "decision_effect": "INFORMATIONAL_ONLY"})
    monkeypatch.setattr(owner_operations, "read_week_schedule_rows", lambda cur, season, week: schedule)
    # Fixture-only schedule freshness approval so kickoff locks can be verified in route tests.
    if schedule_max_age is None:
        monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    else:
        monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", schedule_max_age)
    blueprint = owner_operations.create_owner_operations_blueprint(
        lambda: RouteConnection(),
        lambda league_id: league,
        lambda league_id: [{"user_id": "owner", "is_owner": True}],
        lambda league_id: [{"owner_id": "owner", "roster_id": 1, "players": ["1", "2", "3", "4"], "starters": list(starters)}],
        lambda: catalog,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder="templates")
    app.config.update(TESTING=True, SLEEPER_LEAGUE_ID="controlled")
    app.config["WEEK_AUTHORITY_ACQUIRER"] = lambda season: build_sleeper_week_contract({"season": str(season), "week": 3}, season=season)
    if provider_fetcher is not None:
        app.config["LINEUP_PROVIDER_PROJECTIONS"] = provider_fetcher
    if consensus is not None:
        app.config["LINEUP_CONSENSUS_RANKINGS"] = consensus
    app.register_blueprint(blueprint)
    app.jinja_env.globals["url_for"] = lambda *args, **kwargs: "/"
    app.jinja_env.globals["ux_roster_lineage"] = lambda roster: []
    app.jinja_env.globals["ux_route_evidence"] = lambda *args: {"fields": {}}
    response = app.test_client().get("/team")
    return response, captured, response.get_data(as_text=True)


def test_team_route_payload_exposes_the_decision_contract(monkeypatch):
    calls = []

    def fetcher(players, *, season, week, scoring):
        calls.append(([row["source_player_id"] for row in players], season, week, scoring))
        return {"state": "AVAILABLE", "players": {"3": provider("3", 40.0, "UNAVAILABLE")}, "blockers": []}

    weekly = {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}
    response, captured, html = render_team_route(monkeypatch, weekly=weekly, provider_fetcher=fetcher)
    contract = captured["lineup_decision"]
    assert response.status_code == 200 and contract["schema_version"] == "lineup-decision.v1"
    assert calls == [(["1", "2", "3", "4"], 2026, 3, "ppr")]
    assert [(change["verb"], change["start"]["player"], change["sit"]["player"]) for change in contract["changes"]] == [("FLEX", "Delta RB", "Charlie WR")]
    assert set(captured["decisions_by_slot"]) == {"QB", "RB", "FLEX"}
    assert captured["lineup_reconciliation"]["changes"][0]["recommended"] == "Delta RB"
    assert [row["player"] for row in captured["starters"]] == ["Alpha QB", "Bravo RB", "Delta RB"]
    assert "FLEX Delta RB" in html and "SIT Charlie WR" in html and "Full-PPR" in html
    assert "40.00 per game" in html and "INFORMATIONAL_ONLY" in html


@pytest.mark.parametrize("scenario,weekly,statuses,league,expected,absent", [
    ("supported", {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}, {}, None,
     ["Supported change", "PRELIMINARY", "+4.00 weekly value vs Charlie WR"], ["% evidence confidence"]),
    ("unresolved", {}, {}, None,
     ["Keep your current lineup", "No supported change", "INSUFFICIENT_EVIDENCE", "Not ranked: Delta RB"], ["FLEX Delta RB", "% evidence confidence"]),
    ("degraded", {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}, {"Delta RB": "Questionable"}, None,
     ["DEGRADED", "MONITOR", "Official game-day status for Delta RB (Questionable)"], []),
    ("blocked", {"Alpha QB": 20.0}, {}, {"name": "Controlled", "scoring_settings": {"rec": 1.0}},
     ["Lineup recommendation blocked", "BLOCKED", "Scoring format unavailable"], ["Recommended lineup available"]),
])
def test_team_route_renders_each_decision_state(monkeypatch, scenario, weekly, statuses, league, expected, absent):
    response, captured, html = render_team_route(monkeypatch, weekly=weekly, statuses=statuses, league=league)
    assert response.status_code == 200
    assert all(text in html for text in expected), scenario
    assert not any(text in html for text in absent), scenario
    assert "<details open" not in html


def test_team_route_shows_required_slot_moves(monkeypatch):
    response, captured, html = render_team_route(monkeypatch, weekly={}, statuses={"Delta RB": "Out"}, starters=("1", "4", "2"))
    assert response.status_code == 200
    assert [(move["player"], move["from"], move["to"]) for move in captured["lineup_decision"]["moves"]] == [("Bravo RB", "FLEX", "RB")]
    assert "Move Bravo RB from FLEX to RB" in html and "Move Bravo RB</strong> &middot; FLEX to RB" in html
    assert "Delta RB out &middot; moves from FLEX</p>" in html and "FLEX Charlie WR" in html
    assert "No lineup changes recommended." not in html


def test_team_route_keeps_consensus_rank_as_context_and_compares_league_scored_projections(monkeypatch):
    today = datetime.now(timezone.utc).date().isoformat()
    ranks = consensus({"1": ("QB", 4.0), "2": ("RB", 30.0), "3": ("WR", 20.0), "4": ("RB", 12.0)}, source_date=today)

    def fetcher(players, *, season, week, scoring):
        lines = {"2": {"receptions": 5.0}, "4": {"receptions": 2.0}}
        return {"state": "AVAILABLE", "blockers": [], "players": {pid: provider(pid, 20.0 if pid == "2" else 5.0, "UNAVAILABLE", stat_line=line, data_through_week=2)
                                                                  for pid, line in lines.items()}}

    response, captured, html = render_team_route(monkeypatch, weekly={}, consensus=lambda meta: ranks, provider_fetcher=fetcher)
    contract = captured["lineup_decision"]
    assert response.status_code == 200
    # Consensus ranks Delta RB ahead of Bravo RB, but it has no lineup authority and never overrides the projection comparison.
    assert changes_of(contract) == [] and "START Delta RB over Bravo RB" not in html
    assert contract["consensus_basis"]["used_for"] == "NONE" and "consensus RB 12" in html and "Context only: weekly consensus has no lineup decision authority" in html
    assert contract["consensus_basis"]["recommendation_impact"] == "DISPLAY_ONLY"
    assert {view["consensus_rank"]["recommendation_impact"] for view in contract["players"] if view["consensus_rank"]["state"] == "AVAILABLE"} == {"DISPLAY_ONLY"}
    assert contract["weekly_score_v2_basis"].items() >= {"state": "PRELIMINARY", "exact_players": 2, "identified_players": 4, "authority": "SHADOW",
                                                         "used_for": "SHADOW_EVIDENCE", "freshness_threshold_state": "UNAPPROVED"}.items()
    assert "Weekly projection (Weekly Score v2, shadow)" in html and "freshness threshold UNAPPROVED" in html
    assert "Weekly projection: <strong>Unavailable</strong> &middot; Not requested" in html
    comparison = slot(contract, "RB")["projection_comparison"]
    assert (comparison["state"], comparison["preferred"], comparison["projection_delta"]) == ("CLOSE_CALL", "CURRENT", -3.0)
    assert comparison["authorizes_lineup_change"] is False and contract["game_lock_basis"]["state"] == "AVAILABLE"
    assert "Projection comparisons (preliminary)" in html and "Bravo RB projects 3.00 more league points" in html
    assert "Weekly projection: <strong>5.00 pts</strong> &middot; Preliminary · informational only" in html and "Lock unverified" not in html
    assert "League-scored projection: <strong>" not in html
    assert "<details open" not in html


def test_team_route_withholds_lineup_changes_when_kickoff_freshness_is_unapproved(monkeypatch):
    weekly = {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}
    response, captured, html = render_team_route(monkeypatch, weekly=weekly, schedule_max_age=None)
    contract = captured["lineup_decision"]
    lock_summary = contract["lock_summary"]
    assert response.status_code == 200 and contract["changes"] == [] and {slot["status"] for slot in contract["slots"]} == {"LOCK_UNVERIFIED"}
    assert contract["game_lock_basis"]["blockers"] == ["SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED"]
    assert (lock_summary["week_state"], lock_summary["unverified_count"], lock_summary["schedule_authority"]["threshold_state"]) == ("LOCK_COVERAGE_INCOMPLETE", 4, "UNAPPROVED")
    assert "Keep current assignments for players whose kickoff cannot be verified." in html and "LOCK COVERAGE INCOMPLETE" in html
    assert "4 players appear not yet started, but these lock states cannot be verified because schedule freshness is not approved" in html
    assert "Lock unverified</span> Stored kickoff" in html and "(unverified; appears not yet started)" in html
    assert "Kickoff lock state is unverified for" not in html and "LOCKS UNVERIFIED" not in html
    assert "FLEX Delta RB" not in html and "<details open" not in html


@pytest.mark.parametrize("bench_team,expected,absent", [
    ("GB", ["<strong>IN PROGRESS</strong> &middot; 2 open · 2 locked", "FLEX Delta RB over Charlie WR", "Decide before the ", "Still open:</strong> Charlie WR (FLEX, kickoff "],
     ["Lock unverified", "LOCK COVERAGE INCOMPLETE"]),
    ("CHI", ["<strong>LOCK COVERAGE INCOMPLETE</strong> &middot; 1 open · 2 locked · 1 unverified", "Keep current assignments for players whose kickoff cannot be verified.",
             "2 players are locked after kickoff and 1 remains open. Lock status for 1 player cannot be verified (no game was found for the player", "Lock unverified</span> Kickoff unverified"],
     ["FLEX Delta RB", "Decide before the "]),
])
def test_team_route_reports_each_players_lock_state_instead_of_a_blanket_warning(monkeypatch, bench_team, expected, absent):
    now = datetime.now(timezone.utc)
    games = [("KC", "BUF", now - timedelta(hours=3)), ("DAL", "NYG", now + timedelta(hours=2)), ("DET", "GB", now + timedelta(days=1))]
    schedule = [{"home_team": home, "away_team": away, "game_time_utc": kickoff, "game_time_pacific": None, "source": "automated:nflverse-schedules:games.csv.gz:sha256:fixture",
                 "source_recorded_at": now - timedelta(hours=1), "retrieved_at": now - timedelta(hours=1)} for home, away, kickoff in games]
    weekly = {"Alpha QB": 20.0, "Bravo RB": 10.0, "Charlie WR": 8.0, "Delta RB": 12.0}
    response, captured, html = render_team_route(monkeypatch, weekly=weekly, schedule=schedule, teams={"3": "DAL", "4": bench_team})
    states = {view["player"]: view["lock_status"]["state"] for view in captured["lineup_decision"]["players"]}
    assert response.status_code == 200 and states == {"Alpha QB": "LOCKED", "Bravo RB": "LOCKED", "Charlie WR": "OPEN", "Delta RB": "OPEN" if bench_team == "GB" else "LOCK_UNVERIFIED"}
    assert html.count("Locked</span> Kickoff ") == 2 and "Open</span> Kickoff " in html
    assert all(text in html for text in expected), [text for text in expected if text not in html]
    assert not any(text in html for text in [*absent, "LOCKS UNVERIFIED", "Kickoff lock state is unverified for", "<details open"])


def test_team_template_fails_closed_without_the_decision_contract():
    from app import app
    from flask import render_template

    with app.test_request_context("/team"):
        html = render_template("team.html", title="My Team", context={"mode": "LIVE"}, meta={"week": 3}, roster=[], league_settings={}, team_health={}, team_needs={}, roster_outlook={}, team_priority_action={}, opportunity_view={}, preliminary_matchup_context={}, weekly_risks=[], lineup_snapshot={"counts": {}})
    assert "Recommended starting lineup unavailable" in html
    assert "Lineup decision unavailable." in html
    assert "UNAVAILABLE &middot; Review lineup evidence" in html
