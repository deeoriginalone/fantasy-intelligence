from datetime import datetime, timedelta, timezone
import hashlib
from datetime import date
import pytest
from services.schedule_bye_evidence import evidence_contract
from weekly_intelligence import enrich_players
from imports.import_nflverse_schedule import (
    LEGACY_BYE_SOURCE,
    NFL_TEAMS,
    ScheduleEvidenceError,
    _source_time,
    build_schedule_evidence,
    publish_schedule_evidence,
)
NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)
def test_import_time_does_not_make_csv_authoritative():
    result = evidence_contract("schedule", source="csv:old.csv", imported_at=NOW.isoformat(), max_age_seconds=3600, now=NOW)
    assert not result["authoritative"]
    assert result["freshness_state"] == "UNAVAILABLE"
def test_source_recorded_time_can_make_csv_fresh_with_disclosure():
    result = evidence_contract("schedule", source="csv:verified.csv", source_recorded_at=NOW.isoformat(), imported_at=(NOW + timedelta(days=7)).isoformat(), max_age_seconds=3600, now=NOW)
    assert result["authoritative"] and result["source_tier"] == "CSV_BOOTSTRAP_OR_RECOVERY"
def test_stale_csv_is_not_refreshed_by_reimport():
    result = evidence_contract("schedule", source="csv:old.csv", source_recorded_at=(NOW-timedelta(days=8)).isoformat(), imported_at=NOW.isoformat(), max_age_seconds=3600, now=NOW)
    assert result["freshness_state"] == "STALE"
def test_csv_writer_protects_null_automated_and_cache_rows():
    text = open("imports/import_weekly_intelligence.py", encoding="utf-8").read()
    assert "WHERE nfl_schedule.source LIKE 'csv:%'" in text
    assert "WHERE bye_weeks.source LIKE 'csv:%'" in text
    assert "source IS NULL OR" not in text

def test_missing_or_import_only_provenance_is_unavailable():
    missing = evidence_contract("bye", source="csv:old.csv", max_age_seconds=3600, now=NOW)
    imported = evidence_contract("bye", source="csv:old.csv", imported_at=NOW.isoformat(), max_age_seconds=3600, now=NOW)
    assert missing["freshness_state"] == imported["freshness_state"] == "UNAVAILABLE"

def test_stale_schedule_only_blocks_the_schedule_dependent_decision():
    result = evidence_contract("schedule", source="csv:verified.csv", source_recorded_at=(NOW-timedelta(days=8)).isoformat(), max_age_seconds=3600, now=NOW)
    assert result["blocker"] == "SCHEDULE_DATA_STALE"

def test_invalid_domain_is_blocked():
    result = evidence_contract("matchup", source="automated:test", source_recorded_at=NOW.isoformat(), max_age_seconds=3600, now=NOW)
    assert result["freshness_state"] == "BLOCKED"
    assert result["authoritative"] is False

def test_malformed_injected_threshold_is_unavailable():
    result = evidence_contract("schedule", source="automated:test", source_recorded_at=NOW.isoformat(), max_age_seconds="bad", now=NOW)
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["authoritative"] is False

def test_naive_evaluation_time_is_supported():
    result = evidence_contract("schedule", source="automated:test", source_recorded_at=NOW.isoformat(), max_age_seconds=3600, now="2026-09-14T00:00:00")
    assert result["freshness_state"] == "FRESH"

class ProvenanceCursor:
    def __init__(self): self.query = ""
    def execute(self, query, params=None): self.query = query
    def fetchone(self):
        if "bye_weeks" in self.query: return (8, "csv:verified.csv", NOW, None, NOW)
        if "nfl_schedule" in self.query: return ("SF", "HOME", NOW, "csv:verified.csv", NOW, None, NOW)
        return None

def test_live_enrichment_reads_post_migration_schedule_and_bye_provenance():
    player = {"player": "Test", "position": "WR", "nfl_team": "SEA", "projection": 100, "injury_status": "Healthy", "health_status_available": True}
    row = enrich_players(ProvenanceCursor(), [player], week=1, require_automated_weekly_evidence=True)[0]
    assert row["weekly_evidence"]["schedule"]["source"] == "csv:verified.csv"
    assert row["weekly_evidence"]["bye"]["source"] == "csv:verified.csv"


def complete_schedule_rows():
    teams=sorted(NFL_TEAMS); rows=[]; first_day=date(2026,9,10)
    for week in range(1,19):
        bye_teams={teams[week-1],teams[week+15]} if week<=16 else set()
        active=[team for team in teams if team not in bye_teams]
        gameday=(first_day+timedelta(days=7*(week-1))).isoformat()
        for index in range(0,len(active),2):
            away,home=active[index:index+2]
            rows.append({"game_id":f"2026_{week:02d}_{away}_{home}","season":"2026","game_type":"REG","week":str(week),"gameday":gameday,"gametime":"20:20","home_team":home,"away_team":away,"location":"Home","result":""})
    return rows


