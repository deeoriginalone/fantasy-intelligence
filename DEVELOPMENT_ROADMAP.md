##### Development Roadmap

###### Current checkpoint
- Date: 2026-09-12
- Branch: feature/evidence-bundle-pipeline
- HEAD: 0733fc1b64d6a9da6ccf197f272d51d0136d2d91

###### Historical completed milestones
- F3-D.1 through F3-D.5 remain complete at their recorded boundaries.

###### Completed development track: Data Integrity
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

###### Post-A.10 UX correctness progress
- Shared evidence-state, lineage, explanation, freshness, roster-requirement, waiver-availability, GM-impact, and route-payload contracts are present.
- UX.1 Dashboard Modernization and Truth Audit is complete at the verified focused-test and rendered active-route boundary.
- UX.2 My Team Accuracy and League-Settings Validation is complete at the verified focused-test and rendered active-route boundary.
- Team needs use active Full-PPR league settings and evaluate QB, RB, WR, TE, FLEX, K, and DEF.
- Team Health and Team Accuracy contracts are wired into the active `/team` route and rendered through the My Team template.
- Unknown or unsupported health and matchup evidence fails closed through explicit unavailable states, blockers, or reduced recommendation trust.
- UX.3 through UX.7 remain pending their formal definition-of-done reviews.

###### Completed milestone: UX.1 Dashboard Modernization and Truth Audit
- Shared season and league-status facts are wired through Dashboard, My Team, and Weekly Command Center route contracts.
- The rendered Dashboard reports Cross-Page Agreement as AVAILABLE and states that overlapping verified facts agree.
- Focused UX.1 validation passed with 17 tests in 0.77 seconds.
- Python compile validation passed.
- `git diff --check` passed.
- `git diff --cached --check` passed.

###### Completed milestone: UX.2 My Team Accuracy and League-Settings Validation
- League-settings, team-needs, team-health, and team-accuracy contracts are wired into the active `/team` route.
- Full-PPR team-needs coverage includes QB, RB, WR, TE, FLEX, K, and DEF.
- Health and recommendation evidence use explicit unavailable and blocker states instead of presenting unknown evidence as authoritative.
- Matchup rank displays `Unavailable` when no supported value exists.
- Team Health template and route validation passed with 14 tests in 0.38 seconds.
- The focused UX.2 suite passed with 35 tests in 0.47 seconds.
- Python compile validation passed for the changed UX.2 Python modules and health test modules.
- `git diff --check` passed.
- `git diff --cached --check` passed.
- Rendered active `/team` page evidence was recorded for the My Team trust, league-settings, team-needs, health, matchup, and blocker presentation.
- Notebook bundle validation passed.
- Canonical memory synchronization passed for branch, HEAD, and the exact next milestone.
- Final UX.2 commit review remains outstanding.

###### UX.3: Waiver Correctness and Availability Validation
**Status: ACTIVE EVIDENCE WIRING AND FAIL-CLOSED CONTRACTS PRESENT, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes owned-player filtering and explicit unverified-eligibility blockers. Remaining review: active-route ownership, eligibility, league-derived needs, unsupported-metric handling, and route/template proof.

###### UX.4: Shared Integrity Expansion
**Status: ACTIVE PRESENTATION WIRING PRESENT, FORMAL COMPLETION REVIEW PENDING.** Remaining review: final focused payload and rendering proof for Team, Waivers, and Trades.

###### UX.5: Lineup Explainability and Bench Redesign
**Status: RECONCILIATION VALIDATED, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes the labeled Bench Order table, lineage-panel wiring, and reconciled lineage precedence. Remaining review: stronger evidence-based explanations and alternatives plus missing-evidence distinctions.

###### UX.6: GM Center Impact Redesign
**Status: ACTIVE EVIDENCE AND IMPACT SUPPORT PRESENT, FORMAL COMPLETION REVIEW PENDING.** Remaining review: validate the full impact-redesign definition of done with focused route/template evidence.

###### UX.7: Player Identity and Data Lineage Audit
**Status: ACTIVE LINEAGE AND DIAGNOSTIC SUPPORT PRESENT, FORMAL COMPLETION REVIEW PENDING.** Completed progress includes unknown-field, fallback, and transformation diagnostics. Remaining review: reproducible mismatch diagnostics, verified history/change explanations, and route/template proof.

###### Strategic Intelligence Roadmap
The following systems remain planned and deferred, not abandoned:
- A.11 VOR Engine
- A.12 Floor / Median / Ceiling Model
- A.13 Opportunity Metrics Engine
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine
- A.18 Trade Impact Simulator

###### Outstanding validation track
- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required for later milestones.
- Production deployment and recovery proof are not claimed.

## Next milestone
**Complete UX.3 Waiver Correctness and Availability Validation.**
