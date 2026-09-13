from weekly_intelligence import enrich_players


class RejectingCursor:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("LIVE enrichment must not query CSV-derived local weekly tables")

    def fetchone(self):
        raise AssertionError("LIVE enrichment must not read CSV-derived local weekly tables")


def test_live_enrichment_does_not_use_local_csv_health_fallback():
    player = {
        "player": "Player",
        "position": "WR",
        "nfl_team": "SEA",
        "injury_status": "Healthy",
        "health_status_available": True,
        "health_fetched_at": "2026-09-13T00:00:00+00:00",
    }
    class WeeklyCursor:
        def execute(self, query, params=None):
            if "injury_reports" in query:
                raise AssertionError("LIVE health enrichment must not query stale injury_reports")
        def fetchone(self):
            return None
    result = enrich_players(WeeklyCursor(), [player], week=1, allow_local_weekly_data=False, allow_local_health_fallback=False)[0]
    assert result["weekly_score"] is None
    assert "SCHEDULE_UNAVAILABLE" in result["evidence_gaps"]
    assert "MATCHUP_EVIDENCE_UNAVAILABLE" in result["evidence_gaps"]
