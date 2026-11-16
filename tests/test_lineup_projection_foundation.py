import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from services.game_lock import build_game_lock, build_roster_game_locks
from services.jerrygm_projections import JerryGMProjectionClient, build_projection_evidence, build_roster_projections
from services.league_scoring import league_score_stat_line
from services.lineup_decision_intelligence import build_lineup_decision
from services.lineup_projection import (
    best_projection_alternative,
    build_forward_validation_snapshots,
    build_player_projection,
    compare_projections,
    evidence_agreement,
    recent_workload,
    workload_summary,
)
from services.team_needs import league_settings_contract

NOW = datetime(2026, 11, 15, 17, 0, tzinfo=timezone.utc)
SOURCE = "automated:nflverse-schedules:games.csv.gz:sha256:fixture"
GENERATED = "2026-11-15T12:00:00+00:00"
FRESH_HEALTH = {"state": "AVAILABLE", "source": "Sleeper API", "freshness_state": "FRESH", "last_verified": NOW.isoformat()}
HEALTHY = {"state": "HEALTHY", "availability": "AVAILABLE", "label": "Active"}
OPEN_LOCK = {"state": "OPEN", "label": "Open", "kickoff_utc": "2026-11-15T18:00:00+00:00", "kickoff_display": "Sun Nov 15 10:00 AM PST"}
LEAGUE_SCORING = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -1.0, "rush_yd": 0.1, "rush_td": 6.0, "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0,
    "pass_2pt": 2.0, "rush_2pt": 2.0, "rec_2pt": 2.0, "fum_lost": -2.0, "fum": 0.0, "fum_rec_td": 6.0, "st_td": 0.0,
    "fgm_0_19": 3.0, "fgm_20_29": 3.0, "fgm_30_39": 3.0, "fgm_40_49": 4.0, "fgm_50_59": 5.0, "fgm_60p": 0.0, "fgmiss": 0.0, "xpm": 1.0,
    "sack": 1.0, "int": 2.0, "fum_rec": 2.0, "def_td": 6.0, "safe": 2.0, "blk_kick": 2.0, "def_st_td": 0.0, "def_st_fum_rec": 0.0, "ff": 0.0,
    "pts_allow_0": 10.0, "pts_allow_1_6": 7.0, "pts_allow_7_13": 4.0, "pts_allow_14_20": 1.0, "pts_allow_21_27": 0.0, "pts_allow_28_34": -1.0, "pts_allow_35p": -4.0,
}
QB_LINE = {"passYds": 250.0, "passTds": 2.0, "passInts": 1.0, "rushYds": 20.0, "rushTds": 0.0, "receptions": 0.0, "recYds": 0.0, "recTds": 0.0,
           "twoPt": 0.1, "fumblesLost": 0.5, "fumbleRecoveryTds": 0.0}
RB_LINE = {"rushYds": 60.0, "rushTds": 0.5, "receptions": 3.0, "recYds": 25.0, "recTds": 0.2, "fumblesLost": 0.1, "twoPt": 0.0,
           "passYds": 0.0, "passTds": 0.0, "passInts": 0.0, "fumbleRecoveryTds": 0.0}
DEF_LINE = {"defSacks": 2.0, "defInterceptions": 1.0, "defFumbleRecoveries": 0.5, "defFumblesForced": 0.8, "defTds": 0.2, "defReturnTds": 0.05,
            "defSafeties": 0.02, "defBlocks": 0.0, "defTwoPtReturns": 0.0, "pointsAllowed": 20.0, "yardsAllowed": 310.0}


def game(home, away, *, kickoff=NOW + timedelta(hours=3), recorded=NOW - timedelta(hours=2), source=SOURCE):
    return {"season": 2026, "week": 10, "home_team": home, "away_team": away, "game_time_utc": kickoff, "source": source,
            "source_recorded_at": recorded, "retrieved_at": recorded}


def roster_row(player_id, position, *, slot=None, index=None, status="Active", team="KC"):
    return {"player": f"P{player_id}", "position": position, "source_player_id": player_id, "nfl_team": team, "injury_status": status,
            "health_status_available": True, "opponent": "BUF", "is_bye": False, "weekly_score": None, "weekly_baseline": None, "matchup_modifier": 0.0,
            "injury_multiplier": 1.0, "sleeper_current_starter": slot is not None, "sleeper_lineup_slot": slot, "sleeper_lineup_index": index}


def evidence(**overrides):
    base = {"state": "PRELIMINARY", "projected_ppg": 15.0, "season": 2026, "week": 10, "source_record_time": GENERATED, "retrieved_at": "2026-11-15T13:00:00+00:00",
            "data_through_week": 9, "scoring_format": "ppr", "attribution": "JerryGM projections.", "provider_position": "RB", "provider_team": "KC",
            "gsis_id": "00-0000001", "roster_status": "active", "provider_availability": {"injury_status": None, "p_play": 0.97},
            "stat_line": dict(RB_LINE), "blockers": ["JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"]}
    return {**base, **overrides}


