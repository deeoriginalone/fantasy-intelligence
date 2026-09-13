###### Development Roadmap

####### Last recorded repository checkpoint
- Date: 2026-09-12
- Branch: feature/evidence-bundle-pipeline
- HEAD: 6458cb0f3aa5b88e5559c6c996be8c18f9f3b630

The branch, HEAD, and working-tree state must be reverified from the repository before import, staging, validation, or commit.

####### Historical completed milestones
- F3-D.1 through F3-D.5 remain complete at their recorded boundaries.

####### Completed development track: Data Integrity
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

####### Post-A.10 UX correctness progress
- Shared evidence-state, lineage, explanation, freshness, roster-requirement, waiver-availability, GM-impact, and route-payload contracts are present.
- UX.1 Dashboard Modernization and Truth Audit remains complete at its verified focused-test and rendered active-route boundary.
- UX.2 has a validated implementation foundation for league settings, Full-PPR Team Needs, Team Health, Team Accuracy, unavailable matchup presentation, and recommendation blockers.
- A hands-on rendered-page review identified unresolved UX.2 product-completion work.
- UX.2.1 passed the All-Season Usability Gate; UX.3 is next and was not implemented in this session.
- UX.4 through UX.7 remain pending their formal definition-of-done reviews.

####### Completed milestone: UX.1 Dashboard Modernization and Truth Audit
- Shared season and league-status facts are wired through Dashboard, My Team, and Weekly Command Center route contracts.
- The rendered Dashboard reports Cross-Page Agreement as AVAILABLE and states that overlapping verified facts agree.
- Focused UX.1 validation passed with 17 tests in 0.77 seconds.
- Python compile validation passed.
- `git diff --check` passed.
- `git diff --cached --check` passed.

####### Active milestone: UX.2 My Team Accuracy, Explainability, and League-Settings Validation

**Status: VALIDATED AT FOCUSED, CONTROLLED ACTIVE-ROUTE, AND LIVE CURRENT-STATE BOUNDARY.**

Preserved foundation:
- League-settings, Team Needs, Team Health, and Team Accuracy contracts are wired into the active `/team` route.
- Full-PPR Team Needs coverage includes QB, RB, WR, TE, FLEX, K, and DEF.
- Unsupported health and matchup evidence can fail closed through unavailable states and blockers.
- Matchup rank can display Unavailable when no supported value exists.
- Historical Team Health template and route validation passed with 14 tests in 0.38 seconds.
- The historical focused UX.2 suite passed with 35 tests in 0.47 seconds.
- Historical compile, whitespace, rendered-route, notebook-bundle, and canonical-synchronization evidence remains recorded for the earlier foundation.

Completed UX.2 gate work:
- Overall Grade and aggregate Weekly Starter Score authority are absent.
- Verified zero and unavailable weekly values are distinct.
- Matchup Rank authority is fail-closed without population, directionality, source, and freshness evidence.
- Team Needs summary/detail, starter coverage, depth, and strategic need are consistent.
- Recommendation confidence, reasons, health targeting, and matchup blockers are present.

Validated presentation work:
- Action-first My Team summary and expected impact are visible.
- Health source, age, freshness, and recommendation impact are visible.
- Technical lineage is secondary and collapsed by default.
- Manager-facing unavailable, stale, blocked, zero, and not-applicable states are normalized.

Definition-of-done evidence:
- Repository-reality reconciliation.
- Focused metric, Team Needs, health, recommendation, route, and template tests.
- Active `/team` rendered-page verification.
- Compile checks for changed Python files.
- Working-tree and staged whitespace checks.
- Relevant defect-status review.
- Exact commit-scope review.
- Canonical synchronization and notebook-bundle validation.

####### Current UX.2 remediation evidence
- The My Team route now selects one deterministic priority action from vacant slots, affected health recommendations, supported Team Needs, or fail-closed evidence review.
- Recommendation evidence visibly carries weekly-value availability, health source, health freshness, health impact, confidence, reason, and targeted blockers.
- Focused UX.2 validation passed with 85 tests.
- Controlled active `/team` state matrix passed with 11 tests.
- Related UX.2, health, integrity, matchup, and lineup validation passed with 133 tests after restoring freshness metadata compatibility and defensive optional lineage rendering.
- Fresh live `/team` verification on port 5051 returned HTTP 200 with action-first ordering, explicit unavailable health freshness and impact, and closed technical lineage.
- Alternate health, weekly-value, and league-settings states are validated through controlled active-route tests; the live server evidence records only its current unavailable-health state.

