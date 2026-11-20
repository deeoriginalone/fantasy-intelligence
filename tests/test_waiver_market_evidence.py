"""W5 league FAAB market evidence (waiver.faab_market.v1) and the explicit transaction-history refresh."""
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from services.sleeper_snapshots import read_transaction_history, refresh_transaction_history
from services.waiver_market_evidence import (LOST_NOTE, NOT_A_BID, ROSTER_LIMIT_NOTE, TIEBREAK_LIMITATION, build_faab_market_evidence, distribution,
                                             market_context, normalize_transaction, parse_bid)

SEASON, LEAGUE = 2026, "league-1"
START = datetime(2026, 9, 9, tzinfo=timezone.utc)
RETRIEVED = START + timedelta(days=16, hours=12)
OK_NOTE = "Your waiver claim was processed successfully!"
CATALOG = {
    "qb-1": {"position": "QB", "full_name": "Quarter One"}, "qb-2": {"position": "QB", "full_name": "Quarter Two"},
    "rb-1": {"position": "RB", "full_name": "Runner One"}, "rb-2": {"position": "RB", "full_name": "Runner Two"},
    "wr-1": {"position": "WR", "full_name": "Wide One"}, "wr-2": {"position": "WR", "full_name": "Wide Two"},
    "te-1": {"position": "TE", "full_name": "Tight One"}, "te-2": {"position": "TE", "full_name": "Tight Two"},
    "k-1": {"position": "K", "full_name": "Kicker One"}, "k-2": {"position": "K", "full_name": "Kicker Two"},
    "DEN": {"position": "DEF", "first_name": "Denver", "last_name": "Broncos"}, "KC": {"position": "DEF", "first_name": "Kansas City", "last_name": "Chiefs"},
    "dst-1": {"position": "DST", "full_name": "Old Defense"},
    "twin-a": {"position": "WR", "full_name": "Same Name"}, "twin-b": {"position": "WR", "full_name": "Same Name"},
}
USERS = [{"user_id": "u1", "is_owner": True, "metadata": {"team_name": "My Team"}}, {"user_id": "u2", "display_name": "rival_two"},
         {"user_id": "u3", "metadata": {"team_name": "Third Team"}}]
PROHIBITED = re.compile(r"expected winning bid|likely winning bid|should win at|you need to bid|(?<!not a )recommended bid|minimum bid|maximum bid|fair bid|"
                        r"market price|\bworth\b|probability|demand|aggressive|hot market|cold market|value score", re.I)


def at(week, day, hour=12):
    return int((START + timedelta(days=7 * (week - 1) + day, hours=hour)).timestamp() * 1000)


def claim(tid, week, player, roster, bid=5, status="complete", *, note=None, run_day=6, seq=0, adds=None, drops=None, settings=None):
    note = note if note is not None else (OK_NOTE if status == "complete" else LOST_NOTE)
    return {"transaction_id": str(tid), "type": "waiver", "status": status, "leg": week, "created": at(week, 2), "status_updated": at(week, run_day),
            "roster_ids": [roster], "creator": f"u{roster}", "consenter_ids": [roster], "adds": adds if adds is not None else {player: roster},
            "drops": drops if drops is not None else {}, "settings": settings if settings is not None else {"waiver_bid": bid, "seq": seq},
            "metadata": {"notes": note}, "draft_picks": [], "waiver_budget": []}


def free_agent(tid, week, player, roster, day=1, settings=None):
    return {"transaction_id": str(tid), "type": "free_agent", "status": "complete", "leg": week, "created": at(week, day), "status_updated": at(week, day),
            "roster_ids": [roster], "creator": f"u{roster}", "consenter_ids": [roster], "adds": {player: roster}, "drops": {}, "settings": settings or {},
            "metadata": {}, "draft_picks": [], "waiver_budget": []}


def season_weeks(*, week1=(), week2=(), week3=()):
    """Weeks 1-2 closed and week 3 open (the league's current week); one free-agent add per week shows when each week began."""
    return {1: [free_agent("fa-1", 1, "x1", 1), *week1], 2: [free_agent("fa-2", 2, "x2", 2), *week2], 3: [free_agent("fa-3", 3, "x3", 3), *week3]}


def league(**settings):
    return {"league_id": LEAGUE, "season": "2026", "total_rosters": 3, "settings": {"waiver_type": 2, "waiver_budget": 100, "leg": 3, "start_week": 1, **settings}}


def rosters(used=(10, 20, 0)):
    return [{"roster_id": index + 1, "owner_id": f"u{index + 1}", "settings": {"waiver_budget_used": value}} for index, value in enumerate(used)]


def history(weeks, *, fetched=RETRIEVED, skip=(), latest=None, extra_rows=()):
    rows = [{"week": week, "payload": payload, "fetched_at": fetched.get(week, RETRIEVED) if isinstance(fetched, dict) else fetched, "league_id": LEAGUE, "season": SEASON}
            for week, payload in weeks.items() if week not in skip]
    return {"state": "READ", "rows": [*rows, *extra_rows], "latest_refresh": latest}


def market(weeks=None, *, league_payload=None, users=USERS, roster_list=None, owner_balance=None, read=None, **history_options):
    league_payload = league_payload or league()
    roster_list = roster_list if roster_list is not None else rosters()
    if owner_balance is None:
        used = (roster_list[0].get("settings") or {}).get("waiver_budget_used")
        owner_balance = {"state": "AVAILABLE", "budget": 100, "spent": used, "remaining": 100 - used} if isinstance(used, int) else {"state": "UNAVAILABLE"}
    return build_faab_market_evidence(league_id=LEAGUE, season=SEASON, league=league_payload, users=users, rosters=roster_list,
                                      history=read if read is not None else history(weeks if weeks is not None else season_weeks(), **history_options),
                                      catalog=CATALOG, owner_balance=owner_balance)


