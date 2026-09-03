from services.roster_slots import build_roster_slots
from sleeper_intelligence import build_local_roster_context, build_waiver_action_plans


def roster():
    return [
        (1, "QB Starter", "QB", ""),
        (2, "RB Starter 1", "RB", ""),
        (3, "RB Starter 2", "RB", ""),
        (4, "WR Starter 1", "WR", ""),
        (5, "WR Starter 2", "WR", ""),
        (6, "TE Starter", "TE", ""),
        (7, "Flex RB", "RB", ""),
        (8, "Bench WR", "WR", ""),
        (9, "Bench QB", "QB", ""),
    ]


def test_shared_slot_assignment_matches_repository_shape():
    slots, bench = build_roster_slots(roster())
    assert slots["QB"][1] == "QB Starter"
    assert slots["FLEX"][1] == "Flex RB"
    assert [row[1] for row in bench] == ["Bench WR", "Bench QB"]


def test_local_context_contains_verified_bench_counts_and_needs():
    context = build_local_roster_context(roster())
    assert [row[1] for row in context["bench"]] == ["Bench WR", "Bench QB"]
    assert context["position_counts"] == {"QB": 2, "RB": 3, "WR": 3, "TE": 1}
    assert context["need_scores"]["RB"] > 0
    assert context["team"]["primary_need"] in {"RB", "WR", "TE"}


def test_local_context_empty_roster_is_safe():
    context = build_local_roster_context([])
    assert context["bench"] == []
    assert context["position_counts"] == {"QB": 0, "RB": 0, "WR": 0, "TE": 0}


def test_context_drives_action_plans_without_starters_as_drops():
    context = build_local_roster_context(roster())
    adds = [{
        "player_id": "add-rb", "name": "Trending RB", "position": "RB",
        "waiver_score": 340, "urgency": "HIGH", "recommended_bid_pct": 15,
        "recommended_bid": None,
    }]
    plan = build_waiver_action_plans(
        adds, context["bench"], context["position_counts"], context["need_scores"], limit=1
    )[0]
    assert plan["drop"]["player_name"] in {"Bench WR", "Bench QB"}
    assert "Starter" not in plan["drop"]["player_name"]


def test_context_preserves_original_roster_rows():
    rows = roster()
    before = list(rows)
    build_local_roster_context(rows)
    assert rows == before
