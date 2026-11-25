from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock

import pytest

from services.dynastyprocess_rankings import evaluate, read_cached_rankings, refresh, refresh_rankings
from services.waiver_roster_decision import ranking_horizon_summary, ros_player_value

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
STATE = {"season": "2026", "week": 4, "season_type": "regular", "season_start_date": "2026-09-10"}


def snapshot():
    identity = {"fantasypros_id": "fp-1", "sleeper_id": "s-1", "position": "WR"}
    weekly = {"page": "ppr-wr", "fantasypros_id": "fp-1", "ecr": "12.5", "scrape_date": "2026-10-03", "player_game_kickoff_ts": str(datetime(2026, 10, 4, 17, tzinfo=timezone.utc).timestamp())}
    ros = {"fp_page": "/nfl/rankings/ros-ppr-wr.php", "id": "fp-1", "ecr": "20", "scrape_date": "2026-10-02"}
    return {"artifacts": {"db_playerids.csv": {"rows": [identity]}, "fp_latest_weekly.csv": {"rows": [weekly]}, "db_fpecr_latest.csv": {"rows": [ros]}}, "last_successful_refresh": NOW.isoformat()}


def test_scoped_ranks_reject_stale_wrong_week_and_duplicate_identity():
    data = snapshot()
    assert evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]["s-1"]["ecr"] == 12.5
    assert evaluate(data, STATE, NOW)["horizons"]["rest_of_season"]["ranks"]["s-1"]["ecr"] == 20
    assert not evaluate(data, {**STATE, "week": 5}, NOW)["horizons"]["this_week"]["ranks"]
    assert not evaluate(data, STATE, NOW + timedelta(days=8))["horizons"]["rest_of_season"]["ranks"]
    assert not evaluate(data, {**STATE, "season_type": "off"}, NOW)["horizons"]["this_week"]["ranks"]
    data["artifacts"]["db_playerids.csv"]["rows"] *= 2
    assert not evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]


def test_expert_rank_range_is_published_and_invalid_values_never_reject_the_rank():
    data = snapshot()
    weekly = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    weekly.update(best="9", worst="16", sd="2.1")
    row = evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]["s-1"]
    assert (row["expert_best_rank"], row["expert_worst_rank"], row["expert_rank_sd"]) == (9.0, 16.0, 2.1)
    weekly.update(best="", worst="nan", sd="-1")
    row = evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]["s-1"]
    assert row["ecr"] == 12.5 and (row["expert_best_rank"], row["expert_worst_rank"], row["expert_rank_sd"]) == (None, None, None)


def test_kicker_alias_and_defense_team_ids_are_not_false_identity_failures():
    data = snapshot()
    data["artifacts"]["db_playerids.csv"]["rows"][0]["position"] = "PK"
    weekly = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    weekly["page"] = "k"
    ros = data["artifacts"]["db_fpecr_latest.csv"]["rows"][0]
    ros["fp_page"] = "/nfl/rankings/ros-k.php"
    assert evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]["s-1"]["position"] == "K"
    weekly.update(page="dst", fantasypros_id="defense", team="SEA")
    ros.update(fp_page="/nfl/rankings/ros-dst.php", id="defense", team="SEA")
    catalog = {"SEA": {"team": "SEA", "position": "DEF"}}
    assert evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]["ranks"]["SEA"]["position"] == "DEF"
    assert not evaluate(data, STATE, NOW)["horizons"]["this_week"]["ranks"]


def test_missing_kickoff_is_not_reported_as_invalid_rank():
    data = snapshot()
    row = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    row["player_game_kickoff_ts"] = "NA"
    result = evaluate(data, STATE, NOW)["horizons"]["this_week"]
    assert result["diagnostics"][0]["reason"] == "KICKOFF_UNAVAILABLE"
    assert result["diagnostics"][0]["raw_ecr"] == "12.5"
    assert result["diagnostics"][0]["classification"] == "PENDING_VERIFICATION"
    assert result["reconciliation"]["reconciled"] is True
    row["player_game_kickoff_ts"] = str(datetime(2026, 10, 4, 17, tzinfo=timezone.utc).timestamp())
    row["ecr"] = "NaN"
    assert evaluate(data, STATE, NOW)["horizons"]["this_week"]["diagnostics"][0]["reason"] == "Consensus rank is invalid"


