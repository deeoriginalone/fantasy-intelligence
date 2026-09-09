# Development Roadmap

## Current checkpoint

- Date: 2026-09-09
- Branch: `feature/evidence-bundle-pipeline`
- HEAD: `3c6aef5bb1995887f4e553a2a7954f83eb7cecb7`

## Historical completed milestones

- F3-D.1: complete and verified.
- F3-D.2: complete and verified.
- F3-D.3: complete and verified.
- F3-D.4: complete and verified.
- F3-D.5: complete and verified at the repository-test boundary.

## Active development track: Data Integrity

### Batch A.1: Shared Integrity Foundation

**Complete.**

- Central integrity package.
- Unit tests.
- Shared documentation.

### Batch A.2: Matchup and Lineup Integration

**Complete at the focused repository-test boundary.**

- Shared integrity summary added to matchup intelligence.
- Shared integrity summary added to weekly lineup intelligence.
- Focused result: `14 passed in 0.08s`.
- Syntax validation passed.
- `git diff --check` clean.

### Batch A.3: Freshness and Fail-Closed Confidence

**Installed/in progress. Not complete until focused tests and evidence are recorded.**

Definition of done:

- Fresh, stale, expired, and unknown timestamp states tested.
- Unknown health and missing required matchup evidence cap confidence.
- Focused Batch A suite passes.
- Syntax checks pass.
- Audit evidence is recorded.

### Batch A.4: Verified Timestamp Wiring

**Next after A.3 validation.**

- Pass verified roster sync timestamps.
- Pass verified injury/health timestamps.
- Pass verified matchup refresh timestamps.
- Pass verified projection refresh timestamps.
- Do not invent or substitute timestamps.
- Preserve fail-closed behavior when evidence is absent.

## Priority defect track

1. Stale roster synchronization.
2. Stale injury-status synchronization.
3. Static needs engine; replace with league-settings-derived logic.
4. User-facing Yahoo remnants.
5. Missing matchup enrichment coverage.
6. Cross-page freshness, completeness, and confidence display.

## Decision-engine improvements after integrity defects

1. VOR Engine.
2. Floor/Median/Ceiling Model.
3. Opportunity Metrics.
4. Trade Impact Simulator.
5. Schedule and Matchup Forecaster.
6. Vegas Integration.
7. Correlation Engine.
8. Market Mispricing Engine.

## Outstanding validation track

This work remains required and is not removed from the roadmap:

- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required.
- Production deployment and recovery proof.

## Stop conditions

Stop rather than guess when roster truth, timestamp provenance, health source, matchup evidence, database isolation, cleanup safety, external-write boundaries, or test evidence cannot be proven.
