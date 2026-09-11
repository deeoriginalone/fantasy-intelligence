### Development Roadmap

#### Current checkpoint
- Date: 2026-09-10
- Branch: feature/evidence-bundle-pipeline
- HEAD: 6c97d30f20c4d9e9becf9ccf1007ef5b84e8b3d9

#### Historical completed milestones
- F3-D.1 through F3-D.5 remain complete at their recorded boundaries.

#### Completed development track: Data Integrity
- A.1 Shared Integrity Foundation: COMPLETE
- A.2 Matchup and Lineup Integration: COMPLETE AT FOCUSED TEST BOUNDARY
- A.3 Freshness and Fail-Closed Confidence: VALIDATED
- A.4 Verified Timestamp Wiring: WIRED AT RECORDED CONTRACT BOUNDARY
- A.5 Roster Synchronization and Reconciliation: GATE PASS
- A.6 League-Settings-Derived Needs: GATE PASS
- A.7 Injury Status Synchronization and Health Confidence: IMPLEMENTATION PACKAGE VALIDATED
- A.8 Matchup Enrichment Coverage: VALIDATED
- A.9 User-Facing Yahoo Remnant Removal: IMPLEMENTED AT VERIFIED TEMPLATE BOUNDARY
- A.10 Cross-Page Integrity Display: IMPLEMENTED AND FOCUSED VALIDATION PASSED

#### Post-A.10 UX correctness progress
- Shared evidence-state, lineage, explanation, freshness, roster-requirement, waiver-availability, GM-impact, and route-payload contracts are present.
- Dashboard season, league status, and draft start-time values are rendered from evidence fields instead of fixed template values.
- Team, Waivers, Trades, Lineup, and GM contain shared completion-panel wiring.
- Team and Lineup competing lineage assignments were reconciled.
- DST-to-DEF roster requirement normalization is implemented and validated.
- pytest repository-root import stability is provided by tests/conftest.py.
- UX.1-UX.7 reconciliation validation recorded 29 passing tests in 0.47 seconds.
- Python compilation and both Git whitespace checks passed.
- Full UX.1 through UX.7 completion is not yet claimed pending formal definition-of-done review.

### Next milestone

**Complete UX.1 Dashboard Modernization and Truth Audit.**

##### Remaining UX.1 work
- Verify dashboard agreement with My Team and Weekly Command Center at the active-route boundary.
- Expose freshness or last-refresh data only where verified timestamps exist.
- Complete focused route and template proof for season, league status, draft status, draft type, draft start time, unavailable-source behavior, and cross-page agreement.
- Re-run the full focused validation and continuity pipeline after the final UX.1 definition-of-done review.

##### UX.1 definition of done
- Data sources and route contracts are identified from repository evidence.
- Stale or contradictory dashboard values are repaired or fail closed explicitly.
- Dashboard truth agrees with related active views where those values overlap.
- Focused route and template tests pass.
- Compile checks and both Git whitespace checks pass.

#### UX.2: My Team Accuracy and League-Settings Validation

**Status: ACTIVE WIRING AND RECONCILIATION VALIDATED, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes lineage precedence reconciliation and DST-to-DEF roster requirement normalization. Remaining review: full roster-slot rules, league settings, scoring settings, health and matchup gaps, unavailable-state explanations, and active-route proof.

#### UX.3: Waiver Correctness and Availability Validation

**Status: ACTIVE EVIDENCE WIRING AND FAIL-CLOSED CONTRACTS PRESENT, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes owned-player filtering and explicit unverified-eligibility blockers. Remaining review: active-route ownership, eligibility, league-derived needs, unsupported-metric handling, and route/template proof.

#### UX.4: Shared Integrity Expansion

**Status: ACTIVE PRESENTATION WIRING PRESENT, FORMAL COMPLETION REVIEW PENDING.** Remaining review: final focused payload and rendering proof for Team, Waivers, and Trades.

#### UX.5: Lineup Explainability and Bench Redesign

**Status: RECONCILIATION VALIDATED, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes the labeled Bench Order table, lineage-panel wiring, and reconciled lineage precedence. Remaining review: stronger evidence-based explanations and alternatives plus missing-evidence distinctions.

#### UX.6: GM Center Impact Redesign

**Status: ACTIVE EVIDENCE AND IMPACT SUPPORT PRESENT, FORMAL COMPLETION REVIEW PENDING.** Remaining review: validate the full impact-redesign definition of done with focused route/template evidence.

#### UX.7: Player Identity and Data Lineage Audit

**Status: ACTIVE LINEAGE AND DIAGNOSTIC SUPPORT PRESENT, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes unknown-field, fallback, and transformation diagnostics. Remaining review: reproducible mismatch diagnostics, verified history/change explanations, and route/template proof.

#### Strategic Intelligence Roadmap

The following systems remain planned and deferred, not abandoned:
- A.11 VOR Engine
- A.12 Floor / Median / Ceiling Model
- A.13 Opportunity Metrics Engine
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine
- A.18 Trade Impact Simulator

#### Outstanding validation track
- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required.
- Production deployment and recovery proof are not claimed.