def texts(result):
    found = []

    def walk(value):
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
    walk(result)
    return found


# Source / normalization (1-18)

def test_completed_and_failed_waiver_claims_normalize_with_exact_source_ids():
    raw = claim("1290019938291123", 2, "wr-1", 2, bid=7)
    completed = normalize_transaction(raw, week=2, catalog=CATALOG, budget=100)
    assert (completed["transaction_id"], completed["player_id"], completed["roster_id"], completed["status"], completed["outcome"], completed["bid_state"],
            completed["bid"], completed["position"], completed["attribution"]) == ("1290019938291123", "wr-1", 2, "complete", "COMPLETED", "VERIFIED", 7, "WR", "VERIFIED")
    assert completed["created_at"] == datetime.fromtimestamp(raw["created"] / 1000, timezone.utc).isoformat()
    assert normalize_transaction(claim("88", 2, "wr-1", 3, bid=4, status="failed"), week=2, catalog=CATALOG)["outcome"] == "CLAIMED_BY_ANOTHER"
    assert normalize_transaction(claim("89", 2, "wr-1", 1, status="failed", note=ROSTER_LIMIT_NOTE), week=2, catalog=CATALOG)["outcome"] == "ROSTER_LIMIT"
    assert normalize_transaction({**raw, "transaction_id": 991}, week=2)["transaction_id"] == "991"
    assert normalize_transaction({**raw, "transaction_id": None}, week=2) is None


def test_pending_claims_are_counted_separately_and_never_as_completed_history():
    weeks = season_weeks(week2=[claim("c1", 2, "wr-1", 2, bid=7), claim("f1", 2, "wr-1", 3, bid=4, status="failed", seq=1),
                                claim("p1", 2, "rb-1", 1, bid=50, status="pending", note="")])
    summary = market(weeks)["season_summary"]
    assert (summary["waiver_claims"], summary["completed"], summary["failed"], summary["pending"]) == (3, 1, 1, 1)
    assert (summary["completed_bids"]["n"], summary["completed_bids"]["max"], summary["failed_bids"]["n"], summary["failed_bids"]["max"]) == (1, 7, 1, 4)


def test_free_agent_adds_and_other_transaction_types_never_enter_the_waiver_bid_population():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3), free_agent("fa-x", 1, "rb-1", 1, settings={"waiver_bid": 40}),
                                {**claim("cm", 1, "te-1", 3, bid=99), "type": "commissioner"}])
    result = market(weeks)
    summary = result["season_summary"]
    assert (summary["waiver_claims"], summary["completed_bids"]["text"], summary["free_agent_adds"], summary["other_types"]) == (1, "$3 (N=1, single observation)", 3, 1)
    assert {claim["transaction_id"] for claim in result["claims"]} == {"c1"}


def test_a_verified_zero_bid_stays_zero_and_counts_in_bid_figures():
    summary = market(season_weeks(week1=[claim("c0", 1, "wr-1", 2, bid=0), claim("c5", 1, "rb-1", 3, bid=5)]))["season_summary"]
    assert (summary["completed_bids"]["min"], summary["completed_bids"]["text"], summary["zero_bid_completed"]) == (0, "$0–$5, median $2.5 (N=2)", 1)


def test_a_missing_bid_is_unavailable_never_zero_but_the_claim_still_counts():
    result = market(season_weeks(week1=[claim("c-missing", 1, "wr-1", 2, settings={"seq": 0}), claim("c5", 1, "rb-1", 3, bid=5)]))
    missing = next(item for item in result["claims"] if item["transaction_id"] == "c-missing")
    summary = result["season_summary"]
    assert (missing["bid_state"], missing["bid"]) == ("MISSING", None)
    assert (summary["completed"], summary["missing_bids"], summary["completed_bids"]["text"]) == (2, 1, "$5 (N=1, single observation)")
    assert any("without a valid bid are counted as claims but excluded from bid figures" in line for line in result["limitations"])


@pytest.mark.parametrize("value,expected", [
    (0, ("VERIFIED", 0)), (7, ("VERIFIED", 7)), (7.0, ("VERIFIED", 7)), ("12", ("VERIFIED", 12)), (100, ("VERIFIED", 100)), (None, ("MISSING", None)),
    (-3, ("INVALID", None)), (float("nan"), ("INVALID", None)), ("NaN", ("INVALID", None)), (float("inf"), ("INVALID", None)), ("Infinity", ("INVALID", None)),
    (5.5, ("INVALID", None)), (True, ("INVALID", None)), ("abc", ("INVALID", None)), (101, ("INVALID", None)),
    ("-1e-400", ("INVALID", None)), ("7.0000000000000001", ("INVALID", None)),
])
def test_bid_integrity_accepts_only_whole_finite_non_negative_amounts_within_the_budget(value, expected):
    assert parse_bid(value, 100) == expected


def test_without_a_league_budget_claims_count_but_no_bid_is_verified():
    assert (parse_bid(5, None), parse_bid(None, None), parse_bid(-1, None)) == (("BUDGET_UNVERIFIED", None), ("MISSING", None), ("INVALID", None))
    payload = league()
    del payload["settings"]["waiver_budget"]
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=150), claim("c2", 1, "rb-1", 3, bid=4)]), league_payload=payload)
    summary = result["season_summary"]
    assert (summary["completed"], summary["verified_bids"], summary["budget_unverified_bids"], summary["completed_bids"]["text"]) == (2, 0, 2, "no observed bids")
    assert result["budget_context"]["state"] == "UNAVAILABLE"
    assert "The league FAAB budget is not published, so 2 bid(s) cannot be verified; those claims are counted without bid figures." in result["limitations"]