def project(supplied=None, **kwargs):
    kwargs.setdefault("lock", OPEN_LOCK)
    kwargs.setdefault("sleeper_team", "KC")
    kwargs.setdefault("sleeper_health", HEALTHY)
    return build_player_projection(evidence() if supplied is None else supplied, position=kwargs.pop("position", "RB"), scoring_settings=LEAGUE_SCORING,
                                   season=2026, week=10, **kwargs)


def view(player_id, value, *, position="RB", lock=None, availability="AVAILABLE", eligible=True, state="PRELIMINARY", generated=GENERATED,
         value_range=None, blocker=None, health="Active", **extra):
    projection = {"value": value, "value_range": value_range or ({"low": value, "high": value} if value is not None else None), "decision_eligible": eligible,
                  "evidence_state": state, "generated_at": generated, "blocker": blocker, "blockers": [blocker] if blocker else [],
                  "scoring_completeness": "COMPLETE" if value is not None else "PARTIAL" if value_range else "UNAVAILABLE", "confidence": {"state": "UNAVAILABLE"}}
    projection.update(extra.pop("projection_extra", {}))
    return {"player": f"Player {player_id}", "player_id": player_id, "identity_state": "RESOLVED", "position": position, "availability": availability,
            "lock": lock or dict(OPEN_LOCK), "projection": projection, "is_bye": False,
            "health": {"label": health, "status": health, "availability": "AVAILABLE" if availability == "AVAILABLE" else "UNCERTAIN"},
            "opportunity": {}, "matchup": {}, **extra}


# Schedule-owned kickoff locks

def test_schedule_lock_is_open_before_kickoff_and_locked_at_kickoff():
    rows = [game("KC", "BUF")]
    before = build_game_lock("KC", schedule_rows=rows, season=2026, week=10, now=NOW, max_age_seconds=86400)
    at_kickoff = build_game_lock("BUF", schedule_rows=rows, season=2026, week=10, now=NOW + timedelta(hours=3), max_age_seconds=86400)
    assert (before["state"], before["opponent"], before["venue"], before["kickoff_passed"]) == ("OPEN", "BUF", "HOME", False)
    assert before["kickoff_utc"] == "2026-11-15T20:00:00+00:00" and before["authority"] == "SCHEDULE_OWNED" and before["freshness_state"] == "FRESH"
    assert (at_kickoff["state"], at_kickoff["opponent"], at_kickoff["venue"], at_kickoff["kickoff_passed"]) == ("LOCKED", "KC", "AWAY", True)


@pytest.mark.parametrize("rows,max_age,blocker", [
    ([game("KC", "BUF")], None, "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED"),
    ([game("KC", "BUF", recorded=NOW - timedelta(days=42))], 86400, "SCHEDULE_DATA_STALE"),
    ([game("KC", "BUF", source="csv:schedule.csv")], 86400, "SCHEDULE_SOURCE_NOT_AUTOMATED"),
    ([game("KC", "BUF", kickoff=None)], 86400, "SCHEDULE_KICKOFF_UNAVAILABLE"),
    ([game("DAL", "NYG")], 86400, "SCHEDULE_GAME_NOT_FOUND"),
    ([game("KC", "BUF"), game("DEN", "KC")], 86400, "SCHEDULE_GAME_CONFLICT"),
    ([], 86400, "SCHEDULE_UNAVAILABLE"),
])
def test_unverifiable_kickoff_fails_closed_to_lock_unverified(monkeypatch, rows, max_age, blocker):
    monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    lock = build_game_lock("KC", schedule_rows=rows, season=2026, week=10, now=NOW, max_age_seconds=max_age)
    assert lock["state"] == "LOCK_UNVERIFIED" and lock["blocker"] == blocker and lock["reason"]


def test_bye_weeks_have_no_kickoff_and_team_codes_follow_sleeper():
    rows = [game("LA", "JAC")]
    rams = build_game_lock("LAR", schedule_rows=rows, season=2026, week=10, now=NOW, max_age_seconds=86400)
    jaguars = build_game_lock("JAX", schedule_rows=rows, season=2026, week=10, now=NOW, max_age_seconds=86400)
    bye = build_game_lock("KC", schedule_rows=rows, season=2026, week=10, now=NOW, is_bye=True, max_age_seconds=86400)
    contradicted = build_game_lock("LAR", schedule_rows=rows, season=2026, week=10, now=NOW, is_bye=True, max_age_seconds=86400)
    assert (rams["state"], rams["team"], rams["opponent"]) == ("OPEN", "LAR", "JAX") and jaguars["opponent"] == "LAR"
    assert (bye["state"], bye["no_game"], bye["kickoff_utc"], bye["decision_authority"]) == ("BYE", True, None, True)
    assert contradicted["state"] == "LOCK_UNVERIFIED" and contradicted["blocker"] == "SCHEDULE_BYE_CONFLICT"


