from datetime import datetime, timedelta, timezone
from services.integrity.integrity_service import BYE_EVIDENCE_THRESHOLD_ID, SCHEDULE_EVIDENCE_THRESHOLD_ID, schedule_bye_freshness_limits
from services.schedule_bye_evidence import evidence_contract
NOW = datetime(2026, 9, 14, tzinfo=timezone.utc)

def test_schedule_bye_threshold_identifiers_are_distinct():
    assert SCHEDULE_EVIDENCE_THRESHOLD_ID != BYE_EVIDENCE_THRESHOLD_ID

def test_missing_empty_invalid_zero_and_negative_thresholds_are_unapproved(monkeypatch):
    for value in (None, "", "bad", "0", "-1"):
        if value is None:
            monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
            monkeypatch.delenv("BYE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
        else:
            monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", value)
            monkeypatch.setenv("BYE_EVIDENCE_MAX_AGE_SECONDS", value)
        limits = schedule_bye_freshness_limits()
        assert limits["schedule"]["seconds"] is None
        assert limits["bye"]["seconds"] is None

def test_positive_configured_thresholds_are_loaded(monkeypatch):
    monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", "100")
    monkeypatch.setenv("BYE_EVIDENCE_MAX_AGE_SECONDS", "200")
    limits = schedule_bye_freshness_limits()
    assert limits["schedule"]["seconds"] == 100
    assert limits["bye"]["seconds"] == 200

def test_schedule_contract_uses_registry_when_not_injected(monkeypatch):
    monkeypatch.setenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", "100")
    row = evidence_contract("schedule", source="csv:verified.csv", source_recorded_at=(NOW - timedelta(seconds=80)).isoformat(), now=NOW)
    assert row["freshness_state"] == "FRESH"
    assert row["freshness_threshold_id"] == SCHEDULE_EVIDENCE_THRESHOLD_ID

def test_injected_threshold_remains_deterministic(monkeypatch):
    monkeypatch.delenv("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    row = evidence_contract("schedule", source="csv:verified.csv", source_recorded_at=NOW.isoformat(), max_age_seconds=100, now=NOW)
    assert row["authoritative"] is True

def test_zero_and_negative_injected_thresholds_fail_closed():
    for value in (0, -1, "bad"):
        row = evidence_contract("schedule", source="automated:test", source_recorded_at=NOW.isoformat(), max_age_seconds=value, now=NOW)
        assert row["freshness_state"] == "UNAVAILABLE"
        assert row["authoritative"] is False