def schedule_evidence(monkeypatch, rows=None):
    monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS","")
    monkeypatch.setenv("BYE_EVIDENCE_MAX_AGE_SECONDS","")
    source_time=_source_time("2026-10-04 04:36:32 EDT")
    retrieved=datetime(2026,10,4,12,0,0,tzinfo=timezone.utc)
    return build_schedule_evidence(rows or complete_schedule_rows(),season=2026,source_recorded_at=source_time,retrieved_at=retrieved,checksum=hashlib.sha256(b"schedule artifact").hexdigest())


def test_nflverse_schedule_build_validates_population_derives_byes_and_keeps_threshold_blocked(monkeypatch):
    evidence=schedule_evidence(monkeypatch)
    assert len(evidence["rows"])==272 and evidence["team_count"]==32
    assert set(evidence["games_per_team"].values())=={17}
    assert len(evidence["byes"])==32 and len({row["team"] for row in evidence["byes"]})==32
    assert evidence["rows"][0]["game_time_utc"].isoformat()=="2026-09-11T00:20:00+00:00"
    assert evidence["rows"][0]["game_time_pacific"].isoformat()=="2026-09-10T17:20:00"
    assert evidence["source_recorded_at"].isoformat()=="2026-10-04T08:36:32+00:00"
    assert evidence["retrieved_at"].isoformat()=="2026-10-04T12:00:00+00:00"
    assert evidence["schedule_contract"]["blocker"]=="SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED"
    assert evidence["bye_contract"]["authoritative"] is True and evidence["bye_contract"]["contract_id"]=="bye.season_static.v1"
    assert evidence["authoritative"] is False
    assert evidence["license_url"].endswith("LICENSE.md")


def test_nflverse_schedule_rejects_incomplete_and_contradictory_team_weeks(monkeypatch):
    rows=complete_schedule_rows()
    with pytest.raises(ScheduleEvidenceError,match="TEAM_POPULATION_INCOMPLETE"):
        schedule_evidence(monkeypatch,rows[:-1])
    rows=complete_schedule_rows(); duplicate=dict(rows[0]); duplicate["game_id"]="second-id"; rows.append(duplicate)
    with pytest.raises(ScheduleEvidenceError,match="TEAM_WEEK_CONFLICT"):
        schedule_evidence(monkeypatch,rows)


def test_nflverse_source_time_requires_real_eastern_offset_and_consistent_zone():
    assert _source_time("2026-10-04 04:36:32 EDT").isoformat()=="2026-10-04T08:36:32+00:00"
    with pytest.raises(ScheduleEvidenceError,match="TIMEZONE_UNSUPPORTED"):
        _source_time("2026-10-04 04:36:32 UTC")
    with pytest.raises(ScheduleEvidenceError,match="TIMEZONE_CONTRADICTORY"):
        _source_time("2026-10-04 04:36:32 EST")


class ScheduleWriteCursor:
    def __init__(self,bye_source=LEGACY_BYE_SOURCE): self.query=""; self.params=(); self.rowcount=1; self.bye_source=bye_source; self.statements=[]
    def execute(self,query,params=()):
        self.query=query; self.params=params; self.statements.append((query,params)); self.rowcount=1
    def fetchall(self):
        if "SELECT DISTINCT source FROM bye_weeks" in self.query: return [(self.bye_source,)] if self.bye_source else []
        return []
    def close(self): pass


class ScheduleWriteConnection:
    def __init__(self,bye_source=LEGACY_BYE_SOURCE): self.cursor_value=ScheduleWriteCursor(bye_source); self.commits=0; self.rollbacks=0
    def cursor(self): return self.cursor_value
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1


def test_nflverse_writer_requires_explicit_legacy_bye_source_replacement(monkeypatch):
    evidence=schedule_evidence(monkeypatch); connection=ScheduleWriteConnection()
    with pytest.raises(ScheduleEvidenceError,match="REQUIRES_EXPLICIT_FLAG"):
        publish_schedule_evidence(connection,evidence)
    assert connection.commits==0 and connection.rollbacks==1
    assert not any("INSERT INTO" in query for query,_ in connection.cursor_value.statements)


def test_nflverse_writer_records_genuine_times_and_updates_only_explicit_sources(monkeypatch):
    evidence=schedule_evidence(monkeypatch); connection=ScheduleWriteConnection()
    counts=publish_schedule_evidence(connection,evidence,replace_known_legacy_byes=True)
    assert counts=={"schedule_rows":272,"bye_rows":32}
    assert connection.commits==1 and connection.rollbacks==0
    schedule_insert=next((query,params) for query,params in connection.cursor_value.statements if "INSERT INTO nfl_schedule" in query)
    bye_insert=next((query,params) for query,params in connection.cursor_value.statements if "INSERT INTO bye_weeks" in query)
    assert all(field in schedule_insert[0] for field in ("source_recorded_at","retrieved_at","imported_at"))
    assert schedule_insert[1][10]==evidence["source_recorded_at"] and schedule_insert[1][11]==evidence["retrieved_at"]
    assert bye_insert[1][4]==evidence["source_recorded_at"] and bye_insert[1][5]==evidence["retrieved_at"]
    assert "WHERE nfl_schedule.source LIKE 'csv:%%' OR nfl_schedule.source LIKE 'automated:nflverse-schedules:%%'" in schedule_insert[0]
    assert "replace_known_legacy_byes" not in bye_insert[0]


