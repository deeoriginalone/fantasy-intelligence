from datetime import datetime, timezone, timedelta
import pytest

from services.ux_evidence import derived_waiver_availability, evaluate_waiver_availability, resolve_waiver_candidate_identity, waiver_evidence_contract, waiver_ownership_freshness, waiver_roster_coverage
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from owner_operations import waiver_projection_contribution


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