def test_roster_locks_are_keyed_by_sleeper_id_including_team_defenses():
    roster = [{"source_player_id": "4046", "position": "QB", "nfl_team": "KC"}, {"source_player_id": "JAX", "position": "DEF", "nfl_team": None}]
    locks = build_roster_game_locks(roster, schedule_rows=[game("KC", "BUF"), game("JAX", "LA")], season=2026, week=10, now=NOW, max_age_seconds=86400)
    assert locks["state"] == "AVAILABLE" and locks["counts"] == {"OPEN": 2}
    assert locks["players"]["4046"]["opponent"] == "BUF" and locks["players"]["JAX"]["opponent"] == "LAR"
    sandbox = build_roster_game_locks(roster, schedule_rows=[], season=2026, week=10, now=NOW, mode="MOCK")
    assert sandbox["state"] == "NOT_APPLICABLE" and {lock["state"] for lock in sandbox["players"].values()} == {"NOT_APPLICABLE"}


def test_unverified_kickoff_pins_starters_and_withholds_every_lineup_change(monkeypatch):
    monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    roster = [roster_row("1", "RB", slot="RB", index=0, status="Out"), roster_row("2", "RB")]
    settings = league_settings_contract({"roster_positions": ["RB", "BN"], "scoring_settings": {"rec": 1.0}})
    unverified = build_roster_game_locks(roster, schedule_rows=[game("KC", "BUF")], season=2026, week=10, now=NOW)
    result = build_lineup_decision(roster, league_settings=settings, team_health=FRESH_HEALTH, season=2026, week=10, game_locks=unverified, now=NOW)
    decision = result["slots"][0]
    assert decision["status"] == "LOCK_UNVERIFIED" and decision["recommended"]["player"] == "P1" and result["changes"] == []
    assert decision["requires_attention"] and decision["decision_confidence"]["state"] == "INSUFFICIENT_EVIDENCE"
    assert "kickoff lock cannot be verified" in decision["why"] and "No schedule freshness threshold is approved" in decision["why"]
    assert {view["player"]: view["availability_reason"] for view in result["players"]}["P2"] == "LOCK_UNVERIFIED"
    assert result["summary"]["status"] == "MONITOR" and "kickoff lock unverified" in result["summary"]["action"]
    assert result["lock_summary"]["week_state"] == "LOCK_COVERAGE_INCOMPLETE" and result["lock_summary"]["unverified_count"] == 2
    verified = build_roster_game_locks(roster, schedule_rows=[game("KC", "BUF")], season=2026, week=10, now=NOW, max_age_seconds=86400)
    opened = build_lineup_decision(roster, league_settings=settings, team_health=FRESH_HEALTH, season=2026, week=10, game_locks=verified, now=NOW)
    assert [(change["start"]["player"], change["sit"]["player"]) for change in opened["changes"]] == [("P2", "P1")]


def test_missing_lock_evidence_fails_closed_live_and_does_not_apply_in_sandbox():
    roster = [roster_row("1", "RB", slot="RB", index=0), roster_row("2", "RB")]
    settings = league_settings_contract({"roster_positions": ["RB", "BN"], "scoring_settings": {"rec": 1.0}})
    live = build_lineup_decision(roster, league_settings=settings, team_health=FRESH_HEALTH, season=2026, week=10, now=NOW)
    assert {view["lock"]["state"] for view in live["players"]} == {"LOCK_UNVERIFIED"} and live["slots"][0]["status"] == "LOCK_UNVERIFIED"
    assert live["game_lock_basis"]["blockers"] == ["SCHEDULE_LOCK_NOT_SUPPLIED"] and live["game_lock_basis"]["supplied"] is False
    sandbox = build_lineup_decision(roster, league_settings=None, team_health=FRESH_HEALTH, mode="MOCK", season=2026, week=10, now=NOW)
    assert {view["lock"]["state"] for view in sandbox["players"]} == {"NOT_APPLICABLE"} and sandbox["game_lock_basis"]["state"] == "NOT_APPLICABLE"


def test_consensus_rank_is_context_only_by_default():
    roster = [roster_row("1", "RB", slot="RB", index=0), roster_row("2", "RB")]
    ranks = {"source": "FantasyPros consensus via DynastyProcess", "last_successful_refresh": NOW.isoformat(),
             "horizons": {"this_week": {"state": "AVAILABLE", "max_age_seconds": 172800, "diagnostics": [], "ranks": {
                 player_id: {"player_id": player_id, "position": "RB", "ecr": ecr, "source_date": "2026-11-15", "horizon": "this_week", "scoring": "PPR",
                             "season": 2026, "week": 10, "game_evidence": None} for player_id, ecr in (("1", 30.0), ("2", 5.0))}}}}
    settings = league_settings_contract({"roster_positions": ["RB", "BN"], "scoring_settings": {"rec": 1.0}})
    locks = build_roster_game_locks(roster, schedule_rows=[game("KC", "BUF")], season=2026, week=10, now=NOW, max_age_seconds=86400)
    result = build_lineup_decision(roster, league_settings=settings, team_health=FRESH_HEALTH, season=2026, week=10, consensus_ranks=ranks, game_locks=locks, now=NOW)
    assert result["changes"] == [] and result["slots"][0]["status"] == "UNRESOLVED"
    assert result["consensus_basis"]["used_for"] == "NONE" and result["consensus_basis"]["decision_authority"] is False
    assert {view["player"]: view["consensus_rank"]["recommendation_impact"] for view in result["players"]} == {"P1": "DISPLAY_ONLY", "P2": "DISPLAY_ONLY"}


