import json

import pytest

from phase_f.adapters import NoOpRecommendationAdapter
from phase_f.models import DraftPick, DraftState
from phase_f.simulator import DraftSimulator
from phase_f.sources import JsonLinesPickSource


def pick(number, roster, player):
    return DraftPick(
        pick_no=number,
        round_no=((number - 1) // 4) + 1,
        roster_id=roster,
        player_id=player,
    )


def test_complete_mock_draft():
    simulator = DraftSimulator(teams=4, rounds=2)
    picks = [pick(i, str(((i - 1) % 4) + 1), f"p{i}") for i in range(1, 9)]
    result = simulator.replay(picks)
    assert result.state.complete
    assert len(result.state.picks) == 8
    assert len(result.recommendations) == 8


def test_rejects_out_of_order_pick():
    state = DraftState(teams=4, rounds=2)
    with pytest.raises(ValueError, match="expected pick 1"):
        state.apply_pick(pick(2, "2", "p2"))


def test_rejects_duplicate_player():
    state = DraftState(teams=4, rounds=2)
    state.apply_pick(pick(1, "1", "p1"))
    with pytest.raises(ValueError, match="already drafted"):
        state.apply_pick(pick(2, "2", "p1"))


def test_json_lines_source(tmp_path):
    path = tmp_path / "draft.jsonl"
    records = [
        {"pick_no": 1, "round_no": 1, "roster_id": "1", "player_id": "p1"},
        {"pick_no": 2, "round_no": 1, "roster_id": "2", "player_id": "p2"},
    ]
    path.write_text("\n".join(json.dumps(x) for x in records), encoding="utf-8")
    parsed = list(JsonLinesPickSource(path))
    assert [x.player_id for x in parsed] == ["p1", "p2"]