def test_missing_kickoff_retains_verified_sleeper_team_without_claiming_unavailability():
    data = snapshot()
    row = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    row.update(player_game_kickoff_ts="NA", team="FA", player_name="Healthy Player")
    catalog = {"s-1": {"team": "LAR", "status": "Active", "injury_status": None}}
    result = evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]
    diagnostic = result["diagnostics"][0]
    assert diagnostic["sleeper_check"]["team"] == "LAR"
    assert diagnostic["classification"] == "PENDING_VERIFICATION"
    assert diagnostic["raw_ecr"] == "12.5"
    assert result["reconciliation"]["supported_scope_rows"] == 1
    assert result["reconciliation"]["review_records"] == 1


def test_missing_provider_id_retains_research_candidates_without_guessing_rank_identity():
    data = snapshot()
    row = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    row.update(fantasypros_id="new-provider", player_name="Active Player")
    catalog = {"new-sleeper": {"full_name": "Active Player", "position": "WR", "team": "LAR", "status": "Active", "injury_status": None}}
    result = evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]
    assert result["ranks"] == {}
    diagnostic = result["diagnostics"][0]
    assert diagnostic["reason"] == "PROVIDER_ID_ABSENT_FROM_CROSSWALK"
    assert diagnostic["investigation_candidates"][0]["player_id"] == "new-sleeper"
    assert diagnostic["investigation_candidates"][0]["method"] == "NAME_POSITION_RESEARCH_ONLY"
    assert diagnostic["classification"] == "PENDING_VERIFICATION"


def test_owner_approved_contextual_match_requires_unique_name_position_and_team():
    data = snapshot()
    row = data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]
    row.update(fantasypros_id="new-provider", player_name="Tyler Loop", page="k", team="BAL")
    record = {"full_name": "Tyler Loop", "position": "K", "team": "BAL", "status": "Active", "injury_status": None}
    catalog = {"12711": record}
    result = evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]
    assert result["ranks"]["12711"]["identity_method"] == "OWNER_APPROVED_UNIQUE_NAME_POSITION_TEAM"
    assert result["ranks"]["12711"]["provider_id"] == "new-provider"
    assert result["reconciliation"]["reconciled"] is True
    assert not evaluate(data, STATE, NOW, sleeper_catalog={"12711": {**record, "team": "LAR"}})["horizons"]["this_week"]["ranks"]
    assert not evaluate(data, STATE, NOW, sleeper_catalog={"12711": {**record, "position": "WR"}})["horizons"]["this_week"]["ranks"]
    assert not evaluate(data, STATE, NOW, sleeper_catalog={"12711": record, "duplicate": record})["horizons"]["this_week"]["ranks"]
    data["artifacts"]["db_playerids.csv"]["rows"] = [{"fantasypros_id": "new-provider", "sleeper_id": "one", "position": "K"}, {"fantasypros_id": "new-provider", "sleeper_id": "two", "position": "K"}]
    assert not evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]["ranks"]