# JerryGM free projections

class Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def jerrygm_response(*players):
    return {"season": 2026, "week": 10, "scoring": "ppr", "source": "jgm_baseline", "generatedAt": "2026-11-15T12:00:00Z", "dataThroughWeek": 9,
            "attribution": "JerryGM projections. Derived from openly licensed nflverse data.", "statLineCoverage": {"passYds": "modeled"}, "players": list(players)}


def jerrygm_player(sleeper_id, *, gsis, position, team, points, stat_line, **extra):
    return {"name": f"Player {sleeper_id or gsis}", "position": position, "team": team, "gsisId": gsis, "ids": {"sleeper": sleeper_id, "gsis": gsis},
            "projectedPPG": points, "statLine": stat_line, "rosterStatus": "active", "injuryStatus": None, "practiceStatus": None, "pPlay": 0.98,
            "expectedPPG": points * 0.9, "breakdown": {"paTierExpectedPPG": 2.14, "pointsAllowedSd": 9.9, "trailingPPG": 8.0}, **extra}


def test_jerrygm_evidence_keeps_the_stat_line_identity_and_display_only_availability():
    payload = jerrygm_response(jerrygm_player("4046", gsis="00-0033873", position="QB", team="KC", points=22.6, stat_line=QB_LINE, injuryStatus="Questionable"))
    player = build_projection_evidence(payload, ["4046"], season=2026, week=10, scoring="ppr", retrieved_at="2026-11-15T13:00:00Z")["4046"]
    assert player["stat_line"] == QB_LINE and player["stat_line_coverage"] == {"passYds": "modeled"}
    assert (player["gsis_id"], player["provider_position"], player["provider_team"], player["identity_method"]) == ("00-0033873", "QB", "KC", "EXACT_SLEEPER_ID")
    assert player["provider_availability"]["injury_status"] == "Questionable" and player["breakdown"] == {"paTierExpectedPPG": 2.14, "pointsAllowedSd": 9.9}
    assert player["state"] == "PRELIMINARY" and player["blockers"] == ["JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED"]
    defense = build_projection_evidence(jerrygm_response(jerrygm_player(None, gsis="DST-LA", position="DST", team="LA", points=8.0, stat_line=DEF_LINE)),
                                        ["DST-LA"], season=2026, week=10, scoring="ppr", retrieved_at="2026-11-15T13:00:00Z", id_type="gsis")["DST-LA"]
    assert defense["identity_method"] == "EXACT_GSIS_ID" and defense["projected_ppg"] == 8.0 and defense["stat_line"] == DEF_LINE


def test_roster_projections_request_team_defenses_by_their_documented_gsis_id():
    calls = []

    class Client:
        def fetch(self, ids, *, season, week, scoring, id_type="sleeper"):
            calls.append((list(ids), id_type))
            return {player_id: {"state": "PRELIMINARY", "projected_ppg": 7.5, "sleeper_id": player_id, "blockers": []} for player_id in ids}

    roster = [{"source_player_id": "4046", "position": "QB"}, {"source_player_id": "LAR", "position": "DEF", "nfl_team": "LAR"}]
    result = build_roster_projections(roster, season=2026, week=10, scoring="ppr", client=Client())
    assert calls == [(["4046"], "sleeper"), (["DST-LA"], "gsis")] and result["state"] == "AVAILABLE"
    assert {key: result["players"]["LAR"][key] for key in ("sleeper_id", "provider_id", "identity_method")} == {
        "sleeper_id": "LAR", "provider_id": "DST-LA", "identity_method": "TEAM_DEFENSE_GSIS_ID"}


def test_client_sends_the_gsis_identity_type_and_rejects_unsupported_types():
    seen = {}

    def opener(request, timeout):
        seen["query"] = parse_qs(urlparse(request.full_url).query)
        return Response(jerrygm_response(jerrygm_player(None, gsis="DST-LA", position="DST", team="LA", points=8.0, stat_line=DEF_LINE)))

    client = JerryGMProjectionClient(api_key="fixture-key", opener=opener, clock=lambda: NOW)
    result = client.fetch(["DST-LA"], season=2026, week=10, scoring="ppr", id_type="gsis")
    assert seen["query"]["idType"] == ["gsis"] and seen["query"]["ids"] == ["DST-LA"] and result["DST-LA"]["projected_ppg"] == 8.0
    with pytest.raises(ValueError, match="JERRYGM_ID_TYPE_UNSUPPORTED"):
        client.fetch(["DST-LA"], season=2026, week=10, scoring="ppr", id_type="name")


# Exact league rescoring

