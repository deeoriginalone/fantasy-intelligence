from datetime import datetime, timezone, timedelta
import json
import re
import pytest

from services.ux_evidence import derived_waiver_availability, evaluate_waiver_availability, resolve_waiver_candidate_identity, waiver_evidence_contract, waiver_ownership_freshness, waiver_roster_coverage
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from owner_operations import attach_waiver_opportunity_identity, waiver_candidate_context, waiver_projection_contribution, waiver_recent_production, waiver_snap_share


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

    def test_projection_contribution_is_available_with_warning_metadata():
        result = waiver_projection_contribution({
            "projection": 18.4,
            "projection_retrieved_at": "2026-09-16T12:00:00+00:00",
            "identity_resolution": {"resolution_state": "RESOLVED"},
            "projection_evidence": {"blockers": ["PROJECTION_UNIT_UNVERIFIED"]},
        })
        assert result == {
            "value": 18.4,
            "state": "AVAILABLE",
            "warnings": ["PROJECTION_UNIT_UNVERIFIED"],
        }

    def test_missing_or_unresolved_projection_contribution_is_unavailable():
        assert waiver_projection_contribution({"projection": None})["state"] == "UNAVAILABLE"
        assert waiver_projection_contribution({
            "projection": 18.4,
            "projection_retrieved_at": "2026-09-16T12:00:00+00:00",
            "identity_resolution": {"resolution_state": "AMBIGUOUS"},
        })["value"] is None


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


def test_rejected_transaction_history_preserves_blocked_publication():
    eligibility = waiver_evidence_contract(
        domain="eligibility",
        source="Sleeper transaction history (not current addability)",
        freshness_state="UNAVAILABLE",
        completeness_state="INCOMPLETE",
        blocker="WAIVER_TRANSACTION_HISTORY_NOT_CURRENT_ADDABILITY",
        authority_state="REJECTED",
        authority_detail="Completed historical events do not establish current add eligibility.",
    )
    result = evaluate_waiver_availability(
        [{"player_id": "p1"}],
        {**evidence("ownership"), "owned_player_ids": set()},
        {**eligibility, "eligible_player_ids": {"p1"}},
    )
    assert eligibility["authority_state"] == "REJECTED"
    assert "current add eligibility" in eligibility["authority_detail"]
    assert result["candidates"] == []
    assert result["blockers"] == ["WAIVER_TRANSACTION_HISTORY_NOT_CURRENT_ADDABILITY"]


@pytest.mark.parametrize(
    "proxy",
    [
        "unrostered_player",
        "catalog_player",
        "stable_player_id",
        "active_nfl_status",
        "position_eligibility",
        "recommendation_membership",
        "ownership_filtering_success",
    ],
)
def test_proxies_do_not_establish_independent_add_eligibility(proxy):
    candidate = {
        "player_id": "p1",
        "name": "Available Player",
        "catalog_present": True,
        "status": "Active",
        "position": "WR",
        "recommended": True,
    }
    ownership = {**evidence("ownership"), "owned_player_ids": set()}
    eligibility = {
        **evidence(
            "eligibility",
            blocker="WAIVER_ADD_ELIGIBILITY_CONTRACT_UNVERIFIED",
        ),
        "eligible_player_ids": {"p1"},
        "proxy": proxy,
    }

    result = evaluate_waiver_availability([candidate], ownership, eligibility)

    assert result["allowed"] is False
    assert result["candidates"] == []
    assert result["blockers"] == ["WAIVER_ADD_ELIGIBILITY_CONTRACT_UNVERIFIED"]


def test_ownership_freshness_uses_registry_and_calculates_age():
    now = datetime(2026, 9, 13, 12, tzinfo=timezone.utc)
    result = waiver_ownership_freshness(
        source_record_time=None,
        retrieved_at=(now - timedelta(seconds=60)).isoformat(),
        now=now,
    )
    assert result["freshness_threshold_id"] == "integrity.roster.v1"
    assert result["freshness_threshold_seconds"] == 3600
    assert result["freshness_state"] == "FRESH"
    assert result["age"] == 60
    assert result["allowed"] is True


def test_fresh_retrieved_roster_time_does_not_require_provider_source_time():
    now = datetime(2026, 9, 13, 12, tzinfo=timezone.utc)
    result = waiver_ownership_freshness(
        source_record_time=None,
        retrieved_at=(now - timedelta(seconds=60)).isoformat(),
        now=now,
    )
    assert result["source_record_time"] is None
    assert result["freshness_state"] == "FRESH"
    assert result["age"] == 60
    assert result["blocker"] is None
    assert result["allowed"] is True


def test_derived_availability_publishes_only_supported_unrostered_ids():
    ownership = {
        **waiver_ownership_freshness(
            retrieved_at="2026-09-13T11:59:00+00:00",
            now=datetime(2026, 9, 13, 12, tzinfo=timezone.utc),
        ),
        "owned_player_ids": {"owned"},
    }
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"owned", "available"},
        supported_positions={"WR"},
        candidates=[
            {"player_id": "owned", "position": "WR"},
            {"player_id": "available", "position": "WR"},
        ],
    )
    result = evaluate_waiver_availability(
        [
            {"player_id": "owned", "position": "WR"},
            {"player_id": "available", "position": "WR"},
        ],
        ownership,
        availability,
    )
    assert availability["authority_state"] == "DERIVED"
    assert availability["eligible_player_ids"] == {"available"}
    assert [candidate["player_id"] for candidate in result["candidates"]] == ["available"]


def test_derived_availability_excludes_unsupported_positions_and_ids():
    ownership = {
        **waiver_ownership_freshness(
            retrieved_at="2026-09-13T11:59:00+00:00",
            now=datetime(2026, 9, 13, 12, tzinfo=timezone.utc),
        ),
        "owned_player_ids": set(),
    }
    candidates = [
        {"player_id": "valid", "position": "WR"},
        {"player_id": "wrong-position", "position": "K"},
        {"player_id": "outside-universe", "position": "WR"},
        {"player_id": None, "position": "WR"},
    ]
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"valid", "wrong-position"},
        supported_positions={"WR"},
        candidates=candidates,
    )
    result = evaluate_waiver_availability(candidates, ownership, availability)
    assert availability["eligible_player_ids"] == {"valid"}
    assert availability["unsupported_player_ids"] == ["outside-universe", "wrong-position"]
    assert availability["missing_candidate_id_count"] == 1
    assert [candidate["player_id"] for candidate in result["candidates"]] == ["valid"]


def test_derived_availability_blocks_without_supported_universe_or_positions():
    ownership = {
        **waiver_ownership_freshness(retrieved_at="2026-09-13T12:00:00+00:00"),
        "owned_player_ids": set(),
    }
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids=set(),
        supported_positions=set(),
    )
    result = evaluate_waiver_availability(
        [{"player_id": "p1", "position": "WR"}], ownership, availability
    )
    assert availability["allowed"] is False
    assert availability["blocker"] == "WAIVER_SUPPORTED_PLAYER_UNIVERSE_UNAVAILABLE"
    assert result["candidates"] == []


def test_derived_availability_blocks_stale_ownership():
    ownership = {
        **waiver_ownership_freshness(
            retrieved_at="2026-09-13T10:00:00+00:00",
            now=datetime(2026, 9, 13, 12, tzinfo=timezone.utc),
        ),
        "owned_player_ids": set(),
    }
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"p1"},
        supported_positions={"WR"},
    )
    result = evaluate_waiver_availability(
        [{"player_id": "p1", "position": "WR"}], ownership, availability
    )
    assert result["candidates"] == []
    assert "WAIVER_OWNERSHIP_STALE" in result["blockers"]


def test_derived_availability_allows_missing_optional_enrichment():
    ownership = {
        **waiver_ownership_freshness(
            retrieved_at="2026-09-13T11:59:00+00:00",
            now=datetime(2026, 9, 13, 12, tzinfo=timezone.utc),
        ),
        "owned_player_ids": set(),
    }
    candidate = {
        "player_id": "p1",
        "position": "WR",
        "projection": None,
        "faab": None,
        "role": None,
        "duration": None,
        "risk": None,
    }
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"p1"},
        supported_positions={"WR"},
        candidates=[candidate],
    )
    result = evaluate_waiver_availability([candidate], ownership, availability)
    assert [candidate["player_id"] for candidate in result["candidates"]] == ["p1"]
    assert result["candidates"][0]["projection"] is None
    assert result["candidates"][0]["faab"] is None


def catalog():
    return {
        "p1": {"full_name": "Exact Player", "position": "WR", "team": "SEA"},
        "p2": {"full_name": "Duplicate Player", "position": "RB", "team": "DEN"},
        "p3": {"full_name": "Duplicate Player", "position": "RB", "team": "LV"},
    }


def normalize(value):
    return "".join(character for character in str(value).lower() if character.isalnum())


def test_candidate_identity_accepts_direct_catalog_id():
    result = resolve_waiver_candidate_identity(
        {"player_id": "p1", "player": "Different Display", "position": "WR", "nfl_team": "SEA"},
        catalog(),
        normalize,
    )
    assert result["resolution_state"] == "RESOLVED"
    assert result["resolution_method"] == "DIRECT_SLEEPER_ID"
    assert result["resolved_player_id"] == "p1"


def test_candidate_identity_rejects_unresolved_ambiguous_and_conflicting_matches():
    unresolved = resolve_waiver_candidate_identity(
        {"player": "Partial", "position": "WR"}, catalog(), normalize
    )
    ambiguous = resolve_waiver_candidate_identity(
        {"player": "Duplicate Player", "position": "RB"}, catalog(), normalize
    )
    conflicting = resolve_waiver_candidate_identity(
        {"player": "Exact Player", "position": "RB", "nfl_team": "SEA"}, catalog(), normalize
    )
    assert (unresolved["resolution_state"], unresolved["blocker"]) == (
        "UNRESOLVED", "WAIVER_CANDIDATE_ID_UNRESOLVED"
    )
    assert (ambiguous["resolution_state"], ambiguous["blocker"]) == (
        "AMBIGUOUS", "WAIVER_CANDIDATE_ID_AMBIGUOUS"
    )
    assert (conflicting["resolution_state"], conflicting["blocker"]) == (
        "CONFLICTING", "WAIVER_CANDIDATE_ID_CONFLICTING"
    )


def test_catalog_identity_index_normalizes_once_and_preserves_duplicate_matches():
    from services.ux_evidence import build_waiver_catalog_name_index

    calls = []
    def counted_normalize(value):
        calls.append(value)
        return normalize(value)

    players = catalog()
    index = build_waiver_catalog_name_index(players, counted_normalize)
    catalog_normalization_count = len(calls)
    exact = resolve_waiver_candidate_identity(
        {"player": "Exact Player", "position": "WR", "nfl_team": "SEA"},
        players, counted_normalize, index,
    )
    ambiguous = resolve_waiver_candidate_identity(
        {"player": "Duplicate Player", "position": "RB"},
        players, counted_normalize, index,
    )

    assert catalog_normalization_count == len(players)
    assert len(calls) == catalog_normalization_count + 2
    assert exact["resolution_state"] == "RESOLVED"
    assert ambiguous["resolution_state"] == "AMBIGUOUS"


def test_candidate_identity_rejects_unknown_direct_id_and_team_conflict():
    unsupported = resolve_waiver_candidate_identity(
        {"player_id": "missing", "player": "Exact Player", "position": "WR"}, catalog(), normalize
    )
    team_conflict = resolve_waiver_candidate_identity(
        {"player": "Exact Player", "position": "WR", "nfl_team": "DEN"}, catalog(), normalize
    )
    assert unsupported["resolution_state"] == "UNSUPPORTED"
    assert unsupported["blocker"] == "WAIVER_CANDIDATE_ID_UNSUPPORTED"
    assert team_conflict["resolution_state"] == "CONFLICTING"


def test_mixed_identity_candidates_publish_only_resolved_unrostered_id_once():
    ownership = {**evidence("ownership"), "owned_player_ids": {"owned"}}
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"available", "owned"},
        supported_positions={"WR"},
    )
    result = evaluate_waiver_availability(
        [
            {"player_id": "available", "position": "WR"},
            {"player_id": None, "position": "WR"},
            {"player_id": "owned", "position": "WR"},
            {"player_id": "available", "position": "WR"},
        ],
        ownership,
        availability,
    )
    assert result["allowed"] is True
    assert [candidate["player_id"] for candidate in result["candidates"]] == ["available"]


def test_published_candidates_are_limited_after_rostered_exclusion():
    ownership = {**evidence("ownership"), "owned_player_ids": {"rostered"}}
    availability = derived_waiver_availability(
        league_id="league-1",
        ownership=ownership,
        supported_player_ids={"rostered", "available"},
        supported_positions={"WR"},
    )
    evaluated = evaluate_waiver_availability(
        [
            {"player_id": "rostered", "position": "WR"},
            {"player_id": "available", "position": "WR"},
        ],
        ownership,
        availability,
    )
    assert [candidate["player_id"] for candidate in evaluated["candidates"][:1]] == ["available"]


def test_ownership_freshness_stale_blocks():
    now = datetime(2026, 9, 13, 12, tzinfo=timezone.utc)
    result = waiver_ownership_freshness(
        retrieved_at=(now - timedelta(seconds=3601)).isoformat(),
        now=now,
    )
    assert result["freshness_state"] == "STALE"
    assert result["blocker"] == "WAIVER_OWNERSHIP_STALE"
    assert result["allowed"] is False


def test_ownership_freshness_missing_timestamps_blocks():
    result = waiver_ownership_freshness()
    assert result["freshness_state"] == "BLOCKED"
    assert result["blocker"] == "WAIVER_RETRIEVED_AT_MISSING"
    result = waiver_ownership_freshness(source_record_time="2026-09-13T12:00:00+00:00")
    assert result["blocker"] == "WAIVER_RETRIEVED_AT_MISSING"


def test_retrieved_at_is_not_provider_source_time():
    result = waiver_ownership_freshness(
        source_record_time=None,
        retrieved_at="2026-09-13T12:00:00+00:00",
    )
    assert result["source_record_time"] is None
    assert result["age"] is not None
    assert result["freshness_state"] in {"FRESH", "STALE"}


def test_snapshot_fetched_at_is_not_provider_source_time():
    snapshot_fetched_at = "2026-09-13T12:00:00+00:00"
    result = waiver_ownership_freshness(
        source_record_time=None,
        retrieved_at=snapshot_fetched_at,
    )
    assert result["source_record_time"] is None
    assert result["retrieved_at"] == snapshot_fetched_at
    assert result["blocker"] != "WAIVER_SOURCE_TIMESTAMP_MISSING"


def test_missing_provider_source_time_does_not_block_publication():
    ownership = waiver_ownership_freshness(
        source_record_time=None,
        retrieved_at="2026-09-13T12:00:00+00:00",
        now=datetime(
            2026,
            9,
            13,
            12,
            5,
            0,
            tzinfo=timezone.utc,
        ),
    )
    eligibility = {
        **evidence("eligibility"),
        "eligible_player_ids": {"p1"},
    }
    result = evaluate_waiver_availability(
        [{"player_id": "p1"}],
        {**ownership, "owned_player_ids": set()},
        eligibility,
    )
    assert result["allowed"] is True
    assert [candidate["player_id"] for candidate in result["candidates"]] == ["p1"]


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


def render_waivers(**overrides):
    template = Environment(loader=FileSystemLoader(Path(__file__).parents[1] / "templates")).from_string(
        "{% extends 'waivers.html' %}"
    )
    context = {
        "title": "Waivers",
        "url_for": lambda endpoint, **kwargs: "#",
        "ux_route_evidence": lambda page, count: {"fields": {}},
        "recommendations": [],
        "preliminary_suggestions": [],
        "monitor_candidates": [],
        "health_excluded_diagnostics": {"excluded_count": 0, "reason_counts": {}, "source_freshness_counts": {}},
        "informational_candidates": [],
        "needs": [],
        "vacancies": [],
        "roster": [{"player": "Current Player", "position": "WR"}],
        "grades": {"WR": "B"},
        "wda_roster": [{"player_id": "roster-current", "player": "Current Player", "position": "WR", "projection": 100.0}],
        "wda_candidates": [{"player": "Waiver Candidate", "position": "WR", "projection": 120.0, "need": 1, "recommendation_state": "ACTIONABLE", "recommendation_blockers": []}],
        "waiver_evidence": {
            "allowed": True, "blockers": [], "ranking_confidence": "VERIFIED",
            "ownership": {"source": "Sleeper API", "freshness_state": "FRESH"},
            "eligibility": {"source": "local player catalog", "freshness_state": "FRESH"},
        },
    }
    context.update(overrides)
    return template.render(**context)


def preliminary_candidate(**overrides):
    candidate = {
        "player_id": "sleeper-preliminary",
        "player": "Healthy Candidate",
        "position": "WR",
        "recommendation_state": "PRELIMINARY_SUGGESTION",
        "recommendation_blockers": ["WAIVER_RANKING_SOURCE_UNVERIFIED"],
        "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API", "opportunity": {"state": "AVAILABLE", "reason": "Supported informational opportunity."}, "evidence_coverage": {"label": "Two-week comparison available"}},
        "recent_production": {"state": "AVAILABLE", "rows": []},
        "snap_share": {"state": "UNAVAILABLE", "rows": []},
        "opportunity_metrics": {"state": "AVAILABLE", "rows": []},
        "player_comparison": {"status": "UNAVAILABLE", "summary": [], "what_changed": {"changes": []}, "sample": {"weeks": 0}, "freshness": {"state": "UNAVAILABLE"}},
    }
    candidate.update(overrides)
    return candidate


def test_decision_assistant_dropdown_lists_rostered_players():
    candidate = preliminary_candidate()
    roster_player = {"player_id": "roster-current", "player": "Current Player", "position": "WR", "projection": 100.0}
    rendered = render_waivers(roster=[roster_player], wda_roster=[roster_player], preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert 'id="wda-player-select"' in rendered
    assert '<option value="roster-current" data-player-id="roster-current" selected>Current Player (WR)</option>' in rendered
    assert "Choose a preliminary candidate" not in rendered
    assert 'id="wda-candidates-data"' in rendered


def test_ranking_review_separates_pending_checks_from_started_game_records():
    source = {"horizons": {"this_week": {"state": "AVAILABLE", "ranks": {}, "diagnostics": [{"player": "Thursday Player", "classification": "CONFIRMED_STARTED_GAME", "reason": "Game already started", "raw_ecr": 10, "source_date": "2026-10-03", "raw_kickoff": 1790900100}, {"player": "Active Pending Player", "classification": "PENDING_VERIFICATION", "reason": "KICKOFF_CURRENT_TEAM_NOT_SUPPLIED", "raw_ecr": 100, "sleeper_check": {"team": None, "status": "Active", "injury_status": None}}]}}}
    rendered = render_waivers(ranking_source=source)
    assert "Pending verification (1)" in rendered
    assert "Confirmed source/timing exclusions (1)" in rendered
    assert 'id="this_week-confirmed-exclusions"' in rendered
    assert "None listed; not an injury exclusion" in rendered
    assert "Eligible unrostered players remain available for long-term review" in rendered


def test_decision_assistant_blocked_when_evidence_blocked():
    rendered = render_waivers(waiver_evidence={
        "allowed": False, "blockers": ["WAIVER_OWNERSHIP_RETRIEVAL_FAILED"],
        "ownership": {"source": "Sleeper API", "freshness_state": "BLOCKED"},
        "eligibility": {"source": "local player catalog", "freshness_state": "UNAVAILABLE"},
    })
    assert "DECISION ASSISTANT BLOCKED" in rendered
    assert "WAIVER_OWNERSHIP_RETRIEVAL_FAILED" in rendered
    assert 'id="wda-player-select"' not in rendered


def test_decision_assistant_unavailable_when_no_preliminary_candidate_exists():
    rendered = render_waivers(preliminary_suggestions=[], wda_candidates=[])
    assert "MOVE CHECKER UNAVAILABLE" in rendered
    assert 'id="wda-player-select"' not in rendered


def test_decision_assistant_states_use_potential_upgrade_wording():
    candidate = preliminary_candidate()
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "SAME-POSITION AND FLEX-ELIGIBLE CANDIDATES TO REVIEW" in rendered
    assert "PROVISIONAL GUIDANCE" in rendered
    assert "POTENTIAL UPGRADE" not in rendered


def test_decision_assistant_no_upgrade_disclosure_present():
    candidate = preliminary_candidate()
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "consensus ranks are informational only" in rendered
    assert "not guaranteed winning bids" in rendered


def test_waiver_page_renders_action_before_diagnostics_and_separates_horizons():
    candidate = preliminary_candidate(
        candidate_disposition="PRELIMINARY_SUGGESTION",
        acquisition_evaluation={
            "action": "CONSIDER", "evidence_relevance": "MEANINGFUL_COMPARISON", "horizon": "IMMEDIATE", "would_start": "YES",
            "affected_slot": "WR", "roster_fit": "Could fill a supported WR starter-slot shortage; no points improvement is projected.",
            "suggested_drop": {"state": "UNAVAILABLE", "reason": "No supported drop comparison."},
            "reasons": ["One required WR starter slot is uncovered."], "risks": ["Expected role unavailable."],
            "confidence_rationale": "Preliminary roster-fit evidence only.",
            "faab": {"state": "UNAVAILABLE", "rationale": "No supported valuation."},
        },
    )
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])

    positions = [rendered.index(marker) for marker in (
        'id="waiver-title"', 'class="waiver-verdict"',
        'id="your-waiver-decisions"',
        'id="best-waiver-moves-title"', 'id="waiver-board-title"',
        'id="waiver-decision-assistant"', 'id="selected-waiver-primary"',
        'id="waiver-what-changed-title"',
        'id="waiver-evidence-methodology"',
    )]
    assert positions == sorted(positions)
    assert "YOUR WAIVER PLAN" in rendered
    assert "Best Waiver Moves for Your Team" not in rendered
    assert "Player-to-Roster Checks" in rendered
    assert "Rest of Season" in rendered and "Upside / Stash" in rendered
    assert "expected role and acquisition duration are not supported" in rendered
    assert 'data-acquisition-action="CONSIDER"' in rendered
    assert "samePosition || flexCandidate" in rendered
    assert "production comparisons remain same-position only" in rendered
    assert "url.searchParams.set('player_id', selectionControl.value)" in rendered
    assert "url.searchParams.set('focus'" in rendered
    assert '<details class="waiver-card" id="waiver-evidence-methodology">' in rendered