def test_defense_ids_normalize_to_def_and_an_unknown_player_keeps_his_claim_without_a_position():
    result = market(season_weeks(week1=[claim("d1", 1, "DEN", 2, bid=2), claim("d2", 1, "dst-1", 3, bid=1), claim("u1", 1, "ghost-9", 1, bid=4)]))
    by_id = {item["transaction_id"]: item for item in result["claims"]}
    assert (by_id["d1"]["position"], by_id["d1"]["player"], by_id["d2"]["position"]) == ("DEF", "Denver Broncos", "DEF")
    assert (by_id["u1"]["player_id"], by_id["u1"]["position"], by_id["u1"]["position_state"]) == ("ghost-9", None, "UNAVAILABLE")
    assert result["season_summary"]["completed"] == 3 and sum(summary["completed"] for summary in result["position_summaries"].values()) == 2
    assert result["position_summaries"]["DEF"]["completed"] == 2
    assert any("could not be matched to a current Sleeper position" in line for line in result["limitations"])


def test_a_multi_add_claim_counts_in_the_season_but_never_in_player_or_position_history_and_drops_add_no_value():
    result = market(season_weeks(week1=[claim("m1", 1, None, 2, bid=9, adds={"wr-1": 2, "rb-1": 2}), claim("w1", 1, "wr-2", 3, bid=3, drops={"x9": 3, "x8": 3})]))
    by_id = {item["transaction_id"]: item for item in result["claims"]}
    assert (by_id["m1"]["attribution"], by_id["m1"]["player_id"], by_id["m1"]["position"]) == ("UNVERIFIED", None, None)
    assert (result["season_summary"]["completed_bids"]["max"], result["season_summary"]["attribution_unverified"]) == (9, 1)
    assert set(result["players"]) == {"wr-2"} and (result["position_summaries"]["WR"]["completed"], result["position_summaries"]["RB"]["completed"]) == (1, 0)
    assert by_id["w1"]["drops"] == {"x9": 3, "x8": 3} and not [key for key in by_id["w1"] if "value" in key]
    assert any(line.startswith("PLAYER ATTRIBUTION UNVERIFIED") for line in result["limitations"])


def test_identical_duplicate_records_count_once_and_conflicting_records_block_bid_history():
    original = claim("dup", 1, "wr-1", 2, bid=6)
    same = market(season_weeks(week1=[original, dict(original)]))
    assert (same["state"], same["season_summary"]["completed"], same["completeness"]["duplicates_removed"]) == ("AVAILABLE", 1, 1)
    conflict = market(season_weeks(week1=[original, {**original, "settings": {"waiver_bid": 60, "seq": 0}}]))
    assert (conflict["state"], conflict["completeness"]["state"], conflict["season_summary"], conflict["groups"]) == ("CONTRADICTORY", "CONTRADICTORY", None, [])
    assert conflict["completeness"]["conflicting_transaction_ids"] == ["dup"] and "no bid history is published" in conflict["reason"]


# Completeness / weeks (19-28)

def test_an_empty_week_retrieved_after_it_closed_is_verified_evidence():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)])
    weeks[2] = []
    result = market(weeks)
    assert result["completeness"]["weeks"] == {1: "FINAL", 2: "CLOSED", 3: "OPEN"}
    assert (result["state"], result["completeness"]["state"], result["through_week"], result["scope_text"]) == ("AVAILABLE", "COMPLETE", 2, "Weeks 1–2")
    assert result["completeness"]["empty_verified_weeks"] == [2] and result["recent_summary"]["text"].startswith("Week 2: 0 completed claims")


def test_a_missing_week_is_never_an_empty_week_and_makes_the_history_partial():
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)], week2=[claim("c2", 2, "rb-1", 3, bid=8)]), skip=(1,))
    assert (result["completeness"]["weeks"][1], result["state"], result["completeness"]["state"], result["through_week"]) == ("MISSING", "PARTIAL", "PARTIAL", None)
    assert result["scope_text"] == "across 1 verified transaction week (Weeks 2)" and result["season_summary"]["completed"] == 1
    assert "Week 1 not stored" in result["reason"] and result["label"] == "PARTIAL MARKET HISTORY"
    assert market(season_weeks(), skip=(1, 2))["state"] == "UNAVAILABLE"


def test_the_open_week_and_a_week_retrieved_before_it_closed_are_not_history():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)], week3=[claim("open", 3, "rb-1", 1, bid=40, run_day=2)])
    result = market(weeks)
    assert "open" not in {item["transaction_id"] for item in result["claims"]} and result["completeness"]["open_week"]["processed_claims"] == 1
    assert result["limitations"][0].startswith("Week 3 is still open on Sleeper: its waiver run has not been processed")
    early = market(weeks, fetched={1: RETRIEVED, 2: START + timedelta(days=10), 3: RETRIEVED})
    assert (early["completeness"]["weeks"][2], early["state"], early["through_week"]) == ("OPEN_AT_RETRIEVAL", "PARTIAL", 1)
    assert "Week 2 retrieved before Sleeper closed it" in early["reason"]
    assert result["limitations"][1].endswith("refresh after the Week 3 waiver run to make Week 2 final.")
    later = market({**weeks, 4: [free_agent("fa-4", 4, "x4", 1)]}, league_payload=league(leg=4), fetched={4: START + timedelta(days=23)})
    assert (later["through_week"], later["completeness"]["weeks"][2], later["completeness"]["open_at_retrieval_weeks"]) == (2, "CLOSED", [3])
    assert later["limitations"][1].endswith("Week 2 was stored before the following week closed, so a new refresh will make it final.")