def test_offense_rescoring_applies_the_league_weights_not_the_provider_preset():
    result = league_score_stat_line(QB_LINE, LEAGUE_SCORING, position="QB")
    assert result["value"] == 18.2 and result["scoring_completeness"] == "COMPLETE" and result["missing_scoring_components"] == []
    assert league_score_stat_line(QB_LINE, {**LEAGUE_SCORING, "pass_int": -2.0}, position="QB")["value"] == 17.2


def test_kicker_long_field_goal_split_is_a_bounded_partial_range():
    line = {"fgMade0to19": 0.1, "fgMade20to29": 0.5, "fgMade30to39": 0.5, "fgMade40to49": 0.4, "fgMade50plus": 0.3, "patMade": 2.5}
    result = league_score_stat_line(line, LEAGUE_SCORING, position="K")
    assert result["value"] is None and result["value_range"] == {"low": 7.4, "high": 8.9} and result["scoring_completeness"] == "PARTIAL"
    assert [item["rule"] for item in result["missing_scoring_components"]] == ["fgm_50_59/fgm_60p/fgm_50p"]


def test_defense_rescoring_uses_the_tier_expectation_only_under_identical_tiers():
    result = league_score_stat_line(DEF_LINE, LEAGUE_SCORING, position="DEF", breakdown={"paTierExpectedPPG": 2.0})
    assert result["value_range"] == {"low": 6.94, "high": 7.94} and result["blocker"] == "LEAGUE_SCORING_PARTIAL"
    assert [item["rule"] for item in result["missing_scoring_components"]] == ["fum_rec/def_st_fum_rec"]
    other_tiers = league_score_stat_line(DEF_LINE, {**LEAGUE_SCORING, "pts_allow_0": 5.0}, position="DEF", breakdown={"paTierExpectedPPG": 2.0})
    assert other_tiers["value"] is None and other_tiers["value_range"] == {"low": 0.94, "high": 12.94}
    assert "pts_allow tiers" in [item["rule"] for item in other_tiers["missing_scoring_components"]]


def test_unreproducible_rules_or_missing_inputs_never_produce_a_value():
    unknown = league_score_stat_line(QB_LINE, {**LEAGUE_SCORING, "bonus_pass_yd_300": 3.0}, position="QB")
    assert unknown["value"] is None and unknown["value_range"] is None and unknown["blocker"] == "LEAGUE_SCORING_UNREPRODUCIBLE"
    assert league_score_stat_line(QB_LINE, {}, position="QB")["blocker"] == "LEAGUE_SCORING_UNAVAILABLE"
    assert league_score_stat_line(None, LEAGUE_SCORING, position="QB")["blocker"] == "PROJECTION_STAT_LINE_UNAVAILABLE"
    not_modeled = league_score_stat_line(QB_LINE, LEAGUE_SCORING, position="QB", coverage={"passInts": "notModeled"})
    assert not_modeled["value"] is None and "pass_int" in [item["rule"] for item in not_modeled["missing_scoring_components"]]


# Projection contract and gates

def test_projection_is_preliminary_and_decision_eligible_only_before_a_verified_kickoff():
    projection = project()
    assert (projection["evidence_state"], projection["value"], projection["decision_eligible"]) == ("PRELIMINARY", 15.5, True)
    assert projection["provider_points"] == 15.0 and projection["confidence"]["state"] == "UNAVAILABLE" and projection["recommendation_impact"] == "INFORMATIONAL_ONLY"
    for lock, blocker in (({"state": "LOCKED"}, "PROJECTION_GAME_STARTED"), ({"state": "LOCK_UNVERIFIED"}, "PROJECTION_KICKOFF_UNVERIFIED"),
                          ({"state": "OPEN", "kickoff_utc": "2026-11-15T12:30:00+00:00"}, "PROJECTION_RETRIEVED_AFTER_KICKOFF"),
                          ({"state": "OPEN", "no_game": True}, "PLAYER_HAS_NO_GAME")):
        gated = project(lock=lock)
        assert gated["decision_eligible"] is False and gated["blocker"] == blocker and gated["value"] == 15.5


@pytest.mark.parametrize("overrides,state,blocker", [
    ({"week": 9}, "BLOCKED", "PROJECTION_WEEK_MISMATCH"),
    ({"season": 2025}, "BLOCKED", "PROJECTION_SEASON_MISMATCH"),
    ({"data_through_week": 8}, "DEGRADED", "PROJECTION_DATA_THROUGH_WEEK_ROLLOVER_LAG"),
    ({"data_through_week": 6}, "UNAVAILABLE", "PROJECTION_DATA_THROUGH_WEEK_STALE"),
    ({"data_through_week": 10}, "BLOCKED", "PROJECTION_DATA_THROUGH_WEEK_AHEAD"),
    ({"state": "UNAVAILABLE", "projected_ppg": None, "blockers": ["JERRYGM_PLAYER_NOT_RETURNED"]}, "UNAVAILABLE", "JERRYGM_PLAYER_NOT_RETURNED"),
    ({"state": "STALE", "blockers": ["JERRYGM_STALE_HISTORICAL_ONLY"]}, "STALE", "JERRYGM_STALE_HISTORICAL_ONLY"),
    ({"provider_position": "WR"}, "BLOCKED", "PROJECTION_IDENTITY_CONFLICT"),
    ({"provider_team": "BUF"}, "BLOCKED", "PROJECTION_TEAM_CONFLICT"),
])
def test_projection_gates_fail_closed(overrides, state, blocker):
    projection = project(evidence(**overrides))
    assert projection["evidence_state"] == state and projection["blocker"] == blocker
    assert (projection["value"] is not None) == (state == "DEGRADED")


