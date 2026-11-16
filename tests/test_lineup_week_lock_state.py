"""Lineup lock state across a fixed Week 10 (Thursday through Monday night) and when schedule evidence cannot be verified."""
import random
from datetime import datetime, timedelta, timezone

import pytest

from services.game_lock import build_roster_game_locks
from services.lineup_decision_intelligence import build_lineup_decision
from services.team_needs import league_settings_contract

UTC = timezone.utc
SOURCE = "automated:nflverse-schedules:games.csv.gz:sha256:fixture"
RECORDED = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
# Fixture-only freshness limit passed explicitly; the production limit is owner-approved configuration, not a code default.
FIXTURE_MAX_AGE = 7 * 86400
KICKOFFS = {
    "TNF": datetime(2026, 11, 13, 1, 15, tzinfo=UTC),
    "EARLY": datetime(2026, 11, 15, 18, 0, tzinfo=UTC),
    "LATE": datetime(2026, 11, 15, 21, 25, tzinfo=UTC),
    "SNF": datetime(2026, 11, 16, 1, 20, tzinfo=UTC),
    "MNF": datetime(2026, 11, 17, 1, 15, tzinfo=UTC),
}
GAMES = [("NE", "NYJ", "TNF"), ("KC", "BUF", "EARLY"), ("ATL", "MIA", "EARLY"), ("SEA", "SF", "LATE"), ("ARI", "LAR", "LATE"), ("DAL", "NYG", "SNF"),
         ("DET", "GB", "MNF")]
WINDOW = {team: window for home, away, window in GAMES for team in (home, away)}
OPPONENT = {**{home: away for home, away, _window in GAMES}, **{away: home for home, away, _window in GAMES}}
THU_BEFORE_TNF = datetime(2026, 11, 12, 20, 0, tzinfo=UTC)
SUN_MORNING = datetime(2026, 11, 15, 15, 0, tzinfo=UTC)
SUN_BETWEEN = datetime(2026, 11, 15, 20, 0, tzinfo=UTC)
SUN_EVENING = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)
MON_BEFORE_MNF = datetime(2026, 11, 16, 22, 0, tzinfo=UTC)
SETTINGS = league_settings_contract({"roster_positions": ["QB", "RB", "WR", "FLEX", *["BN"] * 7], "scoring_settings": {"rec": 1.0}})
HEALTH = {"state": "AVAILABLE", "source": "Sleeper API", "freshness_state": "FRESH"}


@pytest.fixture(autouse=True)
def fixed_environment(monkeypatch):
    monkeypatch.setenv("TIME_ZONE", "America/Los_Angeles")
    monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)


def schedule(*, skip=(), recorded=RECORDED, source=SOURCE):
    return [{"season": 2026, "week": 10, "home_team": home, "away_team": away, "game_time_utc": KICKOFFS[window], "source": source,
             "source_recorded_at": recorded, "retrieved_at": recorded} for home, away, window in GAMES if home not in skip and away not in skip]


def player(name, position, team, value, *, slot=None, index=None, status="Active", bye=False):
    return {"player": name, "position": position, "source_player_id": name, "nfl_team": team, "injury_status": status, "health_status_available": True,
            "opponent": OPPONENT.get(team), "is_bye": bye, "weekly_score": value, "weekly_baseline": value, "matchup_modifier": 0.0, "injury_multiplier": 1.0,
            "sleeper_current_starter": slot is not None, "sleeper_lineup_slot": slot, "sleeper_lineup_index": index}