def test_most_recent_week_is_the_latest_verified_week_even_with_a_gap():
    weeks = {**season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)], week3=[claim("c3", 3, "rb-1", 1, bid=9)]), 4: [free_agent("fa-4", 4, "x4", 1)]}
    result = market(weeks, league_payload=league(leg=4), skip=(2,), fetched=START + timedelta(days=30))
    assert (result["completeness"]["weeks"], result["through_week"]) == ({1: "FINAL", 2: "MISSING", 3: "CLOSED", 4: "OPEN"}, 1)
    assert result["recent_summary"]["week"] == 3 and result["recent_summary"]["text"].startswith("Week 3: 1 completed claim ($9 (N=1, single observation))")
    assert result["scope_text"] == "across 2 verified transaction weeks (Weeks 1, 3)"


def test_season_and_league_scope_must_match():
    assert market(league_payload={**league(), "season": "2025"})["blockers"] == ["SEASON_MISMATCH"]
    assert market(league_payload={**league(), "league_id": "another"})["blockers"] == ["LEAGUE_MISMATCH"]
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)])
    stray = market(weeks, skip=(2,), extra_rows=[{"week": 2, "payload": weeks[2], "fetched_at": RETRIEVED, "league_id": "another", "season": SEASON},
                                                {"week": 2, "payload": weeks[2], "fetched_at": RETRIEVED, "league_id": LEAGUE, "season": 2025}])
    assert (stray["completeness"]["weeks"][2], stray["completeness"]["mismatched_rows"], stray["state"]) == ("MISSING", 2, "PARTIAL")


def test_a_later_retrieval_never_rewrites_when_a_claim_happened():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)])
    first, later = market(weeks), market(weeks, fetched=RETRIEVED + timedelta(days=30))
    assert [(item["created_at"], item["status_updated_at"]) for item in first["claims"]] == [(item["created_at"], item["status_updated_at"]) for item in later["claims"]]
    assert first["claims"][0]["status_updated_at"] == datetime.fromtimestamp(at(1, 6) / 1000, timezone.utc).isoformat()
    assert first["completeness"]["latest_retrieval"] != later["completeness"]["latest_retrieval"]


def test_a_failed_latest_refresh_keeps_the_last_verified_weeks_but_never_claims_complete():
    latest = {"status": "partial", "resources": {"weeks": {"1": {"ok": True, "count": 2}, "2": {"ok": False, "error": "RuntimeError: 503"}}},
              "started_at": RETRIEVED, "completed_at": RETRIEVED, "error": "Week 2: RuntimeError: 503"}
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 2, bid=3)]), latest=latest)
    assert (result["state"], result["completeness"]["state"], result["completeness"]["verified_weeks"]) == ("PARTIAL", "PARTIAL", [1, 2])
    assert "the latest refresh attempt (partial) could not reverify completeness; it failed for Week 2" in result["reason"]
    assert result["completeness"]["latest_refresh"]["text"].endswith("failed for Week 2.") and result["season_summary"]["completed"] == 1


# Completed / failed claims (29-40)

def test_completed_and_failed_bids_are_separate_populations():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=20), claim("f1", 1, "wr-1", 2, bid=12, status="failed", seq=1),
                                claim("f2", 1, "wr-1", 3, bid=10, status="failed", seq=2)], week2=[claim("c2", 2, "rb-1", 2, bid=4)])
    summary = market(weeks)["season_summary"]
    assert (summary["completed"], summary["failed"]) == (2, 2)
    assert summary["completed_bids"] == {"n": 2, "sample": "MULTIPLE_OBSERVATIONS", "min": 4, "median": 12, "max": 20, "text": "$4–$20, median $12 (N=2)"}
    assert summary["failed_bids"]["text"] == "$10–$12, median $11 (N=2)" and summary["failed_reasons_text"] == "2 lost to another team's claim"


@pytest.mark.parametrize("values,expected", [
    ([], (0, "NO_SAMPLE", None, None, None, "no observed bids")),
    ([5], (1, "SINGLE_OBSERVATION", 5, 5, 5, "$5 (N=1, single observation)")),
    ([9, 1, 4], (3, "MULTIPLE_OBSERVATIONS", 1, 4, 9, "$1–$9, median $4 (N=3)")),
    ([1, 2, 6, 9], (4, "MULTIPLE_OBSERVATIONS", 1, 4, 9, "$1–$9, median $4 (N=4)")),
    ([1, 2], (2, "MULTIPLE_OBSERVATIONS", 1, 1.5, 2, "$1–$2, median $1.5 (N=2)")),
])
def test_bid_distribution_reports_n_and_never_turns_an_empty_population_into_zero(values, expected):
    result = distribution(values)
    assert (result["n"], result["sample"], result["min"], result["median"], result["max"], result["text"]) == expected


# Player / position (41-50)

def test_player_history_is_keyed_only_by_the_exact_sleeper_id():
    result = market(season_weeks(week1=[claim("a", 1, "twin-a", 2, bid=7)], week2=[claim("b", 2, "twin-b", 3, bid=1)]))
    assert set(result["players"]) == {"twin-a", "twin-b"} and result["players"]["twin-a"]["groups"][0]["completed"]["bid"] == 7
    twin_b = market_context(result, player_id="twin-b", position="WR", player="Same Name")
    assert twin_b["player_state"] == "HISTORY" and "$1" in twin_b["lines"][0] and "$7" not in twin_b["lines"][0]
    unseen = market_context(result, player_id="wr-2", position="WR", player="Wide Two")
    assert (unseen["player_state"], unseen["lines"][0]) == ("NO_OBSERVED_CLAIM_HISTORY", "Player history: NO LEAGUE CLAIM HISTORY for Wide Two in Weeks 1–2.")


