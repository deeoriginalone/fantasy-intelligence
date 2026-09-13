###### Project State

####### Current state

Fantasy Intelligence has completed the Shared Integrity and Data Integrity track through A.10. UX.1 remains complete at its verified focused-test and rendered active-route boundary.

UX.2 My Team Accuracy, Explainability, and League-Settings Validation is validated at the focused and controlled active-route boundary. The route, contracts, recommendation evidence, health targeting, priority action, and collapsed lineage are preserved.

UX.2.1C is owner-accepted as of 2026-09-13 (`APPROVED: MY TEAM UI`). UX.3 is validated at a supported, read-only waiver-publication boundary. UX.4.1 through UX.4.12 are validated at focused, controlled-browser, and live nine-partner dropdown boundaries; UX.5 through UX.7 remain pending.

####### Last recorded repository checkpoint
- Date: 2026-09-13
- Branch: feature/evidence-bundle-pipeline
- HEAD: 8f9dec3821fe48fed62da1a5c13a364f38f321cd

The branch, HEAD, and working-tree state must be reverified from the repository before import, staging, validation, or commit.

####### Preserved verified capabilities
- Shared completeness, confidence, freshness, blocker, evidence-state, and lineage contracts previously recorded.
- Dashboard state, freshness, Pacific-time draft presentation, truth-audit, and fail-closed cross-page agreement evidence.
- League-settings-derived roster requirements with DST-to-DEF normalization.
- Full-PPR Team Needs evaluation for QB, RB, WR, TE, FLEX, K, and DEF.
- Team Health and Team Accuracy contracts wired into the active `/team` route.
- Explicit unavailable-state and blocker handling for unsupported health and matchup evidence.
- Tested owned-player waiver filtering and fail-closed eligibility evidence remain preserved as partial UX.3 foundation only.
- Read-only decision support with no external transaction submission.

####### Historical validation evidence
- UX.1-UX.7 reconciliation validation: 29 passed in 0.47 seconds.
- Focused UX.1 validation: 17 passed in 0.77 seconds.
- Team Health template and route validation: 14 passed in 0.38 seconds.
- Focused UX.2 validation: 35 passed in 0.47 seconds.
- Python compile validation passed for the previously recorded UX.2 modules and health-test modules.
- Working-tree and staged whitespace validation passed.
- Rendered Dashboard active-route evidence was recorded for UX.1.
- Rendered My Team active-route evidence was recorded for the earlier UX.2 foundation.
- Notebook bundle validation: PASS.
- Canonical memory synchronization: PASS.

The revised UX.2 product-completion criteria are validated at the focused, controlled active-route, and current live-render boundaries recorded below.

####### Validated UX.2 boundary
- Unsupported aggregate metrics are absent or explicitly unavailable.
- Matchup Rank fails closed without complete authority metadata.
- Shared Team Needs, recommendation evidence, health targeting, priority action, and collapsed lineage are validated.

####### Revised UX.2 acceptance boundary
- Active Full-PPR league settings and current supported roster truth drive the page.
- QB, RB, WR, TE, FLEX, K, and DEF remain represented in Team Needs.
- Team Needs summary and detail cannot contradict each other.
- Minimum starter coverage, desired depth, and strategic need are distinguished.
- Unsupported Overall Grade and Weekly Score values are removed or fully defined and tested.
- Missing weekly evidence cannot silently become zero.
- Matchup Rank identifies its meaning, population, directionality, and unavailable behavior.
- Every supported lineup recommendation includes player, slot, opponent, supported weekly value, matchup context, health, confidence, reason, and any targeted blocker.
- Unknown health is not displayed as healthy.
- Stale or unavailable evidence lowers confidence, produces MONITOR, makes a component unavailable, or blocks the exact affected recommendation.
- The highest-priority supported action appears before technical diagnostics.
- Technical lineage remains available but is secondary and collapsible.

####### Working-tree safety
- Reinspect current staged, unstaged, and untracked state before implementation.
- Review both Git layers for any file shown in both staged and unstaged state.
- Preserve unrelated changes.
- Use exact file paths for staging.
- Keep generated evidence, backups, exports, archives, and implementation changes in separate commit scopes.

####### Known boundaries
- UX.3 publishes only candidates with stable Sleeper IDs that are absent from complete, fresh current league rosters and belong to the supported player pool. Availability is application-derived, not provider-declared addability.
- Ownership freshness is calculated from successful `retrieved_at` using `integrity.roster.v1`; source-record time remains unavailable when Sleeper does not supply it.
- The focused UX.3 suite passes 78 tests; compilation and working-tree/staged whitespace checks pass.
- Active `/waivers` and `/gm` checks return HTTP 200 with shared FRESH/COMPLETE ownership and DERIVED/FRESH/COMPLETE availability. `/waivers` publishes nine stable IDs, `/gm` publishes its five-candidate prefix, and neither set intersects rostered IDs.
- Rendered supported state exposes source, freshness, completeness, derived authority, unavailable optional values, and collapsed identity diagnostics. Unsupported or degraded inputs remain fail-closed.
- UXQA-001 is VALIDATED, not CLOSED. Commit review and canonical/continuity validation remain required for closure.
- UX.4 shared integrity receives owner/partner roster and injury retrieval provenance plus writer-owned matchup/projection retrieval provenance. It publishes only with complete FRESH evidence, degrades for AGING, and blocks stale, expired, unknown, incomplete, or contradictory domains.
- PostgreSQL applies the UX.4.4 timestamp schema: `defense_matchups.retrieved_at` and `players.projection_retrieved_at`. Successful source import mutations own timestamps; failed imports roll back and route reads remain read-only.
- Current live dropdown coverage is complete for all nine audited partner populations. Team alias normalization and deterministic suffix-aware local joins repaired supported source matches; unsupported/ambiguous test scenarios remain explicitly blocked.
- UX.4.10 scenarios verify READY, READY-empty, DEGRADED, BLOCKED, unsupported partner fit, and identity ambiguity in browser at desktop and 390px. UX.4.12 verifies the normal live server and all nine dropdown selections with current feasibility and package presentation.
- Focused UX.4 validation passed 90 tests; compile and whitespace validation passed. No transaction feasibility, acceptance, negotiation, rest-of-season impact, production readiness, or closure claim is made.
- Focused UX.2 validation passed with 85 tests, the controlled active-route matrix passed with 11 tests, and the related suite passed with 133 tests.
- Live `/team` verification covers the currently served unavailable-health state; alternate states are validated through the controlled active-route matrix.
- Defects are validated but not marked CLOSED because no commit boundary has been reviewed.
- UX.2.1 passed isolated browser validation for all required states at desktop and 390px mobile widths.
- UX.2.1B related validation passes 147 tests; fresh desktop and 390px route inspection passed with no clipped cards or primary overflow.
- Complete, healthy, multiple-monitor, no-urgent, unavailable, stale, blocked, bench-unavailable, and missing-league browser captures passed without primary overflow or clipped cards.
- PostgreSQL 1000-event/10-replay parity verification remains outstanding.
- Failure injection, rollback, recovery, guarded cleanup, and repeatability evidence remain outstanding.
- Production readiness is not claimed.
- No automatic external fantasy transaction submission is enabled.

## Next milestone

**Finalize UX.4 canonical continuity validation and narrow commit-readiness review.**