def test_selected_suggested_faab_is_prominent_immediately_after_comparison():
    rendered = render_waivers(
        preliminary_suggestions=[{"player_id": "candidate", "player": "Brian Robinson Jr.", "position": "RB", "recommendation_state": "PRELIMINARY_SUGGESTION"}],
        selected_player={"player_id": "selected", "player": "Mike Evans", "position": "WR"},
        selected_focus="this_week",
        selected_result={
            "decision": "ADD", "evidence_level": "PRELIMINARY", "roster_effect": "Improves the supported roster.",
            "comparison_summary": {"candidate_average": 15.13, "selected_average": 11.13, "sample_size": 3, "weeks": [{"season": 2026, "week": week} for week in (2, 3, 4)], "freshness_states": ["FRESH"], "sources": ["automated:nflverse"], "retrieved_at": ["2026-10-06T04:50:51Z"], "disclosure": "Historical evidence, not a forecast."},
            "suggested_drop": {"player": "Mike Evans", "reason": "Selected player is a safe drop."},
            "reasons": ["Supported comparison favors the candidate."], "concerns": ["Role duration unavailable."],
            "faab": {"state": "PROVISIONAL", "low": 1, "high": 3, "remaining": 79, "category": "FLEX_CHALLENGER", "rationale": "Provisional only."},
            "missing_evidence": ["expected role", "duration"],
        },
        selected_comparisons=[{"player_id": "candidate", "player": "Brian Robinson Jr.", "selected_comparison": {"decision": "ADD", "roster_effect": "Improves the supported roster.", "comparison_summary": {"disclosure": "Historical evidence."}}}],
    )

    observed = rendered.index("Observed comparison:")
    suggested = rendered.index('<p class="selected-faab">')
    depth = rendered.index("Sleeper depth chart:")
    assert observed < suggested < depth
    assert "FAAB:</strong> $1–$3 provisional · FLEX_CHALLENGER · $79 remaining" in rendered


def test_pagewide_best_moves_hides_team_need_only_candidate():
    candidate = preliminary_candidate(
        acquisition_evaluation={
            "action": "NO_RECOMMENDATION", "evidence_relevance": "SCREENING_ONLY",
            "horizon": "UNAVAILABLE", "roster_fit": "Addresses a generic depth need only.",
            "faab": {"state": "UNAVAILABLE", "category": "UNAVAILABLE", "rationale": "No bid."},
        },
    )
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[])
    best_moves = rendered[rendered.index('id="best-waiver-moves"'):rendered.index('id="waiver-board"')]

    assert "NO ACTIONABLE WAIVER PRIORITY" in best_moves
    assert "Team need, health, eligibility, rank, projection, and snap share alone are screening signals." in best_moves
    assert "Healthy Candidate" not in best_moves
    assert 'data-acquisition-action="NO_RECOMMENDATION"' not in best_moves


def test_pagewide_best_move_shows_free_news_and_depth_as_informational():
    candidate = preliminary_candidate(
        acquisition_evaluation={
            "action": "CONSIDER", "evidence_relevance": "DIRECTIONAL_SIGNAL", "horizon": "UNAVAILABLE",
            "roster_fit": "Current opportunity signal merits review.", "suggested_drop": {"reason": "No drop."},
            "reasons": ["Fresh matched opportunity change."], "risks": ["Role duration unavailable."],
            "confidence_rationale": "PRELIMINARY.", "faab": {"state": "NO_BID", "category": "NONE", "rationale": "No bid."},
        },
        sleeper_depth_chart={"state": "AVAILABLE", "team": "ATL", "position": "RB", "order": 2, "retrieved_at": COMPARISON_NOW, "decision_effect": "SCREENING_ONLY"},
        player_news={"state": "AVAILABLE", "freshness_state": "UNVERIFIED", "decision_effect": "INFORMATIONAL_ONLY", "articles": [{"headline": "Current player report", "description": "Dated report text.", "published_at": COMPARISON_NOW, "url": "https://espn.example/news"}], "blockers": []},
    )
    rendered = render_waivers(preliminary_suggestions=[candidate], selected_comparisons=[])
    best_moves = rendered[rendered.index('id="best-waiver-moves"'):rendered.index('id="waiver-board"')]

    assert "Current player report" in best_moves
    assert "Dated report text." in best_moves
    assert "ATL RB · order 2" in best_moves
    assert "freshness unverified, informational only" in best_moves
    assert "screening context only" in best_moves


def test_decision_assistant_missing_projection_handled_client_side():
    candidate = preliminary_candidate(projection=None)
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "candidateData.find" in rendered
    assert "candidate.recommendation_state === 'PRELIMINARY_SUGGESTION'" in rendered


def test_decision_assistant_informational_disclosure_present():
    candidate = preliminary_candidate()
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "same position" in rendered
    assert 'id="preliminary-candidates-title"' not in rendered
    assert "balanceData.state === 'AVAILABLE'" in rendered
    assert "bid.high <= balanceData.remaining" in rendered


def test_decision_assistant_filters_candidates_by_position_and_flex_eligibility():
    candidate = preliminary_candidate()
    roster_player = {"player_id": "roster-current", "player": "Current Player", "position": "WR", "projection": 100.0}
    kicker = {"player_id": "roster-kicker", "player": "Current Kicker", "position": "K", "projection": 100.0}
    rendered = render_waivers(roster=[roster_player, kicker], wda_roster=[kicker, roster_player], preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "candidate.recommendation_state === 'PRELIMINARY_SUGGESTION'" in rendered
    assert "var samePosition = candidatePosition === selectedPosition;" in rendered
    assert "var flexCandidate = selectedFlexEligible && flexPositions.indexOf(candidatePosition) !== -1;" in rendered
    assert '<option value="roster-current" data-player-id="roster-current" selected>Current Player (WR)</option>' in rendered
    assert "No verified-healthy preliminary candidates are available at " in rendered


def test_decision_assistant_uses_paginated_cards_without_truncating_pool():
    candidates = [preliminary_candidate(player_id=f"candidate-{index}", player=f"Candidate {index}") for index in range(14)]
    rendered = render_waivers(preliminary_suggestions=candidates, wda_candidates=candidates)
    payload = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', rendered, re.S).group(1))
    assert len(payload) == 14
    assert 'class="wda-suggestion"' in rendered
    assert 'class="wda-grid"' in rendered
    assert "var pageSize = 6;" in rendered
    assert "preliminaryCandidates.slice(pageStart, pageStart + pageSize)" in rendered
    assert "pageIndex = 0; renderCandidates();" in rendered
    assert 'aria-label="Previous candidates"' in rendered
    assert 'aria-label="Next candidates"' in rendered
    assert "<details><summary>Player evidence</summary>" in rendered
    assert "Owner-approved unique name, position and team match; not a source-published crosswalk." in rendered
    assert rendered.count('class="waiver-verdict"') == 1
    assert rendered.index('class="waiver-verdict"') < rendered.index('id="waiver-decision-assistant"')


def test_decision_assistant_never_uses_authoritative_drop_or_keep_wording():
    rendered = render_waivers()
    assert "DROP PLAYER" not in rendered
    assert "KEEP PLAYER" not in rendered
    assert "meaningful improvement" not in rendered


def test_decision_assistant_projection_zero_treated_as_missing():
    from owner_operations import wda_projection_or_none
    assert wda_projection_or_none(0.0) is None
    assert wda_projection_or_none(None) is None
    assert wda_projection_or_none(18.4) == 18.4


def test_waiver_roster_comparison_uses_matched_weeks_and_preserves_zero():
    from owner_operations import waiver_roster_comparison
    def player(points):
        return {"position": "WR", "recent_production": {"state": "AVAILABLE", "rows": [{"season": 2026, "week": week, "fantasy_points_ppr": value, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for week, value in points]}}
    result = waiver_roster_comparison(player([(1, 30), (2, 0), (3, 20)]), player([(2, 10), (3, 5)]))
    assert result["state"] == "PRELIMINARY"
    assert result["weeks"] == [{"season": 2026, "week": 2}, {"season": 2026, "week": 3}]
    assert result["candidate_average"] == 10
    assert result["roster_average"] == 7.5
    assert result["difference"] == 2.5
    assert result["decision_effect"] == "INFORMATIONAL_ONLY"
    assert waiver_roster_comparison(player([(1, 10)]), player([(2, 5)]))["state"] == "UNAVAILABLE"
    stale = player([(1, 10)])
    stale["recent_production"]["rows"][0]["freshness_state"] = "STALE"
    assert waiver_roster_comparison(stale, player([(1, 5)]))["state"] == "UNAVAILABLE"
    assert waiver_roster_comparison(player([(1, 10), (1, 20)]), player([(1, 5)]))["state"] == "UNAVAILABLE"


def test_live_faab_balance_and_provisional_bid_preserve_actual_budget():
    from owner_operations import waiver_faab_balance, waiver_provisional_bid
    league = {"settings": {"waiver_type": 2, "waiver_budget": 100}}
    users = [{"user_id": "owner", "is_owner": True}]
    rosters = [{"owner_id": "owner", "roster_id": 1, "settings": {"waiver_budget_used": 21}}]
    balance = waiver_faab_balance(league, users, rosters)
    assert balance["remaining"] == 79
    guidance = {"authority": "PROVISIONAL", "this_week": {"action": "REVIEW_ADD"}, "rest_of_season": {"action": "REVIEW_ADD"}}
    bid = waiver_provisional_bid(guidance, balance, False)
    assert (bid["low"], bid["high"]) == (1, 3)
    assert bid["state"] == "PROVISIONAL"
    assert waiver_provisional_bid(guidance, {"state": "UNAVAILABLE"}, False)["high"] is None
    assert waiver_provisional_bid(guidance, {"state": "AVAILABLE", "remaining": 0}, False)["high"] is None
    assert waiver_provisional_bid(guidance, {"state": "AVAILABLE", "remaining": 1}, True)["high"] == 1
    rosters[0]["settings"]["waiver_budget_used"] = 101
    assert waiver_faab_balance(league, users, rosters)["remaining"] is None
    rosters[0]["settings"] = {}
    assert waiver_faab_balance(league, users, rosters)["remaining"] is None
    assert waiver_faab_balance(league, users + users, rosters)["remaining"] is None
    assert waiver_faab_balance({}, users, rosters)["state"] == "NOT_APPLICABLE"


def test_provisional_waiver_guidance_separates_weekly_and_season_decisions():
    from owner_operations import waiver_move_guidance
    def production(points):
        return {"state": "AVAILABLE", "rows": [{"season": 2026, "week": index + 1, "fantasy_points_ppr": value, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for index, value in enumerate(points)]}
    candidate = preliminary_candidate(recent_production=production([8, 15, 18]))
    candidate["evidence_context"].update(ownership_state="VERIFIED", eligibility_state="VERIFIED")
    roster_player = {"player_id": "roster", "player": "Bench Player", "position": "WR", "is_starter": False, "recent_production": production([10, 10, 10])}
    guidance = waiver_move_guidance(candidate, roster_player)
    assert guidance["authority"] == "PROVISIONAL"
    assert guidance["this_week"]["action"] == "MONITOR"
    assert guidance["rest_of_season"]["action"] == "MONITOR"
    assert "duration are unavailable" in guidance["rest_of_season"]["reason"]
    assert "No drop suggestion is supported" in guidance["drop_review"]
    assert guidance["faab"] is None
    roster_player["is_starter"] = True
    assert "No drop is supported" in waiver_move_guidance(candidate, roster_player)["drop_review"]
    candidate["recent_production"] = production([30, 20, 0])
    guidance = waiver_move_guidance(candidate, roster_player)
    assert guidance["this_week"]["action"] == "MONITOR"
    assert guidance["rest_of_season"]["action"] == "MONITOR"
    candidate["recent_production"] = production([0, 0, 0])
    guidance = waiver_move_guidance(candidate, roster_player)
    assert guidance["this_week"]["action"] == "KEEP"
    assert guidance["rest_of_season"]["action"] == "MONITOR"


def test_waiver_recent_production_prefers_gsis_identity(monkeypatch):
    observed = {}

    def fake_reader(connection, **kwargs):
        observed.update(kwargs)
        return {"state": "AVAILABLE", "rows": [{"week": 3, "fantasy_points_ppr": 14.8}]}

    monkeypatch.setattr("owner_operations.read_player_production", fake_reader)
    result = waiver_recent_production(
        object(),
        {"player_id": "5045", "sleeper_gsis_id": "00-0034348", "position": "WR"},
        2026,
    )
    assert observed["player_id"] == "00-0034348"
    assert result["state"] == "AVAILABLE"


def test_waiver_recent_production_drops_rows_when_reader_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "owner_operations.read_player_production",
        lambda connection, **kwargs: {"state": "BLOCKED", "rows": [{"week": 3, "fantasy_points_ppr": None}], "blockers": ["PLAYER_WEEK_PRODUCTION_VALUE_UNAVAILABLE"]},
    )
    result = waiver_recent_production(object(), {"player_id": "00-1", "position": "WR"}, 2026)
    assert result["state"] == "BLOCKED"
    assert result["rows"] == []


def test_waiver_candidate_context_reuses_need_and_discloses_projection_only_drop():
    context = waiver_candidate_context(
        {"player": "Add", "position": "WR", "projection": 120.0, "recent_production": {"state": "AVAILABLE"}},
        [{"player": "Roster WR", "position": "WR", "projection": 90.0}],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": ["2 WR option(s) are available against a depth target of 4."]}},
        "VERIFIED",
    )
    assert context["roster_fit"]["label"] == "improves depth"
    assert context["suggested_drop"]["state"] == "UNAVAILABLE"
    assert "No supported ADD/DROP conclusion" in context["suggested_drop"]["reason"]
    assert context["confidence"] == "preliminary observed production evidence; not a forecast"


def test_waiver_candidate_context_preserves_unavailable_news_and_role_reasons():
    context = waiver_candidate_context(
        {"player": "Add", "position": "TE", "recent_production": {"state": "UNAVAILABLE"}},
        [],
        {"TE": {"state": "BLOCKED"}},
        "UNVERIFIED",
    )
    assert "no verified player-news source" in context["news"]["reason"]
    assert "no verified role contract" in context["role"]["reason"]
    assert "No supported ADD/DROP conclusion" in context["suggested_drop"]["reason"]


def test_waiver_candidate_context_states_preserve_identity_and_source_limits():
    identity_limited = waiver_candidate_context({"player": "A", "position": "WR", "projection": 100.0}, [], {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}}, "UNVERIFIED")
    assert identity_limited["context_state"] == "PARTIAL_CONTEXT"

    source_limited = waiver_candidate_context({"player": "B", "position": "WR", "opportunity_player_id": "gsis-b", "projection": None}, [], {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}}, "UNVERIFIED")
    assert source_limited["context_state"] == "SOURCE_LIMITED"

    full = waiver_candidate_context({"player": "C", "position": "WR", "opportunity_player_id": "gsis-c", "opportunity_metrics": {"state": "AVAILABLE", "rows": [{"target_share": 0.2, "carry_share": 0.1, "touch_share": 0.15}]}, "recent_production": {"state": "AVAILABLE"}}, [], {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}}, "VERIFIED")
    assert full["context_state"] == "FULL_CONTEXT"


def test_identity_limited_candidate_with_projection_emits_partial_context():
    result = waiver_candidate_context(
        {"player": "Projection Candidate", "position": "WR", "projection": 120.0},
        [],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": ["Depth target is unmet."]}},
        "UNVERIFIED",
    )
    assert result["context_state"] == "PARTIAL_CONTEXT"
    assert "roster fit" in result["context_reason"]


def test_identity_limited_candidate_without_non_opportunity_evidence_remains_identity_limited():
    result = waiver_candidate_context(
        {"player": "Unknown Candidate", "position": "WR"},
        [],
        {"WR": {"state": "BLOCKED"}},
        "UNVERIFIED",
    )
    assert result["context_state"] == "IDENTITY_LIMITED"


def current_sleeper_health(status):
    return {
        "health_status_available": True,
        "injury_status": status,
        "injury_source": "Sleeper API",
        "health_fetched_at": datetime.now(timezone.utc).isoformat(),
        "health_freshness_state": "FRESH",
    }


def test_waiver_candidate_context_surfaces_existing_contract_states():
    result = waiver_candidate_context(
        {"player": "Healthy Add", "position": "WR", "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", **current_sleeper_health("Healthy")},
        [],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}},
        "UNVERIFIED",
    )
    assert result["ownership_state"] == "VERIFIED"
    assert result["eligibility_state"] == "VERIFIED"
    assert result["health_state"] == "HEALTHY"


@pytest.mark.parametrize("status", ["IR", "Injured Reserve", "Injured Reserve - Designated for Return"])
def test_waiver_candidate_context_preserves_injured_reserve_state(status):
    result = waiver_candidate_context(
        current_sleeper_health(status), [], {}, "UNVERIFIED"
    )
    assert result["health_state"] == "IR"
    assert result["health_source"] == "Sleeper API"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("Questionable", "QUESTIONABLE"),
        ("Doubtful", "DOUBTFUL"),
        ("Out", "OUT"),
        ("Suspended", "UNAVAILABLE"),
        ("PUP", "UNAVAILABLE"),
        ("Active", "HEALTHY"),
        ("Healthy", "HEALTHY"),
        ("Healthy / Not listed", "UNAVAILABLE"),
    ],
)
def test_waiver_candidate_context_preserves_supported_live_health_mappings(status, expected):
    result = waiver_candidate_context(
        current_sleeper_health(status), [], {}, "UNVERIFIED"
    )
    assert result["health_state"] == expected


def _waiver_gate_candidate(status="Active"):
    from owner_operations import _waiver_candidate_health
    candidate = _waiver_candidate_health(
        {"injury_status": status}, datetime.now(timezone.utc).isoformat(), True
    )
    candidate.update(
        ownership_state="VERIFIED",
        eligibility_state="VERIFIED",
        player_id="sleeper-1",
        identity_resolution={"resolution_state": "RESOLVED", "resolution_method": "DIRECT_SLEEPER_ID"},
        opportunity_player_id="gsis-1",
        opportunity_identity_state="RESOLVED",
        opportunity_metrics={"state": "AVAILABLE", "rows": [{"week": 3, "target_share": 0.2}]},
    )
    return candidate


def test_waiver_recommendation_gate_keeps_verified_rank_preliminary():
    from owner_operations import waiver_candidate_recommendation_state
    candidate = _waiver_gate_candidate("Active")

    assert candidate["health_freshness_state"] == "FRESH"
    assert waiver_candidate_recommendation_state(candidate, "VERIFIED")["recommendation_state"] == "PRELIMINARY_SUGGESTION"
    assert waiver_candidate_recommendation_state(candidate, "UNVERIFIED")["recommendation_state"] == "PRELIMINARY_SUGGESTION"


@pytest.mark.parametrize("status", ["IR", "Injured Reserve", "Questionable", "Doubtful", "Out"])
def test_waiver_recommendation_gate_blocks_non_actionable_health(status):
    from owner_operations import waiver_candidate_recommendation_state
    assert waiver_candidate_recommendation_state(_waiver_gate_candidate(status), "VERIFIED")["recommendation_state"] == "NON_ACTIONABLE_HEALTH"


@pytest.mark.parametrize("status", [None, "Suspended", "PUP", "Inactive", "Practice Squad"])
def test_waiver_recommendation_gate_fails_closed_for_unverified_health(status):
    from owner_operations import _waiver_candidate_health, waiver_candidate_recommendation_state
    record = {"injury_status": status} if status is not None else {}
    candidate = _waiver_candidate_health(record, datetime.now(timezone.utc).isoformat(), True)
    candidate.update(ownership_state="VERIFIED", eligibility_state="VERIFIED")
    assert waiver_candidate_recommendation_state(candidate, "VERIFIED")["recommendation_state"] == "HEALTH_UNVERIFIED"