@pytest.mark.parametrize("position,player", [("QB", "qb-2"), ("RB", "rb-2"), ("WR", "wr-2"), ("TE", "te-2"), ("K", "k-2"), ("DEF", "KC")])
def test_each_position_summary_counts_only_its_own_claims(position, player):
    background = [claim(f"bg-{name}", 1, name, 2, bid=1) for name in ("qb-1", "rb-1", "wr-1", "te-1", "k-1", "DEN")]
    summaries = market(season_weeks(week1=background, week2=[claim("target", 2, player, 3, bid=13)]))["position_summaries"]
    for name, summary in summaries.items():
        expected = (2, 13, "$1–$13, median $7 (N=2)") if name == position else (1, 1, "$1 (N=1, single observation)")
        assert (summary["completed"], summary["completed_bids"]["max"], summary["completed_bids"]["text"]) == expected


# Contest groups (51-60)

def test_competing_claims_in_one_waiver_run_form_a_contested_group_without_a_minimum_winning_bid():
    result = market(season_weeks(week1=[claim("win", 1, "wr-1", 1, bid=17, seq=0), claim("lose-b", 1, "wr-1", 2, bid=13, status="failed", seq=1),
                                        claim("lose-c", 1, "wr-1", 3, bid=8, status="failed", seq=2)]))
    [group] = result["groups"]
    assert (group["state"], group["claims"], group["competing_claims"], group["highest_failed_competing_bid"], group["tie"]) == ("CONTESTED", 3, 2, 13, False)
    assert group["completed"] == {"roster_id": 1, "team": "My Team", "bid": 17, "bid_state": "VERIFIED"}
    assert [(item["team"], item["bid"], item["reason"]) for item in group["failed"]] == [("rival_two", 13, "LOST_TO_ANOTHER_TEAM"), ("Third Team", 8, "LOST_TO_ANOTHER_TEAM")]
    assert group["text"] == ("Week 1 · Wide One (WR) · 3 claims: My Team completed at $17; 2 competing claims from other teams failed "
                             "(highest observed failed competing bid $13).")
    keys = set()

    def collect(value):
        if isinstance(value, dict):
            keys.update(str(key) for key in value)
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    collect(result)
    assert not [key for key in keys if "minimum" in key or "min_win" in key] and "minimum" not in " ".join(texts(result)).lower()


def test_claims_group_only_within_one_player_one_week_and_one_waiver_run():
    groups = market(season_weeks(week1=[claim("a", 1, "wr-1", 1, bid=5), claim("b", 1, "wr-2", 2, bid=4, status="failed"),
                                        claim("c", 1, "rb-1", 2, bid=3, run_day=3), claim("d", 1, "rb-1", 3, bid=6, run_day=6)],
                                 week2=[claim("e", 2, "wr-1", 3, bid=2, status="failed")]))["groups"]
    assert sorted((group["week"], group["player_id"], group["claims"]) for group in groups) == [(1, "rb-1", 1), (1, "rb-1", 1), (1, "wr-1", 1), (1, "wr-2", 1), (2, "wr-1", 1)]
    assert {group["state"] for group in groups if group["player_id"] == "rb-1"} == {"UNCONTESTED"}
    assert next(group for group in groups if group["week"] == 2)["failed"][0]["reason"] == "WINNER_NOT_IN_GROUP"


def test_single_claims_same_team_duplicates_and_roster_limit_failures_are_not_competition():
    result = market(season_weeks(week1=[claim("solo", 1, "k-1", 2, bid=1), claim("own-win", 1, "rb-1", 1, bid=7, seq=0),
                                        claim("own-dup", 1, "rb-1", 1, bid=6, status="failed", seq=1), claim("rl-win", 1, "te-1", 3, bid=5, seq=2),
                                        claim("rl-high", 1, "te-1", 2, bid=12, status="failed", note=ROSTER_LIMIT_NOTE, seq=0)]))
    groups = {group["player_id"]: group for group in result["groups"]}
    assert (groups["k-1"]["state"], groups["k-1"]["label"]) == ("UNCONTESTED", "UNCONTESTED CLAIM")
    assert groups["k-1"]["text"] == "Week 1 · Kicker One (K) · 1 claim: rival_two completed at $1; no competing claim from another team in this waiver run."
    assert (groups["rb-1"]["state"], groups["rb-1"]["failed"][0]["reason"]) == ("UNCONTESTED", "OWN_OTHER_CLAIM_WON")
    assert (groups["te-1"]["state"], groups["te-1"]["highest_failed_competing_bid"], groups["te-1"]["failed"][0]["reason"]) == ("OTHER_CLAIMS_ROSTER_LIMIT", None, "ROSTER_LIMIT")
    summary = result["season_summary"]
    assert (summary["contested"], summary["uncontested"], summary["other_claims_roster_limit"], summary["uncontested_bids"]["text"]) == (0, 2, 1, "$1–$7, median $4 (N=2)")


def test_a_tied_failed_bid_is_disclosed_without_inferring_the_tiebreak():
    result = market(season_weeks(week1=[claim("w", 1, "wr-1", 1, bid=4, seq=0), claim("l", 1, "wr-1", 2, bid=4, status="failed", seq=1)]))
    [group] = result["groups"]
    assert group["tie"] is True and group["text"].endswith("1 competing claim from another team failed at $4; a failed bid tied the completed bid.")
    assert TIEBREAK_LIMITATION in result["limitations"]


