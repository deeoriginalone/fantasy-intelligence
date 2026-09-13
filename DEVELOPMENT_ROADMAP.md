###### Development Roadmap

####### Last recorded repository checkpoint
- Date: 2026-09-13
- Branch: feature/evidence-bundle-pipeline
- HEAD: 156b514ccfecd4d2afe9b57bdf719aeca928c917

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
- UX.2.1 passed the All-Season Usability Gate; UX.3 is validated at its supported, read-only waiver-publication boundary.
- UX.4.1 through UX.4.12 are validated at focused implementation, controlled-browser, and live all-partner dropdown boundaries. The shared action-first visual system is implemented across Lineup, My Team, Waivers, and Trades with focused and live-render evidence. UX.5 has the formalized implementation and evidence boundary; UX.6 and UX.7 remain pending their formal definition-of-done reviews.

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

**Status: VALIDATED AT THE SUPPORTED, READ-ONLY PUBLICATION BOUNDARY.**

Validated:
- Stable Sleeper player IDs control rostered-player exclusion and publication identity.
- Current Sleeper roster ownership is FRESH from successful `retrieved_at` under `integrity.roster.v1`; provider source-record time is unavailable and remains distinct from retrieval time.
- Configured roster coverage, unique roster IDs, missing IDs, and duplicate diagnostics fail closed when incomplete or contradictory.
- Availability is transparently derived from the supported player pool minus active-league rostered IDs, not from transaction history or a provider-declared addability field.
- `/waivers` and `/gm` share the evaluated source set and evidence; `/waivers` publishes nine stable IDs and `/gm` publishes the five-candidate prefix, with no published rostered ID.
- The focused UX.3 suite passes 78 tests; Python compilation, whitespace checks, and rendered supported-state verification pass.
- UXQA-001 is VALIDATED, not CLOSED.

Remaining enhancements:
- Candidate-level role, opportunity duration, roster fit, confidence, risk, suggested drop, and evidence-backed FAAB sophistication.
- Formal browser validation and separate UX.3 enhancement review.
- Commit review, canonical synchronization, and continuity validation required before defect closure.

####### UX.4: Trade Center Integrity and Freshness Provenance

**Status: UX.4.1-UX.4.12 VALIDATED AT FOCUSED WRITER, ENRICHMENT, INTEGRITY, TEMPLATE, CONTROLLED-BROWSER, AND LIVE NINE-PARTNER DROPDOWN BOUNDARY.**

- Shared Trade Center integrity gates package publication from owner and partner roster evidence.
- Roster and injury retrieval provenance comes from successful Sleeper retrieval. Matchup and projection provenance carries writer-owned source and retrieval-time fields through enrichment.
- `migrations/011_trade_evidence_freshness.sql` is applied to PostgreSQL and defines `defense_matchups.retrieved_at` and `players.projection_retrieved_at`.
- Successful matchup and projection imports record their retrieval timestamps; failed imports roll back and route reads do not mutate source freshness.
- READY requires complete FRESH evidence across roster, injury, matchup, and projection domains. AGING is DEGRADED. Stale, expired, unknown, unavailable, incomplete, or contradictory evidence is BLOCKED with domain-specific reasons.
- Trade recommendations remain read-only. Action-first presentation precedes collapsed integrity, freshness, provenance, lineage, completeness, and blocker diagnostics.
- Source imports populated required timestamps and canonical alias/suffix normalization completed supported partner coverage. The local `/trades` route is HTTP 200 and the live selector verified all nine opponents as READY.
- Test-only, `TESTING=True` scenarios render READY, READY-empty, DEGRADED, BLOCKED, unsupported partner fit, and identity ambiguity through the actual template at desktop and 390px. Unknown scenarios fail closed and scenarios perform no external or database writes.
- One-for-one and two-for-one alternatives are manager-visible. Acceptance-like verdicts were removed; partner fit, modeled value, and feasibility-unavailable are distinct. Integrity, identity lineage, ranking comparison, and metric definitions are collapsed.
- Focused validation passed 90 tests, compilation passed, and both whitespace checks passed.

Remaining closure controls:
- Canonical continuity validation and narrow exact-path commit review.
- Do not claim transaction acceptance, negotiation, rest-of-season impact, production readiness, or defect closure.

####### UX.5: Lineup Explainability and Bench Redesign

**Status: ACTION-FIRST CROSS-PAGE VISUAL SYSTEM IMPLEMENTED; FORMAL COMPLETION REVIEW PENDING.**

Validated evidence includes the action-first weekly verdict, decision cards, dedicated risk panel, league-valid formation, ranked bench cards, unavailable change history, collapsed metric explanations, bottom-only diagnostics, explicit START/FLEX/MONITOR/SIT decisions, deterministic Bench Order, manager-facing explanations and confidence, unavailable-value distinction, baseline and Weekly Score definitions, 10 focused UX.5 tests, 27 related integrity/route tests, and live desktop/390px `/lineup` inspection with HTTP 200 and no HOLD output. The page remains read-only. Remaining controls are formal definition-of-done review and canonical continuity validation.

The visual system has since been applied to My Team, Waivers, and Trades. My Team passed 34 focused tests plus live desktop/390px verification; Waivers passed 47 focused tests plus live desktop/390px verification; Trades passed 27 focused tests plus live desktop/390px verification. These redesigns preserve existing evidence contracts and remain read-only.

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