def test_identity_cross_checks_use_gsis_and_explicit_team_mapping():
    assert project(known_gsis_id="00-0000002")["blocker"] == "PROJECTION_IDENTITY_CONFLICT"
    assert project(evidence(provider_team="LA"), sleeper_team="LAR")["evidence_state"] == "PRELIMINARY"


def test_sleeper_owns_availability_when_the_provider_disagrees():
    zeroed = evidence(projected_ppg=0.0, provider_availability={"injury_status": "Out", "p_play": 0.0}, stat_line={key: 0.0 for key in RB_LINE})
    conflict = project(zeroed)
    assert (conflict["evidence_state"], conflict["blocker"], conflict["value"]) == ("BLOCKED", "PROVIDER_AVAILABILITY_CONFLICT", None)
    assert "Sleeper owns availability" in conflict["availability_disagreement"]
    doubtful = project(evidence(projected_ppg=0.0, provider_availability={"injury_status": "Doubtful"}),
                       sleeper_health={"state": "DOUBTFUL", "availability": "UNCERTAIN", "label": "Doubtful"})
    assert (doubtful["evidence_state"], doubtful["blocker"], doubtful["value"]) == ("UNAVAILABLE", "PROVIDER_PROJECTION_ZEROED_FOR_AVAILABILITY", None)
    lagged = project(evidence(provider_availability={"injury_status": "Questionable", "p_play": 0.0}))
    assert lagged["value"] == 15.5 and lagged["decision_eligible"] and "used unchanged" in lagged["availability_disagreement"]
    assert lagged["provider_availability"]["authority"] == "DISPLAY_ONLY"


# Projection comparisons

def test_projection_edge_is_a_close_call_that_never_authorizes_a_change():
    result = compare_projections(view("A", 12.4), view("B", 14.53))
    assert (result["state"], result["preferred"], result["projection_delta"]) == ("CLOSE_CALL", "ALTERNATIVE", 2.13)
    assert result["authorizes_lineup_change"] is False and result["recommendation_impact"] == "INFORMATIONAL_ONLY"
    assert "no validated action threshold" in result["reasons"][0]
    tie = compare_projections(view("A", 10.0), view("B", 10.0))
    assert (tie["state"], tie["preferred"], tie["projection_delta"]) == ("CLOSE_CALL", "TIE", 0.0)


def test_supported_comparison_requires_an_approved_threshold_and_clean_evidence():
    approved = {"id": "projection.edge.fixture.v1", "points": 3.0}
    assert compare_projections(view("A", 10.0), view("B", 15.0))["state"] == "CLOSE_CALL"
    assert compare_projections(view("A", 10.0), view("B", 15.0), action_threshold={"points": 3.0})["state"] == "CLOSE_CALL"
    supported = compare_projections(view("A", 10.0), view("B", 15.0), action_threshold=approved)
    assert supported["state"] == "SUPPORTED_COMPARISON" and supported["authorizes_lineup_change"] is False
    assert compare_projections(view("A", 10.0), view("B", 12.0), action_threshold=approved)["state"] == "CLOSE_CALL"
    assert compare_projections(view("A", 10.0), view("B", 15.0, state="DEGRADED"), action_threshold=approved)["state"] == "CLOSE_CALL"


@pytest.mark.parametrize("current,alternative,state,blocker", [
    (view("A", 10.0), view("B", None, eligible=False, blocker="JERRYGM_PLAYER_NOT_RETURNED"), "INSUFFICIENT_EVIDENCE", "JERRYGM_PLAYER_NOT_RETURNED"),
    (view("A", 10.0), view("B", 12.0, generated="2026-11-14T12:00:00+00:00"), "INSUFFICIENT_EVIDENCE", "PROJECTION_BOARD_MISMATCH"),
    (view("A", 10.0), view("B", None, value_range={"low": 9.0, "high": 11.0}), "INSUFFICIENT_EVIDENCE", "LEAGUE_SCORING_PARTIAL"),
    (view("A", 10.0, lock={"state": "LOCK_UNVERIFIED", "reason": "No threshold."}), view("B", 12.0), "BLOCKED", "LOCK_UNVERIFIED"),
    (view("A", 10.0), view("B", 12.0, lock={"state": "LOCKED"}), "BLOCKED", "GAME_LOCKED"),
    (view("A", 10.0, availability="UNAVAILABLE", health="Out"), view("B", 12.0), "BLOCKED", "CURRENT_STARTER_UNAVAILABLE"),
    (view("A", 10.0), view("B", None, eligible=False, state="BLOCKED", blocker="PROVIDER_AVAILABILITY_CONFLICT"), "BLOCKED", "CONTRADICTORY_EVIDENCE"),
    (view("A", 10.0), view("B", 12.0, identity_state="AMBIGUOUS"), "BLOCKED", "IDENTITY_UNRESOLVED"),
])
def test_missing_or_contradictory_evidence_never_becomes_a_projection_edge(current, alternative, state, blocker):
    result = compare_projections(current, alternative)
    assert result["state"] == state and blocker in result["blockers"] and result["projection_delta"] is None and result["preferred"] is None