def test_missing_kickoff_requires_exact_identity_and_unique_fresh_team_evidence():
    data = snapshot()
    rows = data["artifacts"]["fp_latest_weekly.csv"]["rows"]
    player = rows[0]
    original_kickoff = player["player_game_kickoff_ts"]
    player.update(player_game_kickoff_ts="NA", team="FA")
    for provider_id in ("support-1", "support-2"):
        rows.append({**player, "fantasypros_id": provider_id, "team": "LAR", "player_game_kickoff_ts": original_kickoff})
    catalog = {"s-1": {"team": "LAR", "position": "WR", "status": "Active"}}
    result = evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]
    assert result["ranks"]["s-1"]["game_evidence"]["publisher_team"] == "FA"
    assert result["ranks"]["s-1"]["game_evidence"]["sleeper_team"] == "LAR"
    assert result["ranks"]["s-1"]["game_evidence"]["supporting_source_player_count"] == 2
    rows[2]["player_game_kickoff_ts"] = str(float(original_kickoff) + 3600)
    assert "s-1" not in evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]["ranks"]
    rows[2]["player_game_kickoff_ts"] = original_kickoff
    rows[1]["scrape_date"] = rows[2]["scrape_date"] = "2026-09-01"
    assert "s-1" not in evaluate(data, STATE, NOW, sleeper_catalog=catalog)["horizons"]["this_week"]["ranks"]
    assert "s-1" not in evaluate(data, STATE, NOW, sleeper_catalog={})["horizons"]["this_week"]["ranks"]
    no_team = {"s-1": {"team": None, "position": "WR", "status": "Active", "injury_status": None}}
    diagnostic = evaluate(data, STATE, NOW, sleeper_catalog=no_team)["horizons"]["this_week"]["diagnostics"][0]
    assert diagnostic["reason"] == "KICKOFF_CURRENT_TEAM_NOT_SUPPLIED"
    assert diagnostic["classification"] == "PENDING_VERIFICATION"
    assert diagnostic["sleeper_check"]["status"] == "Active"


def test_failed_refresh_keeps_source_age_and_reports_failure(tmp_path):
    path = tmp_path / "rankings.json"
    original = snapshot()
    path.write_text(json.dumps(original))
    def fail(url):
        raise OSError("offline")
    updated = refresh(path, fetch=fail, now=NOW + timedelta(days=8), force=True)
    assert updated["last_successful_refresh"] == original["last_successful_refresh"]
    assert updated["refresh_error"]
    ros = evaluate(updated, STATE, NOW + timedelta(days=8))["horizons"]["rest_of_season"]
    assert (ros["ranks"], ros["latest_source_date"], ros["freshness_state"]) == ({}, "2026-10-02", "STALE")
    result = read_cached_rankings(path, STATE, now=NOW + timedelta(days=8))
    assert result["last_successful_refresh"] == original["last_successful_refresh"]
    assert result["refresh_error"]
    assert result["cache_freshness_state"] == "STALE"


def test_cached_read_never_acquires_and_publishes_cache_age(tmp_path, monkeypatch):
    from services import dynastyprocess_rankings

    path = tmp_path / "rankings.json"
    path.write_text(json.dumps(snapshot()))
    acquire = Mock(side_effect=AssertionError("cached read attempted a refresh"))
    monkeypatch.setattr(dynastyprocess_rankings, "acquire", acquire)

    result = read_cached_rankings(path, STATE, now=NOW + timedelta(hours=2))

    assert result["cache_missing"] is False
    assert result["cache_age_seconds"] == 7200
    assert result["cache_freshness_state"] == "FRESH"
    assert result["horizons"]["this_week"]["ranks"]["s-1"]["ecr"] == 12.5
    acquire.assert_not_called()


def test_missing_and_future_dated_cache_fail_closed(tmp_path):
    path = tmp_path / "missing.json"
    missing = read_cached_rankings(path, STATE, now=NOW)
    assert missing["cache_missing"] is True
    assert missing["cache_freshness_state"] == "UNAVAILABLE"
    assert missing["horizons"]["this_week"]["state"] == "UNAVAILABLE"

    future = snapshot()
    future["last_successful_refresh"] = (NOW + timedelta(minutes=1)).isoformat()
    path.write_text(json.dumps(future))
    result = read_cached_rankings(path, STATE, now=NOW)
    assert result["cache_age_seconds"] is None
    assert result["cache_freshness_state"] == "UNAVAILABLE"


def test_forced_refresh_updates_cache_even_when_recent(tmp_path, monkeypatch):
    from services import dynastyprocess_rankings

    acquire = Mock(return_value=snapshot())
    monkeypatch.setattr(dynastyprocess_rankings, "acquire", acquire)
    path = tmp_path / "rankings.json"
    path.write_text(json.dumps({**snapshot(), "last_attempt": NOW.isoformat()}))

    result = refresh_rankings(path, STATE, now=NOW + timedelta(minutes=1), force=True)

    assert acquire.call_count == 1
    assert result["last_successful_refresh"] == (NOW + timedelta(minutes=1)).isoformat()
    assert result["cache_freshness_state"] == "FRESH"


