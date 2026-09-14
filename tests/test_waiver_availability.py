from services.ux_evidence import evaluate_waiver_availability, waiver_evidence_contract, waiver_roster_coverage
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


def evidence(domain, state="FRESH", completeness="COMPLETE", blocker=None):
    return waiver_evidence_contract(
        domain=domain,
        league_id="league-1",
        source="Sleeper API",
        source_record_time="2026-09-13T10:00:00+00:00",
        retrieved_at="2026-09-13T10:05:00+00:00",
        freshness_threshold_id="waiver-test-threshold",
        freshness_state=state,
        completeness_state=completeness,
        blocker=blocker,
        expected_active_roster_count=0,
        observed_active_roster_count=0,
        require_roster_coverage=domain == "ownership",
        require_timestamps=True,
    )


def test_rostered_by_any_manager_is_excluded_by_stable_id():
    result = evaluate_waiver_availability(
        [{"player_id": "p1", "name": "Different Display Name"}, {"player_id": "p2", "name": "Available"}],
        {**evidence("ownership"), "owned_player_ids": {"p1"}},
        {**evidence("eligibility"), "eligible_player_ids": {"p1", "p2"}},
    )
    assert [row["player_id"] for row in result["candidates"]] == ["p2"]


def test_fresh_complete_evidence_can_publish_candidates():
    result = evaluate_waiver_availability(
        [{"player_id": "p2", "name": "Available"}],
        {**evidence("ownership"), "owned_player_ids": set()},
        {**evidence("eligibility"), "eligible_player_ids": {"p2"}},
    )
    assert result["allowed"] is True
    assert result["candidates"][0]["verified_available"] is True


def test_unknown_or_stale_evidence_blocks_candidates():
    for state in ("UNAVAILABLE", "STALE"):
        result = evaluate_waiver_availability(
            [{"player_id": "p2"}],
            {**evidence("ownership", state=state), "owned_player_ids": set()},
            {**evidence("eligibility"), "eligible_player_ids": {"p2"}},
        )
        assert result["candidates"] == []
        assert result["allowed"] is False


def test_missing_threshold_fails_closed_instead_of_claiming_freshness():
    result = waiver_evidence_contract(
        domain="ownership",
        source_record_time="2026-09-13T10:00:00+00:00",
        retrieved_at="2026-09-13T10:05:00+00:00",
        freshness_state="FRESH",
        completeness_state="COMPLETE",
        expected_active_roster_count=0,
        observed_active_roster_count=0,
        require_roster_coverage=True,
        require_timestamps=True,
    )
    assert result["freshness_state"] == "BLOCKED"
    assert result["blocker"] == "WAIVER_FRESHNESS_THRESHOLD_UNVERIFIED"


def test_roster_coverage_and_timestamps_are_required():
    result = waiver_evidence_contract(
        domain="ownership",
        freshness_threshold_id="waiver-test-threshold",
        freshness_state="FRESH",
        completeness_state="COMPLETE",
        require_roster_coverage=True,
        require_timestamps=True,
    )
    assert result["allowed"] is False
    assert result["blocker"] == "WAIVER_SOURCE_TIMESTAMP_MISSING"


def test_observed_roster_count_below_expected_blocks():
    result = waiver_evidence_contract(
        domain="ownership",
        source_record_time="2026-09-13T10:00:00+00:00",
        retrieved_at="2026-09-13T10:05:00+00:00",
        freshness_threshold_id="waiver-test-threshold",
        freshness_state="FRESH",
        completeness_state="COMPLETE",
        expected_active_roster_count=12,
        observed_active_roster_count=11,
        require_roster_coverage=True,
        require_timestamps=True,
    )
    assert result["allowed"] is False
    assert result["blocker"] == "WAIVER_ROSTER_COVERAGE_INCOMPLETE"


def test_roster_coverage_rejects_missing_and_duplicate_ids():
    result = waiver_roster_coverage(
        [{"roster_id": "r1", "players": []}, {"roster_id": "r1", "players": []}, {"players": []}],
        expected_count=3,
    )
    assert result["allowed"] is False
    assert result["completeness_state"] == "INCOMPLETE"
    assert "WAIVER_ROSTER_ID_MISSING" in result["blockers"]
    assert "WAIVER_DUPLICATE_ROSTER_IDS" in result["blockers"]


def test_roster_coverage_requires_configured_expected_count():
    result = waiver_roster_coverage([{"roster_id": "r1", "players": []}])
    assert result["allowed"] is False
    assert result["blockers"] == ["WAIVER_EXPECTED_ROSTER_COUNT_UNAVAILABLE"]


def test_eligibility_contract_remains_blocked_when_unsupported():
    result = evaluate_waiver_availability(
        [{"player_id": "p1"}],
        {**evidence("ownership"), "owned_player_ids": set()},
        {
            **evidence("eligibility", blocker="WAIVER_ADD_ELIGIBILITY_CONTRACT_UNVERIFIED"),
            "eligible_player_ids": {"p1"},
        },
    )
    assert result["candidates"] == []
    assert result["allowed"] is False


def test_active_template_explains_blocked_evidence():
    template = Environment(loader=FileSystemLoader(Path(__file__).parents[1] / "templates")).from_string(
        "{% extends 'waivers.html' %}"
    )
    rendered = template.render(
        title="Waivers",
        url_for=lambda endpoint, **kwargs: "#",
        ux_route_evidence=lambda page, count: {"fields": {}},
        recommendations=[],
        needs=[],
        vacancies=[],
        waiver_evidence={
            "allowed": False,
            "blockers": ["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"],
            "ownership": {"source": "Sleeper API", "freshness_state": "BLOCKED"},
            "eligibility": {"source": "local player catalog", "freshness_state": "UNAVAILABLE"},
        },
    )
    assert "Recommendations blocked" in rendered
    assert "Sleeper API" in rendered
    assert "WAIVER_OWNERSHIP_RETRIEVAL_FAILED" in rendered