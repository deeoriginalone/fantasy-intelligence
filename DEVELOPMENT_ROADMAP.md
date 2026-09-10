### Development Roadmap

#### Current checkpoint
- Date: 2026-09-10
- Branch: feature/evidence-bundle-pipeline
- HEAD: 17a60d3a71cecf49df5dafe937c604662c025890
#### Historical completed milestones
- F3-D.1 through F3-D.5 remain complete at their recorded boundaries.

#### Active development track: Data Integrity

##### Batch A.1: Shared Integrity Foundation
**Complete.**

##### Batch A.2: Matchup and Lineup Integration
**Complete at the focused repository-test boundary.**

##### Batch A.3: Freshness and Fail-Closed Confidence
**Validated.**

##### Batch A.4: Verified Timestamp Wiring
**Wired at the recorded consumer-contract boundary.**

##### Batch A.5: Roster Synchronization and Reconciliation Gate
**Gate passed.**

##### Batch A.6: League-Settings-Derived Needs Gate
**Gate passed.**

##### Batch A.7: Injury Status Synchronization and Health Confidence
**Implementation package validated.**
- Focused validation recorded as 34 passed.
- Compile validation passed.
- `git diff --check` passed.
- Boundary remains read-only and does not claim live-route or production proof.

##### Batch A.8: Matchup Enrichment Coverage
**Validated.**
- Focused and regression validation recorded as 34 passed.
- Compile validation passed.
- `git diff --check` passed.
- Standalone coverage validation does not itself prove every route is wired.

##### Batch A.9: User-Facing Yahoo Remnant Removal
**Implemented at the verified Pick'em template boundary.**
- User-facing Yahoo wording was removed from the verified active Pick'em templates.
- Legacy `yahoo_*` storage identifiers were preserved.
- Compile and whitespace validation passed.

##### Batch A.10: Cross-Page Integrity Display
**Implemented and focused-validation passed.**
- Reusable integrity summary template added.
- Lineup and Weekly Command Center consume `lineup_intelligence.integrity`.
- Focused and regression validation recorded as 19 passed.
- Compile validation and `git diff --check` passed.
- My Team, Waivers, and Trades remain outside this batch until a verified integrity payload is wired.

#### Next milestone

**Repository-state reconciliation and next-batch selection.**

No A.11 milestone is assigned by the currently verified evidence. The next step is to regenerate repository metadata and continuity outputs, reconcile the canonical files, and select the next milestone from the current repository state.

#### Outstanding validation track
- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required.
- Production deployment and recovery proof are not claimed.

#### Decision-engine improvements after integrity defects
- VOR Engine.
- Floor/Median/Ceiling Model.
- Opportunity Metrics.
- Trade Impact Simulator.
- Schedule and Matchup Forecaster.
- Vegas Integration.
- Correlation Engine.
- Market Mispricing Engine.

#### Stop conditions

Stop rather than guess when repository state, timestamp provenance, health source, matchup evidence, database isolation, cleanup safety, external-write boundaries, or test evidence cannot be proven.
