from dataclasses import replace
from datetime import datetime, timezone

from draft_events.models import DraftEvent
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore


class RecordingCursor:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params):
        self.statements.append((statement, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class RecordingConnection:
    def __init__(self):
        self.cursor_instance = RecordingCursor()

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def test_failed_event_retry_refreshes_corrected_ownership_metadata():
    store = InMemoryDraftEventStore()
    processor = DraftEventProcessor(
        store,
        player_exists=lambda player_id: player_id == "7564",
        owner_exists=lambda roster_id, owner_id: roster_id == "1",
    )
    original = DraftEvent(
        event_id="retry-1",
        league_id="league",
        draft_id="draft",
        pick_number=5,
        round=1,
        round_pick=5,
        roster_id=None,
        owner_id=None,
        player_id="7564",
        event_type="selection",
        occurred_at=datetime.now(timezone.utc),
        source="sleeper",
    )
    assert processor.process(original).status == "FAILED"

    corrected = replace(original, roster_id="1", owner_id="owner-1")
    assert processor.process(corrected).status == "APPLIED"
    assert store.ordered_state("draft")[0].roster_id == "1"


def test_applied_event_refreshes_corrected_metadata_without_reapplying():
    store = InMemoryDraftEventStore()
    processor = DraftEventProcessor(store)
    event = DraftEvent(
        event_id="applied-refresh-1",
        league_id="league",
        draft_id="draft",
        pick_number=1,
        round=1,
        round_pick=1,
        roster_id="5",
        owner_id="owner-1",
        player_id="7564",
        event_type="selection",
        occurred_at=datetime.now(timezone.utc),
        source="sleeper",
    )
    assert processor.process(event).status == "APPLIED"
    corrected = replace(event, roster_id="1")
    result = processor.process(corrected)
    assert result.duplicate is True
    assert result.applied is False
    assert store.ordered_state("draft")[0].roster_id == "1"


def test_postgres_applied_metadata_refresh_preserves_stored_ownership_on_nulls():
    from draft_events.postgres_store import PostgresDraftEventStore

    connection = RecordingConnection()
    store = PostgresDraftEventStore(lambda: connection)
    event = DraftEvent(
        event_id="applied-refresh-ownership",
        league_id="league",
        draft_id="draft",
        pick_number=1,
        round=1,
        round_pick=1,
        roster_id=None,
        owner_id=None,
        player_id="7564",
        event_type="selection",
        occurred_at=datetime.now(timezone.utc),
        source="sleeper",
    )

    store.refresh_applied_metadata(event)

    draft_event_sql, draft_event_params = connection.cursor_instance.statements[0]
    selection_sql, selection_params = connection.cursor_instance.statements[1]
    assert "roster_id=COALESCE(%s, roster_id)" in draft_event_sql
    assert "owner_id=COALESCE(%s, owner_id)" in draft_event_sql
    assert "roster_id=COALESCE(%s, roster_id)" in selection_sql
    assert "owner_id=COALESCE(%s, owner_id)" in selection_sql
    assert draft_event_params[5:7] == (None, None)
    assert selection_params[3:5] == (None, None)