# Development Roadmap

## Current checkpoint

- Date: 2026-09-10
- Branch: feature/evidence-bundle-pipeline
- HEAD: 118ba6c557970403fcc81f9960a2a3ec19a52226

## Historical completed milestones

- F3-D.1 through F3-D.5 remain complete at their recorded boundaries.

## Completed development track: Data Integrity

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

## Post-A.10 UX foundation completed on 2026-09-10

A shared implementation foundation for UX.1 through UX.7 was added and validated. It includes fail-closed dashboard evidence, reusable evidence and lineage contracts, owned-player waiver filtering, a reusable evidence-state template, and a labeled Lineup Bench Order table.

Focused validation recorded:

- Focused UX validation suite: 20 passed in 0.38 seconds.
- `app.py` and `services/ux_evidence.py` compiled.
- imports passed.
- `git diff --check` passed.
- `git diff --cached --check` passed.

This foundation is not equivalent to full completion of UX.1 through UX.7.


### UX evidence presentation expansion validated
- Dashboard hard-coded draft-readiness, simulation-count, projection-count, tier-count, duplicated league-summary, and pre-draft status claims were removed or replaced with explicit UNKNOWN or UNSUPPORTED states.
- Reusable page evidence, lineup explanation, waiver explanation, and GM action evidence helpers were added.
- A reusable UX completion panel was added for evidence and lineage presentation.
- The Lineup page includes the player identity and lineup evidence presentation boundary.
- Focused UX validation suite: 20 passed in 0.38 seconds.
- Python compile validation passed.
- git diff --check passed.
- git diff --cached --check passed.
- This expansion does not prove full active-route completion of UX.1 through UX.7.

## Next milestone

**Complete UX.1 Dashboard Modernization and Truth Audit.**

### Verified progress

- Dashboard league metadata no longer needs the unmaintained `league_info` read in the current working tree.
- Current dashboard league, owner-team, roster-count, and scoring metadata are derived from verified Sleeper league, users, and rosters calls.
- Missing or incomplete source data fails closed.
- Dashboard evidence contract and focused tests pass.

### Remaining UX.1 work

- Replace or remove unsupported hard-coded dashboard values, including draft-era status, readiness claims, simulations, projection counts, tier counts, dates, and duplicated league summary values.
- Verify current season, week, draft, and league status from supported sources.
- Expose source freshness or last-refresh data only where verified timestamps exist.
- Verify dashboard agreement with My Team and Weekly Command Center.
- Add focused route and template tests for repaired dashboard values.

### UX.1 definition of done

- Data sources and route contracts are identified from repository evidence.
- Stale or contradictory dashboard values are repaired.
- Focused route and template tests pass.
- Compile checks and `git diff --check` pass.

## UX.2: My Team Accuracy and League-Settings Validation

**Status: FOUNDATION ONLY, NOT COMPLETE.**

Available foundation: evidence states and player-lineage helpers.

Remaining work includes active-route proof for roster slots, K and DEF requirements, scoring settings, health and matchup gaps, and explicit unavailable-state explanations.

## UX.3: Waiver Correctness and Availability Validation

**Status: FOUNDATION ONLY, NOT COMPLETE.**

Available foundation: tested owned-player filtering helper.

Remaining work includes verified active-route integration, ownership and eligibility proof, league-derived needs, filters, and fail-closed unsupported metrics.

## UX.4: Shared Integrity Expansion

**Status: FOUNDATION ONLY, NOT COMPLETE.**

Available foundation: reusable UX evidence contract and evidence-state renderer.

Remaining work includes verified payload wiring and route/template tests for My Team, Waivers, and Trades.

## UX.5: Lineup Explainability and Bench Redesign

**Status: PARTIAL.**

Completed portion: Bench Order is rendered as a labeled table.

Remaining work includes stronger evidence-based explanations, alternatives, missing-evidence distinctions, and proof for the full definition of done.

## UX.6: GM Center Impact Redesign

**Status: NOT VERIFIED COMPLETE.**

The existing GM Center has decision-ranking and blocker concepts, but the UX.6 impact redesign definition of done has not been validated from the recorded UX batch.

## UX.7: Player Identity and Data Lineage Audit

**Status: FOUNDATION ONLY, NOT COMPLETE.**

Available foundation: reusable player lineage helper covering position, ownership, health, matchup, projection, source, update time, and unknown states.

Remaining work includes active lineage presentation, reproducible mismatch diagnostics, transformation and fallback reporting, and change explanations where verified history exists.

## Strategic Intelligence Roadmap

The following systems remain planned and deferred, not abandoned:

- A.11 VOR Engine
- A.12 Floor / Median / Ceiling Model
- A.13 Opportunity Metrics Engine
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine
- A.18 Trade Impact Simulator

## Cross-cutting requirements

- Prefer decision support, transparency, freshness, and actionable fantasy value.
- Separate data health, model confidence, and decision confidence.
- Show data lineage for important values.
- Distinguish unknown, stale, unsupported, and not-applicable evidence.
- Do not invent missing player, health, matchup, projection, ownership, market, or betting data.
- Preserve read-only behavior unless transaction safeguards are separately requested and validated.

## Outstanding validation track

- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required.
- Production deployment and recovery proof are not claimed.

## Stop conditions

Stop rather than guess when repository state, player identity, roster truth, timestamp provenance, health source, matchup evidence, projection evidence, ownership availability, database isolation, cleanup safety, external-write boundaries, or test evidence cannot be proven.
