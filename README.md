# Fantasy Intelligence

A Flask-based fantasy football intelligence platform focused on draft intelligence, live draft-state validation, draft outcome tracking, pick'em intelligence, market ingestion, and operational readiness checks.

## Current repository status

This branch is currently on `feature/draft-outcome-tracking` and the working tree includes both tracked edits and untracked batch artifacts. The current runtime is code-valid and test-valid, but it is not yet a proven live database-backed release state.

## Verified evidence

The latest repo-level verification in this workspace is:

```bash
cd /home/deeoriginalone/fantasy-intelligence
source venv/bin/activate
python -m pytest -q
```

Result from the current repo state:
- 102 passed
- 2 xfailed
- 0 failed

The Postgres service was not available during live validation, so database schema and object verification remain blocked until the database is running.

## First-year league note

This is a first-year fantasy league. Historical owner behavior should not be fabricated or assumed. Historical tables and behavior-modeling structures may exist as forward-compatible infrastructure, but they should be treated as empty or low-signal unless real league data exists.

## Current scope

The active runtime includes:
- draft intelligence and recommendation logic
- draft-state management and hardening
- draft outcome tracking and calibration
- readiness and reconciliation checks
- pick'em and market intelligence
- survivor logic and source-gap handling
- weekly ingestion and reporting helpers

The active runtime does not claim:
- Post-Draft Ready
- Week 1 Ready
- Production Ready
unless live data, database validation, and source-freshness checks prove that status.

## Batch A review

Batch A is present in the code and validated to some extent in tests.

Verified implementation:
- draft session identity validation
- sync audit and quarantine logic
- draft mutation tracking
- readiness and publication gating
- hardening-oriented operational checks

Limitations:
- live database validation is blocked by missing Postgres service
- this is operationally useful but not yet live-certified

## Batch B review

Batch B is implemented and validated in code/tests.

Verified implementation:
- outcome health snapshots
- resolution tracking for draft decisions
- calibration metrics and bounded weight logic
- route-level outcome health reporting

Limitations:
- it remains source-dependent and should not be described as production-calibrated without real historical outcomes

## Batch C review

Batch C is implemented and validated in code/tests.

Verified implementation:
- post-draft state evaluation
- transition checks for complete draft status and count invariants
- idempotent season activation logic
- finalization materialization for drafted and available players
- route wiring for readiness and finalize endpoints

Limitations:
- live DB state and schema validation remain unproven in this environment

## Current development direction

The next recommended direction is Batch D: Recommendation Publishing.

This is the logical next step because:
- Batch A/B/C established validation, outcome health, and transition readiness
- recommendation publication is the most immediate operational gate still left to prove
- the code already contains readiness and publication checks, but they have not been fully proven in a live environment

## Required environment variables

The runtime expects environment values without committing secrets:
- FLASK_SECRET_KEY
- DB_HOST
- DB_PORT
- DB_NAME
- DB_USER
- DB_PASSWORD
- ADMIN_TOKEN
- SLEEPER_LEAGUE_ID
- SLEEPER_DRAFT_ID

See [config.py](config.py) for the active contract.

## Database guidance

The project expects a PostgreSQL database matching the active DB contract. No canonical live migration file has been verified as the single source of truth for the full schema in the active runtime state.

This should be treated as a live environment dependency, not as a guaranteed local state.

## Quick-start

Representative local run pattern:

```bash
cd /home/deeoriginalone/fantasy-intelligence
source venv/bin/activate
python app.py
```

Use only after the required environment variables are present and Postgres is running.

## Test command

```bash
cd /home/deeoriginalone/fantasy-intelligence
source venv/bin/activate
python -m pytest -q
```

## Known limitations

- PostgreSQL connectivity is currently unavailable in this workspace validation session.
- Live weekly recommendations remain gated by source freshness and real provider connectivity.
- Survivor intelligence remains blocked by missing ownership, QB-status, and weather/injury inputs.
- Batch ZIPs and backup directories are operational artifacts and should not be mistaken for active runtime sources.

## Data safety warning

- never commit .env files or secrets
- never present partial or synthetic recommendations as authoritative live outputs
- treat batch outputs and backups as traceability artifacts, not as the canonical application source

## Documentation links

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)
- [SEASON_READINESS.md](SEASON_READINESS.md)
- [PROJECT_STATE.md](PROJECT_STATE.md)

## Recommended next milestone

Draft-Day End-to-End Validation remains the highest-priority milestone before broader operational work. After that, the highest-value next direction is recommendation publishing under explicit readiness and freshness gates.