def test_partial_ranges_compare_only_when_disjoint_and_best_alternative_prefers_eligible_projections():
    partial = view("B", None, value_range={"low": 9.0, "high": 10.5})
    result = compare_projections(view("A", 8.0), partial)
    assert (result["state"], result["preferred"], result["projection_delta"], result["delta_range"]) == ("CLOSE_CALL", "ALTERNATIVE", None, {"low": 1.0, "high": 2.5})
    unverified = view("C", 20.0, eligible=False, lock={"state": "LOCK_UNVERIFIED"})
    best, unscored = best_projection_alternative([unverified, partial, view("D", 9.5), view("E", None, eligible=False)])
    assert best["player_id"] == "D" and [item["player_id"] for item in unscored] == ["E"]
    assert best_projection_alternative([unverified])[0]["player_id"] == "C"


def test_flex_comparison_uses_one_league_points_scale_and_never_changes_the_lineup():
    scoring = {"rec": 1.0, "rec_yd": 0.1, "rush_yd": 0.1}
    roster = [roster_row("1", "RB", slot="FLEX", index=0), roster_row("2", "WR"), roster_row("3", "TE")]
    lines = {"1": ("RB", {"rushYds": 50.0, "receptions": 1.0, "recYds": 5.0}), "2": ("WR", {"rushYds": 0.0, "receptions": 5.0, "recYds": 70.0}),
             "3": ("TE", {"rushYds": 0.0, "receptions": 3.0, "recYds": 30.0})}
    projections = {"state": "AVAILABLE", "blockers": [], "players": {player_id: evidence(sleeper_id=player_id, provider_position=position, stat_line=line)
                                                                     for player_id, (position, line) in lines.items()}}
    opportunity = {"players": [{"source_player_id": "2", "state": "AVAILABLE", "opportunity_strength": {"state": "HIGH_OPPORTUNITY"},
                                "recent_workload": {"state": "AVAILABLE", "week": 9, "targets": 9.0, "receptions": 6.0}}]}
    locks = build_roster_game_locks(roster, schedule_rows=[game("KC", "BUF")], season=2026, week=10, now=NOW, max_age_seconds=86400)
    result = build_lineup_decision(roster, league_settings=league_settings_contract({"roster_positions": ["FLEX", "BN", "BN"], "scoring_settings": scoring}),
                                   team_health=FRESH_HEALTH, season=2026, week=10, provider_projections=projections, opportunity=opportunity,
                                   game_locks=locks, scoring_settings=scoring, now=NOW)
    comparison = result["slots"][0]["projection_comparison"]
    assert (comparison["current"]["player"], comparison["alternative"]["player"], comparison["projection_delta"]) == ("P1", "P2", 5.5)
    assert comparison["state"] == "CLOSE_CALL" and comparison["preferred"] == "ALTERNATIVE" and result["changes"] == []
    assert result["slots"][0]["decision"] == "FLEX" and result["projection_comparisons"][0]["slot"] == "FLEX"
    opportunity_domain = next(domain for domain in comparison["agreement"]["domains"] if domain["domain"] == "RECENT_OPPORTUNITY")
    assert opportunity_domain["state"] == "UNAVAILABLE" and "across positions" in opportunity_domain["detail"]
    assert {view["player"]: view["opportunity"]["workload"]["text"] for view in result["players"]}["P2"] == "Week 9: 9 targets · 6 receptions"
    assert result["forward_validation"]["state"] == "BUILT_NOT_PERSISTED" and len(result["forward_validation"]["snapshots"]) == 3


def test_evidence_agreement_reports_independent_domains_without_weighting():
    limited = {"state": "AVAILABLE", "strength": "LIMITED_OPPORTUNITY", "label": "Limited opportunity"}
    high = {"state": "AVAILABLE", "strength": "HIGH_OPPORTUNITY", "label": "High opportunity"}
    current, alternative = view("A", 10.0, opportunity=limited), view("B", 13.0, opportunity=high)
    agrees = evidence_agreement(current, alternative, compare_projections(current, alternative))
    assert agrees["state"] == "AGREES" and set(agrees) == {"state", "domains", "contradictions", "label", "recommendation_impact", "method"}
    assert [domain["domain"] for domain in agrees["domains"]] == ["PROJECTION", "RECENT_OPPORTUNITY", "MATCHUP_CONTEXT", "GAME_ENVIRONMENT", "AVAILABILITY"]
    assert next(domain for domain in agrees["domains"] if domain["domain"] == "GAME_ENVIRONMENT")["state"] == "UNSUPPORTED"
    questionable = view("B", 13.0, availability="UNCERTAIN", health="Questionable")
    assert evidence_agreement(view("A", 10.0), questionable, compare_projections(view("A", 10.0), questionable))["state"] == "MIXED"
    assert evidence_agreement(view("A", 10.0), view("B", 13.0), compare_projections(view("A", 10.0), view("B", 13.0)))["state"] == "INSUFFICIENT_EVIDENCE"
    disputed = view("B", 13.0, projection_extra={"availability_disagreement": "Provider play probability is zero."})
    contradictory = evidence_agreement(view("A", 10.0), disputed, compare_projections(view("A", 10.0), disputed))
    assert contradictory["state"] == "CONTRADICTORY" and contradictory["contradictions"] == ["Player B: Provider play probability is zero."]


