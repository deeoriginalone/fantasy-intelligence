# Batch A.8 Matchup Enrichment Coverage

## Contract

This read-only validator evaluates already-supplied matchup enrichment evidence.
Non-bye players require an opponent, matchup rank, and explicitly supplied matchup modifier. Bye-week rows are exempt from those three fields. A verified matchup timestamp must be supplied as `matchup_updated_at` or `matchup_sync_time`.

## Fail-closed blockers

- `MATCHUP_DATA_MISSING`
- `MATCHUP_ROW_INVALID`
- `MATCHUP_FRESHNESS_UNKNOWN`
- `OPPONENT_DATA_MISSING`
- `MATCHUP_RANK_MISSING`
- `MATCHUP_MODIFIER_MISSING`

## Boundary

This batch creates the validator and focused unit contract. It does not modify the current matchup or lineup consumers, fetch matchup data, write to a database, submit transactions, or claim live-route validation.