def test_preliminary_suggestion_requires_stable_identity_and_supported_evidence():
    from owner_operations import waiver_candidate_recommendation_state
    unresolved = _waiver_gate_candidate("Healthy")
    unresolved["identity_resolution"] = {"resolution_state": "UNRESOLVED"}
    assert waiver_candidate_recommendation_state(unresolved, "UNVERIFIED")["candidate_disposition"] == "HEALTH_BLOCKED"

    zero_only = _waiver_gate_candidate("Healthy")
    zero_only["recent_production"] = {"state": "UNAVAILABLE", "rows": []}
    zero_only["opportunity_metrics"] = {"state": "UNAVAILABLE", "rows": []}
    zero_only["snap_share"] = {"state": "UNAVAILABLE", "rows": []}
    zero_only["projection"] = 0.0
    zero_only["projection_retrieved_at"] = datetime.now(timezone.utc).isoformat()
    zero_only["evidence_context"] = {"roster_fit": {"state": "BLOCKED"}}
    gate = waiver_candidate_recommendation_state(zero_only, "UNVERIFIED")
    assert gate["candidate_disposition"] == "HEALTH_BLOCKED"
    assert "WAIVER_CANDIDATE_EVIDENCE_UNAVAILABLE" in gate["recommendation_blockers"]


def test_waiver_recommendation_gate_rejects_stale_and_contradictory_health():
    from owner_operations import _waiver_candidate_health, waiver_candidate_recommendation_state
    candidate = _waiver_gate_candidate("Healthy")
    candidate["health_freshness_state"] = "STALE"
    assert waiver_candidate_recommendation_state(candidate, "VERIFIED")["recommendation_state"] == "HEALTH_UNVERIFIED"

    stale_source = _waiver_candidate_health(
        {"injury_status": "Active"}, "2026-09-01T00:00:00+00:00", True
    )
    assert stale_source["health_freshness_state"] == "STALE"
    assert waiver_candidate_recommendation_state(stale_source, "VERIFIED")["recommendation_state"] == "HEALTH_UNVERIFIED"
    stale_context = waiver_candidate_context(stale_source, [], {}, "VERIFIED")
    assert stale_context["health_state"] == "UNAVAILABLE"
    assert stale_context["health_freshness_state"] == "STALE"
    assert stale_context["health_source"] == "Sleeper API"

    contradictory = _waiver_candidate_health(
        {"injury_status": "IR", "status": "Active"}, datetime.now(timezone.utc).isoformat(), True
    )
    contradictory.update(ownership_state="VERIFIED", eligibility_state="VERIFIED")
    assert contradictory["health_blocker"] == "WAIVER_HEALTH_STATUS_CONTRADICTORY"
    assert waiver_candidate_recommendation_state(contradictory, "VERIFIED")["recommendation_state"] == "HEALTH_UNVERIFIED"


def test_local_healthy_not_listed_placeholder_cannot_authorize_waiver_health():
    from owner_operations import _waiver_candidate_health
    candidate = _waiver_candidate_health(
        {"injury_status": "Healthy / Not listed"}, datetime.now(timezone.utc).isoformat(), True
    )
    assert candidate["health_status_available"] is False
    assert candidate["health_blocker"] == "WAIVER_HEALTH_STATUS_UNSUPPORTED"


def test_waiver_candidate_context_does_not_trust_local_healthy_placeholder():
    result = waiver_candidate_context(
        {"injury_status": "Healthy / Not listed"}, [], {}, "UNVERIFIED"
    )
    assert result["health_state"] == "UNAVAILABLE"
    assert result["health_source"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    ("catalog_record", "identity_resolved"),
    [
        ({}, True),
        ({"injury_status": "IR"}, False),
        ({"injury_status": "IR", "status": "Active"}, True),
        ({"injury_status": "Practice Squad"}, True),
    ],
)
def test_waiver_candidate_health_fails_closed(catalog_record, identity_resolved):
    from owner_operations import _waiver_candidate_health
    candidate = _waiver_candidate_health(catalog_record, "retrieved-at", identity_resolved)
    context = waiver_candidate_context(candidate, [], {}, "UNVERIFIED")
    assert candidate["health_status_available"] is False
    assert context["health_state"] == "UNAVAILABLE"
    assert context["health_source"] == "UNAVAILABLE"


def test_waiver_template_includes_projection_retrieval_visibility():
    from pathlib import Path
    template = (Path(__file__).parents[1] / "templates" / "waivers.html").read_text(encoding="utf-8")
    assert "Projection evidence" in template
    assert "projection_retrieved_at" in template or "projectionRetrieved" in template


def test_waiver_template_surfaces_usage_and_collapses_repeated_limitations():
    rendered = render_waivers(
        preliminary_suggestions=[{
            "player_id": "sleeper-healthy",
            "player": "Healthy Candidate",
            "position": "WR",
            "recommendation_state": "PRELIMINARY_SUGGESTION",
            "ownership_state": "VERIFIED",
            "eligibility_state": "VERIFIED",
            "health_fetched_at": COMPARISON_NOW,
            "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API", "opportunity": {"state": "AVAILABLE", "reason": "Targets: 7."}, "opportunity_strength": {"state": "LIMITED"}, "usage_stability": {"state": "STABLE"}, "opportunity_trend": {"state": "STABLE", "drivers": []}, "evidence_coverage": {"label": "Two-week comparison available"}, "ranking": {"state": "UNVERIFIED"}},
            "recent_production": {"state": "UNAVAILABLE", "rows": []},
            "snap_share": {"state": "UNAVAILABLE", "rows": [], "blockers": ["SNAP_SHARE_READER_NO_ROWS"]},
            "opportunity_metrics": {"state": "AVAILABLE", "rows": []},
            "player_comparison": {"status": "UNAVAILABLE", "summary": [], "what_changed": {"changes": []}, "sample": {"weeks": 0}, "freshness": {"state": "UNAVAILABLE"}, "limitations": []},
        }],
        waiver_opportunity_status={"state": "PRELIMINARY", "impact": "research only", "candidate_count": 1},
        wda_candidates=[{"player_id": "sleeper-healthy", "player": "Healthy Candidate", "position": "WR", "recommendation_state": "PRELIMINARY_SUGGESTION", "recommendation_blockers": []}],
    )
    assert "Usage Evidence" in rendered
    assert "Snap share:" in rendered
    assert "Informational" in rendered
    assert "STALE" in rendered
    assert "Team Need" in rendered
    assert "What Changed" in rendered
    assert "Evidence Coverage" in rendered
    assert "What Changed This Week" in rendered
    assert "Evidence limitations" in rendered
    evidence_script_start = rendered.index("summary.innerHTML =")
    evidence_summary = rendered[evidence_script_start:rendered.index("if (identity) identity.insertAdjacentElement", evidence_script_start)]
    assert evidence_summary.index("<strong>Health:</strong>") < evidence_summary.index("<strong>Team Need:</strong>") < evidence_summary.index("<strong>Roster Fit:</strong>") < evidence_summary.index("<strong>Projection:</strong>") < evidence_summary.index("<strong>Recent Production:</strong>") < evidence_summary.index("<strong>Usage Evidence:</strong>") < evidence_summary.index("<strong>What Changed:</strong>") < evidence_summary.index("<strong>Suggested Drop:</strong>") < evidence_summary.index("<strong>FAAB:</strong>")
    assert "Role:</strong>" not in rendered
    assert "Duration:</strong>" not in rendered
    assert "Latest News:</strong>" not in rendered
    assert "Ranking:</strong>" not in rendered
    assert rendered.count("Role classification unavailable") == 1
    assert rendered.count("Opportunity duration unavailable") == 1
    assert rendered.count("Latest news unavailable") == 1
    assert rendered.count("Ranking authority unavailable") >= 1


def test_fresh_opportunity_panel_is_informational_without_refresh_blocker():
    rendered = render_waivers(
        waiver_opportunity_status={"state": "PRELIMINARY", "impact": "Research only; no ranking, FAAB, or ADD/DROP authority.", "candidate_count": 1},
        opportunity_view={"current": {"authoritative": False, "recommendation_impact": "Opportunity evidence cannot support a recommendation until refreshed and verified."}},
        preliminary_suggestions=[{"player_id": "sleeper-1", "player": "Fresh Candidate", "position": "WR", "recommendation_state": "PRELIMINARY_SUGGESTION", "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API", "opportunity": {"state": "AVAILABLE", "reason": "Fresh published rows are available."}, "evidence_coverage": {"label": "Two-week comparison available"}}}],
        wda_candidates=[{"player_id": "sleeper-1", "player": "Fresh Candidate", "position": "WR", "recommendation_state": "PRELIMINARY_SUGGESTION", "recommendation_blockers": []}],
    )
    assert "Fresh published opportunity evidence is available for informational research (1 candidates)." in rendered
    assert "does not authorize ranking, FAAB, or ADD/DROP conclusions" in rendered
    assert "until refreshed and verified" not in rendered


def test_stale_opportunity_panel_preserves_stale_blocker():
    rendered = render_waivers(
        waiver_opportunity_status={"state": "STALE", "impact": "Published opportunity evidence is stale and is not presented as current.", "blocker": "OPPORTUNITY_DATA_STALE"},
    )
    assert "STALE: Published opportunity evidence is stale" in rendered
    assert "OPPORTUNITY_DATA_STALE" in rendered
    assert "PRELIMINARY: Fresh published opportunity evidence" not in rendered


def test_waiver_snap_share_is_display_only_and_has_owner_approved_window():
    result = waiver_snap_share(None, {}, 2026)
    assert result["state"] == "UNAVAILABLE"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"
    assert result["display_max_age_seconds"] == 86400


def test_waiver_snap_share_retains_stale_observation_for_display(monkeypatch):
    monkeypatch.setattr(
        "owner_operations.read_snap_share",
        lambda connection, **kwargs: {"state": "STALE", "rows": [{"week": 1, "snap_share": 0.75, "freshness_state": "STALE"}], "blockers": ["SNAP_SHARE_EVIDENCE_STALE"]},
    )
    result = waiver_snap_share(object(), {"opportunity_player_id": "gsis-1"}, 2026)
    assert result["state"] == "STALE"
    assert result["rows"][0]["snap_share"] == 0.75
    assert result["decision_effect"] == "NONE"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"


def test_waiver_candidate_context_exposes_raw_opportunity_metrics_without_thresholds():
    context = waiver_candidate_context(
        {"player": "Add", "position": "WR", "projection": 120.0, "recent_production": {"state": "AVAILABLE"}, "snap_share": {"state": "AVAILABLE", "rows": [{"snap_share": 0.75}]}},
        [],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}},
        "VERIFIED",
    )
    assert context["snap_share"]["state"] == "AVAILABLE"
    assert "High snap" not in str(context)


def test_waiver_candidate_context_describes_evidence_coverage_without_duration_prediction():
    one_week = waiver_candidate_context(
        {"player": "Add", "position": "WR", "opportunity_player_id": "gsis-1", "opportunity_metrics": {"state": "AVAILABLE", "rows": [{"week": 1, "target_share": 0.2}]}, "recent_production": {"state": "AVAILABLE"}},
        [],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}},
        "VERIFIED",
    )
    two_week = waiver_candidate_context(
        {"player": "Add", "position": "WR", "opportunity_player_id": "gsis-1", "opportunity_metrics": {"state": "AVAILABLE", "rows": [{"week": 1, "target_share": 0.1}, {"week": 2, "target_share": 0.2}]}, "recent_production": {"state": "AVAILABLE"}},
        [],
        {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": []}},
        "VERIFIED",
    )
    assert one_week["evidence_coverage"]["label"] == "Week 1 evidence available; one observation only"
    assert two_week["evidence_coverage"]["label"] == "Two-week comparison available"
    assert "duration" not in one_week["evidence_coverage"]["label"].lower()


def test_waiver_identity_reuses_unique_espn_crosswalk_for_five_candidates():
    candidates = [{"player_id": str(index), "position": "WR"} for index in range(5)]
    catalog = {str(index): {"espn_id": f"espn-{index}"} for index in range(5)}
    metadata = [{"espn_id": f"espn-{index}", "gsis_id": f"gsis-{index}"} for index in range(5)]
    lineage = {"source": "nflverse.players", "source_authority": "automated:nflverse", "artifact_id": "players", "version": "v1", "checksum": "sha256:test", "retrieved_at": "2026-09-20T00:00:00Z", "coverage_state": "COMPLETE"}
    result = attach_waiver_opportunity_identity(candidates, catalog, metadata, lineage)
    assert [item["opportunity_player_id"] for item in result] == [f"gsis-{index}" for index in range(5)]
    assert all(item["opportunity_identity_method"] == "espn_id" for item in result)


def test_waiver_identity_fails_closed_for_missing_ambiguous_and_conflicting_espn():
    candidates = [{"player_id": "missing"}, {"player_id": "ambiguous"}, {"player_id": "conflict"}]
    catalog = {"missing": {}, "ambiguous": {"espn_id": "e2"}, "conflict": {"gsis_id": "g0", "espn_id": "e3"}}
    metadata = [{"espn_id": "e2", "gsis_id": "g2a"}, {"espn_id": "e2", "gsis_id": "g2b"}, {"espn_id": "e3", "gsis_id": "g3"}]
    lineage = {"source": "nflverse.players", "source_authority": "automated:nflverse", "artifact_id": "players", "version": "v1", "checksum": "sha256:test", "retrieved_at": "2026-09-20T00:00:00Z", "coverage_state": "COMPLETE"}
    result = attach_waiver_opportunity_identity(candidates, catalog, metadata, lineage)
    assert all("opportunity_player_id" not in item for item in result)


def test_waiver_identity_uses_exact_automated_mapping_and_preserves_order_and_bids():
    candidates = [
        {"player_id": "sleeper-1", "priority_score": 71.5, "confidence": "MEDIUM", "faab": 8, "bid_low": 4, "bid_high": 12},
        {"player_id": "sleeper-2", "priority_score": 64.0, "confidence": "LOW", "faab": 3, "bid_low": 1, "bid_high": 5},
    ]
    catalog = {"sleeper-1": {}, "sleeper-2": {}}
    metadata = [{"gsis_id": "gsis-1"}]
    nflverse_lineage = {"source": "nflverse.players", "source_authority": "automated:nflverse", "artifact_id": "players", "version": "v1", "checksum": "sha256:test", "retrieved_at": "2026-10-03T11:00:00Z", "coverage_state": "COMPLETE"}
    source = {
        "state": "AVAILABLE",
        "lineage": {"source": "https://raw.example/db_playerids.csv", "source_authority": "automated:DynastyProcess", "artifact_id": "db_playerids.csv", "version": "abc", "checksum": "sha256:test", "source_recorded_at": "2026-10-02T05:57:53Z", "retrieved_at": "2026-10-03T11:00:00Z", "completeness_state": "COMPLETE"},
        "mappings": [
            {"source_player_id": "sleeper-1", "gsis_id": "gsis-1", "state": "RESOLVED"},
            {"source_player_id": "sleeper-2", "gsis_id": None, "state": "UNRESOLVED", "blocker": "DYNASTYPROCESS_GSIS_ID_UNAVAILABLE"},
        ],
    }

    result = attach_waiver_opportunity_identity(candidates, catalog, metadata, nflverse_lineage, identity_source=source)

    assert [item["player_id"] for item in result] == ["sleeper-1", "sleeper-2"]
    assert result[0]["opportunity_player_id"] == "gsis-1"
    assert result[0]["opportunity_identity_method"] == "dynastyprocess_gsis_id"
    assert result[0]["opportunity_identity_lineage"]["identity_source"] == source["lineage"]
    assert "opportunity_player_id" not in result[1]
    for before, after in zip(candidates, result):
        for field in ("priority_score", "confidence", "faab", "bid_low", "bid_high"):
            assert after[field] == before[field]


def test_waiver_identity_blocks_duplicate_and_contradictory_external_mappings():
    candidates = [{"player_id": "duplicate"}, {"player_id": "conflict"}]
    catalog = {"duplicate": {}, "conflict": {}}
    metadata = [{"gsis_id": "gsis-1"}, {"gsis_id": "gsis-2"}]
    lineage = {"source": "nflverse.players", "source_authority": "automated:nflverse", "artifact_id": "players", "version": "v1", "checksum": "sha256:test", "retrieved_at": "2026-10-03T11:00:00Z", "coverage_state": "COMPLETE"}
    source = {"state": "AVAILABLE", "mappings": [
        {"source_player_id": "duplicate", "gsis_id": None, "state": "AMBIGUOUS", "blocker": "DYNASTYPROCESS_IDENTITY_DUPLICATE"},
        {"source_player_id": "conflict", "gsis_id": None, "state": "CONTRADICTORY", "blocker": "DYNASTYPROCESS_IDENTITY_CONTRADICTORY"},
    ]}

    result = attach_waiver_opportunity_identity(candidates, catalog, metadata, lineage, identity_source=source)

    assert [item["opportunity_identity_state"] for item in result] == ["AMBIGUOUS", "CONTRADICTORY"]
    assert all("opportunity_player_id" not in item for item in result)


def test_browse_candidates_render_recent_production_newest_first_and_preserve_zero():
    candidate = preliminary_candidate(player="Recent Player", recent_production={"state": "AVAILABLE", "rows": [{"week": 3, "fantasy_points_ppr": 0.0}, {"week": 2, "fantasy_points_ppr": 14.8}]})
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    data = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', rendered, re.S).group(1))
    assert [row["week"] for row in data[0]["recent_production"]["rows"]] == [3, 2]
    assert data[0]["recent_production"]["rows"][0]["fantasy_points_ppr"] == 0.0
    assert "Number(row.fantasy_points_ppr).toFixed(1)" in rendered


def test_browse_candidates_render_k_and_def_fail_closed_messages():
    candidates = [preliminary_candidate(player_id=position, position=position, recent_production={"state": "UNSUPPORTED", "rows": []}) for position in ("K", "DEF")]
    rendered = render_waivers(preliminary_suggestions=candidates, wda_candidates=candidates)
    data = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', rendered, re.S).group(1))
    assert all(item["recent_production"]["state"] == "UNSUPPORTED" and item["recent_production"]["rows"] == [] for item in data)
    assert "production.state === 'AVAILABLE' ? production.rows || [] : []" in rendered


def test_waiver_trust_panel_renders_evidence_and_unavailable_fields():
    templates = Environment(loader=FileSystemLoader(Path(__file__).parents[1] / "templates"))
    rendered = templates.get_template("_waiver_trust_panel.html").render(
        waiver_evidence={
            "ownership": {
                "source": "Sleeper API",
                "freshness_state": "FRESH",
                "retrieved_at": "2026-09-13T12:00:00+00:00",
                "completeness_state": "COMPLETE",
            },
            "eligibility": {
                "source": "Derived from current Sleeper rosters and supported player pool",
                "authority_state": "DERIVED",
                "freshness_state": "FRESH",
                "derivation": "supported pool minus rostered IDs",
                "identity_diagnostics": {
                    "total_source_candidates": 2,
                    "uniquely_canonical_resolved_count": 1,
                    "unresolved_count": 1,
                    "ambiguous_count": 0,
                    "rostered_exclusion_count": 0,
                },
            },
        },
        waiver_candidates=[{"player": "Available", "position": "WR", "need": 1, "projection": None, "faab": None}],
    )
    for text in (
        "Sleeper API",
        "FRESH",
        "2026-09-13 12:00:00 UTC",
        "Derived from current Sleeper rosters and supported player pool",
        "Authority: DERIVED",
        "Roster fit: Not supported",
        "Expected role: Unavailable",
        "FAAB: Unavailable",
        "Identity diagnostics",
        "Source candidates: 2",
    ):
        assert text in rendered


COMPARISON_NOW = "2026-09-20T18:00:00+00:00"


def comparison_rows(*weeks):
    return [
        {"week": week, "targets": targets, "target_share": share, "receptions": receptions, "receiving_yards": yards, "receiving_tds": 0,
         "freshness_state": "FRESH", "source": "automated:nflverse", "retrieved_at": "2026-09-20T12:00:00+00:00"}
        for week, targets, share, receptions, yards in weeks
    ]


def resolved_candidate(**updates):
    candidate = {
        "player": "Avail WR", "position": "WR", "player_id": "s-wr", "opportunity_player_id": "gsis-wr",
        "opportunity_identity_state": "RESOLVED", "opportunity_identity_method": "gsis_id",
        "opportunity_metrics": {"state": "AVAILABLE", "rows": comparison_rows((1, 4, 0.2, 3, 40), (2, 7, 0.27, 5, 71)), "blockers": []},
    }
    candidate.update(updates)
    return candidate


def test_player_comparison_uses_resolved_identity_and_is_informational():
    from owner_operations import waiver_player_comparison
    comparison = waiver_player_comparison(resolved_candidate())
    assert comparison["status"] == "PRELIMINARY"
    assert comparison["decision_effect"] == "NONE"
    assert comparison["comparison_identity"] == {"state": "RESOLVED", "opportunity_player_id": "gsis-wr", "method": "gsis_id"}
    assert comparison["what_changed"]["state"] == "AVAILABLE"
    assert "Target Share (Wk 2): 27%" in comparison["summary"]
    assert not {"rank", "score", "priority", "recommendation", "faab", "confidence"} & set(comparison)


def test_player_comparison_is_unavailable_when_evidence_missing_and_never_zero():
    from owner_operations import waiver_player_comparison
    missing = waiver_player_comparison(resolved_candidate(opportunity_metrics={"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_READER_NO_ROWS"]}))
    absent = waiver_player_comparison(resolved_candidate(opportunity_metrics=None))
    for comparison in (missing, absent):
        assert comparison["status"] == "UNAVAILABLE"
        assert comparison["usage"] == {} and comparison["production"] == {} and comparison["summary"] == []
        assert comparison["what_changed"] == {"state": "INSUFFICIENT_EVIDENCE", "changes": []}
    assert missing["blockers"] == ["OPPORTUNITY_READER_NO_ROWS"]


