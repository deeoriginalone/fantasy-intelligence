# F3-A.2 Production Wiring

## Goal
Connect DraftEventProcessor, PostgresDraftEventStore, RepositoryCallbacks, and SleeperDraftIngestionService to production services.

## Work Items
1. Create PostgreSQL connection factory integration.
2. Wire player lookup using existing player identity mapping.
3. Wire owner/roster validation.
4. Wire roster update callbacks.
5. Wire draft-board update callbacks.
6. Integrate services/sleeper_service.py.
7. Add replay command.
8. Add end-to-end integration tests.

## Acceptance Criteria
- Live Sleeper payload reaches DraftEventProcessor.
- Event persists into draft_events.
- Selection persists into draft_selections.
- Roster ownership updates successfully.
- Draft board updates successfully.
- Replay is idempotent.
- Full repository test suite passes.
