# F3-A: Draft Event Pipeline

## Objective
Ingest draft selection events, validate and persist them idempotently, reconstruct authoritative draft state, and notify existing roster and draft-board integrations.

## In scope
- Provider-neutral canonical draft-event contract
- Sleeper adapter boundary
- Raw payload retention
- Validation and duplicate detection
- Ordered state application
- Processing status and failure records
- Safe replay
- PostgreSQL schema
- Unit tests and CLI reference entry point

## Out of scope
- Yahoo or Pick'em cleanup
- Market intelligence changes
- Recommendation-model changes
- UI redesign
- Deleting or renaming legacy tables

## Canonical event contract
Required: event_id, league_id, draft_id, pick_number, round, round_pick, player_id, event_type, occurred_at, source.
Optional: roster_id, owner_id. At least one of roster_id or owner_id is required.
System fields: received_at, raw_payload, processing_status, validation_error.

## State transitions
RECEIVED -> VALIDATED -> APPLIED
RECEIVED or VALIDATED -> FAILED
FAILED -> VALIDATED -> APPLIED during replay
A previously APPLIED event is an idempotent no-op.

## Idempotency
- `event_id` is globally unique.
- `(draft_id, pick_number)` is unique.
- `(draft_id, player_id)` is unique for selection events.
- Processing and state updates occur within one transaction in the production PostgreSQL adapter.

## Validation
- Required identifiers and timestamps must be present.
- pick_number, round, and round_pick must be positive integers.
- event_type must be `selection` for this batch.
- At least one ownership identifier must be present.
- Provider adapters must preserve raw payloads.
- Unknown player and ownership identifiers are validated by repository integration callbacks.

## Error handling
Validation and integration failures retain the raw event and failure reason. Replay processes only failed events. Duplicate applied events return a no-op result.

## Inputs
- Canonical JSON events
- Sleeper draft-pick payloads through the Sleeper adapter

## Outputs
- Persisted draft event audit row
- Authoritative draft selection row
- Roster-state update callback
- Draft-board update callback
- Structured processing result

## Dependencies
Python standard library for the reference pipeline. Production persistence requires the repository's PostgreSQL connection layer.

## Observability
Every result includes event_id, status, message, duplicate flag, and applied flag. Database rows retain received/processed timestamps and validation errors.

## Acceptance criteria
- Valid selections apply once.
- Identical events are safe to replay.
- Duplicate pick numbers and duplicate player selections are rejected.
- Invalid events retain failure information.
- Raw source payload is retained.
- Roster and draft-board callbacks run after validation.
- Callback failure does not leave an applied in-memory state.
- No Yahoo-specific object is introduced or modified.

## Rollback
Remove the new application package and reverse migration 007 by dropping `draft_selections` and `draft_events`. No legacy table is altered.

## F3-B handoff
F3-B may consume the authoritative ordered draft state and roster ownership produced by this batch for recommendation refreshes.