def test_on_use_refresh_reuses_recent_snapshot_but_refreshes_after_break_or_week_change(tmp_path, monkeypatch):
    from services import dynastyprocess_rankings
    acquire = Mock(side_effect=lambda fetch: snapshot())
    monkeypatch.setattr(dynastyprocess_rankings, "acquire", acquire)
    path = tmp_path / "rankings.json"
    refresh(path, now=NOW, scope="2026:regular:4")
    assert acquire.call_count == 1
    refresh(path, now=NOW + timedelta(minutes=5), scope="2026:regular:4")
    assert acquire.call_count == 1
    refresh(path, now=NOW + timedelta(minutes=10), scope="2026:regular:5")
    assert acquire.call_count == 2
    updated = refresh(path, now=NOW + timedelta(days=8), scope="2026:regular:5")
    assert acquire.call_count == 3
    assert updated["last_successful_refresh"] == (NOW + timedelta(days=8)).isoformat()
    assert not evaluate(updated, STATE, NOW + timedelta(days=8))["horizons"]["this_week"]["ranks"]

KICKER = {"full_name": "Tyler Loop", "position": "K", "team": "BAL", "status": "Active", "injury_status": None}


def ros_view(result, player_id="s-1", position="WR", *, full_ppr=True):
    summary = ranking_horizon_summary(result, "rest_of_season", full_ppr=full_ppr)
    return summary, ros_player_value(summary, result, player_id, position, season=2026)


def with_contextual_kicker():
    """Adds an uncrosswalked ROS kicker row next to the crosswalked WR, so the horizon itself stays available."""
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"].append(
        {"fp_page": "/nfl/rankings/ros-k.php", "id": "new-provider", "player": "Tyler Loop", "team": "BAL", "ecr": "6", "scrape_date": "2026-10-02"})
    return data


def test_fresh_ros_rank_is_available_through_the_exact_sleeper_crosswalk():
    result = evaluate(snapshot(), STATE, NOW)
    horizon = result["horizons"]["rest_of_season"]
    row = horizon["ranks"]["s-1"]
    assert (horizon["state"], horizon["freshness_state"], horizon["latest_source_date"], horizon["latest_source_age_seconds"]) == ("AVAILABLE", "FRESH", "2026-10-02", 129600)
    assert (row["ecr"], row["scoring"], row["week"], row["provider_id"], row["identity_method"]) == (20.0, "PPR", None, "fp-1", "PUBLISHED_PROVIDER_CROSSWALK")
    summary, value = ros_view(result)
    assert (summary["state"], summary["source_date"], summary["max_age_seconds"], summary["ranked_by_position"]) == ("AVAILABLE", "2026-10-02", 604800, {"WR": 1})
    assert (value["evidence_state"], value["ros_ecr"], value["identity_method"], value["freshness_state"]) == ("RANKED", 20.0, "PUBLISHED_PROVIDER_CROSSWALK", "FRESH")


def test_stale_ros_source_is_never_rest_of_season_authority():
    summary, value = ros_view(evaluate(snapshot(), STATE, NOW + timedelta(days=8)))
    assert (summary["state"], summary["blocker"], summary["source_date"]) == ("STALE", "SOURCE_STALE", "2026-10-02")
    assert summary["reason"] == "The newest rest-of-season consensus was published 2026-10-02, 9 days 12 hours ago; the limit is 7 days."
    assert (value["evidence_state"], value["ros_ecr"]) == ("STALE", None)


def test_redownloading_an_old_ros_source_renews_retrieval_but_not_freshness(tmp_path, monkeypatch):
    from services import dynastyprocess_rankings

    monkeypatch.setattr(dynastyprocess_rankings, "acquire", Mock(return_value=snapshot()))
    later = NOW + timedelta(days=8)
    result = refresh_rankings(tmp_path / "rankings.json", STATE, now=later, force=True)
    assert (result["last_successful_refresh"], result["cache_freshness_state"]) == (later.isoformat(), "FRESH")
    summary, value = ros_view(result)
    assert (summary["state"], summary["source_date"], summary["retrieved_at"], value["evidence_state"]) == ("STALE", "2026-10-02", later.isoformat(), "STALE")