def test_without_processing_times_contest_analysis_is_unavailable_but_bid_history_remains():
    result = market(season_weeks(week1=[{**claim("a", 1, "wr-1", 1, bid=9), "status_updated": None},
                                        {**claim("b", 1, "wr-1", 2, bid=3, status="failed"), "status_updated": None}]))
    summary = result["season_summary"]
    assert (result["groups"], summary["contested"], summary["uncontested"], summary["contest_unverified"]) == ([], 0, 0, 1)
    assert (summary["completed_bids"]["text"], summary["failed_bids"]["text"], summary["failed_reasons"]) == (
        "$9 (N=1, single observation)", "$3 (N=1, single observation)", {"WINNER_NOT_IN_GROUP": 1})


# Budget (61-71)

def test_budget_context_reuses_the_page_contract_for_every_team():
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=10), claim("c2", 1, "rb-1", 2, bid=20)]))
    budget = result["budget_context"]
    assert (budget["state"], budget["owner"]["reconciliation"], budget["owner"]["remaining"], budget["verified"]) == ("AVAILABLE", "RECONCILED", 90, 3)
    assert [(team["team"], team["remaining"], team["used"]) for team in budget["teams"]] == [("Third Team", 100, 0), ("My Team", 90, 10), ("rival_two", 80, 20)]
    assert budget["distribution"] == {"n": 3, "median_remaining": 90, "highest_remaining": 100, "lowest_remaining": 80}
    assert (budget["spend_reconciliation"]["coverage"], budget["spend_reconciliation"]["matched"]) == ("COMPLETE", 3)
    assert budget["spend_reconciliation"]["text"] == "Completed waiver bids in Weeks 1–3 equal Sleeper's budget used for 3 of 3 verified teams."
    assert [(row["team"], row["completed_claims"], row["largest_completed_bid"]) for row in result["manager_table"]] == [
        ("Third Team", 0, None), ("My Team", 1, 10), ("rival_two", 1, 20)]


def test_non_faab_league_makes_bid_history_not_applicable():
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=10)]), league_payload=league(waiver_type=0))
    assert (result["state"], result["label"], result["season_summary"], result["budget_context"]) == ("NOT_APPLICABLE", "NOT APPLICABLE", None, None)
    assert market_context(result, player_id="wr-1", position="WR")["lines"] == ["The league is not verified as FAAB-based, so bid history is not applicable."]


def test_team_identity_comes_from_the_roster_owner_mapping_never_from_names():
    users = [{"user_id": "u1", "is_owner": True, "metadata": {"team_name": "Shared"}}, {"user_id": "u2", "display_name": "Shared"}]
    roster_list = [{"roster_id": 1, "owner_id": "u1", "settings": {"waiver_budget_used": 30}}, {"roster_id": 2, "owner_id": "u2", "settings": {"waiver_budget_used": 0}},
                   {"roster_id": 3, "owner_id": None, "settings": {"waiver_budget_used": 0}}]
    teams = {team["roster_id"]: team for team in market(users=users, roster_list=roster_list)["budget_context"]["teams"]}
    assert (teams[1]["used"], teams[1]["is_owner"], teams[2]["used"], teams[2]["is_owner"], teams[3]["team"]) == (30, True, 0, False, "Roster 3")


def test_zero_remaining_stays_zero_and_a_missing_budget_is_unavailable_without_a_league_distribution():
    roster_list = [{"roster_id": 1, "owner_id": "u1", "settings": {"waiver_budget_used": 100}}, {"roster_id": 2, "owner_id": "u2", "settings": {}},
                   {"roster_id": 3, "owner_id": "u3", "settings": {"waiver_budget_used": 5}}]
    budget = market(roster_list=roster_list)["budget_context"]
    teams = {team["roster_id"]: team for team in budget["teams"]}
    assert (teams[1]["remaining"], teams[2]["remaining"], teams[2]["used"], teams[2]["state"]) == (0, None, None, "UNAVAILABLE")
    assert (budget["state"], budget["distribution"], budget["verified"], budget["reason"]) == ("PARTIAL", None, 2, "2 of 3 team budgets are verified; no league distribution is shown.")


def test_a_budget_that_disagrees_with_the_page_amount_is_a_visible_conflict():
    budget = market(owner_balance={"state": "AVAILABLE", "budget": 100, "spent": 50, "remaining": 50})["budget_context"]
    assert (budget["state"], budget["owner"]["reconciliation"]) == ("CONFLICT", "CONFLICT") and budget["reason"].startswith("FAAB BUDGET CONFLICT")


def test_completed_bid_totals_never_rewrite_sleeper_budget_used():
    budget = market(season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=4)]), roster_list=rosters((10, 0, 0)))["budget_context"]
    mine = next(team for team in budget["teams"] if team["roster_id"] == 1)
    assert (mine["used"], mine["remaining"], mine["completed_bid_total"]) == (10, 90, 4)
    assert budget["spend_reconciliation"]["mismatched"] == [{"team": "My Team", "used": 10, "completed_bid_total": 4}]
    assert budget["spend_reconciliation"]["text"].endswith("1 team differ. Neither is adjusted.")


# Market display (72-85)