def week_roster(statuses=None, *, values=True, skip=()):
    """The roster as weekly enrichment supplies it: a team missing from the schedule also has no opponent."""
    rows = [
        player("Jets QB", "QB", "NYJ", 18.0, slot="QB", index=0), player("Chiefs RB", "RB", "KC", 8.0, slot="RB", index=1),
        player("Seahawks WR", "WR", "SEA", 9.0, slot="WR", index=2), player("Cowboys WR", "WR", "DAL", 10.0, slot="FLEX", index=3),
        player("Dolphins WR", "WR", "MIA", 14.0), player("Falcons TE", "TE", "ATL", 5.0), player("Rams RB", "RB", "LAR", 12.0),
        player("Cardinals WR", "WR", "ARI", 6.0), player("Packers WR", "WR", "GB", 11.0), player("Bears RB", "RB", "CHI", None, bye=True),
    ]
    statuses = statuses or {}
    return [{**row, "injury_status": statuses.get(row["player"], "Active"), **({} if values else {"weekly_score": None, "weekly_baseline": None}),
             **({"opponent": None} if row["nfl_team"] in skip else {})} for row in rows]


def evaluate(at, *, roster=None, rows=None, skip=(), max_age=FIXTURE_MAX_AGE, **kwargs):
    roster = week_roster(skip=skip) if roster is None else roster
    rows = schedule(skip=skip) if rows is None else rows
    locks = build_roster_game_locks(roster, schedule_rows=rows, season=2026, week=10, now=at, max_age_seconds=max_age)
    return build_lineup_decision(roster, league_settings=SETTINGS, team_health=HEALTH, season=2026, week=10, game_locks=locks, now=at, **kwargs)


def counts(result):
    summary = result["lock_summary"]
    return summary["week_state"], summary["open_count"], summary["locked_count"], summary["unverified_count"], summary["bye_count"]


def by_player(result):
    return {view["player"]: view for view in result["players"]}


def slot_of(result, label):
    return next(decision for decision in result["slots"] if decision["slot"] == label)


def pairs(result):
    return {(change["start"]["player"], change["sit"]["player"] if change["sit"] else None) for change in result["changes"]}


@pytest.mark.parametrize("at,expected", [
    (THU_BEFORE_TNF, ("PRE_KICKOFF", 9, 0, 0, 1)),
    (KICKOFFS["TNF"], ("IN_PROGRESS", 8, 1, 0, 1)),
    (SUN_MORNING, ("IN_PROGRESS", 8, 1, 0, 1)),
    (SUN_BETWEEN, ("IN_PROGRESS", 5, 4, 0, 1)),
    (SUN_EVENING, ("MOSTLY_LOCKED", 2, 7, 0, 1)),
    (KICKOFFS["SNF"], ("MOSTLY_LOCKED", 1, 8, 0, 1)),
    (MON_BEFORE_MNF, ("MOSTLY_LOCKED", 1, 8, 0, 1)),
    (KICKOFFS["MNF"], ("COMPLETE", 0, 9, 0, 1)),
])
def test_each_player_locks_at_his_own_kickoff_and_the_week_state_follows(at, expected):
    result = evaluate(at)
    assert counts(result) == expected
    for name, view in by_player(result).items():
        team = next(row["nfl_team"] for row in week_roster() if row["player"] == name)
        state = "BYE" if team == "CHI" else "LOCKED" if KICKOFFS[WINDOW[team]] <= at else "OPEN"
        assert (view["lock_status"]["state"], view["lock_status"]["decision_authority"]) == (state, True), name


def test_locked_starters_stay_and_locked_bench_players_cannot_enter():
    result = evaluate(SUN_BETWEEN)
    players = by_player(result)
    assert (slot_of(result, "QB")["status"], slot_of(result, "RB")["status"], slot_of(result, "RB")["recommended"]["player"]) == ("LOCKED", "LOCKED", "Chiefs RB")
    # Dolphins WR has the best weekly value on the bench, but his game started, so only open players are moved.
    assert pairs(result) == {("Packers WR", "Seahawks WR"), ("Rams RB", "Cowboys WR")}
    assert players["Dolphins WR"]["lock_status"]["impact"] == "Locked on your bench; cannot enter your lineup."
    assert players["Chiefs RB"]["lock_status"]["impact"] == "Locked in your lineup; no change is possible."
    assert result["summary"]["action_deadline"]["display"] == "Sun Nov 15 1:25 PM PST"


