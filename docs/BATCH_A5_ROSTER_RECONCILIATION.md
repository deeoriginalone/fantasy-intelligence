# Batch A.5 Roster Reconciliation Contract

## Scope

The service is read-only. The caller supplies:

1. Local roster rows.
2. One already-authoritative Sleeper roster payload.
3. Sleeper player metadata keyed by player ID.
4. The verified `fetched_at` timestamp of that roster snapshot.

## Statuses

- `MATCHED`: all comparable identities match and required evidence exists.
- `DIVERGENT`: comparable evidence exists, but local-only or Sleeper-only players exist.
- `UNKNOWN`: required evidence is absent or unsafe to compare.

## Fail-closed blockers

- `AUTHORITATIVE_SLEEPER_ROSTER_MISSING`
- `ROSTER_SNAPSHOT_TIMESTAMP_MISSING`
- `INVALID_LOCAL_ROSTER_ROWS`
- `DUPLICATE_LOCAL_PLAYERS`
- `UNMAPPED_SLEEPER_PLAYER_IDS`

## Timestamp provenance

`roster_updated_at` is copied only from the supplied Sleeper snapshot timestamp.
The service does not use `my_roster.updated_at` as synchronization evidence.

## Explicit non-goals

- No owner-roster inference.
- No database writes.
- No replacement or deletion of local rows.
- No waiver, lineup, trade, draft, or season transaction submission.
- No claim of live-route or production validation.
