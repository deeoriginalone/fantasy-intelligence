from contextlib import contextmanager
import json

class PostgresDraftEventStore:
    """DB-API 2.0 PostgreSQL adapter for migration 007 tables."""
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        self._connection = None

    @contextmanager
    def transaction(self):
        if self._connection is not None:
            yield self
            return
        cx = self.connection_factory()
        self._connection = cx
        try:
            yield self
            cx.commit()
        except Exception:
            cx.rollback()
            raise
        finally:
            self._connection = None
            cx.close()

    def _cx(self):
        if self._connection is None:
            raise RuntimeError("store operation requires transaction")
        return self._connection

    def _one(self, sql, params):
        with self._cx().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def get_event(self, event_id):
        row = self._one("SELECT event_id, processing_status, validation_error FROM draft_events WHERE event_id=%s", (event_id,))
        return None if row is None else {"event_id": row[0], "status": row[1], "error": row[2]}

    def save_received(self, event):
        sql = "INSERT INTO draft_events(event_id,league_id,draft_id,pick_number,round,round_pick,roster_id,owner_id,player_id,event_type,occurred_at,received_at,source,raw_payload,processing_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,'RECEIVED') ON CONFLICT(event_id) DO NOTHING"
        with self._cx().cursor() as cur:
            cur.execute(sql, (event.event_id,event.league_id,event.draft_id,event.pick_number,event.round,event.round_pick,event.roster_id,event.owner_id,event.player_id,event.event_type,event.occurred_at,event.received_at,event.source,json.dumps(event.raw_payload)))

    def mark(self, event_id, status, error=None):
        with self._cx().cursor() as cur:
            cur.execute("UPDATE draft_events SET processing_status=%s, validation_error=%s, processed_at=CASE WHEN %s IN ('APPLIED','FAILED') THEN NOW() ELSE processed_at END WHERE event_id=%s", (status,error,status,event_id))

    def _selection(self, sql, params):
        row = self._one(sql, params)
        if row is None:
            return None
        return type("StoredSelection", (), {"event_id": row[0], "player_id": row[1]})()

    def selection_by_pick(self, draft_id, pick_number):
        return self._selection("SELECT source_event_id,player_id FROM draft_selections WHERE draft_id=%s AND pick_number=%s", (draft_id,pick_number))

    def selection_by_player(self, draft_id, player_id):
        return self._selection("SELECT source_event_id,player_id FROM draft_selections WHERE draft_id=%s AND player_id=%s", (draft_id,player_id))

    def apply_selection(self, event):
        sql = "INSERT INTO draft_selections(draft_id,league_id,pick_number,round,round_pick,roster_id,owner_id,player_id,source_event_id,selected_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(draft_id,pick_number) DO NOTHING"
        with self._cx().cursor() as cur:
            cur.execute(sql, (event.draft_id,event.league_id,event.pick_number,event.round,event.round_pick,event.roster_id,event.owner_id,event.player_id,event.event_id,event.occurred_at))

    def failed_events(self):
        raise NotImplementedError("production replay requires canonical payload reconstruction")

    def ordered_state(self, draft_id):
        with self._cx().cursor() as cur:
            cur.execute("SELECT * FROM draft_selections WHERE draft_id=%s ORDER BY pick_number", (draft_id,))
            return cur.fetchall()