def test_move_context_lists_player_then_position_then_league_history_with_samples_and_no_bid_language():
    result = market(season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=6), claim("l1", 1, "wr-1", 2, bid=4, status="failed", seq=1)],
                                 week2=[claim("c2", 2, "wr-2", 3, bid=2), claim("c3", 2, "rb-1", 2, bid=9)]))
    seen = market_context(result, player_id="wr-1", position="WR", player="Wide One", monitor=True)
    assert seen["lines"] == [
        "Player history (Weeks 1–2): Week 1, 2 claims (contested claim): My Team completed at $6; 1 competing claim from another team failed at $4.",
        "WR (Weeks 1–2): 2 completed claims, $2–$6, median $4 (N=2); 1 contested, 1 uncontested; 1 failed claim.",
        "This history does not make the move executable.", NOT_A_BID]
    kicker = market_context(result, player_id="k-1", position="K", player="Kicker One")
    assert kicker["lines"] == ["Player history: NO LEAGUE CLAIM HISTORY for Kicker One in Weeks 1–2.",
                               "K (Weeks 1–2): 0 completed claims; 0 contested, 0 uncontested; 0 failed claims.",
                               "All positions (Weeks 1–2): 3 completed claims, $2–$9, median $6 (N=3); 1 contested, 2 uncontested.", NOT_A_BID]
    rostered = market_context(result, player_id="wr-1", position="WR", player="Wide One", rostered=True)
    assert rostered["lines"][0] == "Wide One is on a roster now; this history is informational and does not make this player available."
    every_text = texts(result) + seen["lines"] + kicker["lines"]
    assert not [line for line in every_text if PROHIBITED.search(line)]
    assert all("(N=" in summary["completed_bids"]["text"] for summary in result["position_summaries"].values() if summary["completed_bids"]["n"])


def test_unavailable_history_still_explains_itself_to_the_manager():
    unread = market(read={"state": "READ_FAILED"})
    assert (unread["state"], unread["label"], unread["blockers"]) == ("UNAVAILABLE", "MARKET COVERAGE BLOCKED", ["TRANSACTION_HISTORY_UNREAD"])
    context = market_context(unread, player_id="wr-1", position="WR")
    assert context["lines"] == ["Stored transaction history could not be read for this page view."] and context["player_history"] is None
    empty = market(read={"state": "READ", "rows": [], "latest_refresh": None})
    assert empty["reason"] == "No transaction week is stored that Sleeper had closed when it was retrieved; run python refresh_sleeper_transactions.py."


# Refresh / persistence (27, 28, 108-111)

class FakeSnapshotDB:
    """In-memory stand-in for sleeper_api_snapshots and sleeper_sync_runs: writes apply only on commit, like a database transaction."""

    def __init__(self):
        self.rows, self.runs, self.pending, self.statements = {}, {}, [], []
        self.clock = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)

    def cursor(self):
        return FakeSnapshotCursor(self)

    def commit(self):
        for apply in self.pending:
            apply()
        self.pending = []
        self.clock += timedelta(minutes=1)

    def rollback(self):
        self.pending = []

    def close(self):
        pass


class FakeSnapshotCursor:
    def __init__(self, db):
        self.db, self.result = db, []

    def execute(self, query, params=()):
        db, now = self.db, self.db.clock
        db.statements.append(query)
        if query.startswith("INSERT INTO sleeper_api_snapshots"):
            kind, key, season, week, payload, *retrieved = params
            fetched_at = retrieved[0] if retrieved else now
            db.pending.append(lambda: db.rows.__setitem__((kind, key, season, week), {"payload": json.loads(payload), "fetched_at": fetched_at}))
        elif query.startswith("INSERT INTO sleeper_sync_runs"):
            run_id = len(db.runs) + 1 + sum(1 for _ in db.pending)
            league_id, season, week, resources = params
            db.pending.append(lambda: db.runs.__setitem__(run_id, {"league_id": league_id, "season": season, "status": "running", "resources": json.loads(resources),
                                                                   "error": None, "started_at": now, "completed_at": None}))
            self.result = [(run_id,)]
        elif query.startswith("UPDATE sleeper_sync_runs"):
            season, week, status, resources, error, run_id = params
            db.pending.append(lambda: db.runs[run_id].update(season=season, week=week, status=status, resources=json.loads(resources), error=error, completed_at=now))
        elif "FROM sleeper_api_snapshots" in query:
            kind, key, season = params
            self.result = [(week, row["payload"], row["fetched_at"], key, season) for (row_kind, row_key, row_season, week), row in sorted(db.rows.items(), key=lambda item: item[0][3])
                           if (row_kind, row_key, row_season) == (kind, key, season)]
        elif "FROM sleeper_sync_runs" in query:
            assert "season IN (%s, 0)" in query
            league_id, season, scope = params
            runs = sorted(((run_id, run) for run_id, run in db.runs.items()
                           if run["league_id"] == league_id and run["season"] in (season, 0) and run["resources"].get("scope") == scope), reverse=True)
            self.result = [(run_id, run["status"], run["resources"], run["error"], run["started_at"], run["completed_at"]) for run_id, run in runs[:1]]
        else:
            raise AssertionError(f"unexpected statement {query}")

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return list(self.result)

    def close(self):
        pass


def sleeper(weeks, *, fail=(), league_payload=None):
    calls = Counter()

    def get_league(league_id):
        calls["league"] += 1
        return league_payload or league()

    def get_transactions(league_id, week):
        calls[week] += 1
        if week in fail:
            raise RuntimeError(f"HTTP 503 for week {week}")
        return json.loads(json.dumps(weeks.get(week, [])))
    return get_league, get_transactions, calls


class RequestClock:
    """Times at which refresh requests are sent: distinct from the database write time, which the fake database keeps separately."""

    def __init__(self):
        self.current = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)

    def __call__(self):
        self.current += timedelta(seconds=1)
        return self.current


def refresh(db, weeks, clock=None, season=SEASON, **options):
    get_league, get_transactions, calls = sleeper(weeks, **options)
    return refresh_transaction_history(db, league_id=LEAGUE, season=season, get_league=get_league, get_transactions=get_transactions,
                                       now=clock or RequestClock()), calls


