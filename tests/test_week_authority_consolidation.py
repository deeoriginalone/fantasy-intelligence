from pathlib import Path

from services.authoritative_week import build_authoritative_week_contract, resolve_week_owners

ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = (
    "weekly_intelligence.py",
    "weekly_routes.py",
    "nfl_intelligence_routes.py",
    "survivor_routes.py",
    "market_refresh.py",
    "pickem_auto_feed.py",
    "pickem_inputs_routes.py",
)


def owner(week, source, authority):
    return build_authoritative_week_contract(
        season=2026,
        week=week,
        source=source,
        source_authority=authority,
        retrieved_at="2026-09-16T12:00:00+00:00",
        freshness_state="FRESH",
        completeness_state="COMPLETE",
    )


def test_conflict_publishes_both_owners_and_mismatch_details():
    result = resolve_week_owners(
        owner(3, "application_state", "application_state.current_week"),
        owner(4, "Sleeper NFL state", "sleeper.state.nfl"),
    )
    assert result["state"] == "AVAILABLE"
    assert result["authoritative"] is True
    assert result["week"] == 4
    assert result["authority_agreement"] == "DISAGREEMENT"
    assert "PERSISTED_WEEK_CONFLICT" in result["warnings"]
    assert [owner["week"] for owner in result["conflicting_owners"]] == [4, 3]


def test_sleeper_unavailable_uses_valid_persisted_fallback():
    result = resolve_week_owners(
        build_authoritative_week_contract(blockers=["SLEEPER_NFL_STATE_UNAVAILABLE"]),
        owner(3, "application_state", "application_state.current_week"),
    )
    assert result["authoritative"] is True
    assert result["week"] == 3
    assert result["authority_agreement"] == "PERSISTED_FALLBACK"
    assert "SLEEPER_WEEK_UNAVAILABLE" in result["warnings"]


def test_both_sources_unavailable_remain_unavailable():
    result = resolve_week_owners(
        build_authoritative_week_contract(blockers=["SLEEPER_NFL_STATE_UNAVAILABLE"]),
        build_authoritative_week_contract(blockers=["CURRENT_WEEK_STATE_UNAVAILABLE"]),
    )
    assert result["authoritative"] is False
    assert result["week"] is None
    assert result["state"] == "UNAVAILABLE"


def test_known_consumers_do_not_contain_fallback_to_week_one():
    for name in CONSUMERS:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "or 1" not in text
        assert "get('week',1)" not in text
        assert "get('week', 1)" not in text


def test_contract_preserves_lineage_and_blockers():
    result = build_authoritative_week_contract(
        season=2026,
        week=3,
        source="application_state",
        source_authority="application_state.current_week",
        retrieved_at="2026-09-16T12:00:00+00:00",
        freshness_state="BLOCKED",
        completeness_state="INCOMPLETE",
        blockers=["OWNER_READ_FAILED"],
        lineage={"owner": "application_state.current_week"},
    )
    assert result["state"] == "BLOCKED"
    assert result["lineage"] == {"owner": "application_state.current_week"}
    assert "OWNER_READ_FAILED" in result["blockers"]