def test_player_comparison_identity_ambiguity_fails_closed():
    from owner_operations import waiver_player_comparison
    for state in ("AMBIGUOUS", "CONTRADICTORY", "BLOCKED"):
        comparison = waiver_player_comparison(resolved_candidate(opportunity_identity_state=state, opportunity_identity_blockers=["GSIS_NFLVERSE_ID_DUPLICATE"]))
        assert comparison["status"] == "BLOCKED"
        assert comparison["usage"] == {}
        assert comparison["comparison_identity"]["opportunity_player_id"] is None
    # A raw catalog GSIS ID without a resolved crosswalk is not trusted.
    unresolved = waiver_player_comparison(resolved_candidate(opportunity_identity_state="UNRESOLVED"))
    assert unresolved["status"] == "UNAVAILABLE" and unresolved["usage"] == {}


def test_player_comparison_fallback_is_deterministic():
    from owner_operations import waiver_player_comparison
    assert waiver_player_comparison(resolved_candidate()) == waiver_player_comparison(resolved_candidate())
    assert waiver_player_comparison({"player": "No Identity", "position": "RB"}) == waiver_player_comparison({"player": "No Identity", "position": "RB"})
    assert waiver_player_comparison(resolved_candidate(position="K"))["status"] == "NOT_APPLICABLE"


def test_waiver_template_renders_comparison_informationally():
    from owner_operations import waiver_player_comparison
    base = {"position": "WR", "priority_score": None, "tier": None, "projection": 100.0, "faab": None, "bid_low": None, "bid_high": None, "need": 1, "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "recommendation_state": "PRELIMINARY_SUGGESTION", "recent_production": {"state": "UNAVAILABLE", "rows": []}, "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API", "opportunity": {"reason": "Supported informational opportunity."}, "evidence_coverage": {"label": "Two-week comparison available"}}}
    available = {**base, "player": "Shown WR", "player_comparison": waiver_player_comparison(resolved_candidate())}
    unavailable = {**base, "player": "Missing WR", "faab": 7, "player_comparison": waiver_player_comparison({"player": "Missing WR", "position": "WR"})}
    rendered = render_waivers(preliminary_suggestions=[available, unavailable], wda_candidates=[available, unavailable])
    assert "Informational comparison:" in rendered
    assert "var comparison = candidate.player_comparison || {};" in rendered
    assert "var summary = (comparison.summary || []).join('; ') || 'UNAVAILABLE';" in rendered
    assert 'id="wda-candidates-data"' in rendered
    assert 'id="preliminary-candidates-title"' not in rendered
    assert "$7" not in rendered


class WaiverRouteCursor:
    def __init__(self, pool_rows, executed_queries):
        self.pool_rows = pool_rows
        self.executed_queries = executed_queries

    def execute(self, query, params=None):
        self.query = query
        self.params = params
        self.executed_queries.append(query)

    def fetchone(self):
        return None

    def fetchall(self):
        if "ORDER BY ranking" not in getattr(self, "query", ""):
            return []
        rows = list(self.pool_rows)
        return rows[:self.params[-1]] if "LIMIT %s" in self.query and self.params else rows

    def close(self):
        pass


class WaiverRouteConnection:
    def __init__(self, pool_rows):
        self.pool_rows = pool_rows
        self.executed_queries = []

    def cursor(self):
        return WaiverRouteCursor(self.pool_rows, self.executed_queries)

    def close(self):
        pass


def render_waiver_route(monkeypatch, *, rosters_available=True, disable_comparison=False, candidate_health=None, include_missing_candidate=False, ranking_source_verified=False, extra_candidate_count=0, production_rows=None, faab_settings=None, consensus=None, request_method="GET", testing=True, selected_player_id=None, extra_rostered_player=None, selected_focus="all", extra_pool_candidates=(), explain_player=None):
    from flask import Flask
    import owner_operations
    catalog = {
        "s-owned": {"full_name": "Owned WR", "position": "WR", "team": "KC", "gsis_id": "gsis-owned"},
        "s-wr": {"full_name": "Avail WR", "position": "WR", "team": "DEN", "gsis_id": "gsis-wr", "injury_status": "Healthy"},
        "s-rb": {"full_name": "Avail RB", "position": "RB", "team": "LV", "gsis_id": None},
    }
    for player_id, health_fields in (candidate_health or {}).items():
        catalog[player_id].update(health_fields)
    if extra_rostered_player:
        catalog[extra_rostered_player["player_id"]] = {
            "full_name": extra_rostered_player["player"],
            "position": extra_rostered_player["position"],
            "team": extra_rostered_player.get("team", "KC"),
            "gsis_id": extra_rostered_player.get("gsis_id"),
            "injury_status": extra_rostered_player.get("injury_status", "Healthy"),
        }
    pool_rows = [
        ("Owned WR", "WR", "KC", 1, 150.0, 1, 10.0, 9, None),
        ("Avail WR", "WR", "DEN", 2, 120.0, 2, 20.0, 9, None),
        ("Avail RB", "RB", "LV", 3, 110.0, 3, 30.0, 9, None),
    ]
    if include_missing_candidate:
        catalog["s-te"] = {"full_name": "Avail TE", "position": "TE", "team": "SEA", "gsis_id": None}
        pool_rows.append(("Avail TE", "TE", "SEA", 4, 90.0, 4, 40.0, 9, None))
    for index, candidate in enumerate(extra_pool_candidates):
        player_id = candidate["player_id"]
        catalog[player_id] = {
            "full_name": candidate["name"],
            "position": candidate["position"],
            "team": candidate["team"],
            "gsis_id": candidate.get("gsis_id"),
            "injury_status": candidate.get("injury_status", "Healthy"),
        }
        pool_rows.append((
            candidate["name"], candidate["position"], candidate["team"], index + 100,
            candidate.get("projection"), candidate.get("tier"), None, None, None,
        ))
    for index in range(extra_candidate_count):
        name = f"Deep Candidate {index}"
        status = ("Healthy", "Out", "IR", "Questionable")[index % 4]
        catalog[f"s-deep-{index}"] = {"full_name": name, "position": "WR", "team": "SEA", "injury_status": status}
        pool_rows.append((name, "WR", "SEA", index + 5, 80.0, 4, 50.0, 9, None))
    readers = {"gsis-wr": {"state": "AVAILABLE", "rows": comparison_rows((1, 4, 0.2, 3, 40), (2, 7, 0.27, 5, 71)), "blockers": [], "supported_weeks": [1, 2]}}
    captured = {}
    real_render = owner_operations.render_template

    def capture(name, **kwargs):
        captured.update(kwargs)
        return real_render(name, **kwargs)

    monkeypatch.setattr(owner_operations, "render_template", capture)
    monkeypatch.setattr(owner_operations, "enrich_players", lambda cur, roster, week, **kwargs: roster)
    monkeypatch.setattr(owner_operations, "current_week", lambda cur: 3)
    monkeypatch.setattr(owner_operations, "read_player_opportunity", lambda connection, player_id, season, **kwargs: dict(readers.get(player_id) or {"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_READER_NO_ROWS"]}))
    production_reads = []
    def read_production(*args, **kwargs):
        player_id = kwargs.get("player_id")
        production_reads.append(player_id)
        return {"state": "AVAILABLE", "rows": (production_rows or {})[player_id], "blockers": []} if player_id in (production_rows or {}) else {"state": "UNAVAILABLE", "rows": [], "blockers": ["PLAYER_WEEK_PRODUCTION_UNAVAILABLE"]}
    monkeypatch.setattr(owner_operations, "read_player_production", read_production)
    monkeypatch.setattr(owner_operations, "read_snap_share", lambda *args, **kwargs: {"state": "UNAVAILABLE", "rows": [], "blockers": ["SNAP_SHARE_UNAVAILABLE"]})
    if ranking_source_verified:
        original_contract = owner_operations.weekly_evidence_contract
        def verified_ranking_contract(**kwargs):
            result = original_contract(**kwargs)
            if kwargs.get("domain") == "waiver ranking inputs":
                result.update(authoritative=True, blocker=None)
            return result
        monkeypatch.setattr(owner_operations, "weekly_evidence_contract", verified_ranking_contract)
    if disable_comparison:
        monkeypatch.setattr(owner_operations, "waiver_player_comparison", lambda candidate: {})
    league = {"name": "Controlled", "total_rosters": 2, "roster_positions": ["QB", "RB", "WR", "WR", "TE", "K", "DEF", "BN"]}
    rosters = [
        {"roster_id": 1, "owner_id": "owner", "players": ["s-owned"], "starters": ["s-owned"]},
        {"roster_id": 2, "owner_id": "other", "players": [], "starters": []},
    ]
    if extra_rostered_player:
        rosters[0]["players"].append(extra_rostered_player["player_id"])
    if faab_settings is not None:
        league["settings"] = {"waiver_type": 2, "waiver_budget": faab_settings[0]}
        rosters[0]["settings"] = {"waiver_budget_used": faab_settings[1]}
    connection = WaiverRouteConnection(pool_rows)
    source_reads = {"league": 0, "users": 0, "rosters": 0, "catalog": 0}

    def read_league(league_id):
        source_reads["league"] += 1
        return league

    def read_users(league_id):
        source_reads["users"] += 1
        return [{"user_id": "owner", "is_owner": True}]

    def read_rosters(league_id):
        source_reads["rosters"] += 1
        return rosters if rosters_available else None

    def read_catalog():
        source_reads["catalog"] += 1
        return catalog

    blueprint = owner_operations.create_owner_operations_blueprint(
        lambda: connection,
        read_league,
        read_users,
        read_rosters,
        read_catalog,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder="templates")
    from services.authoritative_week import build_sleeper_week_contract
    app.config["WEEK_AUTHORITY_ACQUIRER"] = lambda season: build_sleeper_week_contract({"season": str(season), "week": 3}, season=season)
    app.config.update(
        TESTING=testing, SLEEPER_LEAGUE_ID="controlled",
        NFLVERSE_PLAYER_METADATA=[{"gsis_id": "gsis-wr", "player_id": "gsis-wr"}, {"gsis_id": "gsis-owned", "player_id": "gsis-owned"}, *([{"gsis_id": extra_rostered_player["gsis_id"], "player_id": extra_rostered_player["gsis_id"]}] if extra_rostered_player and extra_rostered_player.get("gsis_id") else [])],
        NFLVERSE_PLAYER_METADATA_LINEAGE={"source": "nflverse", "source_authority": "automated:nflverse", "artifact_id": "players", "version": "v1", "retrieved_at": COMPARISON_NOW, "coverage_state": "COMPLETE"},
    )
    app.register_blueprint(blueprint)
    if consensus is not None:
        app.config["DYNASTYPROCESS_RANKINGS"] = consensus
        league["scoring_settings"] = {"rec": 1}
    app.jinja_env.globals["url_for"] = lambda *args, **kwargs: "/"
    app.jinja_env.globals["ux_roster_lineage"] = lambda roster: []
    from services.ux_evidence import route_payload_evidence
    app.jinja_env.globals["ux_route_evidence"] = route_payload_evidence
    query = {"player_id": selected_player_id, "focus": selected_focus}
    if explain_player:
        query["explain_player"] = explain_player
    response = app.test_client().open("/waivers", method=request_method, query_string=query)
    captured["executed_queries"] = list(connection.executed_queries)
    captured["source_reads"] = source_reads
    captured["production_reads"] = production_reads
    return response, captured


def test_waiver_route_get_uses_cached_rankings_without_refresh(monkeypatch):
    import owner_operations

    cached = {"cache_missing": False, "last_successful_refresh": "2026-10-03T10:00:00+00:00", "cache_age_seconds": 7200, "cache_freshness_state": "AGING", "horizons": {}}
    reads = []
    monkeypatch.setattr(owner_operations, "get_nfl_state", lambda: {"season": 2026, "season_type": "regular", "week": 4})
    monkeypatch.setattr(owner_operations, "read_cached_rankings", lambda *args, **kwargs: reads.append(args[0]) or cached)
    monkeypatch.setattr(owner_operations, "refresh_rankings", lambda *args, **kwargs: pytest.fail("GET refreshed rankings despite a cache"))

    response, _ = render_waiver_route(monkeypatch, testing=False)

    assert response.status_code == 200
    assert len(reads) == 1
    assert "Cache age:</strong> 2h 0m" in response.get_data(as_text=True)
    assert "Freshness:</strong> AGING" in response.get_data(as_text=True)


def test_waiver_route_missing_cache_refreshes_once_and_discloses_failure(monkeypatch):
    import owner_operations

    calls = []
    missing = {"cache_missing": True, "cache_age_seconds": None, "cache_freshness_state": "UNAVAILABLE", "horizons": {}}
    failed = {**missing, "refresh_error": "Ranking refresh failed: OSError"}
    monkeypatch.setattr(owner_operations, "get_nfl_state", lambda: {"season": 2026, "season_type": "regular", "week": 4})
    monkeypatch.setattr(owner_operations, "read_cached_rankings", lambda *args, **kwargs: missing)
    monkeypatch.setattr(owner_operations, "refresh_rankings", lambda *args, **kwargs: calls.append(kwargs) or failed)

    response, _ = render_waiver_route(monkeypatch, testing=False)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert len(calls) == 1
    assert "Ranking refresh failed: OSError" in html
    assert "Freshness:</strong> UNAVAILABLE" in html
    assert "No current verified ranks" in html


def test_waiver_route_manual_refresh_redirects_without_rendering_page(monkeypatch):
    import owner_operations

    calls = []
    monkeypatch.setattr(owner_operations, "get_nfl_state", lambda: {"season": 2026, "season_type": "regular", "week": 4})
    monkeypatch.setattr(owner_operations, "refresh_rankings", lambda path, state, **kwargs: calls.append((path, state, kwargs)))

    response, _ = render_waiver_route(monkeypatch, request_method="POST")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/waivers")
    assert len(calls) == 1
    assert calls[0][2]["force"] is True


def published_view(recommendations):
    return [(item.get("player"), item.get("faab"), item.get("bid_low"), item.get("bid_high"), item.get("priority_score"), (item.get("evidence_context") or {}).get("confidence")) for item in recommendations]


def test_waiver_route_attaches_comparison_only_to_published_candidates(monkeypatch):
    response, captured = render_waiver_route(monkeypatch)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert captured["recommendations"] == []
    assert captured["source_reads"] == {"league": 1, "users": 1, "rosters": 1, "catalog": 1}
    suggestions = captured["preliminary_suggestions"]
    assert [item["player"] for item in suggestions] == ["Avail WR"]
    assert all("player_comparison" in item for item in suggestions)
    by_name = {item["player"]: item["player_comparison"] for item in suggestions}
    assert by_name["Avail WR"]["status"] == "PRELIMINARY"
    assert by_name["Avail WR"]["status"] == "PRELIMINARY"
    assert all(item["recommendation_state"] == "PRELIMINARY_SUGGESTION" for item in suggestions)
    assert all(item["priority_score"] is None and item["faab"] is None and item["bid_low"] is None and item["bid_high"] is None for item in suggestions)
    preliminary_ids = {str(item["player_id"]) for item in suggestions}
    move_checker_ids = {str(item["player_id"]) for item in captured["wda_candidates"]}
    assert move_checker_ids == preliminary_ids
    assert all("roster_comparisons" in item for item in captured["wda_candidates"])
    roster_ids = {str(item.get("player_id")) for item in captured["wda_roster"] if item.get("player_id")}
    selected = re.search(r'<option value="([^"]+)" data-player-id="([^"]+)" selected>', html)
    selector_ids = {value for value, player_id in re.findall(r'<option value="([^"]+)" data-player-id="([^"]+)"', html) if value == player_id}
    assert selector_ids == roster_ids
    assert selected and selected.group(1) == selected.group(2) and selected.group(1) in roster_ids
    candidate_data = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', html, re.S).group(1))
    assert [item["player"] for item in candidate_data] == ["Avail WR"]
    assert "rostered player to see healthy waiver candidates at the same position" in html
    assert "No verified-healthy preliminary candidates are available at " in html
    assert 'id="preliminary-candidates-title"' not in html
    assert '<td>Visible Preliminary Candidate Count</td><td>1</td>' in html
    assert "Consensus remains informational only" in html


