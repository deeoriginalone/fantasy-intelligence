# Development Roadmap

## Current Checkpoint
- Date: 2026-09-06
- Branch: feature/draft-outcome-tracking
- HEAD: 18e3322944ed6ac99f5e1817b604574f8e928ccd
- League ID: 1398094330668797952
- Protected real draft ID: 1398094331272794112
- Rehearsal mock draft ID: 1402134346244100096

## Current Operational Position

The repository is validated for implementation, unit testing, integration testing, and the documented local supervised route rehearsal. Local evidence includes protected MOCK rotation, populated pick refresh, protected LIVE restoration, Draft HQ, polling, readiness, and reconciliation. Production deployment, production recovery behavior, and full PostgreSQL parity remain unproven and are not claimed.

## Verified Draft Rotation Evidence
- The rehearsal mock reached 29 Sleeper picks.
- Active mock state reached 29 drafted board rows, 29 league-roster rows, and 6 user-roster rows.
- Protected LIVE restoration cleared active mock state.
- The real draft is uniquely authoritative.
- Final active counts: `draft_board=0`, `league_rosters=0`, `my_roster=0`.

## Validation Results
- Python compilation: passed
- Rotation and synchronization suite: 21 passed
- Affected readiness and reconciliation suite: 70 passed
- Fast tier: 44 passed
- `git diff --check`: passed

## Remaining Blockers
- Local supervised Flask route rehearsal: verified.
- Populated MOCK rotation and protected LIVE restoration: verified locally.
- Production deployment and recovery: not proven.
- Full PostgreSQL 1000-event/10-replay parity: pending.
- Legacy `/sleeper/draft-picks/sync` remains live-only for the league-less mock.
- Two mock player quarantine records require investigation.
- Historical `ROTATION_FAILED` audit rows remain preserved.
- No automatic external draft, waiver, lineup, trade, or season transaction is proven.
- Remaining FAAB budget source is not proven authoritative.

## Current Next Milestone

**Full PostgreSQL 1000-event/10-replay verification and failure-injection recovery testing**

### Definition of Done
- Run the full verifier with no skipped PostgreSQL cases.
- Record failure-injection, rollback, and recovery evidence.
- Verify guarded cleanup and repeatability.
- Preserve the no-external-write boundary.
- Reconcile all four canonical documents after the evidence is complete.

## Stop Conditions
- Identity conflict.
- Stale or missing readiness data.
- Reconciliation drift.
- Unsafe database scope.
- Unexpected external write.
- Evidence that cannot be tied to a command and configuration.

## Historical Roadmap Notes
- Mock Draft Lab: completed historical initiative.
- Draft Assistant v2: completed historical planning checkpoint.
- F3-D.5 Waiver Action Publication and UI: historical milestone with source implementation and focused tests.
- Personal Fantasy Operations Center remains the long-term vision.