####### UX.2 test matrix requirements

Metric authority:
- Overall Grade is absent unless fully defined and validated.
- Aggregate Weekly Starter Score is absent unless fully defined and validated.
- Missing weekly evidence renders Unavailable, not numeric zero.
- Verified zero remains distinguishable from unavailable.
- Projection and confidence render separately.
- Matchup Rank meaning, population, directionality, and unavailable behavior are explicit.

Team Needs:
- QB, RB, WR, TE, FLEX, K, and DEF are returned for supported Full-PPR settings.
- Starter coverage and depth target are separate states.
- Summary and detail use the same result and cannot contradict each other.
- League-settings or roster-truth failures make affected calculations unavailable.
- Each need includes an explicit driver when supported.

Health and freshness:
- Unknown health is not converted to healthy.
- Stale or unavailable health reduces confidence or blocks the affected recommendation.
- Source, age, freshness, and last-verified information reach the template when available.
- A failed refresh does not make stale cache appear current.
- Only affected recommendations are degraded.

Recommendation behavior:
- Complete evidence produces a decision, confidence, and reason.
- Material health uncertainty produces MONITOR or reduced confidence.
- Missing required evidence blocks the affected recommendation.
- Every route payload includes supported player, slot, opponent, value, health, confidence, reason, and blockers.
- Active league slot rules are respected.

Presentation and active-route proof:
- The priority action appears before technical diagnostics.
- Technical lineage is collapsed by default.
- Manager-facing blocker impact is visible without opening raw lineage.
- `/team` renders successfully for supported, degraded, unavailable, and blocked states.
- The final render contains no unexplained grade, undefined aggregate score, contradictory Team Needs message, or recommendation without confidence and reason.

####### UX.2.1: My Team Product Hardening and All-Season Usability

**Status: VALIDATED AT VISUAL HIERARCHY, CONTRADICTION, AND DISCLOSURE BOUNDARY.**

- Compact recommendation cards, trust summary, weekly risks, bench decisions, actionable Team Needs cards, and supported roster outlook are implemented from existing contracts.
- Related UX.2.1B validation currently passes 147 tests.
- Isolated browser captures for complete, healthy, multiple-monitor, no-urgent, unavailable, stale, blocked, bench-unavailable, and missing-league states passed at 1440px and 390px; no primary overflow or clipped cards remained after the Team Needs wrap repair.
- Personal-use verdict: YES for the tested My Team boundary.

####### UX.3: Waiver Correctness and Availability Validation

**Status: NEXT MILESTONE AFTER UX.2.1C OWNER ACCEPTANCE.**

Previously recorded partial UX.3 evidence, including owned-player filtering and explicit unverified-eligibility blockers, remains preserved. No UX.3 implementation claim is made here.

####### UX.4: Shared Integrity Expansion

**Status: PARTIAL PRESENTATION FOUNDATION PRESERVED; FORMAL COMPLETION REVIEW PENDING.**

####### UX.5: Lineup Explainability and Bench Redesign

**Status: RECONCILIATION FOUNDATION PRESERVED; FORMAL COMPLETION REVIEW PENDING.**

####### UX.6: GM Center Impact Redesign

**Status: PARTIAL EVIDENCE AND IMPACT FOUNDATION PRESERVED; FORMAL COMPLETION REVIEW PENDING.**

####### UX.7: Player Identity and Data Lineage Audit

**Status: PARTIAL LINEAGE AND DIAGNOSTIC FOUNDATION PRESERVED; FORMAL COMPLETION REVIEW PENDING.**

####### Strategic Intelligence Roadmap

The following systems remain planned and deferred, not abandoned:
- A.11 VOR Engine
- A.12 Floor / Median / Ceiling Model
- A.13 Opportunity Metrics Engine
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine
- A.18 Trade Impact Simulator

####### Outstanding validation track
- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required for later milestones.
- Production deployment and recovery proof are not claimed.

## Next milestone

**Begin UX.3 Waiver Correctness and Availability Validation.**
