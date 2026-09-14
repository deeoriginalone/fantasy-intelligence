from pathlib import Path
from imports.import_draft_intelligence import normalize_team
from imports.import_weekly_intelligence import abbr
from weekly_intelligence import enrich_players


ROOT = Path(__file__).resolve().parents[1]


def test_migration_adds_distinct_matchup_and_projection_retrieval_columns():
    text = (ROOT / "migrations/011_trade_evidence_freshness.sql").read_text(encoding="utf-8")
    assert "defense_matchups" in text and "retrieved_at TIMESTAMPTZ" in text
    assert "players" in text and "projection_retrieved_at TIMESTAMPTZ" in text


def test_successful_matchup_writer_persists_retrieval_time_with_its_upsert():
    text = (ROOT / "imports/import_weekly_intelligence.py").read_text(encoding="utf-8")
    statement = next(line for line in text.splitlines() if "INSERT INTO defense_matchups" in line)
    assert "retrieved_at" in statement
    assert "NOW()" in statement
    assert "retrieved_at=EXCLUDED.retrieved_at" in statement


def test_matchup_import_normalizes_supported_team_abbreviations():
    assert abbr("NWE") == "NE"
    assert abbr("NOR") == "NO"


def test_projection_import_normalizes_jacksonville_before_matching():
    assert normalize_team("JAC") == "JAX"


def test_successful_projection_writer_persists_dedicated_retrieval_time():
    text = (ROOT / "imports/import_draft_intelligence.py").read_text(encoding="utf-8")
    assert "projection_retrieved_at = NOW()" in text


def test_failed_imports_rollback_without_advancing_persisted_timestamps():
    weekly_text = (ROOT / "imports/import_weekly_intelligence.py").read_text(encoding="utf-8")
    projection_text = (ROOT / "imports/import_draft_intelligence.py").read_text(encoding="utf-8")
    assert "except Exception: c.rollback(); raise" in weekly_text
    assert "except Exception:" in projection_text and "conn.rollback()" in projection_text


def test_read_only_enrichment_does_not_contain_update_statements():
    text = (ROOT / "weekly_intelligence.py").read_text(encoding="utf-8")
    assert "UPDATE defense_matchups" not in text
    assert "UPDATE players" not in text


def test_partner_projection_lookup_normalizes_local_name_suffixes():
    text = (ROOT / "owner_operations.py").read_text(encoding="utf-8")
    assert "'(jr|sr|ii|iii|iv|il|ill)$'" in text


class EnrichmentCursor:
    def __init__(self, matchup):
        self.matchup = matchup
        self.query = ""

    def execute(self, query, params=None):
        self.query = query

    def fetchone(self):
        if "bye_weeks" in self.query:
            return (8,)
        if "nfl_schedule" in self.query:
            return ("SF", "HOME", "2026-09-13 13:25")
        if "defense_matchups" in self.query:
            return self.matchup
        return None


def test_enrichment_propagates_distinct_matchup_and_projection_retrieval_fields():
    matchup_stamp = "2026-09-13T10:00:00+00:00"
    projection_stamp = "2026-09-13T09:00:00+00:00"
    player = {
        "player": "Test",
        "position": "WR",
        "nfl_team": "SEA",
        "projection": 200,
        "projection_retrieved_at": projection_stamp,
        "injury_status": "Healthy",
        "health_status_available": True,
    }
    row = enrich_players(
        EnrichmentCursor((12, 20.0, "defense-fp-against-2025.csv", matchup_stamp)),
        [player],
        week=1,
    )[0]
    assert row["matchup_source"] == "nfl_schedule + defense-fp-against-2025.csv"
    assert row["matchup_retrieved_at"] == matchup_stamp
    assert row["matchup_lineage"]["source_recorded_at"] is None
    assert row["projection_retrieved_at"] == projection_stamp
    assert row["projection_lineage"]["source_recorded_at"] is None
    assert row["matchup_completeness"] == row["projection_completeness"] == "COMPLETE"


def test_enrichment_preserves_missing_timestamps_as_unavailable():
    player = {"player": "Test", "position": "WR", "nfl_team": "SEA", "projection": 200, "injury_status": "Healthy", "health_status_available": True}
    row = enrich_players(EnrichmentCursor((12, 20.0, "defense-fp-against-2025.csv", None)), [player], week=1)[0]
    assert row["matchup_completeness"] == "UNAVAILABLE"
    assert row["projection_completeness"] == "UNAVAILABLE"