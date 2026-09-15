import json

import pytest

from services.defense_matchup_calculation import calculate_defense_matchups, full_ppr_points
from services.nflverse_identity_resolution import resolve_player_identity
from services.nflverse_ingestion_validator import validate_nflverse_weekly_stats
from services.defense_matchup_publication import publish_defense_matchups, select_authoritative_matchups


def row(position, defense, game, points, completed=True):
    return {"position": position, "defense_team": defense, "game_id": game, "game_completed": completed, "receiving_yards": points * 10, "receptions": 0}


def complete_rows(points=1):
    defenses = [f"D{i:02d}" for i in range(32)]
    return [row(position, defense, f"{position}-{defense}", points + index) for position in ("QB", "RB", "WR", "TE") for index, defense in enumerate(defenses)]


NOW = "2026-09-15T12:00:00+00:00"


def test_full_ppr_and_completed_games_only():
    assert full_ppr_points({"receiving_yards": 100, "receptions": 10, "receiving_tds": 1}) == 26
    evidence = calculate_defense_matchups([row("WR", "ARI", "g1", 10), row("WR", "ARI", "g2", 100, False)], season=2026, sample_threshold=1, retrieved_at=NOW)
    assert evidence["rows"][0]["fp_per_game_allowed"] == 10


def test_directionality_and_completeness():
    evidence = calculate_defense_matchups(complete_rows(), season=2026, sample_threshold=1, retrieved_at=NOW)
    assert evidence["status"] == "AUTHORITATIVE"
    assert evidence["directionality"] == "LOWER_IS_HARDER"
    assert evidence["rows"][0]["defense_rank"] == 1
    assert evidence["completeness"]["defense_count"] == 32


def test_zero_and_insufficient_samples_fail_closed():
    assert calculate_defense_matchups([], season=2026, sample_threshold=1)["status"] == "UNAVAILABLE"
    assert calculate_defense_matchups(complete_rows(), season=2026, sample_threshold=2, retrieved_at=NOW)["status"] == "INSUFFICIENT_SAMPLE"
    assert calculate_defense_matchups(complete_rows(), season=2026, retrieved_at=NOW)["status"] == "BLOCKED"


def test_exclusions_unresolved_identity_and_scoring():
    evidence = calculate_defense_matchups([row("K", "ARI", "g1", 3), row("DEF", "ARI", "g1", 3), row("WR", "ARI", "g1", 3), {"position": "WR", "game_id": "g2", "game_completed": True}], season=2026, sample_threshold=1)
    assert len(evidence["rows"]) == 1
    assert evidence["unresolved_identities"]
    assert not validate_nflverse_weekly_stats([], season=2026, scoring="half_ppr")["valid"]
    assert resolve_player_identity({"player_id": "p1"}, [{"player_id": "p1", "full_name": "A"}])["resolved"]
    assert not resolve_player_identity({"full_name": "A"}, [{"full_name": "A"}, {"full_name": "A"}])["resolved"]


def test_official_la_identity_maps_to_repository_lar():
    evidence = calculate_defense_matchups([row("WR", "LA", "g1", 3)], season=2026, sample_threshold=1, retrieved_at=NOW)
    assert evidence["rows"][0]["defense_team"] == "LAR"


def test_offline_fixture_is_readable():
    from imports.import_nflverse_weekly_stats import load_weekly_stats
    rows, checksum = load_weekly_stats("tests/fixtures/nflverse_weekly_stats_minimal.csv")
    assert len(rows) == 4 and len(checksum) == 64


def test_provenance_and_historical_selection():
    evidence = calculate_defense_matchups(complete_rows(), season=2026, sample_threshold=1, retrieved_at=NOW, source_recorded_at=NOW, version="v1", checksum="abc")
    assert evidence["provenance"]["attribution"].endswith("CC BY 4.0.")
    selected = select_authoritative_matchups({"authoritative": False}, {"rows": [], "authoritative": True})
    assert selected["status"] == "HISTORICAL" and selected["authoritative"] is False


class FakeCursor:
    def __init__(self, fail=False):
        self.statements = []
        self.fail = fail

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if self.fail and len(self.statements) > 1:
            raise RuntimeError("write failed")

    def close(self):
        pass


class FakeConnection:
    def __init__(self, fail=False):
        self.cursor_value = FakeCursor(fail)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_publication_is_atomic_and_rerunnable():
    evidence = calculate_defense_matchups(complete_rows(), season=2026, sample_threshold=1, retrieved_at=NOW)
    connection = FakeConnection()
    assert publish_defense_matchups(connection, evidence) == 128
    assert connection.commits == 1 and connection.rollbacks == 0
    assert publish_defense_matchups(connection, evidence) == 128
    failing = FakeConnection(fail=True)
    with pytest.raises(RuntimeError):
        publish_defense_matchups(failing, evidence)
    assert failing.commits == 0 and failing.rollbacks == 1