def test_weekly_freshness_boundary_is_48_hours_from_the_upstream_source_date_never_the_retrieval_time():
    data = snapshot()
    # A Monday-night kickoff keeps every evaluation below before the game, so only the source-age limit decides.
    data["artifacts"]["fp_latest_weekly.csv"]["rows"][0]["player_game_kickoff_ts"] = str(datetime(2026, 10, 6, 0, 15, tzinfo=timezone.utc).timestamp())
    published = datetime(2026, 10, 3, tzinfo=timezone.utc)
    for offset, state in ((timedelta(hours=47, minutes=59), "FRESH"), (timedelta(hours=48), "FRESH"), (timedelta(hours=48, seconds=1), "STALE")):
        evaluated_at = published + offset
        # A download at the evaluation moment never renews the scrape date's age.
        horizon = evaluate({**data, "last_successful_refresh": evaluated_at.isoformat()}, STATE, evaluated_at)["horizons"]["this_week"]
        assert (horizon["freshness_state"], horizon["latest_source_age_seconds"]) == (state, int(offset.total_seconds()))
        assert ("s-1" in horizon["ranks"]) is (state == "FRESH")


def test_ros_freshness_boundary_is_seven_days_from_the_upstream_source_date():
    published = datetime(2026, 10, 2, tzinfo=timezone.utc)
    at_limit = evaluate(snapshot(), STATE, published + timedelta(days=7))
    assert at_limit["horizons"]["rest_of_season"]["ranks"]["s-1"]["source_age_seconds"] == 604800
    assert ros_view(at_limit)[1]["evidence_state"] == "RANKED"
    past = evaluate(snapshot(), STATE, published + timedelta(days=7, seconds=1))["horizons"]["rest_of_season"]
    assert (past["ranks"], past["freshness_state"], past["latest_source_age_seconds"]) == ({}, "STALE", 604801)


@pytest.mark.parametrize("page", ["/nfl/rankings/ros-wr.php", "/nfl/rankings/ros-half-point-ppr-wr.php"])
def test_non_ppr_ros_pages_and_non_ppr_leagues_are_rejected(page):
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0]["fp_page"] = page
    horizon = evaluate(data, STATE, NOW)["horizons"]["rest_of_season"]
    assert (horizon["ranks"], horizon["reconciliation"]["supported_scope_rows"]) == ({}, 0)
    summary, value = ros_view(evaluate(snapshot(), STATE, NOW), full_ppr=False)
    assert (summary["state"], summary["blocker"], value["evidence_state"], value["ros_ecr"]) == ("SCORING_UNSUPPORTED", "LEAGUE_NOT_FULL_PPR", "SCORING_UNSUPPORTED", None)


@pytest.mark.parametrize("page", ["/nfl/rankings/ppr-wr.php", "/nfl/rankings/ros-ppr-overall.php", "/nfl/rankings/ros-idp.php"])
def test_weekly_overall_and_unsupported_pages_never_become_ros_ranks(page):
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0]["fp_page"] = page
    assert evaluate(data, STATE, NOW)["horizons"]["rest_of_season"]["ranks"] == {}
    moved = snapshot()
    moved["artifacts"]["fp_latest_weekly.csv"]["rows"] += moved["artifacts"]["db_fpecr_latest.csv"]["rows"]
    moved["artifacts"]["db_fpecr_latest.csv"]["rows"] = []
    horizons = evaluate(moved, STATE, NOW)["horizons"]
    assert horizons["rest_of_season"]["ranks"] == {} and horizons["this_week"]["ranks"]["s-1"]["ecr"] == 12.5


