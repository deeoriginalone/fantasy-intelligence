from .postgres_store import PostgresDraftEventStore
from .repository_integration import RepositoryCallbacks
from .service import DraftEventProcessor
from .sleeper_ingestion import SleeperDraftIngestionService


def mapped_player_exists(connection_factory, sleeper_player_id):
    conn = connection_factory()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1
                   FROM sleeper_player_map AS spm
                   WHERE spm.sleeper_player_id = %s
                     AND (
                         spm.local_player_name IS NOT NULL
                         OR EXISTS (
                             SELECT 1
                             FROM players AS p
                              WHERE REGEXP_REPLACE(
                                  REGEXP_REPLACE(
                                      LOWER(p.player_name), '[^a-z0-9]', '', 'g'
                                  ),
                                  '(jr|sr|ii|iii|iv)$', '', 'g'
                              ) = REGEXP_REPLACE(
                                  spm.normalized_name,
                                  '(jr|sr|ii|iii|iv)$', '', 'g'
                              )
                         )
                     )
                   LIMIT 1""",
                (str(sleeper_player_id),),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def build_runtime_ingestion(connection_factory, valid_roster_ids):
    roster_ids = {str(value) for value in valid_roster_ids if value is not None}
    callbacks = RepositoryCallbacks(
        player_lookup=lambda player_id: mapped_player_exists(connection_factory, player_id),
        owner_lookup=lambda roster_id, owner_id: str(roster_id) in roster_ids,
        roster_writer=lambda event: None,
        draft_board_writer=lambda event: None,
    )
    processor = DraftEventProcessor(
        store=PostgresDraftEventStore(connection_factory),
        player_exists=callbacks.player_exists,
        owner_exists=callbacks.owner_exists,
        roster_update=callbacks.update_roster,
        draft_board_update=callbacks.update_draft_board,
    )
    return SleeperDraftIngestionService(processor)


def process_runtime_picks(connection_factory, picks, league_id, draft_id, rosters):
    valid_roster_ids = [row.get("roster_id") for row in (rosters or [])]
    ingestion = build_runtime_ingestion(connection_factory, valid_roster_ids)
    results = ingestion.process_picks(picks or [], league_id, draft_id)
    return {
        "applied": sum(1 for result in results if result.applied),
        "duplicates": sum(1 for result in results if result.duplicate),
        "failed": sum(1 for result in results if result.status == "FAILED"),
        "results": results,
    }
