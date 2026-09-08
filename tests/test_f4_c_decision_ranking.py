from copy import deepcopy
import pytest

from services.decision_ranking import (
    build_action, build_decision_ranking, lineup_actions, rank_actions,
    score_action, trade_actions, waiver_actions,
)


def test_score_is_deterministic_and_bounded():
    action = build_action(
        action_id="a", category="lineup", title="Start A", action="Start A over B",
        reason="Measured edge", urgency="HIGH", confidence={"score": 90},
        expected_points_gain=7.5,
    )
    assert score_action(action) == score_action(action)
    assert 0 <= score_action(action) <= 100


def test_blocked_action_scores_zero_and_is_separated():
    blocked = build_action(
        action_id="blocked", category="waiver", title="Claim A", action="Add A",
        reason="Missing evidence", blockers=["READINESS_BLOCKED"], evidence_complete=False,
    )
    result = rank_actions([blocked])
    assert result["allowed"] is False
    assert result["action_count"] == 0
    assert result["blocked_count"] == 1
    assert result["blocked_actions"][0]["priority_score"] == 0


def test_ranking_orders_score_then_stable_tiebreakers():
    low = build_action(action_id="b", category="league", title="B", action="B", reason="B", urgency="LOW", confidence=60)
    high = build_action(action_id="a", category="lineup", title="A", action="A", reason="A", urgency="HIGH", confidence=90, expected_points_gain=5)
    result = rank_actions([low, high])
    assert [x["action_id"] for x in result["actions"]] == ["a", "b"]
    assert [x["priority"] for x in result["actions"]] == [1, 2]


def test_duplicate_ids_fail_closed():
    item = build_action(action_id="same", category="lineup", title="A", action="A", reason="A")
    with pytest.raises(ValueError, match="duplicate action_id"):
        rank_actions([item, item])


def test_lineup_adapter_uses_only_swap_decisions():
    intel = {"blockers": [], "missing_evidence_players": [], "start_sit_decisions": [
        {"action": "HOLD", "slot": "QB", "start": {"player": "A"}, "sit": {"player": "B"}, "weekly_score_delta": 1, "confidence": {"score": 100}, "reason": "Hold"},
        {"action": "SWAP", "slot": "FLEX", "start": {"player": "C"}, "sit": {"player": "D"}, "weekly_score_delta": 4.2, "confidence": {"score": 80}, "reason": "C ahead"},
    ]}
    rows = lineup_actions(intel)
    assert len(rows) == 1
    assert rows[0].action == "Start C over D"
    assert rows[0].expected_points_gain == 4.2


def test_waiver_adapter_preserves_bid_metadata_without_inventing_units():
    rows = waiver_actions([{"urgency": "HIGH", "recommended_bid_pct": 12, "recommended_bid": None, "add": {"name": "Add Me", "reason": "Need"}, "drop": None}])
    assert rows[0].metadata["recommended_bid_pct"] == 12
    assert rows[0].metadata["recommended_bid"] is None


def test_trade_adapter_preserves_package_and_owner_gain():
    intel = {"blockers": [], "one_for_one": [{
        "receive": [{"player": "Target"}], "send": [{"player": "Offer"}],
        "owner_gain": 6, "partner_gain": 2, "balance_gap": 4,
        "verdict": "BALANCED", "confidence": {"label": "HIGH", "score": 100},
        "reason": "Roster fit",
    }], "two_for_one": []}
    rows = trade_actions(intel)
    assert rows[0].action == "Offer Offer for Target"
    assert rows[0].expected_points_gain == 6
    assert rows[0].metadata["verdict"] == "BALANCED"


def test_build_decision_ranking_does_not_mutate_inputs():
    lineup = {"blockers": [], "missing_evidence_players": [], "start_sit_decisions": []}
    waiver = [{"urgency": "LOW", "add": {"name": "A", "reason": "Watch"}, "drop": None}]
    trade = {"blockers": [], "one_for_one": [], "two_for_one": []}
    before = deepcopy((lineup, waiver, trade))
    build_decision_ranking(lineup_intelligence=lineup, waiver_plans=waiver, trade_intelligence=trade)
    assert (lineup, waiver, trade) == before


def test_validation_rejects_unsupported_category_and_missing_contract():
    with pytest.raises(ValueError, match="unsupported"):
        build_action(action_id="x", category="unknown", title="X", action="X", reason="X")
    with pytest.raises(ValueError, match="required"):
        build_action(action_id="", category="lineup", title="X", action="X", reason="X")