@pytest.mark.parametrize("values,action,status", [
    (True, "FLEX Packers WR over Cowboys WR", "ACTION REQUIRED"),
    (False, "Most players are locked. Review the 2 players with later kickoffs.", "REVIEW"),
])
def test_sunday_evening_hero_names_only_the_decision_that_is_still_open(values, action, status):
    result = evaluate(SUN_EVENING, roster=week_roster(values=values))
    summary, locks = result["summary"], result["lock_summary"]
    assert (summary["status"], summary["action"], summary["week_state"]) == (status, action, "MOSTLY_LOCKED")
    assert [entry["player"] for entry in locks["remaining_open_players"]] == ["Cowboys WR", "Packers WR"]
    assert [entry["player"] for entry in locks["actionable_open_players"]] == ["Cowboys WR", "Packers WR"]
    assert locks["earliest_remaining_kickoff"]["display"] == "Sun Nov 15 5:20 PM PST"
    assert locks["message"] == "7 roster players are locked after kickoff. Review the 2 players whose games have not started (next kickoff Sun Nov 15 5:20 PM PST)."
    assert pairs(result) == ({("Packers WR", "Cowboys WR")} if values else set())
    assert (summary["action_deadline"] or {}).get("display") == ("Sun Nov 15 5:20 PM PST" if values else None)


@pytest.mark.parametrize("at,status,action", [
    (KICKOFFS["SNF"], "READY", "Most players are locked. No lineup change remains possible for the players with later kickoffs."),
    (MON_BEFORE_MNF, "READY", "Most players are locked. No lineup change remains possible for the players with later kickoffs."),
    (KICKOFFS["MNF"], "WEEK COMPLETE", "No lineup changes remain this week."),
])
def test_no_lineup_action_remains_once_every_slot_is_locked(at, status, action):
    result = evaluate(at)
    assert (result["summary"]["status"], result["summary"]["action"], result["summary"]["action_deadline"]) == (status, action, None)
    assert result["changes"] == [] and result["moves"] == [] and result["lock_summary"]["actionable_open_count"] == 0
    assert result["summary"]["decision_confidence"] == {"state": "NOT_APPLICABLE", "reason": "4 starting slots are locked after kickoff; no start/sit comparison remains."}


def test_lock_summary_is_identical_in_any_roster_order():
    rows = week_roster()
    shuffled = list(rows)
    random.Random(7).shuffle(shuffled)
    results = [evaluate(SUN_EVENING, roster=order) for order in (rows, list(reversed(rows)), shuffled)]
    assert all(result["lock_summary"] == results[0]["lock_summary"] for result in results)
    assert {result["summary"]["action"] for result in results} == {"FLEX Packers WR over Cowboys WR"}


@pytest.mark.parametrize("change,rows,state,blocker", [
    ({}, None, "BYE", None),
    ({"weekly_evidence": {"bye": {"authoritative": False}}}, None, "LOCK_UNVERIFIED", "BYE_EVIDENCE_UNVERIFIED"),
    ({}, [], "LOCK_UNVERIFIED", "SCHEDULE_UNAVAILABLE"),
    ({"is_bye": False}, None, "LOCK_UNVERIFIED", "SCHEDULE_GAME_NOT_FOUND"),
])
def test_bye_needs_bye_evidence_and_a_week_schedule_without_his_team(change, rows, state, blocker):
    bears = {**player("Bears RB", "RB", "CHI", None, bye=True), **change}
    lock = build_roster_game_locks([bears], schedule_rows=schedule() if rows is None else rows, season=2026, week=10, now=SUN_MORNING,
                                   max_age_seconds=FIXTURE_MAX_AGE)["players"]["Bears RB"]
    assert (lock["state"], lock["blocker"], lock["kickoff_utc"], lock["decision_authority"]) == (state, blocker, None, state == "BYE")