from copy import deepcopy
from services.schedule_bye_evidence import team_bye_evidence

AUTO = "automated:nflverse-schedules:derived-bye:games.csv.gz:sha256:abc"


def bye_rows(source=AUTO, recorded=NOW, drop=None):
    teams = sorted(NFL_TEAMS)
    return [{"season": 2026, "team": team, "bye_week": 5 + index % 10, "source": source, "source_recorded_at": recorded, "retrieved_at": recorded, "imported_at": NOW}
            for index, team in enumerate(teams) if team != drop]


def one(rows, **kw):
    return team_bye_evidence(rows, season=kw.pop("season", 2026), team=kw.pop("team", sorted(NFL_TEAMS)[0]), week=kw.pop("week", 5), now=NOW + timedelta(days=30), **kw)


def test_team_bye_is_season_static_authoritative_without_any_age_threshold(monkeypatch):
    monkeypatch.delenv("BYE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    result = one(bye_rows(recorded=NOW - timedelta(days=9)))
    assert result["authoritative"] and result["authority_mode"] == "SEASON_STATIC" and result["freshness_state"] == "FRESH" and result["contract_id"] == "bye.season_static.v1"
    assert result["completeness_state"] == "COMPLETE" and result["is_current_week_bye"] is True and result["season"] == 2026
    assert result["bye_week"] == 5 and result["source_recorded_at"] and result["retrieved_at"] and result["age"] > 0
    assert result["freshness_threshold_id"] is None and result["blocker"] is None


def test_team_bye_non_current_week_is_authoritative_but_not_a_bye():
    result = one(bye_rows(), week=6)
    assert result["authoritative"] and result["is_current_week_bye"] is False


@pytest.mark.parametrize("field", ["source_recorded_at", "retrieved_at"])
def test_team_bye_missing_timestamp_is_unavailable(field):
    rows = bye_rows()
    for row in rows:
        row[field] = None
        row["imported_at"] = NOW
    result = one(rows)
    assert result["freshness_state"] == "UNAVAILABLE" and not result["authoritative"] and result["blocker"] == "BYE_SOURCE_TIMESTAMP_UNVERIFIED"


def test_team_bye_missing_source_is_unavailable():
    rows = bye_rows(source=None)
    assert one(rows)["blocker"] == "BYE_SOURCE_MISSING"


def test_team_bye_incomplete_coverage_is_unavailable():
    result = one(bye_rows(drop=sorted(NFL_TEAMS)[-1]))
    assert result["completeness_state"] == "INCOMPLETE" and not result["authoritative"] and result["freshness_state"] == "UNAVAILABLE"


def test_team_bye_conflicting_or_duplicate_assignments_are_blocked():
    rows = bye_rows(); conflict = rows + [{**rows[0], "bye_week": 12}]; duplicate = rows + [dict(rows[0])]
    assert one(conflict)["blocker"] == "BYE_WEEK_CONFLICT" and one(conflict)["freshness_state"] == "BLOCKED"
    assert one(duplicate)["blocker"] == "BYE_DUPLICATE_ASSIGNMENT" and not one(duplicate)["authoritative"]


def test_team_bye_unsupported_season_or_unresolved_team_is_blocked():
    assert one(bye_rows(), season=None)["blocker"] == "BYE_SEASON_UNSUPPORTED"
    assert one(bye_rows(), team="ZZZ")["blocker"] == "BYE_TEAM_IDENTITY_UNRESOLVED"
    assert one(bye_rows(), season=2025)["freshness_state"] == "BLOCKED"


def test_team_bye_csv_fallback_is_disclosed_and_not_authoritative():
    result = one(bye_rows(source="csv:nfl-2026-bye-weeks.csv"))
    assert not result["authoritative"] and result["fallback_used"] == "CSV_BOOTSTRAP_OR_RECOVERY" and result["is_current_week_bye"] is False


def test_team_bye_read_does_not_mutate_rows():
    rows = bye_rows(); before = deepcopy(rows)
    one(rows)
    assert rows == before


def test_importer_and_reader_share_one_bye_authority_rule(monkeypatch):
    monkeypatch.delenv("BYE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    built = build_schedule_evidence(complete_schedule_rows(), season=2026, source_recorded_at=_source_time("2026-10-04 04:36:32 EDT"),
                                    retrieved_at=datetime(2026, 10, 4, 12, tzinfo=timezone.utc), checksum=hashlib.sha256(b"x").hexdigest())
    rows = [{"season": 2026, "team": row["team"], "bye_week": row["bye_week"], "source": built["bye_source"],
             "source_recorded_at": built["source_recorded_at"], "retrieved_at": built["retrieved_at"]} for row in built["byes"]]
    reader = one(rows, team=built["byes"][0]["team"], week=built["byes"][0]["bye_week"])
    assert built["bye_contract"]["authoritative"] and reader["authoritative"] and reader["is_current_week_bye"] is True
    assert built["bye_contract"]["contract_id"] == reader["contract_id"]
