from contextlib import contextmanager
import json
from .models import DraftEvent


class PostgresDraftEventStore:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        self._connection = None

    @contextmanager
    def transaction(self):
        if self._connection is not None:
            yield self
            return
        conn = self.connection_factory()
        self._connection = conn
        try:
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._connection = None
            conn.close()

    @contextmanager
    def _connection_scope(self):
        if self._connection is not None:
            yield self._connection
            return
        conn = self.connection_factory()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _one(self, sql, params):
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def get_event(self, event_id):
        row = self._one(
            "SELECT event_id, processing_status, validation_error FROM draft_events WHERE event_id=%s",
            (event_id,),
        )
        return None if row is None else {"event_id": row[0], "status": row[1], "error": row[2]}

    def refresh_applied_metadata(self, event):
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE draft_events
                       SET league_id=%s, draft_id=%s, pick_number=%s,
                           round=%s, round_pick=%s,
                           roster_id=COALESCE(%s, roster_id),
                           owner_id=COALESCE(%s, owner_id),
                           player_id=%s, occurred_at=%s, source=%s,
                           raw_payload=%s::jsonb
                       WHERE event_id=%s AND processing_status='APPLIED'""",
                    (
                        event.league_id, event.draft_id, event.pick_number,
                        event.round, event.round_pick, event.roster_id,
                        event.owner_id, event.player_id, event.occurred_at,
                        event.source, json.dumps(event.raw_payload), event.event_id,
                    ),
                )
                cur.execute(
                    """UPDATE draft_selections
                       SET league_id=%s, round=%s, round_pick=%s,
                           roster_id=COALESCE(%s, roster_id),
                           owner_id=COALESCE(%s, owner_id),
                           player_id=%s,
                           selected_at=%s
                       WHERE source_event_id=%s""",
                    (
                        event.league_id, event.round, event.round_pick,
                        event.roster_id, event.owner_id, event.player_id,
                        event.occurred_at, event.event_id,
                    ),
                )

    def save_received(self, event):
        sql = """INSERT INTO draft_events(
          event_id,league_id,draft_id,pick_number,round,round_pick,roster_id,owner_id,
          player_id,event_type,occurred_at,received_at,source,raw_payload,processing_status
        ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,'RECEIVED')
                ON CONFLICT(event_id) DO UPDATE SET
                    league_id=EXCLUDED.league_id,
                    draft_id=EXCLUDED.draft_id,
                    pick_number=EXCLUDED.pick_number,
                    round=EXCLUDED.round,
                    round_pick=EXCLUDED.round_pick,
                    roster_id=EXCLUDED.roster_id,
                    owner_id=EXCLUDED.owner_id,
                    player_id=EXCLUDED.player_id,
                    occurred_at=EXCLUDED.occurred_at,
                    received_at=EXCLUDED.received_at,
                    source=EXCLUDED.source,
                    raw_payload=EXCLUDED.raw_payload,
                    processing_status='RECEIVED',
                    validation_error=NULL
                WHERE draft_events.processing_status='FAILED'"""
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event.event_id,event.league_id,event.draft_id,event.pick_number,
                    event.round,event.round_pick,event.roster_id,event.owner_id,event.player_id,
                    event.event_type,event.occurred_at,event.received_at,event.source,
                    json.dumps(event.raw_payload)))

    def mark(self, event_id, status, error=None):
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE draft_events SET processing_status=%s, validation_error=%s,
                    processed_at=CASE WHEN %s IN ('APPLIED','FAILED') THEN NOW() ELSE processed_at END
                    WHERE event_id=%s""", (status,error,status,event_id))

    def _selection(self, sql, params):
        row = self._one(sql, params)
        if row is None: return None
        return type("StoredSelection", (), {"event_id": row[0], "player_id": row[1]})()

    def selection_by_pick(self, draft_id, pick_number):
        return self._selection("SELECT source_event_id,player_id FROM draft_selections WHERE draft_id=%s AND pick_number=%s", (draft_id,pick_number))

    def selection_by_player(self, draft_id, player_id):
        return self._selection("SELECT source_event_id,player_id FROM draft_selections WHERE draft_id=%s AND player_id=%s", (draft_id,player_id))

    def apply_selection(self, event):
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO draft_selections(
                    draft_id,league_id,pick_number,round,round_pick,roster_id,owner_id,
                    player_id,source_event_id,selected_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(draft_id,pick_number) DO UPDATE SET
                    league_id=EXCLUDED.league_id,
                    round=EXCLUDED.round,
                    round_pick=EXCLUDED.round_pick,
                    roster_id=EXCLUDED.roster_id,
                    owner_id=EXCLUDED.owner_id,
                    player_id=EXCLUDED.player_id,
                    source_event_id=EXCLUDED.source_event_id,
                    selected_at=EXCLUDED.selected_at
                WHERE draft_selections.source_event_id=EXCLUDED.source_event_id""",
                (event.draft_id,event.league_id,event.pick_number,event.round,event.round_pick,
                 event.roster_id,event.owner_id,event.player_id,event.event_id,event.occurred_at))

    def failed_events(self):
        sql = """SELECT event_id,league_id,draft_id,pick_number,round,round_pick,roster_id,
          owner_id,player_id,event_type,occurred_at,received_at,source,raw_payload
          FROM draft_events WHERE processing_status='FAILED' ORDER BY received_at,event_id"""
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        return [DraftEvent(event_id=r[0],league_id=r[1],draft_id=r[2],pick_number=r[3],
            round=r[4],round_pick=r[5],roster_id=r[6],owner_id=r[7],player_id=r[8],
            event_type=r[9],occurred_at=r[10],received_at=r[11],source=r[12],raw_payload=r[13] or {})
            for r in rows]

    def ordered_state(self, draft_id):
        """Return DraftEvent objects, matching the reference-store behavior."""
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT
                           e.event_id,
                           e.league_id,
                           e.draft_id,
                           e.pick_number,
                           e.round,
                           e.round_pick,
                           e.roster_id,
                           e.owner_id,
                           e.player_id,
                           e.event_type,
                           e.occurred_at,
                           e.received_at,
                           e.source,
                           e.raw_payload
                       FROM draft_selections AS s
                       JOIN draft_events AS e
                         ON e.event_id = s.source_event_id
                       WHERE s.draft_id=%s
                       ORDER BY s.pick_number, e.event_id""",
                    (draft_id,),
                )
                rows = cur.fetchall()
        return [
            DraftEvent(
                event_id=row[0],
                league_id=row[1],
                draft_id=row[2],
                pick_number=row[3],
                round=row[4],
                round_pick=row[5],
                roster_id=row[6],
                owner_id=row[7],
                player_id=row[8],
                event_type=row[9],
                occurred_at=row[10],
                received_at=row[11],
                source=row[12],
                raw_payload=row[13] or {},
            )
            for row in rows
        ]

    def cleanup_test_draft(self, draft_id):
        """Delete only isolated F3-B.3.1 parity fixtures."""
        draft_id = str(draft_id)
        if not draft_id.startswith("f3b31-"):
            raise ValueError(
                "cleanup_test_draft only permits draft IDs beginning with 'f3b31-'"
            )
        with self._connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM draft_selections WHERE draft_id=%s",
                    (draft_id,),
                )
                cur.execute(
                    "DELETE FROM draft_events WHERE draft_id=%s",
                    (draft_id,),
                )