def test_bye_starter_is_moved_out_while_his_teammates_games_are_open():
    roster = [{**row, **({"sleeper_current_starter": True, "sleeper_lineup_slot": "RB", "sleeper_lineup_index": 1} if row["player"] == "Bears RB"
                         else {"sleeper_current_starter": False, "sleeper_lineup_slot": None, "sleeper_lineup_index": None} if row["player"] == "Chiefs RB" else {})}
              for row in week_roster()]
    result = evaluate(SUN_MORNING, roster=roster)
    bears = by_player(result)["Bears RB"]["lock_status"]
    assert (bears["state"], bears["game_text"], bears["kickoff_text"]) == ("BYE", "BYE", "No game this week")
    assert bears["impact"] == "Cannot score this week; move him out of your lineup."
    assert slot_of(result, "RB")["status"] == "REPLACEMENT_REQUIRED" and ("Rams RB", "Bears RB") in pairs(result)


def test_unverified_starter_stays_and_unverified_bench_player_cannot_enter():
    result = evaluate(THU_BEFORE_TNF, skip=("DAL", "GB"))
    players, locks = by_player(result), result["lock_summary"]
    flex = slot_of(result, "FLEX")
    assert (flex["status"], flex["recommended"]["player"]) == ("LOCK_UNVERIFIED", "Cowboys WR")
    assert "Packers WR" not in {change["start"]["player"] for change in result["changes"]} and players["Packers WR"]["availability_reason"] == "LOCK_UNVERIFIED"
    assert players["Cowboys WR"]["lock_status"]["impact"] == "Kept in your lineup until his kickoff can be verified."
    assert players["Packers WR"]["lock_status"]["impact"] == "Not recommended into your lineup until his kickoff can be verified."
    assert counts(result) == ("LOCK_COVERAGE_INCOMPLETE", 7, 0, 2, 1) and locks["material_unverified_count"] == 2
    # Verified open decisions still lead the hero, with their own deadline.
    assert result["summary"]["action"] == "START Dolphins WR over Seahawks WR" and result["summary"]["action_deadline"]["display"] == "Sun Nov 15 10:00 AM PST"


def test_verified_open_decisions_lead_the_hero_before_an_unverified_lock_check():
    roster = week_roster({"Cowboys WR": "Out"}, skip=("DAL",))
    thursday = evaluate(THU_BEFORE_TNF, roster=roster, skip=("DAL",))
    assert thursday["summary"]["action"] == "START Rams RB over Chiefs RB"
    assert [decision["status"] for decision in thursday["attention"]][-1:] == ["LOCK_UNVERIFIED"]
    sunday = evaluate(SUN_EVENING, roster=roster, skip=("DAL",))
    assert (sunday["summary"]["action"], sunday["summary"]["action_deadline"]) == ("Check Cowboys WR (Out) in Sleeper: kickoff lock unverified", None)


def test_lock_coverage_incomplete_states_the_supported_subset_instead_of_a_blanket_warning():
    result = evaluate(SUN_EVENING, skip=("DAL",))
    summary, locks = result["summary"], result["lock_summary"]
    assert counts(result) == ("LOCK_COVERAGE_INCOMPLETE", 1, 7, 1, 1)
    assert locks["message"] == ("7 players are locked after kickoff, 1 remains open, and 1 is on bye. "
                                "Lock status for 1 player cannot be verified (no game was found for the player's team). Current assignments remain protected.")
    assert (summary["status"], summary["action"]) == ("LOCK COVERAGE INCOMPLETE", "Keep current assignments for players whose kickoff cannot be verified.")
    assert summary["biggest_risk"] == "Lock state for 1 player cannot be verified here; confirm in Sleeper before moving him."
    assert not any(notice["code"] in {"KICKOFF_LOCK_UNVERIFIED", "GAME_LOCKS"} for notice in result["notices"])