def evidence(read):
    return market(read=read)


def test_refresh_retrieves_each_week_once_and_replaying_the_stored_weeks_reproduces_the_evidence():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=6), claim("l1", 1, "wr-1", 2, bid=4, status="failed", seq=1)], week2=[claim("c2", 2, "rb-1", 3, bid=0)])
    db, clock = FakeSnapshotDB(), RequestClock()
    result, calls = refresh(db, weeks, clock)
    assert (result["status"], result["requests"], result["league_leg"], result["failed_weeks"]) == ("success", 4, 3, [])
    assert dict(calls) == {"league": 1, 1: 1, 2: 1, 3: 1}
    stored = read_transaction_history(db.cursor(), LEAGUE, SEASON)
    assert [row["week"] for row in stored["rows"]] == [1, 2, 3] and stored["latest_refresh"]["status"] == "success"
    # Each week keeps the time its request was sent, not the later database write time.
    assert [row["fetched_at"] for row in stored["rows"]] == [datetime(2026, 11, 20, 8, 0, second, tzinfo=timezone.utc) for second in (1, 2, 3)]
    assert [result["weeks"][week]["requested_at"] for week in (1, 2, 3)] == [row["fetched_at"].isoformat() for row in stored["rows"]]
    replayed = evidence(stored)
    direct = market(weeks, fetched={row["week"]: row["fetched_at"] for row in stored["rows"]}, latest=stored["latest_refresh"])
    for key in ("state", "claims", "season_summary", "groups", "position_summaries", "budget_context", "completeness"):
        assert replayed[key] == direct[key]
    again, _ = refresh(db, weeks, clock)
    assert again["status"] == "success" and len(db.rows) == 3 and len(db.runs) == 2
    restored = read_transaction_history(db.cursor(), LEAGUE, SEASON)
    assert [row["payload"] for row in restored["rows"]] == [row["payload"] for row in stored["rows"]]
    assert evidence(restored)["season_summary"] == replayed["season_summary"]


def test_a_failed_week_is_reported_by_number_and_keeps_its_last_verified_snapshot():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=6)], week2=[claim("c2", 2, "rb-1", 3, bid=2)])
    db, clock = FakeSnapshotDB(), RequestClock()
    refresh(db, weeks, clock)
    before = dict(db.rows[("transactions", LEAGUE, SEASON, 2)])
    week1_before = db.rows[("transactions", LEAGUE, SEASON, 1)]["fetched_at"]
    result, calls = refresh(db, {**weeks, 2: []}, clock, fail=(2,))
    assert (result["status"], result["failed_weeks"], result["error"]) == ("partial", [2], "Week 2: RuntimeError: HTTP 503 for week 2")
    assert calls[2] == 1 and db.rows[("transactions", LEAGUE, SEASON, 2)] == before
    assert db.rows[("transactions", LEAGUE, SEASON, 1)]["fetched_at"] > week1_before
    run = db.runs[max(db.runs)]
    assert (run["status"], run["resources"]["weeks"]["2"]["ok"], run["error"]) == ("partial", False, "Week 2: RuntimeError: HTTP 503 for week 2")
    replay = evidence(read_transaction_history(db.cursor(), LEAGUE, SEASON))
    assert (replay["state"], replay["season_summary"]["completed"], replay["completeness"]["latest_refresh"]["failed_weeks"]) == ("PARTIAL", 2, [2])


def test_a_refresh_that_cannot_verify_the_league_stores_nothing_and_a_dry_run_never_writes():
    db = FakeSnapshotDB()
    result, calls = refresh(db, season_weeks(), league_payload={**league(), "season": "2025"})
    assert (result["status"], result["error"], db.rows, dict(calls)) == ("failed", "League: the league's season is 2025, not 2026.", {}, {"league": 1})
    assert db.runs[1]["status"] == "failed"
    get_league, get_transactions, calls = sleeper(season_weeks())
    dry = refresh_transaction_history(None, league_id=LEAGUE, season=SEASON, get_league=get_league, get_transactions=get_transactions, dry_run=True)
    assert (dry["status"], dry["requests"], dry["run_id"]) == ("success", 4, None)


def test_failed_or_interrupted_refreshes_are_always_visible_to_the_page():
    weeks = season_weeks(week1=[claim("c1", 1, "wr-1", 1, bid=6)])
    db, clock = FakeSnapshotDB(), RequestClock()
    refresh(db, weeks, clock)
    assert evidence(read_transaction_history(db.cursor(), LEAGUE, SEASON))["state"] == "AVAILABLE"

    def unreachable(league_id):
        raise RuntimeError("Sleeper unreachable")
    failed = refresh_transaction_history(db, league_id=LEAGUE, get_league=unreachable, get_transactions=lambda *args: [], now=clock)
    assert (failed["status"], failed["season"], db.runs[failed["run_id"]]["season"]) == ("failed", None, 0)
    after_failure = evidence(read_transaction_history(db.cursor(), LEAGUE, SEASON))
    assert after_failure["state"] == "PARTIAL" and "the latest refresh attempt (failed) could not reverify completeness" in after_failure["reason"]

    def interrupted(league_id, week):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        refresh_transaction_history(db, league_id=LEAGUE, season=SEASON, get_league=lambda league_id: league(), get_transactions=interrupted, now=clock)
    latest = read_transaction_history(db.cursor(), LEAGUE, SEASON)["latest_refresh"]
    assert latest["status"] == "running" and latest["completed_at"] is None
    assert evidence(read_transaction_history(db.cursor(), LEAGUE, SEASON))["state"] == "PARTIAL"
