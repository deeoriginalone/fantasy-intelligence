from datetime import datetime, timedelta, timezone
import json
from unittest.mock import Mock

from services.dynastyprocess_rankings import evaluate, refresh

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
    assert not evaluate(updated, STATE, NOW + timedelta(days=8))["horizons"]["rest_of_season"]["ranks"]


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