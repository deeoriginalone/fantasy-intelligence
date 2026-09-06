from draft_events.runtime import mapped_player_exists


def test_draft_slot_fallback_enriches_pick_with_missing_owner():
    from app import enrich_sleeper_draft_picks

    picks = [{"pick_no": 5, "draft_slot": 5, "roster_id": None}]
    draft = {"slot_to_roster_id": {"5": 5}}

    enriched = enrich_sleeper_draft_picks(picks, draft)

    assert enriched[0]["roster_id"] == 5


def test_draft_slot_fallback_supports_string_slots_with_integer_keys():
    from app import enrich_sleeper_draft_picks

    picks = [{"pick_no": 6, "draft_slot": "6", "roster_id": None}]
    draft = {"slot_to_roster_id": {6: 8}}

    enriched = enrich_sleeper_draft_picks(picks, draft)

    assert enriched[0]["roster_id"] == 8


def test_picked_by_owner_mapping_precedes_draft_slot_mapping():
    from app import enrich_sleeper_draft_picks

    picks = [{
        "pick_no": 5,
        "draft_slot": 5,
        "picked_by": "owner-1",
        "roster_id": None,
    }]
    draft = {"slot_to_roster_id": {"5": 5}}
    rosters = [{"roster_id": 1, "owner_id": "owner-1"}]

    enriched = enrich_sleeper_draft_picks(picks, draft, rosters)

    assert enriched[0]["roster_id"] == 1


def test_existing_roster_id_is_preserved():
    from app import enrich_sleeper_draft_picks

    picks = [{
        "pick_no": 1,
        "draft_slot": 1,
        "picked_by": "owner-1",
        "roster_id": 9,
    }]
    draft = {"slot_to_roster_id": {"1": 1}}
    rosters = [{"roster_id": 2, "owner_id": "owner-1"}]

    enriched = enrich_sleeper_draft_picks(picks, draft, rosters)

    assert enriched[0]["roster_id"] == 9


def test_unresolved_pick_remains_unresolved():
    from app import enrich_sleeper_draft_picks

    picks = [{
        "pick_no": 1,
        "draft_slot": 1,
        "picked_by": "",
        "roster_id": None,
    }]
    draft = {"slot_to_roster_id": {"2": 2}}

    enriched = enrich_sleeper_draft_picks(picks, draft, [{"roster_id": 1, "owner_id": "configured-owner"}])

    assert enriched[0]["roster_id"] is None


def test_player_mapping_uses_existing_local_player_name_column():
    class Cursor:
        def __init__(self):
            self.statement = ""

        def execute(self, statement, params):
            self.statement = statement

        def fetchone(self):
            return ("Ja'Marr Chase",)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()

        def cursor(self):
            return self.cursor_instance

        def close(self):
            pass

    connection = Connection()
    assert mapped_player_exists(lambda: connection, "7564") is True
    assert "local_player_id" not in connection.cursor_instance.statement


def test_player_mapping_allows_normalized_local_name_fallback():
    class Cursor:
        def execute(self, statement, params):
            self.statement = statement

        def fetchone(self):
            return (1,)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    assert mapped_player_exists(lambda: Connection(), "8138") is True