@pytest.mark.parametrize("page", ["/nfl/rankings/ppr-wr.php", "/nfl/rankings/dynasty-wr.php"])
def test_draft_and_dynasty_ranks_published_beside_ros_never_substitute_for_either_horizon(page):
    # The upstream ROS artifact also carries draft (ppr-wr.php) and dynasty pages. With no weekly row and only a stale ROS row, a fresh
    # draft or dynasty rank for the same player supplies no rank to either horizon and never renews the ROS source date.
    data = snapshot()
    data["artifacts"]["fp_latest_weekly.csv"]["rows"] = []
    stale = {**data["artifacts"]["db_fpecr_latest.csv"]["rows"][0], "scrape_date": "2026-09-20"}
    data["artifacts"]["db_fpecr_latest.csv"]["rows"] = [stale, {"fp_page": page, "id": "fp-1", "ecr": "3", "scrape_date": "2026-10-03"}]
    week, ros = (evaluate(data, STATE, NOW)["horizons"][horizon] for horizon in ("this_week", "rest_of_season"))
    assert (week["ranks"], week["state"], week["freshness_state"]) == ({}, "UNAVAILABLE", "UNAVAILABLE")
    assert (ros["ranks"], ros["freshness_state"], ros["latest_source_date"], ros["reconciliation"]["supported_scope_rows"]) == ({}, "STALE", "2026-09-20", 1)


@pytest.mark.parametrize("ecr", ["NaN", "inf", "-3", "abc"])
def test_invalid_ros_rank_is_rejected_and_reconciled(ecr):
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0]["ecr"] = ecr
    horizon = evaluate(data, STATE, NOW)["horizons"]["rest_of_season"]
    assert (horizon["ranks"], horizon["reconciliation"]["reconciled"], horizon["diagnostics"][0]["raw_ecr"]) == ({}, True, ecr)


def test_zero_ros_rank_is_invalid_under_the_rank_validity_contract():
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0]["ecr"] = "0"
    diagnostic = evaluate(data, STATE, NOW)["horizons"]["rest_of_season"]["diagnostics"][0]
    assert (diagnostic["reason"], diagnostic["classification"]) == ("Consensus rank is invalid", "CONFIRMED_INVALID_RANK")
    result = evaluate(snapshot(), STATE, NOW)
    result["horizons"]["rest_of_season"]["ranks"]["s-1"]["ecr"] = 0.0
    value = ros_view(result)[1]
    assert (value["evidence_state"], value["blocker"], value["ros_ecr"]) == ("BLOCKED", "ROS_RANK_ROW_INVALID", None)


def test_ros_contextual_identity_applies_only_where_the_owner_approved_rule_permits():
    data = with_contextual_kicker()
    row = evaluate(data, STATE, NOW, sleeper_catalog={"12711": KICKER})["horizons"]["rest_of_season"]["ranks"]["12711"]
    assert (row["identity_method"], row["provider_id"], row["position"], row["ecr"]) == ("OWNER_APPROVED_UNIQUE_NAME_POSITION_TEAM", "new-provider", "K", 6.0)
    data["artifacts"]["db_playerids.csv"]["rows"].append({"fantasypros_id": "new-provider", "sleeper_id": "crosswalk-k", "position": "K"})
    ranks = evaluate(data, STATE, NOW, sleeper_catalog={"12711": KICKER})["horizons"]["rest_of_season"]["ranks"]
    assert "12711" not in ranks and ranks["crosswalk-k"]["identity_method"] == "PUBLISHED_PROVIDER_CROSSWALK"


def test_ros_contextual_identity_rejects_a_team_conflict():
    result = evaluate(with_contextual_kicker(), STATE, NOW, sleeper_catalog={"12711": {**KICKER, "team": "LAR"}})
    horizon = result["horizons"]["rest_of_season"]
    assert "12711" not in horizon["ranks"] and [item["reason"] for item in horizon["diagnostics"]] == ["PROVIDER_ID_ABSENT_FROM_CROSSWALK"]
    value = ros_view(result, "12711", "K")[1]
    assert (value["evidence_state"], value["blocker"], value["ros_ecr"]) == ("IDENTITY_UNRESOLVED", "PROVIDER_ID_ABSENT_FROM_CROSSWALK", None)


