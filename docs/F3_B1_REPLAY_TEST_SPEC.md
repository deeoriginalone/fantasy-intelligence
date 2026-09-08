# F3-B.1 Replay Test Specification

## Verified production contract used by this batch

The implementation is based on the supplied repository source:

- `DraftEventProcessor.process(event)` returns a `ProcessingResult`.
- An event already stored with status `APPLIED` returns an idempotent no-op.
- `event_id` is the event identity.
- A selection is unique by `(draft_id, pick_number)`.
- A player selection is unique by `(draft_id, player_id)`.
- `InMemoryDraftEventStore.transaction()` restores event and selection snapshots when a callback raises.
- Failed events can be retried through `DraftEventProcessor.replay_failed()`.

## Scope

This batch validates the executable in-memory reference contract already used by the project's unit tests. It does not claim PostgreSQL replay validation because the supplied production store is explicitly a contract placeholder and no PostgreSQL implementation or database schema capture was supplied.

## Deterministic generated batch

- 1,000 events
- one league ID
- one draft ID
- 12 rotating roster IDs
- one unique event ID per pick
- one unique player ID per pick
- sequential `occurred_at` timestamps
- round and round-pick derived from 12 roster slots

The 1,000-event batch is a stress fixture, not a claim that a real NFL fantasy draft contains 1,000 picks.

## Automated scenarios

1. Baseline 1,000-event import
2. Identical replay
3. Ten consecutive replays
4. Partial prefix followed by complete replay
5. Reverse-order import and ordered reconstruction
6. Conflicting event for an existing pick number
7. Existing player assigned to a new pick
8. Mid-batch callback failure followed by failed-event replay

## Required invariants

- First import applies every valid event exactly once.
- Identical replay applies zero new selections.
- Replays return duplicate results rather than failures.
- Selection state does not drift.
- Partial replay adds only missing selections.
- Out-of-order input reconstructs pick order.
- Conflicts fail without changing authoritative selections.
- A callback failure rolls back the failed selection.
- A corrected failed event can later be applied.

## Validation discoveries

During execution, the replay suite confirmed two additional repository contracts:

1. `DraftEvent` is an immutable dataclass. Test scenarios requiring modified
   event values must construct a new event with `dataclasses.replace()` rather
   than mutate an existing event.

2. A rejected conflicting event remains in the event store with status
   `FAILED`. This increases the event audit count while leaving the
   authoritative selection count and ordered draft state unchanged.

These behaviors are intentional parts of the validated replay contract.
