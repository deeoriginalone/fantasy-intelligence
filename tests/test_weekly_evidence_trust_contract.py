from weekly_intelligence import enrich_players
from services.ux_evidence import weekly_evidence_contract
from services.trade_intelligence import evidence_ready


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