def test_unapproved_freshness_threshold_keeps_kickoffs_as_display_only_context():
    result = evaluate(SUN_EVENING, max_age=None)
    locks = result["lock_summary"]
    assert counts(result) == ("LOCK_COVERAGE_INCOMPLETE", 0, 0, 9, 1) and result["changes"] == []
    assert locks["schedule_authority"]["threshold_state"] == "UNAPPROVED" and locks["schedule_authority"]["setting"] == "SCHEDULE_EVIDENCE_MAX_AGE_SECONDS"
    assert (locks["display_context"]["past_count"], locks["display_context"]["future_count"], locks["display_context"]["decision_authority"]) == (7, 2, False)
    assert locks["message"] == ("1 player is on bye. 7 players appear past kickoff and 2 players appear not yet started, but these lock states cannot be verified "
                                "because schedule freshness is not approved (stored schedule 3 days old; kickoff times are display only). "
                                "Current assignments remain protected.")
    cowboys = by_player(result)["Cowboys WR"]
    assert (cowboys["lock"]["kickoff_utc"], cowboys["lock"]["decision_authority"], cowboys["lock"]["display_context"]["decision_authority"]) == (None, False, False)
    assert cowboys["lock_status"]["kickoff_text"] == "Stored kickoff Sun Nov 15 5:20 PM PST (unverified; appears not yet started)"
    assert result["summary"]["action"] == "Keep current assignments for players whose kickoff cannot be verified."
    assert by_player(result)["Bears RB"]["lock_status"]["state"] == "BYE"


@pytest.mark.parametrize("rows,blocker,threshold,context", [
    (schedule(recorded=datetime(2026, 11, 1, 9, 0, tzinfo=UTC)), "SCHEDULE_DATA_STALE", "APPROVED", True),
    (schedule(source="csv:schedule.csv"), "SCHEDULE_SOURCE_NOT_AUTOMATED", "UNVERIFIED", False),
])
def test_stale_or_non_automated_schedules_never_authorize_a_lock(rows, blocker, threshold, context):
    result = evaluate(SUN_EVENING, rows=rows)
    views = [view for view in result["players"] if view["player"] != "Bears RB"]
    assert {(view["lock"]["state"], view["lock"]["blocker"], view["lock"]["kickoff_utc"]) for view in views} == {("LOCK_UNVERIFIED", blocker, None)}
    assert all(bool(view["lock"]["display_context"]) is context for view in views)
    assert result["lock_summary"]["schedule_authority"]["threshold_state"] == threshold and result["changes"] == []


def test_consensus_ranks_and_projections_never_change_lock_state():
    roster = week_roster(values=False)
    ranks = {"source": "FantasyPros consensus via DynastyProcess", "last_successful_refresh": SUN_EVENING.isoformat(),
             "horizons": {"this_week": {"state": "AVAILABLE", "max_age_seconds": 172800, "diagnostics": [], "ranks": {
                 row["player"]: {"player_id": row["player"], "position": row["position"], "ecr": float(rank), "source_date": "2026-11-15", "horizon": "this_week",
                                 "scoring": "PPR", "season": 2026, "week": 10, "game_evidence": None} for rank, row in enumerate(roster, start=1)}}}}
    projections = {"state": "AVAILABLE", "blockers": [], "players": {row["player"]: {
        "state": "PRELIMINARY", "evidence_level": "PRELIMINARY", "recommendation_impact": "INFORMATIONAL_ONLY", "sleeper_id": row["player"], "projected_ppg": 12.0,
        "source": "JerryGM jgm_baseline", "scoring_format": "ppr", "season": 2026, "week": 10, "source_record_time": RECORDED.isoformat(),
        "retrieved_at": RECORDED.isoformat(), "freshness_state": "UNAVAILABLE", "stat_line": {"receptions": 5.0}, "data_through_week": 9, "blockers": []}
        for row in roster}}
    plain = evaluate(SUN_EVENING, roster=roster)
    informed = evaluate(SUN_EVENING, roster=roster, consensus_ranks=ranks, provider_projections=projections, consensus_authority=True)
    assert counts(informed) == counts(plain) == ("MOSTLY_LOCKED", 2, 7, 0, 1)
    assert {view["player"]: view["lock"]["state"] for view in informed["players"]} == {view["player"]: view["lock"]["state"] for view in plain["players"]}


