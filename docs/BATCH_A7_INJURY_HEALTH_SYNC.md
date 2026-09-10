# Batch A.7 Injury Status Synchronization and Health Confidence

## Contract

This read-only service accepts:

1. Roster rows carrying a stable `player_id`.
2. An already-authoritative health snapshot keyed by that player ID.
3. The verified `injury_fetched_at` timestamp for that snapshot.

It does not fetch records, infer player identity, invent health status, generate a current timestamp, write to a database, or submit transactions.

## Fail-closed blockers

- `AUTHORITATIVE_INJURY_SOURCE_MISSING`
- `INJURY_SNAPSHOT_TIMESTAMP_MISSING`
- `ROSTER_PLAYER_ID_MISSING`
- `DUPLICATE_ROSTER_PLAYER_IDS`
- `INJURY_STATUS_UNRESOLVED`

## Output

The service returns synchronized player copies, `injury_updated_at`, a compatible `freshness_metadata` injury field, blockers, unresolved IDs, and capped health confidence.

## Boundary

This batch establishes the synchronization service and focused unit contract. It does not claim active route wiring, live API validation, persistence, or production proof.
