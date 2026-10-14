import pytest

from tests.helpers.health_assertions import (
    assert_missing_payload_rendered,
    assert_unknown_state_rendered,
)

DEFENSIVE_HEALTH_CASES = [
    pytest.param(None, assert_missing_payload_rendered, id="missing-payload"),
    pytest.param({}, assert_missing_payload_rendered, id="empty-payload"),
    pytest.param(
        {"state": "UNKNOWN_STATE", "freshness_state": "FRESH"},
        assert_unknown_state_rendered,
        id="unknown-state",
    ),
    pytest.param(
        {"state": "NOT_SUPPORTED", "freshness_state": "FRESH"},
        assert_unknown_state_rendered,
        id="unsupported-state",
    ),
]

UNKNOWN_FRESHNESS_CASES = [
    pytest.param("UNKNOWN", id="freshness-unknown"),
    pytest.param("INVALID", id="freshness-invalid"),
    pytest.param("UNSUPPORTED", id="freshness-unsupported"),
]
