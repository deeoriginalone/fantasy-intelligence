# F3-A.1 Repository Integration

Connects F3-A to a DB-API PostgreSQL connection factory, injected repository callbacks, and Sleeper payload ingestion.

## Production boundaries
- `PostgresDraftEventStore`: migration 007 persistence.
- `RepositoryCallbacks`: player lookup, owner/roster lookup, roster write, and draft-board write.
- `SleeperDraftIngestionService`: provider adapter to canonical processor.

## Production gate
Repository callbacks must use the same transaction if database-wide atomicity is required. Run the full repository suite after installation. No Yahoo compatibility object is changed.
