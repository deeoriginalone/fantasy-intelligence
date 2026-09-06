from draft_hq_integrity import build_draft_hq_integrity


def test_unresolved_current_picks_block_recommendations():
    result = build_draft_hq_integrity(
        draft_id="active-draft",
        remote_pick_count=35,
        persisted_pick_count=30,
        applied_event_count=17,
        failed_event_count=13,
        total_players=521,
        drafted_player_count=35,
        owner_pick_count=3,
    )

    assert result["consistent"] is False
    assert result["recommendations_allowed"] is False
    assert any("35 picks" in reason for reason in result["reasons"])


from sleeper_draft_signals import build_sleeper_draft_signals


class Cursor:
    def execute(self, statement, params):
        self.statement = statement

    def fetchone(self):
        return None


def test_live_draft_signals_use_active_snapshot_not_cached_league_draft():
    cursor = Cursor()
    stale = build_sleeper_draft_signals(cursor, "league", user_slot=5)

    active_draft = {
        "draft_id": "active-draft",
        "status": "paused",
        "type": "snake",
        "settings": {"teams": 10, "rounds": 14},
        "draft_order": {"owner": 5},
    }
    active_picks = [
        {
            "pick_no": 1,
            "draft_slot": 1,
            "player_id": "p1",
            "metadata": {"first_name": "Bijan", "last_name": "Robinson", "position": "RB"},
        }
        for _ in range(35)
    ]

    current = build_sleeper_draft_signals(
        cursor,
        "league",
        user_slot=5,
        active_draft=active_draft,
        active_picks=active_picks,
    )

    assert stale["draft_id"] != "active-draft"
    assert current["draft_id"] == "active-draft"
    assert current["pick_count"] == 35
    assert current["draft_status"] == "paused"