def test_locked_out_starter_cannot_be_replaced_after_his_kickoff():
    roster = [*week_roster({"Jets QB": "Out"}), player("Giants QB", "QB", "NYG", 15.0)]
    before = evaluate(THU_BEFORE_TNF, roster=roster)
    assert slot_of(before, "QB")["status"] == "REPLACEMENT_REQUIRED" and ("Giants QB", "Jets QB") in pairs(before)
    assert before["summary"]["action_deadline"]["display"] == "Thu Nov 12 5:15 PM PST"
    after = evaluate(SUN_MORNING, roster=roster)
    qb = slot_of(after, "QB")
    assert (qb["status"], qb["recommended"]["player"]) == ("LOCKED", "Jets QB") and not any(start == "Giants QB" for start, _sit in pairs(after))
    assert by_player(after)["Jets QB"]["lock_status"]["impact"] == "Locked in your lineup while listed Out; no replacement is possible after kickoff."


@pytest.mark.parametrize("status,week_state,readiness", [
    ("Out", "COMPLETE", "WEEK COMPLETE"),
    ("Questionable", "MOSTLY_LOCKED", "READY"),
])
def test_only_a_bench_player_who_can_play_keeps_the_week_open(status, week_state, readiness):
    result = evaluate(MON_BEFORE_MNF, roster=week_roster({"Packers WR": status}))
    assert (result["lock_summary"]["week_state"], result["summary"]["status"]) == (week_state, readiness)
    assert result["lock_summary"]["open_count"] == 1 and by_player(result)["Packers WR"]["lock_status"]["lineup_relevant"] is (status != "Out")
    if status == "Out":
        assert result["summary"]["action"] == "No lineup changes remain this week."
        assert "1 bench player with later kickoffs cannot play this week (Packers WR)." in result["lock_summary"]["message"]


def test_unverified_bench_player_who_cannot_play_does_not_block_coverage():
    result = evaluate(THU_BEFORE_TNF, roster=week_roster({"Packers WR": "Out"}, skip=("GB",)), skip=("GB",))
    locks = result["lock_summary"]
    assert counts(result) == ("PRE_KICKOFF", 8, 0, 1, 1) and locks["material_unverified_count"] == 0
    assert locks["message"].endswith("Lock status for 1 player cannot be verified (no game was found for the player's team); it does not affect your lineup.")


def test_team_page_shows_the_sunday_evening_lock_window():
    from app import app
    from flask import render_template

    result = evaluate(SUN_EVENING)
    with app.test_request_context("/team"):
        html = render_template("team.html", title="My Team", context={"mode": "LIVE"}, meta={"week": 10}, roster=[], league_settings={}, team_health={},
                               team_needs={}, roster_outlook={}, team_priority_action={}, opportunity_view={}, preliminary_matchup_context={}, weekly_risks=[],
                               lineup_snapshot={"counts": {}}, lineup_decision=result)
    assert "Decide before the Sun Nov 15 5:20 PM PST kickoff" in html and "<dt>Lineup locks</dt><dd>Mostly locked &middot; 2 open · 7 locked · 1 bye</dd>" in html
    assert "<strong>MOSTLY LOCKED</strong>" in html
    assert "Still open:</strong> Cowboys WR (FLEX, kickoff Sun Nov 15 5:20 PM PST), Packers WR (bench, kickoff Mon Nov 16 5:15 PM PST)" in html
    assert "Locked</span> Kickoff Sun Nov 15 10:00 AM PST" in html and "Bye</span> No game this week" in html
    assert "Lock unverified" not in html and "LOCKS UNVERIFIED" not in html and "<details open" not in html
