# Player Identity Strategy

## Purpose

Define a stable, explicit identity model for players across the Fantasy Intelligence application, PostgreSQL, Sleeper synchronization, draft automation, mock drafts, recommendations, roster tracking, waiver analysis, and outcome evaluation.

This document is a prerequisite for completing Phase F Draft Day and Season Automation. A recommendation must refer to the same player before, during, and after a draft, even when different data sources use different identifiers.

---

## Current Verified State

The live PostgreSQL `players` table currently contains:

```text
id
player_name
position
nfl_team
projected_points
ranking
tier
injury_status
adp
bye_week
age
notes
```

Verified facts:

- `players.id` is an integer.
- `players` does not currently contain `player_id`.
- `players` does not currently contain `sleeper_player_id`.
- `players` does not currently contain `sleeper_id`.
- `player_name` exists, but a name should not be treated as a durable external identity.
- The refactored mock recommendation query currently selects `player_id`, which does not match the verified live schema and must be corrected before runtime use.

---

## Identity Decision

### Current internal identity

Use:

```text
players.id
```

as the current internal database identity for records already stored in `players`.

This identity is suitable for:

- Internal PostgreSQL joins
- Recommendation snapshots generated from the current `players` table
- Local mock-draft references
- Local audit records
- Local outcome records

### Required external identity

Add and maintain a separate stable external identity for Sleeper:

```text
players.sleeper_player_id
```

This identity should be used for:

- Sleeper draft picks
- Sleeper player synchronization
- Sleeper rosters
- Live draft event matching
- Post-draft roster reconciliation

### Identity rule

Never assume that:

```text
players.id == Sleeper player ID
```

`players.id` is the local database key. `sleeper_player_id` is the source-specific external key.

---

## Recommended Identity Model

### Canonical local key

```text
players.id
```

Properties:

- Integer
- Primary key
- Generated and controlled by PostgreSQL
- Never reused
- Never changed because an API value changes

### Sleeper source key

```text
players.sleeper_player_id
```

Recommended properties:

- Text
- Nullable during migration and reconciliation
- Unique when present
- Indexed
- Populated from verified Sleeper player data

### Optional future source keys

Only add source-specific fields when an actual integration requires them:

```text
espn_player_id
fantasypros_player_id
nflverse_player_id
```

Do not create or populate external IDs by guessing.

---

## Source-to-Identity Map

| Source or System | Incoming Identity | Local Identity | Matching Rule | Current Status |
|---|---|---|---|---|
| PostgreSQL `players` | `id` | `players.id` | Direct | Verified |
| Current ranking and projection CSVs | Usually player name plus attributes | `players.id` | Import-time resolution required | Needs validation |
| Sleeper players | Sleeper player identifier | `players.sleeper_player_id` then `players.id` | Exact external-ID lookup | Not implemented in current `players` schema |
| Sleeper draft picks | Sleeper player identifier | `players.sleeper_player_id` then `players.id` | Exact external-ID lookup | Blocked until mapping exists |
| Local mock draft | Current player tuple or local player reference | `players.id` | Exact local-ID lookup | Refactor required |
| Recommendation snapshots | Local player reference | `players.id` | Store local ID and source ID when available | Phase F work |
| Draft outcomes | Recommended and selected player references | `players.id` | Compare stable local IDs | Phase F work |

---

## Why Player Name Is Not the Canonical Identity

`player_name` may remain useful for display and carefully controlled reconciliation, but it should not be the primary identifier because:

- Names can be formatted differently across sources.
- Suffixes may be present or absent.
- Names may contain punctuation or abbreviations.
- Two records can potentially share the same name.
- A name correction could break historical links.

Name-based matching should be a migration or quarantine tool, not the final live-draft identity rule.

---

## Required Schema Work

### Proposed migration

Create a reviewed migration after confirming Sleeper source behavior:

```sql
ALTER TABLE players
    ADD COLUMN IF NOT EXISTS sleeper_player_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_players_sleeper_player_id
    ON players (sleeper_player_id)
    WHERE sleeper_player_id IS NOT NULL;
```

Do not apply this migration until:

1. A backup exists.
2. Duplicate and ambiguous player rows have been measured.
3. The Sleeper player payload and identifier format have been inspected.
4. A mapping report has been generated.
5. The migration has been tested in the sandbox database.

---

## Mapping and Reconciliation Process

### Stage 1: Exact external-ID match

If `sleeper_player_id` is present, match only on the exact value.

```text
Sleeper player ID
        ↓
players.sleeper_player_id
        ↓
players.id
```

### Stage 2: Controlled initial backfill

For records without `sleeper_player_id`, produce candidate matches using normalized attributes such as:

- player name
- position
- NFL team

This stage must generate a review report. It must not silently accept ambiguous matches.

### Stage 3: Quarantine unresolved records

Any record with no match or multiple candidates should be quarantined.

Suggested statuses:

```text
MATCHED
AMBIGUOUS
UNMATCHED
CONFLICT
```

Unresolved records must not be allowed into automated recommendations without a visible warning or blocking state.

---

## Recommended Mapping Table

If identity reconciliation grows beyond one source, use a dedicated mapping table rather than adding many columns to `players`.

```sql
CREATE TABLE player_source_identity (
    id BIGSERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(id),
    source_name TEXT NOT NULL,
    source_player_id TEXT NOT NULL,
    match_status TEXT NOT NULL,
    match_method TEXT,
    confidence NUMERIC,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_name, source_player_id),
    UNIQUE (player_id, source_name)
);
```

