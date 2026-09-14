from datetime import datetime, timedelta, timezone

from survivor_intelligence import build_status, evidence_freshness_state


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
SCHEDULE = [
    {"season": 2026, "week": 1, "away_team": "CLE", "home_team": "JAX"},
    {"season": 2026, "week": 1, "away_team": "SEA", "home_team": "NE"},
]


def row(market_updated_at):
    return {"game_id": "g1", "week": 1, "away_team": "CLE", "home_team": "JAX", "market_updated_at": market_updated_at}


def test_freshness_state_fresh_within_threshold():
    assert evidence_freshness_state(NOW - timedelta(hours=1), now=NOW) == "FRESH"


def test_freshness_state_aging_between_thresholds():
    assert evidence_freshness_state(NOW - timedelta(hours=18), now=NOW) == "AGING"


def test_freshness_state_stale_beyond_threshold():
    assert evidence_freshness_state(NOW - timedelta(hours=48), now=NOW) == "STALE"


def test_freshness_state_unavailable_when_missing():
    assert evidence_freshness_state(None, now=NOW) == "UNAVAILABLE"


def test_status_blocked_when_history_read_failed():
    status = build_status(season=2026, week=1, history_status="read_failed", used_teams=[],
                           schedule_rows=SCHEDULE, current_rows=[], candidates=[], now=NOW)
    assert status["state"] == "BLOCKED"
    assert status["blocker_reason"] == "SURVIVOR_HISTORY_READ_FAILED"
    assert status["used_team_count"] is None
    assert status["remaining_team_count"] is None


def test_status_unavailable_when_no_evidence_for_week():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX"],
                           schedule_rows=SCHEDULE, current_rows=[], candidates=[], now=NOW)
    assert status["state"] == "UNAVAILABLE"
    assert status["blocker_reason"] == "SURVIVOR_WEEK_EVIDENCE_MISSING"


def test_status_ready_with_fresh_complete_evidence():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX"],
                           schedule_rows=SCHEDULE, current_rows=[row(NOW - timedelta(hours=1))],
                           candidates=[{"team": "NE"}], now=NOW)
    assert status["state"] == "READY"
    assert status["used_team_count"] == 1
    assert status["remaining_team_count"] == len({"CLE", "JAX", "SEA", "NE"}) - 1


def test_status_degraded_with_aging_evidence():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX"],
                           schedule_rows=SCHEDULE, current_rows=[row(NOW - timedelta(hours=18))],
                           candidates=[{"team": "NE"}], now=NOW)
    assert status["state"] == "DEGRADED"


def test_status_blocked_with_stale_evidence():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX"],
                           schedule_rows=SCHEDULE, current_rows=[row(NOW - timedelta(hours=48))],
                           candidates=[{"team": "NE"}], now=NOW)
    assert status["state"] == "BLOCKED"
    assert status["blocker_reason"] == "SURVIVOR_EVIDENCE_STALE"


def test_status_unavailable_when_no_eligible_candidates_remain():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX", "NE"],
                           schedule_rows=SCHEDULE, current_rows=[row(NOW - timedelta(hours=1))],
                           candidates=[], now=NOW)
    assert status["state"] == "UNAVAILABLE"
    assert status["blocker_reason"] == "SURVIVOR_NO_ELIGIBLE_TEAMS"


def test_status_never_claims_31_remaining_without_verified_universe():
    status = build_status(season=2026, week=1, history_status="verified", used_teams=["JAX"],
                           schedule_rows=[], current_rows=[], candidates=[], now=NOW)
    assert status["remaining_team_count"] is None
