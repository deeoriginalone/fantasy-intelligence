###### Project State

####### Current state

Fantasy Intelligence has completed the Shared Integrity and Data Integrity track through A.10. UX.1 remains complete at its verified focused-test and rendered active-route boundary.

UX.2 My Team Accuracy, Explainability, and League-Settings Validation is validated at the focused and controlled active-route boundary. The route, contracts, recommendation evidence, health targeting, priority action, and collapsed lineage are preserved.

UX.2.1C is owner-accepted as of 2026-09-13 (`APPROVED: MY TEAM UI`). UX.3 is validated at a supported, read-only waiver-publication boundary. UX.4.1 through UX.4.12 are validated at focused, controlled-browser, and live nine-partner dropdown boundaries. The shared action-first visual system is implemented across Lineup, My Team, Waivers, and Trades. UX.5 has the formalized implementation and evidence boundary; formal definition-of-done review remains pending. UX.6 and UX.7 remain pending.

####### Last recorded repository checkpoint
- Date: 2026-09-13
- Branch: feature/evidence-bundle-pipeline
- HEAD: 156b514ccfecd4d2afe9b57bdf719aeca928c917

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

####### Validated UX.5 boundary
- Weekly Lineup Intelligence emits explicit `START`, `FLEX`, `MONITOR`, and bench `SIT` decisions; ambiguous `HOLD`/`SWAP` output is no longer rendered.
- Bench players receive deterministic `bench_order` values and manager-facing reason, confidence, opponent, health, and weekly-value evidence.
- Missing weekly or matchup evidence renders as `Unavailable`, not verified zero or neutral evidence; blocker impacts and baseline/Weekly Score definitions are visible.
- Focused UX.5 service/template/route-contract validation passed 10 tests. Related integrity and UX.2 route validation passed 27 tests. Compilation, diagnostics, and whitespace checks passed.
- Live `/lineup` returned HTTP 200 and rendered Start/Sit Decisions, Bench Order, START/FLEX/MONITOR/SIT labels, metric definitions, and Unavailable states with no HOLD text. Desktop and 390px mobile inspection passed without primary horizontal overflow.
- The redesigned page prioritizes a weekly verdict and manager action, then decision cards, lineup risks, formation slots, bench priority, unavailable change history, collapsed metric explanations, and bottom-only data quality/lineage diagnostics.
- UX.5 remains read-only. Formal definition-of-done review and canonical continuity validation remain pending.

####### Cross-page action-first presentation boundary
- My Team uses the shared verdict/action shell, modern evidence cards, responsive grids, and bottom diagnostics while preserving Team Health, Team Accuracy, Team Needs, starter, bench, and lineage contracts. Focused validation passed 34 tests; live `/team` returned HTTP 200 and passed desktop/390px overflow checks.
- Waivers uses a waiver verdict, Priority Adds cards, FAAB guidance, blocked ownership/eligibility states, and retained availability/lineage evidence. Focused validation passed 47 tests; live `/waivers` returned HTTP 200 and passed desktop/390px overflow checks.
- Trades uses a trade verdict, partner selector, roster-fit summary, one-for-one/two-for-one package cards, feasibility visibility, and collapsed integrity/identity diagnostics. Focused validation passed 27 tests; live `/trades` returned HTTP 200 and passed desktop/390px overflow checks.
- These pages remain read-only. No route, database, ownership, eligibility, health, matchup, trade, waiver, or transaction logic was changed by the visual rollout.

####### UX.8 Survivor Intelligence progress (in-progress, not complete)

- History/eligibility contract implemented: Week 1 JAX (season 2026) recorded through a conflict-safe write (`SurvivorConflictError`) and a distinct history-read-failure signal (`SurvivorHistoryReadError`); used-team exclusion verified live and by test.
- Week-state contract implemented (`OPEN` / `PENDING_RESULT` / `COMPLETED` / `UNAVAILABLE` / `BLOCKED`); the occupied-week contradiction is fixed — a locked week no longer offers another actionable pick or “Record… pick” control.
- Future Value no longer fabricates a neutral 0.50 when future schedule/prediction evidence is missing; Survivor Score discloses a reduced-scope formula (`current_stability_only` / `current_only`) instead of silently substituting a value.
- Evidence Agreement Score (`stability_score`) no longer reports a fabricated 100% agreement when all three underlying signals are missing; renders Unavailable instead.
- Action-first template redesign is live: hero, pick-this-week, alternatives, risk center, save-for-later, roadmap, used-teams/history, and collapsed rankings/metrics/lineage; locked-week, blocked, unavailable, degraded, and completed states are rendered through the real template (not only unit-tested).
- Added a “Refresh Market Intelligence for Week N” button wired to the existing `/api/market-intelligence/refresh` endpoint; fixed two defects surfaced while wiring it: the endpoint had no auth/CSRF protection (added `@admin_required`), and the running server never loaded `.env.market`/`.env.pickem` (added `load_dotenv` calls in `app.py`), which had silently blocked refresh at runtime.
- Root-caused the Week 2 `SURVIVOR_WEEK_EVIDENCE_MISSING` state: the sandbox schedule is correctly sourced from the real 2026 schedule; the external odds provider has not yet posted Week 2 lines (a temporal data-availability limit, not a code defect).
- Focused survivor + related security tests: 68 passed, 1 xfailed (up from 43/49 recorded earlier this session).
- `docs/PAGE_REQUIREMENTS.md` and `docs/METRIC_DEFINITIONS.md` updated with Survivor Intelligence page and metric contracts.
- UX.8 is not yet formally complete; remaining boundary work is tracked under the Next milestone below.

## Next milestone

**Complete UX.8 Survivor Intelligence Strategy and All-Season Redesign at the verified read-only active-route boundary.**

UX.8 is the only active feature-development milestone. UX.5 retains its validated implementation and live-render evidence, but formal completion review remains deferred. UX.6 and UX.7 remain deferred at their existing recorded boundaries. Waiver and Trade Center enhancements remain deferred. Existing defects retain their evidence-supported statuses; defect closure remains separate. Strategic systems remain deferred, not abandoned. PostgreSQL parity, failure injection, rollback, recovery, cleanup, repeatability, and production-readiness work remain deferred and unclaimed. No external survivor transaction capability is claimed.
