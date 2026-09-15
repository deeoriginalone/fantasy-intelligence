from datetime import datetime, timedelta, timezone
from services.schedule_bye_evidence import evidence_contract
from weekly_intelligence import enrich_players
NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)
def test_import_time_does_not_make_csv_authoritative():
    result = evidence_contract("schedule", source="csv:old.csv", imported_at=NOW.isoformat(), max_age_seconds=3600, now=NOW)
    assert not result["authoritative"]
    assert result["freshness_state"] == "UNAVAILABLE"
def test_source_recorded_time_can_make_csv_fresh_with_disclosure():
    result = evidence_contract("bye", source="csv:verified.csv", source_recorded_at=NOW.isoformat(), imported_at=(NOW + timedelta(days=7)).isoformat(), max_age_seconds=3600, now=NOW)
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
    result = evidence_contract("bye", source="automated:test", source_recorded_at=NOW.isoformat(), max_age_seconds="bad", now=NOW)
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
