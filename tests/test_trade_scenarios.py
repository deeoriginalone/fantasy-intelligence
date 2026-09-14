import pytest

from services.trade_scenarios import build_trade_scenario
from services.trade_target_center import build_trade_target_center


@pytest.mark.parametrize("name,state,allowed", [("ready", "READY", True), ("ready_empty", "READY", True), ("degraded", "DEGRADED", True), ("blocked", "BLOCKED", False), ("identity_ambiguity", "BLOCKED", False)])
def test_controlled_trade_scenario_states(name, state, allowed):
    result = build_trade_scenario(name)
    assert result["publication_state"] == state
    assert result["allowed"] is allowed


def test_ready_empty_remains_ready_without_packages():
    center = build_trade_target_center(build_trade_scenario("ready_empty"))
    assert center["publication_state"] == "READY"
    assert center["allowed"] is True
    assert not center["ranked_opportunities"]


def test_ambiguity_blocks_publication_and_is_in_identity_lineage():
    result = build_trade_scenario("identity_ambiguity")
    assert "TRADE_IDENTITY_AMBIGUOUS" in result["blockers"]
    assert any(row["identity_state"] == "AMBIGUOUS" for row in result["identity_lineage"])


def test_scenario_contract_is_not_a_production_query_feature():
    text = open("owner_operations.py", encoding="utf-8").read()
    assert "if current_app.testing else None" in text


def test_unknown_scenario_fails_closed():
    result = build_trade_scenario("unknown")
    assert result["publication_state"] == "BLOCKED"
    assert "TRADE_SCENARIO_UNKNOWN" in result["blockers"]


def test_degraded_scenario_exposes_reduced_confidence():
    result = build_trade_scenario("degraded")
    assert result["integrity"]["confidence"] == {"label": "MEDIUM", "score": 75}