# Recent opportunity facts

def test_recent_workload_states_published_facts_and_withholds_invalid_rows():
    rows = [{"week": 3, "season": 2026, "carries": 12, "targets": 2, "receptions": 1.0},
            {"week": 4, "season": 2026, "carries": 17, "targets": 3, "receptions": 2.0, "target_share": 0.1, "red_zone_share": None,
             "source": "automated:nflverse", "retrieved_at": datetime(2026, 10, 6, tzinfo=timezone.utc), "freshness_state": "STALE"}]
    snaps = {"state": "STALE", "blockers": ["SNAP_SHARE_EVIDENCE_STALE"], "rows": [{"week": 4, "snap_share": 0.96}]}
    stale = recent_workload({"state": "BLOCKED", "blockers": ["OPPORTUNITY_DATA_STALE", "OPPORTUNITY_EVIDENCE_NOT_CURRENT"], "rows": rows}, snaps)
    assert (stale["state"], stale["week"], stale["carries"], stale["snap_share"], stale["retrieved_at"]) == ("STALE", 4, 17.0, 0.96, "2026-10-06T00:00:00+00:00")
    summary = workload_summary(stale)
    assert summary["text"] == "Last published Week 4 (stale): 17 carries · 3 targets · 2 receptions · 96% snap share · 10% target share"
    assert summary["decision_effect"] == "INFORMATIONAL_ONLY" and "goal-line carries" in summary["unsupported"]
    invalid = recent_workload({"state": "BLOCKED", "blockers": ["OPPORTUNITY_CONTRADICTORY_PLAYER_WEEK"], "rows": rows}, snaps)
    assert invalid["state"] == "BLOCKED" and invalid["week"] is None and workload_summary(invalid)["text"] == "Recent workload unavailable"
    current = recent_workload({"state": "AVAILABLE", "blockers": [], "rows": [{"week": 9, "carries": 1, "targets": 1}]})
    assert workload_summary(current)["text"] == "Week 9: 1 carry · 1 target"


# Forward-validation snapshots

def test_forward_validation_snapshots_cover_only_pre_kickoff_players_and_are_not_persisted():
    open_view = view("A", 10.0)
    others = [view("B", 9.0, lock={"state": "LOCKED"}), view("C", 8.0, lock={"state": "LOCK_UNVERIFIED"}), view("D", None, lock={"state": "OPEN", "no_game": True})]
    decisions = [{"slot": "RB", "recommended": open_view, "current": open_view, "projection_comparison": {"state": "CLOSE_CALL", "current": {"player_id": "A"}}}]
    result = build_forward_validation_snapshots([open_view, *others], decisions, season=2026, week=10, captured_at=NOW)
    assert result["state"] == "BUILT_NOT_PERSISTED" and [snapshot["decision_subject"] for snapshot in result["snapshots"]] == ["sleeper:A"]
    assert {item["reason"] for item in result["skipped"]} == {"LOCK_LOCKED", "LOCK_LOCK_UNVERIFIED", "NO_GAME"}
    snapshot = result["snapshots"][0]
    assert snapshot["decision_effect"] == "NONE" and result["persistence"]["state"] == "NOT_PERSISTED" and result["decision_effect"] == "NONE"
    assert snapshot["decision_output"]["league_scored_projection"] == 10.0 and snapshot["decision_output"]["comparison"]["state"] == "CLOSE_CALL"
    later = build_forward_validation_snapshots([open_view, *others], decisions, season=2026, week=10, captured_at=NOW + timedelta(minutes=5))
    assert later["snapshots"][0]["snapshot_id"] == snapshot["snapshot_id"]


def test_week_schedule_reader_selects_the_utc_kickoff():
    import owner_operations

    class Cursor:
        def execute(self, query, params=None):
            self.query, self.params = query, params

        def fetchall(self):
            return [("KC", "BUF", None, SOURCE, NOW, NOW, NOW + timedelta(hours=3))]

    cursor = Cursor()
    (row,) = owner_operations.read_week_schedule_rows(cursor, 2026, 10)
    assert "game_time_utc" in cursor.query and cursor.params == (2026, 10) and row["game_time_utc"] == NOW + timedelta(hours=3)
