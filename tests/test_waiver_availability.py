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
    assert "SAME-POSITION CANDIDATES TO REVIEW" in rendered
    assert "PROVISIONAL GUIDANCE" in rendered
    assert "POTENTIAL UPGRADE" not in rendered


def test_decision_assistant_no_upgrade_disclosure_present():
    candidate = preliminary_candidate()
    rendered = render_waivers(preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "Rank is not a projected points gain." in rendered
    assert "not guaranteed winning bids" in rendered


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


def test_decision_assistant_filters_candidates_to_selected_player_position():
    candidate = preliminary_candidate()
    roster_player = {"player_id": "roster-current", "player": "Current Player", "position": "WR", "projection": 100.0}
    kicker = {"player_id": "roster-kicker", "player": "Current Kicker", "position": "K", "projection": 100.0}
    rendered = render_waivers(roster=[roster_player, kicker], wda_roster=[kicker, roster_player], preliminary_suggestions=[candidate], wda_candidates=[candidate])
    assert "candidate.recommendation_state === 'PRELIMINARY_SUGGESTION'" in rendered
    assert "String(candidate.position || '').trim().toUpperCase() === selectedPosition" in rendered
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
    assert guidance["rest_of_season"]["action"] == "REVIEW_ADD"
    assert "bench-drop" in guidance["drop_review"]
    assert guidance["faab"] is None
    roster_player["is_starter"] = True
    assert "Do not drop a current starter" in waiver_move_guidance(candidate, roster_player)["drop_review"]
    candidate["recent_production"] = production([30, 20, 0])
    guidance = waiver_move_guidance(candidate, roster_player)
    assert guidance["this_week"]["action"] == "MONITOR"
    assert guidance["rest_of_season"]["action"] == "REVIEW_ADD"
    candidate["recent_production"] = production([0, 0, 0])
    guidance = waiver_move_guidance(candidate, roster_player)
    assert guidance["this_week"]["action"] == guidance["rest_of_season"]["action"] == "KEEP"


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
    assert context["confidence"] == "supported evidence"


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


def test_waiver_recommendation_gate_requires_fresh_healthy_source_and_verified_rank():
    from owner_operations import waiver_candidate_recommendation_state
    candidate = _waiver_gate_candidate("Active")

    assert candidate["health_freshness_state"] == "FRESH"
    assert waiver_candidate_recommendation_state(candidate, "VERIFIED")["recommendation_state"] == "ACTIONABLE"
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
    assert rendered.index("<strong>Health:</strong>") < rendered.index("<strong>Team Need:</strong>") < rendered.index("<strong>Roster Fit:</strong>") < rendered.index("<strong>Projection:</strong>") < rendered.index("<strong>Recent Production:</strong>") < rendered.index("<strong>Usage Evidence:</strong>") < rendered.index("<strong>What Changed:</strong>") < rendered.index("<strong>Suggested Drop:</strong>") < rendered.index("<strong>FAAB:</strong>")
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


def render_waiver_route(monkeypatch, *, rosters_available=True, disable_comparison=False, candidate_health=None, include_missing_candidate=False, ranking_source_verified=False, extra_candidate_count=0, production_rows=None, faab_settings=None, consensus=None):
    from flask import Flask
    import owner_operations
    catalog = {
        "s-owned": {"full_name": "Owned WR", "position": "WR", "team": "KC", "gsis_id": "gsis-owned"},
        "s-wr": {"full_name": "Avail WR", "position": "WR", "team": "DEN", "gsis_id": "gsis-wr", "injury_status": "Healthy"},
        "s-rb": {"full_name": "Avail RB", "position": "RB", "team": "LV", "gsis_id": None},
    }
    for player_id, health_fields in (candidate_health or {}).items():
        catalog[player_id].update(health_fields)
    pool_rows = [
        ("Owned WR", "WR", "KC", 1, 150.0, 1, 10.0, 9, None),
        ("Avail WR", "WR", "DEN", 2, 120.0, 2, 20.0, 9, None),
        ("Avail RB", "RB", "LV", 3, 110.0, 3, 30.0, 9, None),
    ]
    if include_missing_candidate:
        catalog["s-te"] = {"full_name": "Avail TE", "position": "TE", "team": "SEA", "gsis_id": None}
        pool_rows.append(("Avail TE", "TE", "SEA", 4, 90.0, 4, 40.0, 9, None))
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
    monkeypatch.setattr(owner_operations, "read_player_production", lambda *args, **kwargs: {"state": "AVAILABLE", "rows": (production_rows or {})[kwargs["player_id"]], "blockers": []} if kwargs.get("player_id") in (production_rows or {}) else {"state": "UNAVAILABLE", "rows": [], "blockers": ["PLAYER_WEEK_PRODUCTION_UNAVAILABLE"]})
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
    if faab_settings is not None:
        league["settings"] = {"waiver_type": 2, "waiver_budget": faab_settings[0]}
        rosters[0]["settings"] = {"waiver_budget_used": faab_settings[1]}
    connection = WaiverRouteConnection(pool_rows)
    blueprint = owner_operations.create_owner_operations_blueprint(
        lambda: connection,
        lambda league_id: league,
        lambda league_id: [{"user_id": "owner", "is_owner": True}],
        (lambda league_id: rosters) if rosters_available else (lambda league_id: None),
        lambda: catalog,
        lambda value: str(value).lower().replace(" ", ""),
    )
    app = Flask(__name__, root_path=str(Path(__file__).resolve().parents[1]), template_folder="templates")
    app.config.update(
        TESTING=True, SLEEPER_LEAGUE_ID="controlled",
        NFLVERSE_PLAYER_METADATA=[{"gsis_id": "gsis-wr", "player_id": "gsis-wr"}, {"gsis_id": "gsis-owned", "player_id": "gsis-owned"}],
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
    response = app.test_client().get("/waivers")
    captured["executed_queries"] = list(connection.executed_queries)
    return response, captured


def published_view(recommendations):
    return [(item.get("player"), item.get("faab"), item.get("bid_low"), item.get("bid_high"), item.get("priority_score"), (item.get("evidence_context") or {}).get("confidence")) for item in recommendations]


def test_waiver_route_attaches_comparison_only_to_published_candidates(monkeypatch):
    response, captured = render_waiver_route(monkeypatch)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert captured["recommendations"] == []
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
    assert "FAAB ranges remain provisional" in html


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
    assert {candidate["player_id"] for candidate in captured["wda_candidates"]} == {candidate["player_id"] for candidate in suggestions}
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
    assert guidance["this_week"]["action"] == guidance["rest_of_season"]["action"] == "REVIEW_ADD"
    assert guidance["provisional_bid"]["state"] == "PROVISIONAL"
    assert (guidance["provisional_bid"]["low"], guidance["provisional_bid"]["high"]) == (4, 8)
    assert "Do not drop a current starter" in guidance["drop_review"]
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
    assert [item["player"] for item in candidate_data] == ["Avail RB"]
    assert all(item["evidence_context"]["health_state"] == "HEALTHY" for item in candidate_data)
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
    assert [item["player"] for item in captured["recommendations"]] == ["Avail WR"]
    actionable = captured["recommendations"][0]
    assert actionable["recommendation_state"] == "ACTIONABLE"
    assert actionable["faab"] is not None and actionable["bid_low"] is not None and actionable["bid_high"] is not None
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
    assert "PRELIMINARY HEALTHY SUGGESTIONS AVAILABLE" in rendered
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


def test_waiver_route_uses_separate_current_source_ranks_and_blocks_missing_source(monkeypatch):
    def rank(value):
        return {"position": "WR", "ecr": value, "source_date": "2026-10-03"}
    consensus = {"source": "FantasyPros consensus via DynastyProcess", "horizons": {"this_week": {"state": "AVAILABLE", "ranks": {"s-wr": rank(10), "s-owned": rank(20)}}, "rest_of_season": {"state": "AVAILABLE", "ranks": {"s-wr": rank(30), "s-owned": rank(15)}}}}
    response, context = render_waiver_route(monkeypatch, faab_settings=(100, 21), consensus=consensus)
    guidance = context["wda_candidates"][0]["roster_guidance"]["s-owned"]
    assert response.status_code == 200
    assert guidance["this_week"]["action"] == "REVIEW_ADD"
    assert guidance["rest_of_season"]["action"] == "KEEP"
    assert "mean expert rank" in guidance["this_week"]["reason"]
    monkeypatch.undo()
    response, context = render_waiver_route(monkeypatch, faab_settings=(100, 21), consensus={"horizons": {}})
    guidance = context["wda_candidates"][0]["roster_guidance"]["s-owned"]
    assert guidance["this_week"]["action"] == guidance["rest_of_season"]["action"] == "MONITOR"
    assert guidance["provisional_bid"]["high"] is None


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
    panel = html[html.index("waiver-trust-panel"):]
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