Recommended `source_name` values should be controlled constants, for example:

```text
sleeper
espn
fantasypros
nflverse
```

The direct `players.sleeper_player_id` approach is simpler for Phase F. The mapping-table approach is more extensible if multiple external player feeds become active.

---

## Phase F Identity Contract

Every Phase F draft pick should eventually contain:

```text
local_player_id
source_name
source_player_id
player_name
position
nfl_team
```

### Required fields for live Sleeper mode

```text
local_player_id = players.id
source_name = sleeper
source_player_id = Sleeper player ID
```

### Required fields for local sandbox mode

```text
local_player_id = players.id
source_name = local
source_player_id = optional
```

### Synthetic fixture mode

Synthetic IDs must be clearly labeled and must never be published as real player recommendations.

---

## Recommendation Snapshot Contract

Recommendation snapshots should record both local and source identity when available:

```json
{
  "local_player_id": 123,
  "source_name": "sleeper",
  "source_player_id": "external-id",
  "player_name": "Display Name",
  "position": "RB",
  "recommended_at_pick": 42,
  "score": 87.5,
  "reason": "Need, tier scarcity, and strategy score"
}
```

Historical evaluation should compare stable identifiers, not display names.

---

## Current Refactor Correction

The current `mock_pool()` change uses:

```sql
..., adp, player_id
```

The verified live schema has `id`, not `player_id`.

Before using the refactored recommendation path against PostgreSQL, change the query to:

```sql
..., adp, id
```

The Phase F repository adapter should initially use:

```text
player_id_column = id
```

This is only the local identity solution. It does not complete Sleeper-to-local mapping.

---

## Validation Rules

### Database rules

- Every active player row must have a non-null `players.id`.
- Every populated Sleeper ID must be unique.
- A Sleeper ID must map to no more than one local player.
- A local player must map to no more than one current Sleeper ID.
- Duplicate source mappings must be rejected.

### Application rules

- Drafted-player exclusion must compare stable IDs.
- Recommendation snapshots must store the local ID.
- Live Sleeper events must resolve to a local player before recommendation processing continues.
- Unknown players must enter quarantine.
- Ambiguous matches must block automatic processing.
- Display names must not be used as the sole deduplication key.

### Audit rules

- Record the source used to establish the mapping.
- Record when the mapping was verified.
- Record whether the match was exact or manually resolved.
- Preserve historical mappings used by prior recommendation snapshots.

---

## Test Plan

### Unit tests

- Local `players.id` is preserved in recommendation output.
- Duplicate local IDs are rejected in draft state.
- Duplicate Sleeper IDs are rejected by the mapping layer.
- Unknown Sleeper identities are quarantined.
- Ambiguous name matches are not auto-approved.
- Drafted players are excluded using stable IDs.

### Integration tests

- A known Sleeper player resolves to the correct `players.id`.
- A Sleeper draft event updates the correct local draft state.
- A recommendation snapshot stores both local and Sleeper IDs.
- Outcome tracking compares IDs rather than names.
- A missing mapping produces `BLOCKED`, not a silent fallback.
- Read-only sandbox recommendation runs do not modify mapping data.

### Regression tests

- Existing mock-draft pages continue to render.
- Existing recommendation scoring remains unchanged after identity extraction.
- Existing tests remain green.
- CSV imports do not create duplicate player records when a mapping already exists.

---

## Implementation Batches

### Batch F2R-A: Correct local identity

- Change the current recommendation query from `player_id` to `id`.
- Configure the repository adapter to use `id`.
- Verify mock recommendations return the local integer ID.
- Run the full test suite.

### Batch F2R-B: Build Sleeper identity mapping

- Inspect the live Sleeper player payload.
- Add `sleeper_player_id` or the source-identity mapping table.
- Generate a mapping candidate report.
- Quarantine unresolved and ambiguous players.
- Backfill only verified matches.

### Batch F2R-C: Connect Phase F

- Translate Sleeper draft events into local IDs.
- Store both local and source IDs in recommendation snapshots.
- Exclude drafted players by local ID.
- Update outcome tracking to compare stable IDs.

### Batch F3: Live draft watcher

Start live draft automation only after the identity mapping passes the acceptance criteria below.

---

## Acceptance Criteria

Player identity is ready for live draft automation when:

- [ ] `players.id` is confirmed as the local canonical key.
- [ ] The mock recommendation path uses `players.id` successfully.
- [ ] A verified Sleeper identity field or mapping table exists.
- [ ] Every active draftable Sleeper player resolves to one local player, or is explicitly quarantined.
- [ ] No external ID maps to multiple local players.
- [ ] No ambiguous match is silently accepted.
- [ ] Recommendation snapshots store stable local identity.
- [ ] Live draft events retain the source identity.
- [ ] Drafted-player exclusion uses IDs rather than names.
- [ ] Outcome tracking uses IDs rather than names.
- [ ] Sandbox and full repository tests pass.
- [ ] No synthetic identity is shown as real advice.

---

## Immediate Next Action

Correct the Phase F refactor to use:

```text
players.id
```

for local sandbox identity, then build and validate a separate Sleeper-to-local mapping before enabling live draft automation.

---

## Decision Summary

```text
Local canonical identity: players.id
Current external Sleeper identity: not stored in players
Temporary live-draft blocker: no verified Sleeper-to-local mapping
Name-only matching: prohibited as the final automated identity rule
Next implementation: correct local ID usage, then add verified Sleeper mapping
```
