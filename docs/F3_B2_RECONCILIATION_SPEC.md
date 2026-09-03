# F3-B.2 Reconciliation Specification

## Objective

Compare a normalized source-of-truth draft event list with the local draft-event store and report all material drift without modifying local state.

## Input contract

`DraftReconciler.reconcile(source_events, draft_id)` accepts normalized `DraftEvent` objects. Sleeper payload retrieval and normalization remain outside this module. The existing `from_sleeper_pick()` provider can supply normalized events when live integration is added.

## Validated checks

- source, event, and selection counts
- missing local selections
- extra local selections
- duplicate source pick numbers
- duplicate source player IDs
- foreign draft IDs in source input
- event ID mismatch
- league ID mismatch
- draft ID mismatch
- pick, round, and round-pick mismatch
- roster and owner mismatch
- player mismatch
- event type mismatch
- missing local event record
- non-`APPLIED` local event status

## Scope boundary

Batch 03 validates reconciliation against the existing in-memory store contract. It does not call Sleeper, mutate the database, or claim PostgreSQL parity. Live source retrieval and PostgreSQL reconciliation require the concrete production store and an isolated database test strategy.
