from datetime import datetime, timezone

from weekly_intelligence import enrich_players
from services.ux_evidence import weekly_evidence_contract
from services.trade_intelligence import evidence_ready

NOW = datetime(2026, 9, 17, tzinfo=timezone.utc)


class MatchupCursor:
    """Minimal cursor exposing schedule + defense_matchups rows for matchup-authority enrichment tests."""

    def __init__(self, *, matchup_source="automated:nflverse", lineage=None, completed_games=8):
        self.query = ""
        self.matchup_source = matchup_source
        self.lineage = lineage if lineage is not None else {}
        self.completed_games = completed_games

    def execute(self, query, params=None):
        self.query = query

    def fetchone(self):
        if "bye_weeks" in self.query:
            return None
        if "nfl_schedule" in self.query:
            return ("KC", "HOME", None, "automated:nflverse", NOW.isoformat(), NOW.isoformat(), None)
        if "defense_matchups" in self.query:
            return (5, 12.3, self.matchup_source, NOW.isoformat(), "COMPLETE", None, "v1", "chk", NOW.isoformat(), self.lineage, self.completed_games)
        return None


def _publication_lineage(threshold_state="VERIFIED", include_population=True, include_directionality=True):
    contracts = {"threshold": {"identifier": "matchup.sample.v1", "value": 4, "state": threshold_state}}
    if include_population:
        contracts["population"] = {"name": "ALL_DEFENSES_BY_POSITION", "size": 32, "position_scope": ["QB", "RB", "WR", "TE"], "scoring_context": "FULL_PPR"}
    if include_directionality:
        contracts["directionality"] = {"value": "LOWER_IS_HARDER"}
    return {"publication_contracts": contracts}


def _matchup_player():
    return {"player": "Test", "position": "WR", "nfl_team": "KC", "projection": 100, "projection_retrieved_at": NOW.isoformat(), "injury_status": "Healthy", "health_status_available": True}


def test_weekly_contract_requires_automated_source_metadata():
    result = weekly_evidence_contract(domain="matchup", source="local CSV", freshness_state="FRESH", completeness_state="COMPLETE")
    assert result["authoritative"] is False
    assert result["freshness_state"] == "UNAVAILABLE"


def test_live_safe_enrichment_marks_weekly_domains_non_authoritative():
    player = {"player": "Player", "position": "WR", "nfl_team": "SEA", "injury_status": "Healthy", "health_status_available": True}
    result = enrich_players(object(), [player], week=1, allow_local_weekly_data=False, allow_local_health_fallback=False, require_automated_weekly_evidence=True)[0]
    assert result["weekly_score"] is None
    assert all(not item["authoritative"] for item in result["weekly_evidence"].values())


def test_trade_evidence_rejects_non_authoritative_weekly_contracts():
    player = {"player": "Player", "position": "WR", "projection": 100, "weekly_evidence": {"projection": {"authoritative": False}}}
    assert evidence_ready(player) is False


def test_trade_evidence_allows_retrieved_projection_warning_only():
    player = {
        "player": "Player", "position": "WR", "projection": 100,
        "projection_retrieved_at": "2026-09-16T12:00:00+00:00",
        "weekly_evidence": {"projection": {"authoritative": False}},
    }
    assert evidence_ready(player) is True


def test_authoritative_automated_row_populates_matchup_publication_contract():
    row = enrich_players(MatchupCursor(lineage=_publication_lineage()), [_matchup_player()], week=1, require_automated_weekly_evidence=True)[0]
    assert row["matchup_population"] == "ALL_DEFENSES_BY_POSITION"
    assert row["matchup_directionality"] == "LOWER_IS_HARDER"
    assert row["matchup_sample_threshold_id"] == "matchup.sample.v1"
    assert row["matchup_updated_at"] == row["matchup_retrieved_at"]
    assert row["matchup_updated_at"] is not None


def test_non_automated_csv_row_does_not_receive_publication_contract_authority():
    row = enrich_players(MatchupCursor(matchup_source="csv:old.csv", lineage={}), [_matchup_player()], week=1, require_automated_weekly_evidence=True)[0]
    assert row["matchup_population"] is None
    assert row["matchup_directionality"] is None
    assert row["matchup_sample_threshold_id"] is None


def test_threshold_not_verified_leaves_threshold_id_unavailable():
    row = enrich_players(MatchupCursor(lineage=_publication_lineage(threshold_state="UNAVAILABLE")), [_matchup_player()], week=1, require_automated_weekly_evidence=True)[0]
    assert row["matchup_sample_threshold_id"] is None
    assert row["matchup_population"] == "ALL_DEFENSES_BY_POSITION"
    assert row["matchup_directionality"] == "LOWER_IS_HARDER"