def test_ros_position_conflict_rejects_the_mapping():
    data = with_contextual_kicker()
    data["artifacts"]["db_playerids.csv"]["rows"][0]["position"] = "RB"
    result = evaluate(data, STATE, NOW, sleeper_catalog={"12711": KICKER})
    horizon = result["horizons"]["rest_of_season"]
    assert "s-1" not in horizon["ranks"] and horizon["diagnostics"][0]["reason"] == "POSITION_CONFLICT"
    assert ros_view(result, "s-1", "RB")[1]["evidence_state"] == "POSITION_CONFLICT"
    wrong_position = evaluate(with_contextual_kicker(), STATE, NOW, sleeper_catalog={"12711": {**KICKER, "position": "WR"}})["horizons"]["rest_of_season"]
    assert "12711" not in wrong_position["ranks"]


def test_ambiguous_ros_contextual_name_stays_unresolved():
    result = evaluate(with_contextual_kicker(), STATE, NOW, sleeper_catalog={"12711": KICKER, "99999": dict(KICKER)})
    horizon = result["horizons"]["rest_of_season"]
    assert set(horizon["ranks"]) == {"s-1"} and [item["reason"] for item in horizon["diagnostics"]] == ["CONTEXTUAL_IDENTITY_AMBIGUOUS"]
    for player_id in ("12711", "99999"):
        value = ros_view(result, player_id, "K")[1]
        assert (value["evidence_state"], value["blocker"], value["ros_ecr"]) == ("IDENTITY_UNRESOLVED", "CONTEXTUAL_IDENTITY_AMBIGUOUS", None)


# W4: rest-of-season expert-range evidence for materiality.

def test_ros_expert_range_and_dispersion_are_published_with_the_rank():
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0].update(best="18", worst="23", sd="1.4")
    result = evaluate(data, STATE, NOW)
    row = result["horizons"]["rest_of_season"]["ranks"]["s-1"]
    assert (row["ecr"], row["expert_best_rank"], row["expert_worst_rank"], row["expert_rank_sd"], row["expert_range_state"]) == (20.0, 18.0, 23.0, 1.4, "VALID")
    value = ros_view(result)[1]
    assert (value["range_state"], value["expert_best_rank"], value["expert_worst_rank"], value["expert_rank_sd"]) == ("VALID", 18.0, 23.0, 1.4)


def test_missing_ros_expert_range_keeps_the_rank_without_materiality_evidence():
    result = evaluate(snapshot(), STATE, NOW)
    row = result["horizons"]["rest_of_season"]["ranks"]["s-1"]
    assert (row["ecr"], row["expert_best_rank"], row["expert_worst_rank"], row["expert_range_state"]) == (20.0, None, None, "MISSING")
    value = ros_view(result)[1]
    assert (value["evidence_state"], value["ros_ecr"], value["range_state"], value["expert_best_rank"]) == ("RANKED", 20.0, "MISSING", None)


@pytest.mark.parametrize("fields", [{"best": "NaN", "worst": "23"}, {"best": "18", "worst": "inf"}, {"best": "-3", "worst": "23"}, {"best": "24", "worst": "22"},
                                    {"best": "21", "worst": "23"}, {"best": "0", "worst": "23"}, {"best": "18", "worst": "23", "sd": "-1"}])
def test_invalid_ros_expert_range_is_rejected_without_rejecting_the_rank(fields):
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0].update(fields)
    result = evaluate(data, STATE, NOW)
    row = result["horizons"]["rest_of_season"]["ranks"]["s-1"]
    assert (row["ecr"], row["expert_range_state"]) == (20.0, "INVALID")
    value = ros_view(result)[1]
    assert (value["evidence_state"], value["ros_ecr"], value["range_state"], value["expert_best_rank"], value["expert_worst_rank"]) == ("RANKED", 20.0, "INVALID", None, None)


def test_stale_ros_expert_range_is_never_used():
    data = snapshot()
    data["artifacts"]["db_fpecr_latest.csv"]["rows"][0].update(best="18", worst="23", sd="1.4")
    value = ros_view(evaluate(data, STATE, NOW + timedelta(days=8)))[1]
    assert (value["evidence_state"], value["range_state"], value["expert_best_rank"], value["expert_worst_rank"]) == ("STALE", "NOT_RANKED", None, None)