def test_selected_player_id_reaches_reader_and_recomputes_comparison(monkeypatch):
    def rows(points):
        return [{"season": 2026, "week": week, "fantasy_points_ppr": value, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for week, value in zip((3, 4), points)]

    production = {"gsis-owned": rows((20, 21)), "gsis-owned-2": rows((5, 6)), "gsis-wr": rows((14, 15))}
    extra = {"player_id": "s-owned-2", "player": "Second Owned WR", "position": "WR", "team": "SF", "gsis_id": "gsis-owned-2"}
    first_response, first = render_waiver_route(monkeypatch, selected_player_id="s-owned", selected_focus="this_week", extra_rostered_player=extra, production_rows=production)
    monkeypatch.undo()
    second_response, second = render_waiver_route(monkeypatch, selected_player_id="s-owned-2", selected_focus="this_week", extra_rostered_player=extra, production_rows=production)

    assert first_response.status_code == second_response.status_code == 200
    assert first["selected_player"]["player_id"] == "s-owned"
    assert second["selected_player"]["player_id"] == "s-owned-2"
    assert first["selected_result"]["decision"] == "HOLD"
    assert second["selected_result"]["decision"] == "HOLD"
    assert first["selected_result"]["comparison_summary"]["selected_average"] == 20.5
    assert second["selected_result"]["comparison_summary"]["selected_average"] == 5.5
    assert "coverage" in second["selected_result"]["roster_effect"]
    assert "gsis-owned-2" in second["production_reads"]
    assert len(second["selected_comparisons"]) <= 5
    assert second["selected_focus"] == "this_week"
    second_html = second_response.get_data(as_text=True)
    assert "Second Owned WR" in second_html
    assert "MONITOR" in second_html and "Avail WR" in second_html
    serialized_candidates = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', second_html, re.S).group(1))
    assert len(serialized_candidates) <= 5


def test_selected_route_joins_sleeper_depth_and_espn_news_by_stable_ids(monkeypatch):
    import owner_operations

    monkeypatch.setattr(owner_operations, "read_espn_nfl_news", lambda: {
        "state": "AVAILABLE", "source": "ESPN public NFL news JSON", "retrieved_at": COMPARISON_NOW,
        "articles": [{"article_id": "article-1", "headline": "Candidate update", "description": "Dated report text.", "published_at": COMPARISON_NOW, "last_modified_at": COMPARISON_NOW, "url": "https://espn.example/article-1", "espn_athlete_ids": ["espn-wr"], "freshness_state": "UNVERIFIED", "decision_effect": "INFORMATIONAL_ONLY"}],
        "blockers": [],
    })
    response, captured = render_waiver_route(
        monkeypatch,
        selected_player_id="s-owned",
        candidate_health={"s-wr": {"espn_id": "espn-wr", "depth_chart_position": "WR", "depth_chart_order": 2}},
        production_rows={
            "gsis-owned": [{"season": 2026, "week": week, "fantasy_points_ppr": 5.0, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for week in (2, 3, 4)],
            "gsis-wr": [{"season": 2026, "week": week, "fantasy_points_ppr": 15.0, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for week in (2, 3, 4)],
        },
    )
    html = response.get_data(as_text=True)
    comparison = next(candidate["selected_comparison"] for candidate in captured["selected_comparisons"] if candidate["player_id"] == "s-wr")

    assert response.status_code == 200
    assert comparison["decision"] == "HOLD"
    assert comparison["news_context"]["candidate"]["articles"][0]["article_id"] == "article-1"
    assert comparison["news_context"]["candidate"]["freshness_state"] == "UNVERIFIED"
    assert comparison["news_context"]["candidate"]["decision_effect"] == "INFORMATIONAL_ONLY"
    assert comparison["depth_chart_context"]["candidate"]["position"] == "WR"
    assert comparison["depth_chart_context"]["candidate"]["order"] == 2
    assert comparison["depth_chart_context"]["candidate"]["decision_effect"] == "SCREENING_ONLY"
    assert "Candidate update" in html
    assert "not an expected role or duration claim" in html


def test_selected_roster_player_with_no_relevant_candidates_returns_no_actionable_upgrade(monkeypatch):
    te = {"player_id": "s-owned-te", "player": "Rostered TE", "position": "TE", "team": "SEA", "gsis_id": "gsis-owned-te"}
    response, captured = render_waiver_route(monkeypatch, selected_player_id="s-owned-te", extra_rostered_player=te)

    assert response.status_code == 200
    assert captured["selected_player"]["player_id"] == "s-owned-te"
    assert captured["selected_result"]["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert captured["selected_result"]["candidate_id"] is None
    assert "NO ACTIONABLE UPGRADE" in response.get_data(as_text=True)


def test_invalid_selected_player_id_does_not_fall_back_to_default_roster_player(monkeypatch):
    response, captured = render_waiver_route(monkeypatch, selected_player_id="not-rostered")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert captured["selected_player"]["player_id"] == "not-rostered"
    assert captured["selected_player"]["valid"] is False
    assert captured["selected_result"]["decision"] == "BLOCKED"
    assert '<option value="" selected disabled>Requested roster player unavailable</option>' in html


def test_selected_workflow_does_not_render_full_candidate_evidence_dump(monkeypatch):
    response, captured = render_waiver_route(monkeypatch, extra_candidate_count=200, selected_player_id="s-owned")
    html = response.get_data(as_text=True)
    serialized_candidates = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', html, re.S).group(1))

    assert response.status_code == 200
    assert len(captured["selected_comparisons"]) <= 5
    assert len(serialized_candidates) <= 5
    assert "Deep Candidate 196" not in html
    assert "Health verification needed" in html
    assert "Excluded health diagnostics" in html


def test_waiver_route_comparison_never_changes_order_count_faab_or_confidence(monkeypatch):
    with_comparison = render_waiver_route(monkeypatch)[1]["preliminary_suggestions"]
    monkeypatch.undo()
    without_comparison = render_waiver_route(monkeypatch, disable_comparison=True)[1]["preliminary_suggestions"]
    assert published_view(with_comparison) == published_view(without_comparison)
    assert len(with_comparison) == len(without_comparison) == 1


def test_waiver_route_discovers_deep_available_healthy_players_without_caps(monkeypatch):
    response, captured = render_waiver_route(monkeypatch, extra_candidate_count=200)
    assert response.status_code == 200
    suggestions = captured["preliminary_suggestions"]
    names = {candidate["player"] for candidate in suggestions}
    assert len(suggestions) == 51
    assert "Deep Candidate 196" in names
    assert "Owned WR" not in names
    assert all(f"Deep Candidate {index}" not in names for index in range(200) if index % 4)
    assert all(candidate["evidence_context"]["health_state"] == "HEALTHY" for candidate in suggestions)
    assert all(candidate["faab"] is None and candidate["priority_score"] is None for candidate in suggestions)
    assert len(captured["wda_candidates"]) <= 5
    assert all(candidate.get("selected_comparison", {}).get("selected_player_id") == captured["selected_player"]["player_id"] for candidate in captured["wda_candidates"])
    page_candidates = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', response.get_data(as_text=True), re.S).group(1))
    assert len(page_candidates) <= 5
    pool_query = next(query for query in captured["executed_queries"] if "ORDER BY ranking" in query)
    assert "LIMIT" not in pool_query.upper()


def test_waiver_route_reuses_resolved_roster_identity_for_selected_comparison(monkeypatch):
    import owner_operations
    original = owner_operations.attach_waiver_opportunity_identity
    def attach(candidates, *args, **kwargs):
        candidates = original(candidates, *args, **kwargs)
        for candidate in candidates:
            if candidate.get("player_id") == "s-owned":
                candidate.update(opportunity_player_id="resolved-owned", opportunity_identity_state="RESOLVED")
        return candidates
    monkeypatch.setattr(owner_operations, "attach_waiver_opportunity_identity", attach)
    common = {"season": 2026, "week": 3, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"}
    response, captured = render_waiver_route(monkeypatch, production_rows={"resolved-owned": [{**common, "fantasy_points_ppr": 5.0}], "gsis-wr": [{**common, "fantasy_points_ppr": 12.0}]})
    assert response.status_code == 200
    comparison = captured["wda_candidates"][0]["roster_comparisons"]["s-owned"]
    assert comparison["state"] == "PRELIMINARY"
    assert comparison["roster_average"] == 5.0
    assert comparison["candidate_average"] == 12.0
    assert comparison["difference"] == 7.0
    assert comparison["decision_effect"] == "INFORMATIONAL_ONLY"
    assert "Compared with " in response.get_data(as_text=True)


def test_waiver_route_publishes_live_balance_and_provisional_bid_only_for_add_review(monkeypatch):
    rows = lambda points: [{"season": 2026, "week": week, "fantasy_points_ppr": points, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"} for week in (1, 2, 3)]
    response, captured = render_waiver_route(monkeypatch, faab_settings=(100, 21), production_rows={"gsis-owned": rows(5), "gsis-wr": rows(12)})
    assert response.status_code == 200
    assert captured["faab_budget"] == 79
    assert captured["faab_balance"]["spent"] == 21
    guidance = captured["wda_candidates"][0]["roster_guidance"]["s-owned"]
    assert guidance["this_week"]["action"] == "REVIEW_ADD"
    assert guidance["rest_of_season"]["action"] == "MONITOR"
    assert guidance["provisional_bid"]["state"] == "PROVISIONAL"
    assert (guidance["provisional_bid"]["low"], guidance["provisional_bid"]["high"]) == (3, 4)
    assert "No drop is supported" in guidance["drop_review"]
    assert "$79" in response.get_data(as_text=True)
    assert captured["wda_candidates"][0].get("faab") is None


def test_waiver_route_publishes_candidate_health_without_changing_decisions(monkeypatch):
    baseline_response, baseline = render_waiver_route(monkeypatch, include_missing_candidate=True)
    monkeypatch.undo()
    response, captured = render_waiver_route(
        monkeypatch,
        candidate_health={
            "s-wr": {"injury_status": "IR"},
            "s-rb": {"injury_status": "Healthy"},
        },
        include_missing_candidate=True,
    )
    html = response.get_data(as_text=True)
    recommendations = captured["preliminary_suggestions"]

    assert baseline_response.status_code == response.status_code == 200
    assert [item["player"] for item in recommendations] == ["Avail RB"]
    candidate_data = json.loads(re.search(r'<script type="application/json" id="wda-candidates-data">(.*?)</script>', html, re.S).group(1))
    assert candidate_data == []
    assert captured["selected_result"]["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert "NO ACTIONABLE UPGRADE" in html
    assert 'id="preliminary-candidates-title"' not in html
    assert captured["health_excluded_diagnostics"]["excluded_count"] == 1
    assert [item["player"] for item in captured["monitor_candidates"]] == ["Avail TE"]
    assert "Health verification needed" in html
    assert all(query.lstrip().upper().startswith("SELECT") for query in captured["executed_queries"])


def test_waiver_recommendation_gate_retains_missing_health_for_verification():
    from owner_operations import _waiver_candidate_health, waiver_candidate_recommendation_state
    candidate = _waiver_candidate_health({}, datetime.now(timezone.utc).isoformat(), True)
    candidate.update(ownership_state="VERIFIED", eligibility_state="VERIFIED", player_id="sleeper-missing", identity_resolution={"resolution_state": "RESOLVED"})
    result = waiver_candidate_recommendation_state(candidate, "UNVERIFIED")
    assert result["candidate_disposition"] == "MONITOR"
    assert result["recommendation_state"] == "HEALTH_UNVERIFIED"
    assert result["normalized_health_state"] == "HEALTH_UNVERIFIED"


def test_waiver_candidate_health_verifies_active_player_without_injury_label():
    from owner_operations import _waiver_candidate_health, waiver_candidate_recommendation_state
    candidate = _waiver_candidate_health({"status": "Active", "injury_status": None}, datetime.now(timezone.utc).isoformat(), True)
    candidate.update(ownership_state="VERIFIED", eligibility_state="VERIFIED", player_id="sleeper-active", identity_resolution={"resolution_state": "RESOLVED"}, evidence_context={"roster_fit": {"state": "AVAILABLE"}})
    assert candidate["health_status_available"] is True
    assert waiver_candidate_recommendation_state(candidate, "UNVERIFIED")["candidate_disposition"] == "PRELIMINARY_SUGGESTION"


def test_waiver_route_actionable_requires_fresh_healthy_and_verified_ranking(monkeypatch):
    response, captured = render_waiver_route(
        monkeypatch,
        ranking_source_verified=True,
        candidate_health={"s-wr": {"injury_status": "Healthy"}, "s-rb": {"injury_status": "IR"}},
    )
    assert response.status_code == 200
    assert captured["recommendations"] == []
    suggestions = captured["preliminary_suggestions"]
    assert [item["player"] for item in suggestions] == ["Avail WR"]
    assert suggestions[0]["recommendation_state"] == "PRELIMINARY_SUGGESTION"
    assert all(suggestions[0].get(field) is None for field in ("priority_score", "faab", "bid_low", "bid_high"))
    assert suggestions[0]["acquisition_evaluation"]["action"] == "NO_RECOMMENDATION"
    assert suggestions[0]["acquisition_evaluation"]["evidence_relevance"] == "SCREENING_ONLY"
    assert all(item["player"] != "Avail RB" for item in captured["preliminary_suggestions"])
    assert captured["health_excluded_diagnostics"]["excluded_count"] >= 1


def test_waiver_route_ir_candidate_stays_informational_when_ranking_is_verified(monkeypatch):
    response, captured = render_waiver_route(
        monkeypatch,
        ranking_source_verified=True,
        candidate_health={"s-wr": {"injury_status": "IR"}},
    )
    assert response.status_code == 200
    assert captured["recommendations"] == []
    assert all(item["player"] != "Avail WR" for item in captured["preliminary_suggestions"])
    assert all(item["player"] != "Avail WR" for item in captured["monitor_candidates"])
    assert all(item["player"] != "Avail WR" for item in captured["wda_candidates"])
    assert "Avail WR" not in response.get_data(as_text=True)
    assert captured["health_excluded_diagnostics"]["excluded_count"] >= 1
    assert "Avail WR" not in str(captured["health_excluded_diagnostics"])
    template = (Path(__file__).parents[1] / "templates" / "waivers.html").read_text(encoding="utf-8")
    assert "candidate.recommendation_state === 'PRELIMINARY_SUGGESTION'" in template
    assert "POTENTIAL UPGRADE" not in template


def test_verified_zero_faab_remains_distinct_from_unavailable_faab():
    rendered = render_waivers(
        recommendations=[{"player": "Zero Bid", "position": "WR", "recommendation_state": "ACTIONABLE", "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "priority_score": 0, "tier": 1, "projection": None, "faab": 0, "bid_low": 0, "bid_high": 0, "need": 0, "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"}}],
        preliminary_suggestions=[{"player": "Preliminary Healthy", "position": "RB", "recommendation_state": "PRELIMINARY_SUGGESTION", "recommendation_blockers": ["WAIVER_RANKING_SOURCE_UNVERIFIED"], "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API", "opportunity": {"reason": "Unavailable"}, "evidence_coverage": {"label": "Unavailable"}}}],
    )
    assert "$0" in rendered
    assert "Suggested FAAB" in rendered
    assert "balanceData.state === 'AVAILABLE'" in rendered
    assert "bid.high <= balanceData.remaining" in rendered


def test_unverified_ranking_template_hides_all_authoritative_actions():
    informational = [{
        "player": "Research Candidate", "position": "WR", "recommendation_state": "INFORMATIONAL_ONLY",
        "recommendation_blockers": ["WAIVER_RANKING_SOURCE_UNVERIFIED"],
        "evidence_context": {
            "health_state": "HEALTHY", "health_source": "Sleeper API", "health_freshness_state": "FRESH",
            "eligibility_state": "VERIFIED", "ownership_state": "VERIFIED",
            "opportunity": {"state": "AVAILABLE", "reason": "Supported week 3 usage."},
            "evidence_coverage": {"label": "Two-week comparison available"},
        },
    }]
    rendered = render_waivers(
        waiver_evidence={"allowed": True, "blockers": [], "warnings": ["WAIVER_RANKING_SOURCE_UNVERIFIED"], "ranking_confidence": "UNVERIFIED"},
        recommendations=[{"player": "Unsafe payload", "position": "WR", "recommendation_state": "ACTIONABLE", "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "priority_score": 99, "tier": 1, "projection": 130, "faab": 25, "bid_low": 22, "bid_high": 30, "evidence_context": {"health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"}}], preliminary_suggestions=informational,
        vacancies=["WR"],
        wda_candidates=[{"player": "Research Candidate", "position": "WR", "projection": 120, "recommendation_state": "INFORMATIONAL_ONLY", "recommendation_blockers": ["WAIVER_RANKING_SOURCE_UNVERIFIED"]}],
    )
    for unsupported in ("RECOMMENDATIONS READY", "Top priority", "POTENTIAL UPGRADE", "NO PROJECTED UPGRADE FOUND", "Make the claim decision", "Priority score", "Suggested FAAB", "Recommended Add"):
        assert unsupported not in rendered
    assert "NO SUPPORTED CLAIM" in rendered
    assert 'id="preliminary-candidates-title"' not in rendered
    assert "Waiver Move Checker" in rendered
    assert "Selected-player guidance is unavailable." in rendered
    assert "Roster-need context only" in rendered
    assert "Prioritize adds" not in rendered
    assert "Research Candidate" in rendered
    assert "Unsafe payload" not in rendered
    assert "FAAB: $25" not in rendered
    assert "Priority score 99" not in rendered
    assert "$25" not in rendered
    assert "Priority score 99" not in rendered


def test_waiver_route_keeps_consensus_ranks_informational_and_blocks_missing_rank_data(monkeypatch):
    def rank(value):
        return {"position": "WR", "ecr": value, "source_date": "2026-10-03"}
    consensus = {"source": "FantasyPros consensus via DynastyProcess", "horizons": {"this_week": {"state": "AVAILABLE", "ranks": {"s-wr": rank(10), "s-owned": rank(20)}}, "rest_of_season": {"state": "AVAILABLE", "ranks": {"s-wr": rank(30), "s-owned": rank(15)}}}}
    response, context = render_waiver_route(monkeypatch, faab_settings=(100, 21), consensus=consensus)
    guidance = context["wda_candidates"][0]["roster_guidance"]["s-owned"]
    assert response.status_code == 200
    assert guidance["this_week"]["action"] != "REVIEW_ADD" or "mean expert rank" not in guidance["this_week"]["reason"]
    assert guidance["rest_of_season"]["action"] == "MONITOR"
    assert context["recommendations"] == []
    assert context["wda_candidates"][0]["source_rankings"]["this_week"]["ecr"] == 10
    assert context["wda_candidates"][0]["acquisition_evaluation"]["horizon"] == "UNAVAILABLE"
    assert context["wda_candidates"][0]["acquisition_evaluation"]["evidence_relevance"] == "SCREENING_ONLY"
    monkeypatch.undo()
    response, context = render_waiver_route(monkeypatch, faab_settings=(100, 21), consensus={"horizons": {}})
    guidance = context["wda_candidates"][0]["roster_guidance"]["s-owned"]
    assert guidance["rest_of_season"]["action"] == "MONITOR"
    assert guidance["provisional_bid"]["high"] is None


def test_waiver_acquisition_evaluation_uses_roster_need_not_player_rank():
    from owner_operations import waiver_acquisition_evaluation

    settings = {"state": "AVAILABLE", "full_ppr": True, "flex_eligible_positions": ["RB", "WR", "TE"]}
    available = {
        "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "recommendation_state": "PRELIMINARY_SUGGESTION",
        "player_id": "candidate",
        "player": "Candidate",
        "position": "RB",
        "source_rankings": {"this_week": {"ecr": 999}},
        "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
    }
    needs = {"RB": {"state": "AVAILABLE", "position": "RB", "starter_shortage": 1, "depth_shortage": 1, "drivers": ["One required RB starter slot is uncovered."]}}
    evaluation = waiver_acquisition_evaluation(available, needs, settings)

    assert evaluation["horizon"] == "UNAVAILABLE"
    assert evaluation["action"] == "NO_RECOMMENDATION"
    assert evaluation["evidence_relevance"] == "SCREENING_ONLY"
    assert evaluation["faab"]["state"] == "NO_BID"
    assert evaluation["faab"]["low"] == evaluation["faab"]["high"] == 0

    supported = waiver_acquisition_evaluation(available, needs, settings, {"comparison": {"state": "PRELIMINARY", "difference": 4.0, "latest_difference": 2.0, "candidate_wins": 3, "weeks": [{"season": 2026, "week": week} for week in (1, 2, 3)], "reason": "Fresh matched Full-PPR comparison favors the candidate."}})
    assert supported["horizon"] == "IMMEDIATE"
    assert supported["action"] == "CONSIDER"
    assert supported["would_start"] == "YES"
    assert supported["affected_slot"] == "RB"
    assert supported["evidence_relevance"] == "MEANINGFUL_COMPARISON"
    assert "no points improvement is projected" in supported["roster_fit"]
    assert supported["faab"]["state"] == "NO_BID"

    directional_candidate = {
        **available,
        "player_comparison": {"what_changed": {"state": "AVAILABLE", "changes": [{"field": "target_share", "direction": "UP"}]}},
        "opportunity_metrics": {"rows": [{"freshness_state": "FRESH"}]},
    }
    monitor = waiver_acquisition_evaluation(directional_candidate, needs, settings, balance={"state": "AVAILABLE", "remaining": 79})
    assert monitor["action"] == "CONSIDER"
    assert monitor["evidence_relevance"] == "DIRECTIONAL_SIGNAL"
    assert monitor["faab"]["state"] == "NO_BID"

    no_need = {"RB": {"state": "AVAILABLE", "position": "RB", "starter_shortage": 0, "depth_shortage": 0}}
    informational_rank_only = waiver_acquisition_evaluation(available, no_need, settings)
    assert informational_rank_only["action"] == "NO_RECOMMENDATION"
    assert informational_rank_only["evidence_relevance"] == "SCREENING_ONLY"
    assert informational_rank_only["horizon"] == "UNAVAILABLE"
    no_need_wr = waiver_acquisition_evaluation({**available, "position": "WR", "source_rankings": {"this_week": {"ecr": 1}}}, {"WR": {"state": "AVAILABLE", "position": "WR", "starter_shortage": 0, "depth_shortage": 0}}, settings)
    assert available["source_rankings"]["this_week"]["ecr"] > 1
    assert evaluation["sort_group"] == no_need_wr["sort_group"]


def test_waiver_value_ranking_uses_shared_fresh_te_stats_not_name_order():
    from owner_operations import waiver_value_ranking

    def candidate(player_id, player, target_share, routes, ppr):
        return {
            "player_id": player_id,
            "player": player,
            "position": "TE",
            "candidate_disposition": "PRELIMINARY_SUGGESTION",
            "identity_resolution": {"resolution_state": "RESOLVED"},
            "opportunity_identity_state": "RESOLVED",
            "evidence_context": {
                "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED",
                "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API",
            },
            "opportunity_metrics": {
                "state": "AVAILABLE",
                "rows": [
                    {"season": 2026, "week": week, "freshness_state": "FRESH", "target_share": target_share,
                     "route_participation": routes, "targets": 5, "fantasy_points_ppr": ppr}
                    for week in (3, 4)
                ],
            },
        }

    result = waiver_value_ranking(
        [candidate("z-player", "Z Player", .30, .80, 12), candidate("a-player", "A Player", .10, .40, 4)],
        position="TE", season=2026, current_week=5, need={"state": "AVAILABLE", "depth_shortage": 1},
    )

    assert result["z-player"]["position_rank"] == 1
    assert result["a-player"]["position_rank"] == 2
    assert result["z-player"]["positive_reasons"]
    assert result["z-player"]["roster_need"]["depth_shortage"] == 1
    starter_need = {"state": "AVAILABLE", "starter_shortage": 1}
    missing_schedule = waiver_value_ranking(
        [candidate("z-player", "Z Player", .30, .80, 12), candidate("a-player", "A Player", .10, .40, 4)],
        position="TE", season=2026, current_week=5, need=starter_need,
    )
    assert missing_schedule["z-player"]["state"] == "INSUFFICIENT_EVIDENCE"
    scheduled_candidates = [
        candidate("z-player", "Z Player", .30, .80, 12),
        candidate("a-player", "A Player", .10, .40, 4),
    ]
    for item in scheduled_candidates:
        item["waiver_game_context"] = {"game_context_state": "AVAILABLE", "week": 5}
        item["waiver_bye_evidence"] = {"authoritative": True, "freshness_state": "FRESH", "is_current_week_bye": False}
    scheduled = waiver_value_ranking(
        scheduled_candidates, position="TE", season=2026, current_week=5, need=starter_need,
    )
    assert scheduled["z-player"]["position_rank"] == 1


def test_waiver_consensus_ranking_uses_fresh_lower_current_ecr_and_never_usage_as_rank():
    from owner_operations import waiver_consensus_ranking

    def candidate(player_id, name, *, usage_value, ownership="VERIFIED"):
        return {
            "player_id": player_id, "player": name, "position": "TE",
            "candidate_disposition": "PRELIMINARY_SUGGESTION",
            "identity_resolution": {"resolution_state": "RESOLVED"},
            "evidence_context": {
                "ownership_state": ownership, "eligibility_state": "VERIFIED",
                "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API",
            },
            "opportunity_metrics": {"state": "AVAILABLE", "usage": usage_value},
        }

    likely = candidate("likely", "Isaiah Likely", usage_value=99)
    barner = candidate("barner", "AJ Barner", usage_value=1)
    def rank(ecr):
        return {
            "position": "TE", "ecr": ecr, "source_date": "2026-10-13",
            "source_age_seconds": 3600, "horizon": "this_week", "scoring": "PPR",
            "season": 2026, "week": 6, "identity_method": "PUBLISHED_PROVIDER_CROSSWALK",
        }

    results = waiver_consensus_ranking(
        [likely, barner], position="TE", horizon="this_week", season=2026, current_week=6,
        horizon_data={"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": {"likely": rank(8), "barner": rank(30)}},
    )
    assert results["likely"]["rank"] == 8
    assert results["likely"]["position_rank"] == 1
    assert results["barner"]["rank"] == 30
    assert results["barner"]["position_rank"] == 2
    assert results["likely"]["freshness_state"] == "FRESH"


def test_waiver_consensus_missing_stale_and_ros_horizon_fail_closed():
    from owner_operations import waiver_consensus_ranking

    candidate = {
        "player_id": "kicker", "player": "Kaimi Fairbairn", "position": "K",
        "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "identity_resolution": {"resolution_state": "RESOLVED"},
        "evidence_context": {
            "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED",
            "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API",
        },
    }
    missing = waiver_consensus_ranking(
        [candidate], position="K", horizon="this_week", season=2026, current_week=6,
        horizon_data={"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": {}},
    )
    assert missing["kicker"]["state"] == "UNRANKED"
    assert "No fresh this week" in missing["kicker"]["reason"]

    stale_row = {
        "position": "K", "ecr": 4, "source_date": "2026-10-01",
        "source_age_seconds": 999999, "horizon": "this_week", "scoring": "PPR",
        "season": 2026, "week": 6,
    }
    stale = waiver_consensus_ranking(
        [candidate], position="K", horizon="this_week", season=2026, current_week=6,
        horizon_data={"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": {"kicker": stale_row}},
    )
    assert stale["kicker"]["state"] == "UNRANKED"
    assert "freshness is stale" in stale["kicker"]["reason"]

    ros_row = {**stale_row, "source_age_seconds": 3600, "horizon": "rest_of_season", "week": None}
    ros = waiver_consensus_ranking(
        [candidate], position="K", horizon="rest_of_season", season=2026, current_week=6,
        horizon_data={"state": "AVAILABLE", "max_age_seconds": 604800, "ranks": {"kicker": ros_row}},
    )
    assert ros["kicker"]["state"] == "RANKED"
    assert ros["kicker"]["horizon"] == "rest_of_season"


def test_waiver_consensus_route_propagates_current_ecr_to_candidate_and_explanation(monkeypatch):
    rank_row = {
        "position": "WR", "ecr": 12, "source_date": "2026-10-13",
        "source_age_seconds": 3600, "horizon": "this_week", "scoring": "PPR",
        "season": 2026, "week": 3, "identity_method": "PUBLISHED_PROVIDER_CROSSWALK",
    }
    consensus = {
        "source": "FantasyPros consensus via DynastyProcess",
        "horizons": {"this_week": {
            "state": "AVAILABLE", "max_age_seconds": 172800,
            "ranks": {"s-wr": rank_row},
        }, "rest_of_season": {"state": "UNAVAILABLE", "max_age_seconds": 604800, "ranks": {}}},
    }
    response, captured = render_waiver_route(monkeypatch, consensus=consensus, explain_player="Avail WR")
    candidate = next(row for row in captured["preliminary_suggestions"] if row["player"] == "Avail WR")
    outcome = next(row for row in captured["waiver_candidate_outcomes"] if row["player"] == "Avail WR")
    assert response.status_code == 200
    assert candidate["waiver_value_result"]["state"] == "RANKED"
    assert candidate["waiver_value_result"]["rank"] == 12
    assert candidate["waiver_value_result"]["horizon"] == "this_week"
    assert "current-week positional consensus rank 12" in outcome["message"]
    assert outcome["details"]["rankings"]["this_week"]["ecr"] == 12


def test_waiver_consensus_route_uses_ros_rank_only_for_explicit_ros_focus(monkeypatch):
    current = {
        "position": "WR", "ecr": 40, "source_date": "2026-10-13",
        "source_age_seconds": 3600, "horizon": "this_week", "scoring": "PPR",
        "season": 2026, "week": 3,
    }
    ros = {
        "position": "WR", "ecr": 6, "source_date": "2026-10-13",
        "source_age_seconds": 3600, "horizon": "rest_of_season", "scoring": "PPR",
        "season": 2026, "week": None,
    }
    response, captured = render_waiver_route(
        monkeypatch,
        selected_focus="rest_of_season",
        explain_player="Avail WR",
        consensus={"source": "FantasyPros consensus via DynastyProcess", "horizons": {
            "this_week": {"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": {"s-wr": current}},
            "rest_of_season": {"state": "AVAILABLE", "max_age_seconds": 604800, "ranks": {"s-wr": ros}},
        }},
    )
    candidate = next(row for row in captured["preliminary_suggestions"] if row["player"] == "Avail WR")
    outcome = next(row for row in captured["waiver_candidate_outcomes"] if row["player"] == "Avail WR")
    assert response.status_code == 200
    assert candidate["waiver_value_result"]["horizon"] == "rest_of_season"
    assert candidate["waiver_value_result"]["rank"] == 6
    assert "rest-of-season positional consensus rank 6" in outcome["message"]


def test_waiver_route_orders_same_position_options_by_lower_fresh_ecr_not_name(monkeypatch):
    def rank(ecr):
        return {
            "position": "WR", "ecr": ecr, "source_date": "2026-10-13",
            "source_age_seconds": 3600, "horizon": "this_week", "scoring": "PPR",
            "season": 2026, "week": 3,
        }

    response, captured = render_waiver_route(
        monkeypatch,
        extra_pool_candidates=[{
            "player_id": "s-zulu", "name": "Zulu WR", "position": "WR", "team": "ARI",
            "projection": 90.0, "tier": 4,
        }],
        consensus={"source": "FantasyPros consensus via DynastyProcess", "horizons": {
            "this_week": {"state": "AVAILABLE", "max_age_seconds": 172800, "ranks": {"s-wr": rank(40), "s-zulu": rank(5)}},
            "rest_of_season": {"state": "UNAVAILABLE", "max_age_seconds": 604800, "ranks": {}},
        }},
    )
    wr_section = next(section for section in captured["waiver_position_sections"] if section["position"] == "WR")
    assert response.status_code == 200
    assert wr_section["options"][0]["candidate"]["player"] == "Zulu WR"
    assert wr_section["options"][0]["value"]["rank"] == 5
    assert wr_section["options"][1]["candidate"]["player"] == "Avail WR"
    assert wr_section["options"][1]["value"]["rank"] == 40
    assert wr_section["label"] == "BEST SUPPORTED OPTION"


def test_waiver_value_ranking_ties_and_fails_closed_for_stale_or_unsupported_positions():
    from owner_operations import waiver_value_ranking

    def candidate(player_id, value, freshness="FRESH", position="TE"):
        return {
            "player_id": player_id,
            "position": position,
            "candidate_disposition": "PRELIMINARY_SUGGESTION",
            "identity_resolution": {"resolution_state": "RESOLVED"},
            "opportunity_identity_state": "RESOLVED",
            "evidence_context": {
                "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED",
                "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API",
            },
            "opportunity_metrics": {"state": "AVAILABLE", "rows": [
                {"season": 2026, "week": week, "freshness_state": freshness, "target_share": .2,
                 "route_participation": .6, "fantasy_points_ppr": value}
                for week in (3, 4)
            ]},
        }

    tied = waiver_value_ranking(
        [candidate("first", 8), candidate("second", 8)],
        position="TE", season=2026, current_week=5, need={},
    )
    assert tied["first"]["state"] == tied["second"]["state"] == "TIED"
    assert tied["first"]["position_rank"] == tied["second"]["position_rank"] == 1

    route_first = candidate("route-first", 12)
    production_first = candidate("production-first", 8)
    for row in route_first["opportunity_metrics"]["rows"]:
        row.update(target_share=.1, route_participation=.9)
    for row in production_first["opportunity_metrics"]["rows"]:
        row.update(target_share=.3, route_participation=.5)
    tradeoff = waiver_value_ranking(
        [route_first, production_first],
        position="TE", season=2026, current_week=5, need={},
    )
    assert tradeoff["route-first"]["state"] == tradeoff["production-first"]["state"] == "INCOMPARABLE"
    assert tradeoff["route-first"]["recommendation"] == "NO_CLEAR_WINNER"

    stale = waiver_value_ranking(
        [candidate("first", 12, freshness="STALE"), candidate("second", 8, freshness="STALE")],
        position="TE", season=2026, current_week=5, need={},
    )
    assert stale["first"]["position_rank"] is None
    assert any("matching fresh completed weeks" in reason for reason in stale["first"]["missing_important_statistics"])

    defenses = waiver_value_ranking(
        [candidate("kc", 12, position="DEF"), candidate("ari", 8, position="DEF")],
        position="DEF", season=2026, current_week=5, need={},
    )
    assert defenses["kc"]["position_rank"] is None
    assert defenses["kc"]["state"] == "INSUFFICIENT_EVIDENCE"


def test_waiver_qb_value_ranking_uses_published_passing_production_and_usage():
    from owner_operations import waiver_value_ranking

    candidate = {
        "player_id": "qb-1",
        "position": "QB",
        "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "identity_resolution": {"resolution_state": "RESOLVED"},
        "opportunity_identity_state": "RESOLVED",
        "evidence_context": {
            "ownership_state": "VERIFIED", "eligibility_state": "VERIFIED",
            "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API",
        },
        "opportunity_metrics": {"state": "AVAILABLE", "rows": [
            {"season": 2026, "week": week, "freshness_state": "FRESH", "fantasy_points_ppr": 20,
             "carries": 3, "snap_share": .95}
            for week in (3, 4)
        ]},
        "recent_production": {"state": "AVAILABLE", "rows": [
            {"season": 2026, "week": week, "freshness_state": "FRESH", "passing_yards": 250 + week,
             "passing_tds": 2, "passing_interceptions": 1, "rushing_yards": 15}
            for week in (3, 4)
        ]},
    }
    result = waiver_value_ranking(
        [candidate], position="QB", season=2026, current_week=5, need={},
    )

    assert result["qb-1"]["state"] == "RANKED"
    assert "passing_yards" in {stat["field"] for stat in result["qb-1"]["statistics_used"]}


def test_waiver_bid_contracts_do_not_call_budget_guardrail_a_winning_bid():
    from owner_operations import waiver_bid_estimates

    estimates = waiver_bid_estimates({"player": "Candidate"}, {"state": "AVAILABLE", "remaining": 79, "budget": 100})
    assert estimates["value_based_bid"]["state"] == "UNAVAILABLE"
    assert estimates["estimated_winning_bid"]["state"] == "UNAVAILABLE"
    assert estimates["maximum_bid"]["state"] == "UNAVAILABLE"
    assert estimates["maximum_bid"]["remaining_faab"] == 79
    assert estimates["market_demand"]["likely_competitors"] == []


def test_waiver_acquisition_evaluation_keeps_flex_duration_and_faab_states_distinct():
    from owner_operations import waiver_acquisition_evaluation

    candidate = {
        "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "recommendation_state": "PRELIMINARY_SUGGESTION",
        "player_id": "candidate",
        "player": "Candidate",
        "position": "WR",
        "projection": None,
        "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
    }
    needs = {
        "WR": {"state": "AVAILABLE", "position": "WR", "starter_shortage": 0, "depth_shortage": 0},
        "FLEX": {"state": "AVAILABLE", "position": "FLEX", "starter_shortage": 1, "depth_shortage": 1, "drivers": ["One FLEX starter slot is uncovered."]},
    }
    settings = {"state": "AVAILABLE", "full_ppr": True, "flex_eligible_positions": ["RB", "WR", "TE"]}
    guidance = {"comparison": {"state": "PRELIMINARY", "difference": 4.0, "latest_difference": 2.0, "candidate_wins": 3, "weeks": [{"season": 2026, "week": week} for week in (1, 2, 3)], "reason": "Fresh matched Full-PPR comparison favors the candidate."}, "provisional_bid": {"state": "PROVISIONAL", "low": 4, "high": 8, "reason": "4-8% of remaining FAAB. Not a projected winning bid."}}
    evaluation = waiver_acquisition_evaluation(candidate, needs, settings, guidance, {"state": "AVAILABLE", "remaining": 79})

    assert evaluation["horizon"] == "IMMEDIATE"
    assert evaluation["affected_slot"] == "FLEX"
    assert evaluation["would_start"] == "YES"
    assert evaluation["suggested_drop"]["player"] is None
    assert evaluation["faab"]["state"] == "NO_BID"
    assert evaluation["faab"]["category"] == "NONE"
    assert evaluation["faab"]["remaining"] == 79
    assert evaluation["faab"]["low"] == evaluation["faab"]["high"] == 0

    missing_full_ppr = waiver_acquisition_evaluation(candidate, needs, {**settings, "full_ppr": None})
    assert missing_full_ppr["horizon"] == "UNAVAILABLE"
    assert missing_full_ppr["would_start"] == "UNCERTAIN"
    assert "FULL_PPR_SETTINGS_UNAVAILABLE" in missing_full_ppr["blockers"]


def test_pagewide_directional_gate_requires_fresh_position_relevant_change():
    from owner_operations import waiver_acquisition_evaluation

    candidate = {
        "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "recommendation_state": "PRELIMINARY_SUGGESTION",
        "player_id": "candidate", "player": "RB Candidate", "position": "RB",
        "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
        "opportunity_metrics": {"state": "AVAILABLE", "rows": [{"freshness_state": "FRESH"}]},
        "player_comparison": {"what_changed": {"state": "AVAILABLE", "changes": [{"field": "snap_share", "direction": "UP"}]}},
    }
    need = {"RB": {"state": "AVAILABLE", "position": "RB", "starter_shortage": 0, "depth_shortage": 1}}
    settings = {"state": "AVAILABLE", "full_ppr": True}
    irrelevant = waiver_acquisition_evaluation(candidate, need, settings)
    stale = waiver_acquisition_evaluation({**candidate, "opportunity_metrics": {"state": "AVAILABLE", "rows": [{"freshness_state": "STALE"}]}}, need, settings)

    assert irrelevant["evidence_relevance"] == "SCREENING_ONLY"
    assert irrelevant["action"] == "NO_RECOMMENDATION"
    assert stale["evidence_relevance"] == "SCREENING_ONLY"
    assert stale["action"] == "NO_RECOMMENDATION"


def selected_comparison_fixture(selected_points=(10, 10, 10), candidate_points=(15, 15, 15), *, selected_starter=False, candidate_position="WR", selected_snap=None, candidate_snap=None, selected_weeks=(1, 2, 3), candidate_weeks=(1, 2, 3), selected_production_state="AVAILABLE", roster_coverage_complete=True, current_position_count=5, flex_need=False, focus="all", selected_changes=None, candidate_changes=None, selected_opportunity=None, candidate_opportunity=None, include_guidance=True):
    from owner_operations import waiver_selected_player_comparison

    def production(points, weeks, state="AVAILABLE"):
        return {"state": state, "rows": [
            {"season": 2026, "week": week, "fantasy_points_ppr": points[index], "scoring_format": "FULL_PPR", "freshness_state": "FRESH"}
            for index, week in enumerate(weeks)
        ] if state == "AVAILABLE" else [], "blockers": [] if state == "AVAILABLE" else ["OPPORTUNITY_DATA_STALE"]}

    def snap(value):
        return {"state": "AVAILABLE", "rows": [{"season": 2026, "week": 3, "snap_share": value, "freshness_state": "FRESH"}], "blockers": []} if value is not None else {"state": "UNAVAILABLE", "rows": [], "blockers": ["SNAP_SHARE_UNAVAILABLE"]}

    selected = {"source_player_id": "s-selected", "player_id": "s-selected", "player": "Selected WR", "position": "WR", "sleeper_current_starter": selected_starter,
                "recent_production": production(selected_points, selected_weeks, selected_production_state), "snap_share": snap(selected_snap),
                "player_comparison": {"what_changed": {"state": "AVAILABLE" if selected_changes else "INSUFFICIENT_EVIDENCE", "changes": selected_changes or []}},
                "opportunity_metrics": selected_opportunity or {"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_READER_NO_ROWS"]}}
    candidate = {
        "player_id": "s-candidate", "player": "Available WR", "position": candidate_position,
        "candidate_disposition": "PRELIMINARY_SUGGESTION", "recommendation_state": "PRELIMINARY_SUGGESTION",
        "identity_resolution": {"resolution_state": "RESOLVED"},
        "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
        "recent_production": production(candidate_points, candidate_weeks), "snap_share": snap(candidate_snap),
        "player_comparison": {"what_changed": {"state": "AVAILABLE" if candidate_changes else "INSUFFICIENT_EVIDENCE", "changes": candidate_changes or []}},
        "opportunity_metrics": candidate_opportunity or {"state": "UNAVAILABLE", "rows": [], "blockers": ["OPPORTUNITY_READER_NO_ROWS"]},
        "roster_guidance": {"s-selected": {"authority": "PROVISIONAL", "this_week": {"action": "REVIEW_ADD"}, "rest_of_season": {"action": "MONITOR"}, "provisional_bid": {"state": "PROVISIONAL", "low": 4, "high": 8, "reason": "4-8% remaining FAAB. Not a projected winning bid."}}},
    }
    if not include_guidance:
        candidate.pop("roster_guidance", None)
    roster = [selected] + [{"position": "WR"} for _ in range(current_position_count - 1)]
    needs = {"WR": {"state": "AVAILABLE", "position": "WR", "required_starters": 2, "depth_target": 4}}
    if flex_need:
        needs["FLEX"] = {"state": "AVAILABLE", "position": "FLEX", "starter_shortage": 1}
    settings = {"state": "AVAILABLE", "full_ppr": True, "flex_eligible_positions": ["RB", "WR", "TE"]}
    result = waiver_selected_player_comparison(selected, candidate, needs, settings, {"state": "AVAILABLE", "remaining": 79}, roster_coverage_complete, roster, 2026, focus)
    return result


def test_selected_player_comparison_adds_better_bench_player_with_safe_budgeted_drop():
    result = selected_comparison_fixture()

    assert result["selected_player_id"] == "s-selected"
    assert result["candidate_id"] == "s-candidate"
    assert result["decision"] == "ADD"
    assert result["suggested_drop"]["player_id"] == "s-selected"
    assert result["comparison_summary"]["candidate_average"] == 15.0
    assert result["comparison_summary"]["selected_average"] == 10.0
    assert result["comparison_summary"]["difference"] == 5.0
    assert result["comparison_summary"]["sample_size"] == 3
    assert result["faab"]["state"] == "PROVISIONAL"
    assert result["faab"]["high"] <= result["faab"]["remaining"] == 79
    assert {"expected role", "acquisition duration", "player news"} <= set(result["missing_evidence"])
    assert result["evidence_level"] == "PRELIMINARY"

    season_focus = selected_comparison_fixture(focus="rest_of_season")
    assert season_focus["decision"] == "MONITOR"
    assert season_focus["faab"]["state"] == "NO_BID"
    assert season_focus["suggested_drop"]["player_id"] is None

    missing_bid_inputs = selected_comparison_fixture(include_guidance=False)
    assert missing_bid_inputs["decision"] == "ADD"
    assert missing_bid_inputs["faab"]["state"] == "PROVISIONAL"
    assert missing_bid_inputs["faab"]["high"] <= missing_bid_inputs["faab"]["remaining"]


def test_selected_player_comparison_holds_better_selected_player_and_preserves_zero():
    result = selected_comparison_fixture(selected_points=(0, 10, 20), candidate_points=(0, 5, 10))

    assert result["decision"] == "HOLD"
    assert result["comparison_summary"]["weeks"] == [{"season": 2026, "week": week} for week in (1, 2, 3)]
    assert result["comparison_summary"]["candidate_average"] == 5.0
    assert result["comparison_summary"]["selected_average"] == 10.0
    assert result["faab"] == {"state": "NO_BID", "low": 0, "high": 0, "category": "NONE", "rationale": "No bid is suggested for HOLD."}


def test_selected_player_comparison_treats_snap_only_as_screening_and_blocks_unsafe_drop():
    partial = selected_comparison_fixture(
        selected_production_state="BLOCKED", selected_snap=None, candidate_snap=0.91,
    )
    matched_usage = selected_comparison_fixture(
        selected_production_state="BLOCKED", selected_snap=0.86, candidate_snap=0.91,
    )
    unsafe_drop = selected_comparison_fixture(current_position_count=4)
    starter = selected_comparison_fixture(selected_starter=True)

    assert partial["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert partial["comparison_summary"]["state"] == "SCREENING_ONLY"
    assert matched_usage["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert matched_usage["comparison_summary"]["state"] == "SCREENING_ONLY"
    assert unsafe_drop["decision"] == "HOLD"
    assert unsafe_drop["suggested_drop"]["player_id"] is None
    assert starter["decision"] == "HOLD"
    assert starter["suggested_drop"]["player_id"] is None


def test_selected_player_comparison_allows_directional_matched_position_opportunity_monitor():
    selected_usage = {"state": "AVAILABLE", "rows": [{"season": 2026, "week": 4, "target_share": 0.20, "touch_share": 0.18, "freshness_state": "FRESH"}]}
    candidate_usage = {"state": "AVAILABLE", "rows": [{"season": 2026, "week": 4, "target_share": 0.31, "touch_share": 0.28, "freshness_state": "FRESH"}]}
    result = selected_comparison_fixture(
        selected_production_state="BLOCKED",
        selected_opportunity=selected_usage,
        candidate_opportunity=candidate_usage,
    )

    assert result["decision"] == "MONITOR"
    assert result["relevance_class"] == "DIRECTIONAL_SIGNAL"
    assert result["comparison_summary"]["metric"] == "matched_position_opportunity"
    assert result["comparison_summary"]["delta"]["target_share"] == pytest.approx(0.11)
    assert result["faab"]["state"] == "NO_BID"


def test_selected_player_comparison_adds_supported_flex_candidate_with_matched_full_ppr():
    result = selected_comparison_fixture(candidate_position="RB", flex_need=True)

    assert result["decision"] == "ADD"
    assert result["candidate_position"] == "RB"
    assert result["comparison_summary"]["candidate_average"] == 15.0
    assert result["comparison_summary"]["selected_average"] == 10.0
    assert result["suggested_drop"]["player_id"] == "s-selected"
    assert "CANDIDATE_POSITION_NOT_RELEVANT_TO_SELECTED_PLAYER" not in result["blockers"]
    assert result["faab"]["state"] == "PROVISIONAL"
    assert result["faab"]["category"] == "FLEX_CHALLENGER"
    assert result["faab"]["remaining"] == 79
    assert result["faab"]["high"] <= 79


def test_cross_position_snap_share_alone_is_screening_not_a_named_monitor():
    result = selected_comparison_fixture(
        candidate_position="RB", candidate_snap=0.72, selected_snap=0.5,
        selected_production_state="BLOCKED", flex_need=True,
    )

    assert result["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert result["comparison_summary"]["state"] == "SCREENING_ONLY"
    assert "no direct cross-position points comparison" in result["comparison_summary"]["disclosure"].lower()


def test_selected_player_comparison_uses_separate_cohorts_without_direct_difference():
    result = selected_comparison_fixture(selected_weeks=(1, 2), candidate_weeks=(3, 4))

    assert result["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert result["comparison_summary"]["state"] == "SCREENING_ONLY"
    assert "difference" not in result["comparison_summary"]
    assert "candidate_average" not in result["comparison_summary"]
    assert "selected_average" not in result["comparison_summary"]
    assert "screening-only evidence" in result["comparison_summary"]["reason"]


def test_selected_player_comparison_uses_what_changed_from_both_players_as_monitor_context():
    result = selected_comparison_fixture(
        selected_production_state="BLOCKED",
        selected_changes=[{"field": "carry_share", "direction": "DOWN", "label": "Carry Share", "display": "carry share down"}],
        candidate_changes=[{"field": "target_share", "direction": "UP", "label": "Target Share", "display": "target share up"}],
    )

    assert result["decision"] == "MONITOR"
    assert result["comparison_summary"]["state"] == "PARTIAL"
    assert "difference" not in result["comparison_summary"]
    assert any("Candidate: target share up" in reason for reason in result["reasons"])
    assert result["comparison_summary"]["selected_changes"][0]["display"] == "carry share down"


def test_selected_player_decline_alone_does_not_make_every_candidate_monitor():
    result = selected_comparison_fixture(
        selected_production_state="BLOCKED",
        selected_changes=[{"field": "carry_share", "direction": "DOWN", "label": "Carry Share", "display": "carry share down"}],
    )

    assert result["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert result["relevance_class"] == "SCREENING_ONLY"
    assert result["candidate_id"] == "s-candidate"
    assert not any("Selected player" in reason for reason in result["reasons"])


def test_selected_comparison_shows_exact_stale_production_blocker():
    result = selected_comparison_fixture(selected_production_state="BLOCKED")

    assert result["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert "selected player recent_production: OPPORTUNITY_DATA_STALE" in result["missing_evidence"]


def test_news_identity_uses_only_unique_lineage_complete_gsis_espn_crosswalk():
    from owner_operations import resolve_espn_news_identity

    player = {"sleeper_espn_id": None, "opportunity_identity_state": "RESOLVED", "opportunity_player_id": "gsis-1"}
    lineage = {"source_authority": "automated:nflverse", "retrieved_at": COMPARISON_NOW, "coverage_state": "COMPLETE"}
    resolved = resolve_espn_news_identity(player, [{"gsis_id": "gsis-1", "espn_id": "4241474"}], lineage)
    ambiguous = resolve_espn_news_identity(player, [{"gsis_id": "gsis-1", "espn_id": "4241474"}, {"gsis_id": "gsis-1", "espn_id": "4241475"}], lineage)
    unverified = resolve_espn_news_identity(player, [{"gsis_id": "gsis-1", "espn_id": "4241474"}], {**lineage, "coverage_state": "PARTIAL"})

    assert resolved == {"state": "RESOLVED", "espn_id": "4241474", "method": "NFLVERSE_UNIQUE_GSIS_ESPN_CROSSWALK", "blockers": []}
    assert ambiguous["state"] == "UNAVAILABLE"
    assert ambiguous["blockers"] == ["ESPN_NEWS_IDENTITY_AMBIGUOUS"]
    assert unverified["state"] == "UNAVAILABLE"
    assert unverified["blockers"] == ["ESPN_NEWS_IDENTITY_CROSSWALK_UNVERIFIED"]


def test_selected_player_comparison_blocks_identity_ownership_and_irrelevant_positions():
    from owner_operations import waiver_selected_player_comparison

    candidate = {
        "player_id": "bad", "position": "K", "candidate_disposition": "PRELIMINARY_SUGGESTION",
        "identity_resolution": {"resolution_state": "AMBIGUOUS", "blocker": "WAIVER_CANDIDATE_ID_AMBIGUOUS"},
        "evidence_context": {"ownership_state": "UNAVAILABLE", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
    }
    result = waiver_selected_player_comparison({"source_player_id": "selected", "player": "Selected", "position": "WR"}, candidate, {}, {}, roster_coverage_complete=True)

    assert result["decision"] == "BLOCKED"
    assert result["suggested_drop"]["player_id"] is None
    assert "WAIVER_CANDIDATE_ID_AMBIGUOUS" in result["blockers"]
    assert "WAIVER_CANDIDATE_OWNERSHIP_UNVERIFIED" in result["blockers"]
    assert "CANDIDATE_POSITION_NOT_RELEVANT_TO_SELECTED_PLAYER" in result["blockers"]


def test_waiver_candidate_confidence_does_not_depend_on_consensus_verification():
    from owner_operations import waiver_candidate_context

    candidate = preliminary_candidate(recent_production={"state": "AVAILABLE", "rows": [{"week": 3, "fantasy_points_ppr": 8.0, "scoring_format": "FULL_PPR", "freshness_state": "FRESH"}]})
    needs = {"WR": {"state": "AVAILABLE", "strategic_need": "ADD_DEPTH", "drivers": ["WR depth is below target."]}}
    verified = waiver_candidate_context(candidate, [], needs, "VERIFIED")
    unverified = waiver_candidate_context(candidate, [], needs, "UNVERIFIED")

    assert verified["confidence"] == unverified["confidence"]
    assert verified["risk"] == unverified["risk"]
    assert "ranking" not in verified["confidence"].lower()


def test_waiver_route_ownership_blocked_publishes_no_candidates_or_comparisons(monkeypatch):
    response, captured = render_waiver_route(monkeypatch, rosters_available=False)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert captured["waiver_evidence"]["allowed"] is False
    assert captured["recommendations"] == []
    assert "Recommendations blocked" in html
    assert "Player comparison \u00b7 informational context" not in html


def render_trust_panel(candidates):
    templates = Environment(loader=FileSystemLoader(Path(__file__).parents[1] / "templates"))
    return templates.get_template("_waiver_trust_panel.html").render(waiver_evidence={"ownership": {}, "eligibility": {}}, waiver_candidates=candidates)


def trust_panel_article(rendered, player):
    start = rendered.index(f"<h4>{player} ")
    return rendered[start:rendered.index("</article>", start)]


def supported_trust_candidate():
    from owner_operations import waiver_player_comparison
    candidate = resolved_candidate(
        need=1, projection=120.0, faab=9,
        recent_production={"state": "AVAILABLE", "rows": [{"week": 2, "fantasy_points_ppr": 0.0}, {"week": 1, "fantasy_points_ppr": 14.2}]},
        evidence_context={
            "roster_fit": {"state": "AVAILABLE", "label": "addresses an active need"},
            "opportunity": {"state": "AVAILABLE", "reason": "Targets: 7; carries: 0; target share: 0.27."},
            "confidence": "supported evidence",
            "risk": ["no additional evidence-backed risk identified"],
            "suggested_drop": {"state": "INFORMATIONAL_ONLY", "player": "Bench WR"},
            "role": {"state": "UNAVAILABLE"}, "duration": {"state": "UNAVAILABLE"},
        },
    )
    candidate["player_comparison"] = waiver_player_comparison(candidate)
    return candidate


def test_trust_panel_displays_supported_candidate_evidence():
    article = trust_panel_article(render_trust_panel([supported_trust_candidate()]), "Avail WR")
    assert "<strong>Recent Production:</strong> Wk 2: 0.0 Full-PPR pts (2 supported weeks)" in article
    assert "<strong>Usage Evidence:</strong> Targets: 7; carries: 0; target share: 0.27." in article
    assert "<strong>What Changed:</strong> +3 targets" in article
    assert "Confidence: supported evidence" in article
    assert "Roster fit: addresses an active need" in article
    assert "Suggested drop: Unavailable" in article
    assert "FAAB: Unavailable" in article
    assert "Bench WR" not in article
    assert "$9" not in article
    assert "UNAVAILABLE" not in article
    assert "Expected role: Unavailable" in article and "Opportunity duration: Unavailable" in article


def test_trust_panel_keeps_missing_candidate_evidence_unavailable():
    article = trust_panel_article(render_trust_panel([{"player": "Bare RB", "position": "RB", "need": None, "projection": None, "faab": None}]), "Bare RB")
    for text in (
        "<strong>Recent Production:</strong> UNAVAILABLE",
        "<strong>Usage Evidence:</strong> UNAVAILABLE",
        "<strong>What Changed:</strong> UNAVAILABLE",
        "Confidence: Unavailable",
        "Risk: Unavailable",
        "Suggested drop: Unavailable",
        "Roster fit: Not supported",
        "FAAB: Unavailable",
    ):
        assert text in article


def test_trust_panel_shows_partial_evidence_field_by_field():
    candidate = supported_trust_candidate()
    candidate["recent_production"] = {"state": "BLOCKED", "rows": [{"week": 2, "fantasy_points_ppr": 9.0}]}
    candidate["evidence_context"] = {**candidate["evidence_context"], "opportunity": {"state": "UNAVAILABLE", "reason": "no row"}}
    candidate["player_comparison"] = {"what_changed": {"state": "INSUFFICIENT_EVIDENCE", "changes": []}}
    article = trust_panel_article(render_trust_panel([candidate]), "Avail WR")
    assert "<strong>Recent Production:</strong> UNAVAILABLE" in article
    assert "<strong>Usage Evidence:</strong> UNAVAILABLE" in article
    assert "<strong>What Changed:</strong> UNAVAILABLE" in article
    assert "Confidence: supported evidence" in article and "Roster fit: addresses an active need" in article


def test_waiver_route_trust_panel_uses_candidate_evidence_without_changing_publication(monkeypatch):
    response, captured = render_waiver_route(monkeypatch)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    panel = html[html.index('<section class="card waiver-trust-panel">'):]
    wr = trust_panel_article(panel, "Avail WR")
    assert "<strong>Usage Evidence:</strong> Targets:" in wr
    assert "<strong>What Changed:</strong> +3 targets" in wr
    assert "Confidence: " in wr and "Confidence: Unavailable" not in wr
    assert "Avail RB" not in panel
    assert "<strong>Recent Production:</strong> UNAVAILABLE" in wr
    view = published_view(captured["preliminary_suggestions"])
    monkeypatch.undo()
    assert view == published_view(render_waiver_route(monkeypatch)[1]["preliminary_suggestions"])
    assert len(view) == 1


def test_manager_waiver_view_does_not_promote_alphabetical_options():
    options = [
        {"candidate": {"player": "Arizona Cardinals", "nfl_team": "ARI", "position": "DEF"},
         "claim": None, "game_context": {"game_context_state": "UNAVAILABLE"},
         "bye_evidence": {"authoritative": False}},
        {"candidate": {"player": "Atlanta Falcons", "nfl_team": "ATL", "position": "DEF"},
         "claim": None, "game_context": {"game_context_state": "UNAVAILABLE"},
         "bye_evidence": {"authoritative": False}},
        {"candidate": {"player": "Baltimore Ravens", "nfl_team": "BAL", "position": "DEF"},
         "claim": None, "game_context": {"game_context_state": "UNAVAILABLE"},
         "bye_evidence": {"authoritative": False}},
    ]
    section = {
        "position": "DEF", "label": "PLAYERS TO CONSIDER",
        "need": {"state": "AVAILABLE", "strategic_need": "NO_ACTION"},
        "need_message": "No current DEF starter or depth shortage is verified.",
        "explanation": "These are comparable verified options. The display order is not a quality ranking.",
        "options": options, "more_options": [], "available_count": 3,
        "priority_need": False,
    }
    html = render_waivers(waiver_position_sections=[section])
    primary = html[html.index('id="your-waiver-decisions"'):html.index('<details class="manager-waiver"')]
    assert "Arizona Cardinals" in primary and "Atlanta Falcons" in primary and "Baltimore Ravens" in primary
    assert "comparable verified options" in primary
    assert "display order is not a quality ranking" in primary
    assert "BEST SUPPORTED OPTION" not in primary
    assert 'id="waiver-data-details"' in html
    assert '<details class="manager-waiver" id="waiver-data-details">' in html


def test_manager_waiver_view_explains_slot_fill_and_keeps_bid_and_drop_qualified():
    claim = {
        "candidate": "Free K", "candidate_team": "SEA", "candidate_position": "K",
        "manager_reason": "Fills the verified required K starter slot; no player-value advantage is claimed.",
        "faab": {"state": "PROVISIONAL", "recommended": 2, "low": 1, "high": 3, "remaining": 79, "rationale": "Small provisional one-week guardrail."},
        "conditional_drop": {"state": "CONDITIONAL", "reason": "Only if a roster slot must be opened."},
    }
    option = {
        "candidate": {"player": "Free K", "nfl_team": "SEA", "position": "K"},
        "claim": claim,
        "game_context": {"game_context_state": "AVAILABLE", "week": 6, "venue": "HOME", "opponent": "SF"},
        "bye_evidence": {"authoritative": True, "freshness_state": "FRESH", "is_current_week_bye": False},
    }
    fallback = {
        "candidate": {"player": "Fallback K", "nfl_team": "CHI", "position": "K"},
        "claim": {
            "candidate": "Fallback K", "candidate_team": "CHI", "candidate_position": "K",
            "faab": {"state": "PROVISIONAL", "recommended": 1, "low": 1, "high": 2},
        },
        "game_context": {"game_context_state": "AVAILABLE", "week": 6, "venue": "AWAY", "opponent": "ATL"},
        "bye_evidence": {"authoritative": True, "freshness_state": "FRESH", "is_current_week_bye": False},
    }
    section = {
        "position": "K", "label": "SLOT-FILL OPTION",
        "need": {"state": "AVAILABLE", "strategic_need": "ADD_STARTER", "starter_shortage": 1},
        "need_message": "1 required K starter slot needs filling.",
        "explanation": "This fills a verified one-week starter need.",
        "options": [option, fallback], "more_options": [], "available_count": 2,
        "priority_need": True,
    }
    html = render_waivers(waiver_position_sections=[section])
    primary = html[html.index('id="your-waiver-decisions"'):html.index('<details class="manager-waiver"')]
    assert "ACTION:</strong> SLOT-FILL OPTION" in primary
    assert "Week 6" in primary and "Home vs SF" in primary and "Not on bye" in primary
    assert "Fills the verified required K starter slot" in primary
    assert "VALUE-BASED BID:</strong> Unavailable" in primary
    assert "PROVISIONAL SLOT-FILL GUARDRAIL:</strong> $2 ($1–$3)" in primary
    assert "This is not an estimated winning bid." in primary
    assert "ESTIMATED WINNING BID:</strong> Unavailable" in primary
    assert "Separate contingent claims; bids are not cumulative." in primary
    assert "$1 provisional slot-fill guardrail; not a winning-bid estimate" in primary
    assert "Conditional only (not automatic):" in primary and "not an automatic drop" in primary


def test_manager_waiver_view_shows_searchable_player_specific_outcome():
    html = render_waivers(waiver_candidate_outcomes=[{
        "player_id": "s-likely", "player": "Isaiah Likely", "team": "NYG", "position": "TE",
        "message": "Available, but there is not enough current evidence to rank this player above alternatives.",
    }], waiver_explain_player="Isaiah Likely")
    assert 'placeholder="For example, Isaiah Likely"' in html
    assert 'data-player="isaiah likely"' in html
    assert "Available, but there is not enough current evidence to rank this player above alternatives." in html
    assert 'class="manager-outcome" data-player="isaiah likely"' in html


def test_live_waiver_route_exposes_isaiah_likely_specific_outcome(monkeypatch):
    response, captured = render_waiver_route(
        monkeypatch,
        include_missing_candidate=True,
        extra_pool_candidates=[{
            "player_id": "s-likely", "name": "Isaiah Likely", "position": "TE",
            "team": "NYG", "projection": 90.0, "tier": 4,
        }],
        explain_player="Isaiah Likely",
    )
    assert response.status_code == 200
    outcome = next(row for row in captured["waiver_candidate_outcomes"] if row["player"] == "Isaiah Likely")
    assert outcome["message"].startswith("Available, but unranked for current-week:")
    assert outcome["details"]["waiver_value"]["state"] == "UNRANKED"
    assert outcome["details"]["waiver_value"]["horizon"] == "this_week"
    html = response.get_data(as_text=True)
    assert 'data-player="isaiah likely"' in html
    assert outcome["message"] in html
    assert "matching recent production and position-relevant usage across these alternatives are unavailable.." not in html.lower()


def test_live_waiver_route_always_returns_explicit_outcome_for_kaimi_fairbairn(monkeypatch):
    response, captured = render_waiver_route(
        monkeypatch,
        explain_player="Kaimi Fairbairn",
        consensus={"source": "FantasyPros consensus via DynastyProcess", "horizons": {}},
    )
    assert response.status_code == 200
    outcomes = captured["waiver_candidate_outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["player"] == "Kaimi Fairbairn"
    assert outcomes[0]["message"].startswith("Not in the evaluated candidate pool")
    assert outcomes[0]["details"]["ownership"] == "NOT_EVALUATED"
    assert outcomes[0]["details"]["identity"]["resolution_state"] == "UNRESOLVED"
    assert outcomes[0]["details"]["ranking_horizon"] == "this_week"

SLOT_NOW = "2026-10-13T00:00:00+00:00"


FAAB_BALANCE = {"state": "AVAILABLE", "budget": 100, "remaining": 79, "min_bid": 0}


def game_context(**overrides):
    base = {"contract_id": "schedule.game_context.v1", "season": 2026, "week": 6, "team": "SEA", "opponent": "SF", "venue": "HOME", "display_matchup": "vs SF",
            "kickoff_pacific": "2026-10-18 13:05:00", "schedule_source": "automated:nflverse-schedules:games.csv.gz:sha256:x", "schedule_retrieved_at": SLOT_NOW,
            "schedule_freshness": "FRESH", "game_context_state": "AVAILABLE", "blocker": None}
    return {**base, **overrides}


def slot_fill_fixture(position="K", *, starter=True, bye=None, health="HEALTHY", shortage=0, candidate_overrides=None, settings_state="AVAILABLE", candidate_bye="default", empty_slots=None, game="default", balance="default", roster_extra=0):
    from owner_operations import waiver_selected_player_comparison
    selected = {"source_player_id": "s-sel", "player_id": "s-sel", "player": f"Rostered {position}", "position": position, "team": "MIN",
                "sleeper_current_starter": starter, "lineup_slot": position if starter else None, "empty_required_slots": empty_slots, "health_state": health, "health_freshness_state": "FRESH",
                "recent_production": {"state": "UNAVAILABLE", "rows": [], "blockers": ["PLAYER_WEEK_PRODUCTION_INPUT_UNAVAILABLE:x"]},
                "opportunity_metrics": {"state": "STALE", "rows": [], "blockers": ["OPPORTUNITY_DATA_STALE"]}}
    candidate = {"player_id": "s-cand", "player": f"Free {position}", "position": position, "team": "SEA", "candidate_disposition": "PRELIMINARY_SUGGESTION",
                 "recommendation_state": "PRELIMINARY_SUGGESTION", "identity_resolution": {"resolution_state": "RESOLVED"},
                 "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
                 "recent_production": {"state": "UNAVAILABLE", "rows": []}, "opportunity_metrics": {"state": "UNAVAILABLE", "rows": []}, **(candidate_overrides or {})}
    need = {position: {"state": "AVAILABLE", "position": position, "required_starters": 1, "starter_shortage": shortage, "depth_target": 1}}
    settings = {"state": settings_state, "starter_slots": {position: 1}, "flex_eligible_positions": ["RB", "WR", "TE"]}
    return waiver_selected_player_comparison(selected, candidate, need, settings, FAAB_BALANCE if balance == "default" else balance, True, [selected] + [{"position": "WR"}] * roster_extra, 2026, "all", bye_evidence=bye,
                                              candidate_game_context=game_context() if game == "default" else game, roster_capacity=14,
                                              candidate_bye_evidence=bye_contract(team="SEA", bye_week=9, is_current_week_bye=False) if candidate_bye == "default" else candidate_bye)


def bye_contract(**overrides):
    base = {"domain": "bye", "team": "MIN", "season": 2026, "bye_week": 6, "current_week": 6, "is_current_week_bye": True, "authoritative": True,
            "authority_mode": "SEASON_STATIC", "contract_id": "bye.season_static.v1", "freshness_state": "FRESH", "completeness_state": "COMPLETE", "blocker": None, "source": "automated:nflverse-schedules:derived-bye", "retrieved_at": SLOT_NOW}
    return {**base, **overrides}


@pytest.mark.parametrize("position", ["K", "DEF"])
def test_mandatory_slot_on_authoritative_bye_is_preliminary_recommendation(position):
    result = slot_fill_fixture(position, bye=bye_contract())
    assert result["decision"] == "PRELIMINARY_RECOMMENDATION" and result["authority"] == "PRELIMINARY"
    assert result["decision_basis"] == "MANDATORY_STARTER_SLOT" and result["evidence_level"] == "PRELIMINARY"
    assert result["disclosure"] and result["evidence_used"] and result["missing_evidence"] and result["recommendation_impact"] and result["manager_reason"]
    assert result["faab"]["state"] == "PROVISIONAL" and result["suggested_drop"]["player"] is None and result["conditional_drop"]["state"] == "UNAVAILABLE"
    assert not any(key in result for key in ("rank", "priority_score", "confidence", "expected_gain"))
    assert "production and opportunity comparison: NOT_APPLICABLE for K/DEF" in result["missing_evidence"]
    assert not any("OPPORTUNITY_DATA_STALE" in item for item in result["missing_evidence"])


def test_empty_required_slot_and_unusable_health_trigger_without_bye():
    assert slot_fill_fixture("K", starter=False, shortage=1)["decision"] == "PRELIMINARY_RECOMMENDATION"
    assert slot_fill_fixture("K", health="OUT")["decision_basis"] == "MANDATORY_STARTER_SLOT"


def test_usable_starter_not_on_bye_stays_no_actionable_upgrade():
    assert slot_fill_fixture("K")["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert slot_fill_fixture("K", bye=bye_contract(is_current_week_bye=False, bye_week=9))["decision"] == "NO_ACTIONABLE_UPGRADE"


@pytest.mark.parametrize("bye", [
    bye_contract(authoritative=False, freshness_state="UNAVAILABLE", blocker="BYE_TEAM_COVERAGE_INCOMPLETE", is_current_week_bye=False),
    bye_contract(authoritative=False, freshness_state="UNAVAILABLE", blocker="BYE_SOURCE_TIMESTAMP_UNVERIFIED", is_current_week_bye=False),
    bye_contract(authoritative=False, freshness_state="BLOCKED", blocker="BYE_WEEK_CONFLICT", is_current_week_bye=False),
    bye_contract(authoritative=False, completeness_state="INCOMPLETE", is_current_week_bye=False),
    bye_contract(team="SEA"),
])
def test_non_authoritative_or_mismatched_bye_cannot_trigger(bye):
    assert slot_fill_fixture("DEF", bye=bye)["decision"] == "NO_ACTIONABLE_UPGRADE"


def test_unverified_candidate_or_league_slot_truth_stays_blocked_or_unchanged():
    unverified = slot_fill_fixture("K", bye=bye_contract(), candidate_overrides={"evidence_context": {"ownership_state": "UNAVAILABLE", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"}})
    assert unverified["decision"] == "BLOCKED"
    assert slot_fill_fixture("K", bye=bye_contract(), settings_state="UNAVAILABLE")["decision"] == "NO_ACTIONABLE_UPGRADE"


def test_preliminary_slot_fill_renders_without_authoritative_language():
    result = slot_fill_fixture("K", bye=bye_contract())
    candidate = {"player": "Free K", "player_id": "s-cand", "position": "K", "selected_comparison": result}
    html = render_waivers(preliminary_suggestions=[{"player_id": "s-cand", "player": "Free K", "position": "K", "recommendation_state": "PRELIMINARY_SUGGESTION"}], wda_roster=[{"player_id": "s-sel", "player": "Rostered K", "position": "K"}], selected_result=result, selected_comparisons=[candidate], selected_player={"player": "Rostered K", "position": "K", "player_id": "s-sel", "valid": True},
                          selected_screened_summary={"count": 0, "reason_counts": {}}, selected_focus="all")
    assert "PRELIMINARY RECOMMENDATION" in html and "Mandatory Starter Slot" in html and "MIN bye week 6" in html
    assert "ADD Free K" not in html and "NO ACTIONABLE UPGRADE" not in html


def test_unavailable_bye_state_is_visible_without_recommendation():
    result = slot_fill_fixture("K", bye=bye_contract(authoritative=False, freshness_state="UNAVAILABLE", blocker="BYE_TEAM_COVERAGE_INCOMPLETE", is_current_week_bye=False, recommendation_impact="Bye evidence is present but does not cover every NFL team."))
    html = render_waivers(preliminary_suggestions=[{"player_id": "s-cand", "player": "Free K", "position": "K", "recommendation_state": "PRELIMINARY_SUGGESTION"}], wda_roster=[{"player_id": "s-sel", "player": "Rostered K", "position": "K"}], selected_result=result, selected_comparisons=[], selected_player={"player": "Rostered K", "position": "K", "player_id": "s-sel", "valid": True},
                          selected_screened_summary={"count": 0, "reason_counts": {}}, selected_focus="all")
    assert "NO ACTIONABLE UPGRADE" in html and "BYE_TEAM_COVERAGE_INCOMPLETE" in html


def test_season_static_bye_contract_drives_slot_fill_without_age_threshold(monkeypatch):
    from services.schedule_bye_evidence import team_bye_evidence
    monkeypatch.delenv("BYE_EVIDENCE_MAX_AGE_SECONDS", raising=False)
    teams = [f"T{index:02d}" for index in range(31)] + ["MIN"]
    rows = [{"season": 2026, "team": team, "bye_week": 6, "source": "automated:nflverse-schedules:derived-bye:games.csv.gz:sha256:x",
             "source_recorded_at": "2026-10-04T08:36:32+00:00", "retrieved_at": "2026-10-04T09:57:59+00:00"} for team in teams]
    bye = team_bye_evidence(rows, season=2026, team="MIN", week=6, now=SLOT_NOW)
    result = slot_fill_fixture("DEF", bye=bye)
    assert bye["authoritative"] and result["decision"] == "PRELIMINARY_RECOMMENDATION" and result["slot_trigger"] == "BYE_WEEK"


@pytest.mark.parametrize("candidate_bye", [None, bye_contract(team="SEA", bye_week=6, is_current_week_bye=True), bye_contract(team="SEA", authoritative=False, is_current_week_bye=False, blocker="BYE_TEAM_COVERAGE_INCOMPLETE")])
def test_candidate_on_bye_or_unverified_bye_cannot_fill_the_slot(candidate_bye):
    result = slot_fill_fixture("K", bye=bye_contract(), candidate_bye=candidate_bye)
    assert result["decision"] == "NO_ACTIONABLE_UPGRADE"


def test_sleeper_empty_lineup_slot_with_unusable_only_player_triggers_slot_fill():
    from owner_operations import sleeper_empty_required_slots
    positions = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"]
    starters = ["1", "2", "3", "4", "5", "6", "7", "0", "0"]
    assert sleeper_empty_required_slots(starters, positions) == ["K", "DEF"]
    assert sleeper_empty_required_slots(starters[:-1], positions) is None
    result = slot_fill_fixture("K", starter=False, bye=bye_contract(), empty_slots=["K", "DEF"])
    assert result["decision"] == "PRELIMINARY_RECOMMENDATION" and result["slot_trigger"] == "BYE_WEEK"
    assert slot_fill_fixture("K", starter=False, empty_slots=["K"])["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert slot_fill_fixture("K", starter=False, bye=bye_contract(), empty_slots=[])["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert slot_fill_fixture("K", starter=False, bye=bye_contract(), empty_slots=None)["decision"] == "NO_ACTIONABLE_UPGRADE"


def test_team_defense_health_is_not_applicable_but_unknown_player_health_stays_unavailable():
    from owner_operations import _waiver_candidate_health, _waiver_health_state
    now = datetime.now(timezone.utc).isoformat()
    defense = _waiver_candidate_health({"position": "DEF", "injury_status": None, "status": None}, now, True)
    assert defense["health_status_available"] and _waiver_health_state(defense["injury_status"]) == "HEALTHY" and defense["health_blocker"] is None
    player = _waiver_candidate_health({"position": "K", "injury_status": None, "status": None}, now, True)
    assert player["health_status_available"] is False


def plan_inputs(position="K", candidates=None, **kw):
    roster_player = {"player_id": "s-sel", "source_player_id": "s-sel", "player": f"Rostered {position}", "position": position, "team": "MIN", "is_starter": False, "lineup_slot": None,
                     "empty_required_slots": [position], "health_state": "HEALTHY", "health_freshness_state": "FRESH"}
    def cand(pid, name, team):
        return {"player_id": pid, "player": name, "position": position, "team": team, "candidate_disposition": "PRELIMINARY_SUGGESTION", "recommendation_state": "PRELIMINARY_SUGGESTION",
                "identity_resolution": {"resolution_state": "RESOLVED"}, "recommendation_blockers": [],
                "evidence_context": {"ownership_state": "VERIFIED", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"},
                "recent_production": {"state": "UNAVAILABLE", "rows": []}, "opportunity_metrics": {"state": "UNAVAILABLE", "rows": []}}
    cands = [cand(*c) for c in (candidates or [("c2", "Zed Kicker", "SEA"), ("c1", "Abe Kicker", "NE"), ("c3", "Mid Kicker", "KC")])]
    bye_rows = [{"season": 2026, "team": team, "bye_week": 6 if team in ("MIN", "KC") else 9, "source": "automated:nflverse-schedules:derived-bye:x", "source_recorded_at": SLOT_NOW, "retrieved_at": SLOT_NOW}
                for team in ["MIN", "SEA", "NE", "KC"] + [f"T{i:02d}" for i in range(28)]]
    games = [{"home_team": "SEA", "away_team": "SF", "game_time_pacific": "2026-10-18 13:05:00", "source": "automated:nflverse-schedules:games.csv.gz:sha256:x", "source_recorded_at": SLOT_NOW, "retrieved_at": SLOT_NOW},
             {"home_team": "DEN", "away_team": "NE", "game_time_pacific": "2026-10-18 10:00:00", "source": "automated:nflverse-schedules:games.csv.gz:sha256:x", "source_recorded_at": SLOT_NOW, "retrieved_at": SLOT_NOW}]
    needs = {position: {"state": "AVAILABLE", "position": position, "required_starters": 1, "starter_shortage": 0, "depth_target": 1, "rostered": 1}}
    settings = {"state": "AVAILABLE", "starter_slots": {position: 1}}
    from owner_operations import build_waiver_plan
    args = dict(wda_roster=[roster_player], wda_candidates=cands, team_needs=needs, league_settings=settings, faab_balance=FAAB_BALANCE, roster=[roster_player] * 14, season=2026, week=6,
                bye_rows=bye_rows, schedule_rows=games, roster_capacity=14)
    args.update(kw)
    return build_waiver_plan(**args)


def test_plan_k_and_def_show_team_opponent_home_away_and_reject_bye_candidates():
    plan = plan_inputs("K")
    names = [c["candidate"] for c in plan["problems"][0]["claims"]]
    assert names == ["Abe Kicker", "Zed Kicker"] and "Mid Kicker" not in names
    by_name = {c["candidate"]: c["game_context"] for c in plan["problems"][0]["claims"]}
    assert by_name["Zed Kicker"]["display_matchup"] == "vs SF" and by_name["Zed Kicker"]["venue"] == "HOME"
    assert by_name["Abe Kicker"]["display_matchup"] == "at DEN" and by_name["Abe Kicker"]["venue"] == "AWAY"
    assert plan_inputs("DEF", candidates=[("d1", "Seattle Seahawks", "SEA")])["problems"][0]["claims"][0]["game_context"]["opponent"] == "SF"


def test_plan_ordering_is_not_input_order_and_is_labeled_equivalent():
    plan = plan_inputs("K")
    problem = plan["problems"][0]
    assert problem["claims"][0]["candidate"] == "Abe Kicker" and problem["ordering"] == "VERIFIED_EQUIVALENT_OPTIONS"
    assert "Verified equivalent slot-fill options" in problem["ordering_note"] and problem["fallback_count"] == 1


def test_plan_missing_schedule_blocks_publication_and_renders_no_supported_claim():
    plan = plan_inputs("K", schedule_rows=[])
    problem = plan["problems"][0]
    assert plan["state"] == "NO_SUPPORTED_CLAIM" and problem["claims"] == [] and problem["state"] == "NO_SUPPORTED_CLAIM"
    html = render_waivers(waiver_plan=plan)
    assert "NO SUPPORTED CLAIM" in html


def test_plan_pass_when_no_mandatory_slot_problem():
    plan = plan_inputs("K", wda_roster=[{"player_id": "te", "player": "TE One", "position": "TE", "team": "SEA"}])
    assert plan["state"] == "PASS" and plan["problems"] == [] and "PASS." in render_waivers(waiver_plan=plan)


def test_team_game_context_fails_closed_on_missing_conflict_and_identity():
    from services.schedule_bye_evidence import team_game_context
    row = {"home_team": "SEA", "away_team": "SF", "source": "automated:nflverse-schedules:x", "source_recorded_at": SLOT_NOW, "retrieved_at": SLOT_NOW}
    ok = team_game_context([row], season=2026, week=6, team="SF")
    assert ok["display_matchup"] == "at SEA" and ok["venue"] == "AWAY" and ok["game_context_state"] == "AVAILABLE"
    assert team_game_context([row], season=2026, week=None, team="SF")["blocker"] == "SCHEDULE_WEEK_UNVERIFIED"
    assert team_game_context([row], season=2026, week=6, team="DEN")["blocker"] == "SCHEDULE_GAME_NOT_FOUND"
    assert team_game_context([row, dict(row)], season=2026, week=6, team="SF")["game_context_state"] == "BLOCKED"
    assert team_game_context([{**row, "away_team": "SEA"}], season=2026, week=6, team="SEA")["blocker"] == "SCHEDULE_TEAM_IDENTITY_MISMATCH"
    assert team_game_context([{**row, "source": "csv:x"}], season=2026, week=6, team="SF")["blocker"] == "SCHEDULE_SOURCE_NOT_AUTOMATED"
    assert team_game_context([{**row, "retrieved_at": None}], season=2026, week=6, team="SF")["game_context_state"] == "UNAVAILABLE"


@pytest.mark.parametrize("position,remaining,alternatives", [("K", 79, 0), ("K", 250, 3), ("DEF", 79, 0), ("DEF", 400, 1), ("DEF", 400, 2), ("K", 10, 0), ("K", 1, 0)])
def test_slot_fill_faab_derives_from_remaining_and_stays_conservative(position, remaining, alternatives):
    from owner_operations import slot_fill_faab
    f = slot_fill_faab(position, {"state": "AVAILABLE", "budget": 500, "remaining": remaining, "min_bid": 0}, one_week_rental=True, equivalent_alternatives=alternatives)
    percent = 2 if position == "DEF" and alternatives < 2 else 1
    assert f["state"] == "PROVISIONAL" and f["recommended"] == max(1, int(remaining * percent / 100 + 0.5)) if remaining > 1 else f["recommended"] == 1
    assert 1 <= f["recommended"] <= f["high"] <= remaining and f["low"] <= f["recommended"]
    assert f["high"] <= max(f["recommended"], int(remaining * 0.03)) and f["posture"] == "CONSERVATIVE_ONE_WEEK_RENTAL"
    assert "winning bid" in f["rationale"] and "confidence" not in f


def test_slot_fill_faab_unavailable_not_zero_for_unknown_conflicting_or_exhausted_budget():
    from owner_operations import slot_fill_faab
    for balance in (None, {}, {"state": "UNAVAILABLE", "remaining": None, "min_bid": 0}, {"state": "AVAILABLE", "budget": 10, "remaining": 20, "min_bid": 0},
                    {"state": "AVAILABLE", "budget": 100, "remaining": 50, "min_bid": None}, {"state": "AVAILABLE", "budget": 100, "remaining": 0, "min_bid": 0}):
        f = slot_fill_faab("K", balance, one_week_rental=True)
        assert f["state"] == "UNAVAILABLE" and f["recommended"] is None
    assert slot_fill_faab("TE", FAAB_BALANCE, one_week_rental=True)["state"] == "UNAVAILABLE"


def test_plan_totals_count_primary_claims_only_and_never_fallbacks():
    plan = plan_inputs("K")
    primary = plan["problems"][0]["claims"][0]["faab"]["recommended"]
    assert plan["total_recommended_faab"] == primary and plan["projected_remaining_faab"] == 79 - primary
    unknown = plan_inputs("K", faab_balance={"state": "UNAVAILABLE"})
    assert unknown["total_recommended_faab"] is None and unknown["projected_remaining_faab"] is None


def test_conditional_drop_and_rental_wording_and_no_unsupported_claims():
    claim = plan_inputs("DEF", candidates=[("d1", "Seattle Seahawks", "SEA")])["problems"][0]["claims"][0]
    drop = claim["conditional_drop"]
    assert drop["label"] == "CONDITIONAL DROP FOR THIS CLAIM" and drop["roster_full"] is True and "not an automatic transaction" in drop["reason"]
    assert claim["rental"] == {"status": "ONE_WEEK_RENTAL", "reason": "Fills the required Week 6 slot. Reevaluate after the bye."}
    html = render_waivers(waiver_plan=plan_inputs("K"))
    for forbidden in ("Waiver Score", "ROS value", "confidence %", "Floor", "Ceiling", "Vegas", "implied"):
        assert forbidden not in html
    assert "YOUR WAIVER PLAN" in html and "PROVISIONAL SLOT-FILL FAAB" in html and "<details><summary>Technical details" in html


def test_candidate_without_schedule_context_cannot_fill_slot_and_blockers_stay():
    assert slot_fill_fixture("K", bye=bye_contract(), game=game_context(game_context_state="UNAVAILABLE", blocker="SCHEDULE_GAME_NOT_FOUND", opponent=None))["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert slot_fill_fixture("K", bye=bye_contract(), game=game_context(team="DEN"))["decision"] == "NO_ACTIONABLE_UPGRADE"
    assert slot_fill_fixture("K", bye=bye_contract(), balance={"state": "UNAVAILABLE"})["faab"]["state"] == "UNAVAILABLE"
    blocked = slot_fill_fixture("K", bye=bye_contract(), candidate_overrides={"evidence_context": {"ownership_state": "UNAVAILABLE", "eligibility_state": "VERIFIED", "health_state": "HEALTHY", "health_freshness_state": "FRESH", "health_source": "Sleeper API"}})
    assert blocked["decision"] == "BLOCKED"
