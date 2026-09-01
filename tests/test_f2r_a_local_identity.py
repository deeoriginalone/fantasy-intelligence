from phase_f.models import DraftState
from services.draft_recommendation_service import Candidate


def test_integer_local_id_is_normalized_to_string():
    candidate = Candidate.from_row(
        (1, "Example Player", "RB", "ABC", 250.0, 1, 1.5, 123)
    )
    assert candidate.player_id == "123"


def test_draft_state_excludes_same_normalized_local_id():
    state = DraftState(teams=2, rounds=1)
    state.drafted_player_ids.add("123")
    candidate = Candidate.from_row(
        (1, "Example Player", "RB", "ABC", 250.0, 1, 1.5, 123)
    )
    assert candidate.player_id in state.drafted_player_ids
