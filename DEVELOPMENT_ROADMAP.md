###### Development Roadmap

## Fantasy Intelligence 2.0 Roadmap

The six-page architecture is an approved target direction, not completed navigation work. Primary navigation has not yet been simplified; the Command Center target is not complete; no redirect, route archive, or route removal has been completed. Supporting routes remain operational. `MERGE`, `REDIRECT`, and `ARCHIVE` are future classifications.

These pending plans include navigation simplification, route merging, new redirects, and archive actions. Decision Journal, Process vs Results, and Season Planning are planned priorities, not delivered capabilities.

## Evidence-first delivery rule

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Matchup Signal remains context-only where its specific metric contract does not support recommendation use; Matchup Rank remains subject to its own contract.

Apply this model across Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. Each page should retain supported context and clearly name evidence state, freshness, limitations, and impact while preserving page-specific identity, ownership, contradiction, corruption, and transaction-safety protections.

## Current My Team delivery boundary

The committed `/team` template orders My Team header, Your Lineup, Health & Availability, Biggest Decisions, Why These Decisions, What Could Change, Supporting Roster Details, and collapsed Data/Model Diagnostics. Current Sleeper Lineup, Bench Priority, and Team Needs remain supporting details. This supersedes the earlier hero-first presentation description. Behavioral and rendered-page evidence for the current working tree is recorded under the current committed Starting Lineup Decision Intelligence and schedule-lock boundary below (`695ff74`, `a306f3a`).

Recovery Ready is a planned mandatory standard, not a completed checkpoint. Recovery Ready planned work remains pending. It will require a runnable checkpoint, documented startup verification, database backup, canonical-memory snapshot, Notebook/reference export, and six-core-page verification.

Priority order:
1. Decision Center
2. My Team
3. Waivers
4. Trades
5. Survivor
6. NFL Intelligence
7. What Changed
8. Decision Journal
9. Process vs Results
10. Season Planning

Other work is deferred, merged, or retained as internal support until it directly improves manager value. No existing functionality, route, database, integration, or historical data is deleted by this roadmap.

## Navigation Reconciliation Target

### Primary navigation

Command Center, My Team, Waivers, Trades, Survivor, NFL Intelligence, and What Changed.

### Command Center responsibilities

The Command Center is the primary landing page and summarizes League Overview, Must Act, Start/Sit Summary, Waiver Priorities, Trade Watch, Survivor Status, NFL Intelligence Highlights, What Changed, and Risk Alerts. League Overview is incorporated into the Command Center and is not a separate destination. The Command Center links to owning pages and does not duplicate their engines.

### NFL Intelligence consolidation

NFL Intelligence is the single NFL-wide intelligence destination. Market Intelligence is merged into it. Responsibilities include Top Picks, Top Risk Games, Game Predictions, Market Intelligence, Weather, Injury Context, Insights, Blockers, and Diagnostics. Market Intelligence is not a separate navigation item.

### Season Planning and Admin

Draft Board and Mock Draft remain preserved and accessible for recurring seasonal value. Sleeper Hub, Draft Day Readiness, Draft Intelligence & Learning Center, Imports, Readiness, and Diagnostics are intended for an Admin area.

### Intended route disposition

| Destination | Intended disposition |
|---|---|
| Command Center | Primary |
| League Overview | Merge into Command Center |
| My Team | Primary |
| Waivers | Primary |
| Trades | Primary |
| Survivor | Primary |
| NFL Intelligence | Primary |
| Market Intelligence | Merge into NFL Intelligence |
| What Changed | Primary / Secondary |
| Draft Board | Keep |
| Mock Draft | Keep |
| Sleeper Hub | Admin |
| Draft Day Readiness | Admin |
| Draft Intelligence & Learning Center | Admin |
| Imports | Admin |
| Readiness | Admin |
| Diagnostics | Admin |

This is target navigation documentation only. Navigation simplification, merges, and Admin placement remain planned work.

####### Current repository checkpoint
- Date: 2026-11-16
- Branch: test-weekly-evidence-trust
- HEAD: 5abe2fd51d24a3b949b6b2d57aab5d2cb88f5f83

## Current committed delivery boundary

- Branch: `test-weekly-evidence-trust`, in sync with `origin/test-weekly-evidence-trust`.
- Implementation HEAD: `a306f3a210835ae9c9c5fb62a4295271ec69eb6a` - `feat(team): add evidence-aware lineup decision intelligence`.
- Commits after the historical My Team boundary `b75ed87`: `87a43ca` restores the action-first My Team hero and verified NFL week; `bff775f` adds evidence-gated waiver decisions and FAAB guidance; `3ddd37c` uses the configured timezone and authoritative week; `34c3498` adds schedule-backed waiver ranking, the automated nflverse schedule importer (`imports/import_nflverse_schedule.py`), and `services/schedule_bye_evidence.py`; `41dfe47` ranks visible Command Center lineup decisions; `c25e4f2` shares defensive health test assertions; `d37229b` adds an nflverse artifact watchdog; `beb5482` and `d478060` refresh reference and database documents; `ddd329d` ignores local generated artifacts; `695ff74` commits schedule automation (importer republish guards, systemd units, schedule tests); and `a306f3a` commits My Team lineup decision intelligence (services, route, template, and tests).
- Commits through `ddd329d` are recorded from Git history. `695ff74` and `a306f3a` were each revalidated in a clean worktree (see validation below). This reconciliation did not revalidate the earlier commits and claims no defect closure, production readiness, PostgreSQL parity, or recovery readiness.

## Current committed Starting Lineup Decision Intelligence and schedule-lock boundary (2026-11-16)

State: IMPLEMENTED and VALIDATED at the focused, controlled-route, and live `/team` boundary. Schedule automation is OPERATIONALLY VERIFIED. COMMITTED in `695ff74` (schedule) and `a306f3a` (lineup).

- Owners: `services/lineup_decision_intelligence.py` (`lineup-decision.v1`), `services/game_lock.py` (`lineup.game_lock.v1`), `services/lineup_projection.py`, `services/league_scoring.py` (`league-scored-projection.v1`), `services/team_codes.py`, `scheduler/nflverse-schedule-refresh.service`, and `scheduler/nflverse-schedule-refresh.timer`. Tests: `tests/test_lineup_decision_intelligence.py`, `tests/test_lineup_projection_foundation.py`, and `tests/test_lineup_week_lock_state.py`. Updated owners: `owner_operations.py` (`/team` wiring), `templates/team.html`, `services/jerrygm_projections.py`, `services/team_needs.py`, `imports/import_nflverse_schedule.py`, and four tests.
- Lineup decisions: whole-lineup assignment uses the league's Sleeper slots and FLEX eligibility, so one slot change cannot silently weaken another. The page reconciles the current and recommended lineups, shows the best eligible alternatives, uses only START, SIT, FLEX, and MONITOR (no HOLD), and includes manager-facing reasons, What Could Change triggers, and missing-evidence lists. Health and availability gate eligibility; unknown health is never treated as healthy.
- Selection authority: the repository Weekly Score (season projection / 17, adjusted for matchup and health) at PRELIMINARY evidence level. Projection confidence and decision confidence are separate categorical states. No projection-accuracy model exists, so projection reliability is not rated. Floor, ceiling, and volatility remain UNSUPPORTED.
- League-scored projections: JerryGM `jgm_baseline` stat lines are rescored with the league's Sleeper scoring settings in fantasy points, so FLEX-eligible positions can be compared. Unreproducible K/DEF components keep scoring PARTIAL and are shown as ranges; a missing projection is never zero. These comparisons are PRELIMINARY and `INFORMATIONAL_ONLY`. The action threshold is UNAPPROVED, so a projected edge never selects players, raises confidence, or authorizes a change.
- Weekly consensus (ECR): live `/team` passes `consensus_authority=False`. ECR is DISPLAY_ONLY context: it is never converted to points, never compared across positions, and never selects or locks a player.
- Workload and opportunity evidence (nflverse usage and snap share) is `INFORMATIONAL_ONLY` supporting evidence. Stale rows are labelled; rows that fail validation are withheld.
- Kickoff locks are owned only by the automated nflverse schedule. Player states are OPEN, LOCKED, LOCK_UNVERIFIED, and BYE (NOT_APPLICABLE in Season Sandbox). Week states are PRE_KICKOFF, IN_PROGRESS, MOSTLY_LOCKED, COMPLETE, and LOCK_COVERAGE_INCOMPLETE. Locked starters stay pinned, locked bench players cannot enter, and LOCK_UNVERIFIED players are never moved in or out. Lock state does not depend on ECR, projections, or opportunity rows.
- Forward-validation snapshots are built per decision but are NOT_PERSISTED. Migration `014_pre_decision_snapshots.sql` is not applied (the `pre_decision_snapshots` table is absent), and no pre-kickoff capture step exists.
- Read-only boundary: no lineup is submitted. No waiver, trade, Survivor, or draft transaction behavior changed.

## Current schedule and kickoff-evidence boundary (operationally verified 2026-11-16)

- Source: the automated nflverse `schedules` release (`games.csv.gz`), published by `imports/import_nflverse_schedule.py --publish`; byes are derived from the same artifact. A read-only query of persisted 2026 state found 272 `nfl_schedule` rows and 32 `bye_weeks` rows, each owned by a single automated source. `source_recorded_at=2026-11-16 05:16:26+00` and `retrieved_at=2026-11-16 05:20:50+00` remain distinct.
- Threshold: `schedule.evidence.v1` = 86400 seconds, set by `SCHEDULE_EVIDENCE_MAX_AGE_SECONDS` in the local, git-ignored environment config (no code default). Byes use the season-static contract `bye.season_static.v1`.
- Republish guards (committed in `695ff74`): ownership from an earlier automated derived-bye artifact no longer blocks the next artifact; unknown or foreign bye owners still fail. `NFLVERSE_SCHEDULE_GAME_WEEK_MOVED` rejects a home/away pair that moves to another week instead of duplicating it. LA/LAR and JAC/JAX normalization is tested.
- Refresh: the user systemd timer `nflverse-schedule-refresh.timer` (00/06/12/18:00 America/Los_Angeles, Persistent) is enabled and active, the installed unit files match `scheduler/`, and `Linger=yes`. The latest service run (manual start, 2026-11-16 05:20:51 UTC) succeeded with `authoritative=true`, `blockers=[]`, COMPLETE, 272 games, 32 byes, and schedule FRESH. The next timer run is 2026-11-16 08:00 UTC; no timer-triggered run has been observed yet.
- Failure behavior: stale, missing, contradictory, or unsupported evidence makes affected players LOCK_UNVERIFIED. A failed refresh writes nothing and never renews freshness.
- Consumer and impact: My Team START/SIT/FLEX lock safety only. Schedule freshness is not player-performance authority. External transactions: none.

## Historical committed My Team delivery boundary (b75ed87; 2026-10-05)

- Branch: `test-weekly-evidence-trust`.
- HEAD: `b75ed8739ea55c04aaa366e4272a84e86083f284` - `feat(team): improve My Team lineup decision experience`.
- Scope: `templates/team.html`, `owner_operations.py`, `services/jerrygm_projections.py`, `imports/import_draft_intelligence.py`, `tests/test_ux5_lineup_route_contract.py`, `tests/test_jerrygm_projections.py`, and `tests/test_fantasypros_projection.py`.
- Implementation boundary: My Team page structure, health presentation, changed-slot explanations and informational JerryGM projections joined by exact Sleeper IDs. CSV projection updates clear unsupported source freshness instead of renewing it.
- Validation recorded for this commit: exact seven-file staged scope, six Python syntax checks, Jinja parsing, staged/working-tree equality, and staged whitespace checks passed. Tests were not rerun because the permitted rerun condition could not be established; no current behavioral, browser, or live-route PASS is claimed.
- Preserved limits: provider projections do not change lineup selection or confidence; current-use freshness needs a verified provider-specific threshold. No new milestone completion, defect closure, production readiness, parity, recovery, or transaction capability is claimed.
- Outstanding local work: `.gitignore` cleanup ignores verified local/generated outputs and TLS credentials; ignore and whitespace checks passed, but the change is uncommitted. Already-tracked bundles and continuity state remain tracked. Unrelated dirty files are preserved.
- Immediate follow-up: establish focused My Team behavioral and rendered-page evidence before strengthening completion claims; the exact next milestone below is unchanged.

## Historical committed Trade delivery boundary (2026-10-04)

- Branch: `test-weekly-evidence-trust`.
- HEAD: `c4011b18be4d3a043150f832ffebdaa0a3c772c0` - `feat(trades): enforce roster-safe trade recommendations`.
- Completion boundary: manager-first Trade Center UX places partner selection near the top and presents a recommendation hero, EXPLORE and MONITOR states, Why No Trade Exists, position labels and flow, before/after roster impact, the best roster-fit package, published/rejected package separation, manager-facing rejection explanations, and collapsed rejected packages, diagnostics, and identity lineage. Desktop and 390px usability are verified.
- Roster-safe publication contract: reject packages that create positional deficits, worsen existing deficits, violate minimum starter coverage, reduce supported FLEX coverage, or are need-neutral. Publish only packages that improve a verified owner need or supported FLEX coverage. Missing roster-impact inputs fail closed.
- Validation boundary: 71 focused Trade tests and 8 controlled Trade-route cases passed; all nine Python files in the commit compiled. The rendered Trade route showed the recommendation, position impact, best roster fit, published/rejected packages, and diagnostics at 1440px and 390px with no horizontal overflow. Working-tree and staged whitespace checks passed.
- Preserved boundaries: read-only decision support; no automatic trade submission. Trade-value, package-generation, ranked-list, and confidence formulas and transaction behavior are preserved.
- Unsupported claims: production readiness, external transaction capability, trade-acceptance likelihood or prediction, negotiation prediction, fabricated probability, full rest-of-season authority, PostgreSQL parity completion, recovery completion, and defect closure.
- Remaining Trade limitations: partner acceptance and transaction feasibility are unsupported, rest-of-season impact is unavailable, and missing roster-impact inputs block publication.
- Defect boundary: `docs/CURRENT_DEFECTS.md` remains authoritative and unchanged; this commit does not close a defect.

## Current validation and continuity status

- Focused validation on the current working tree (2026-11-16): 384 passed and 2 failed across 16 lineup, lock, schedule, JerryGM, and My Team route test files. The 2 failures (`tests/test_lineup_evidence.py::test_identity_fix_preserves_current_lineup_fields` and `::test_team_opportunity_changes_receives_player_specific_identity`) reproduce identically at clean HEAD `ddd329d`; that identity-route fixture does not supply `WEEK_AUTHORITY_ACQUIRER`. `tests/test_ux2_team_needs.py` fails collection at HEAD because `apply_waiver_ranking` does not exist. Both are pre-existing test defects outside this boundary. The same 16-file set reproduced 384 passed and the same 2 failures on committed `a306f3a` in a clean worktree, and `tests/test_schedule_bye_source_contract.py` passed (39) on `695ff74` alone.
- All 16 changed Python files compiled. `git diff --check` and `git diff --cached --check` passed.
- Live `/team` (HTTPS, served by code reloaded at 04:47 UTC) returned HTTP 200: Week 10, Week complete, 14 LOCKED from the automated schedule, START/FLEX decisions, no HOLD, league-scored projections labelled PRELIMINARY, and consensus labelled context only. The only remaining Week 10 game (LAC at BAL) has no rostered player. No live pre-kickoff open-window render has been observed on the current code.
- Canonical sources are reconciled to implementation HEAD `a306f3a` as of 2026-11-16. Bundle and canonical-sync results come from the continuity run, not from this text.

####### Historical waiver recovery boundary (through ee451ca; verified 2026-10-03)
- Recovery commits: `98dee6a` corrects candidate health from live Sleeper status; `34e55d3` publishes source-backed snap share; `ee451ca` restores exact waiver GSIS identity from DynastyProcess player IDs.
- Manager-facing result: `/waivers` returned HTTP 200 with 19 candidates. The 13 candidates previously lacking GSIS identity now resolve through exact `sleeper_id` to `gsis_id` from `DynastyProcess/files/db_playerids.csv` (GPL-3.0); names, team/position, and similarity do not authorize identity. Source artifact, version, checksum, schema, source/retrieval times, completeness, and reconciliation remain in lineage; the artifact is not committed. Live Sleeper health fails closed when missing, unresolved, contradictory, or unsupported; supported injured-reserve variants do not render healthy, and the local "Healthy / Not listed" placeholder is not verified health.
- Evidence boundary: all 19 candidates have fresh current-season production and opportunity evidence; `What Changed` consumes published multiweek opportunity rows. All 19 also have source-backed snap-share evidence from nflverse `offense_pct`, joined by exact PFR-to-GSIS identity with CC BY 4.0 attribution. Snap share remains informational only.
- Operational database state: the week 1-3 refresh published 1,078 opportunity rows and 4,480 resolved snap-share rows; 51 snap rows cover the 19 waiver candidates. `opportunity.evidence.v1` and `snap_share.evidence.v1` retain their 86,400-second contracts. Source and retrieval times remain distinct; stale evidence expires normally and requires legitimate reacquisition/republication, never timestamp copying. Database publications are not Git content.
- Decision authority: these identity, opportunity, and snap-share changes do not alter ranking, priority, confidence, FAAB, ownership, eligibility, or health, add formulas, or authorize external fantasy transactions. The health repair corrects health evidence only. Candidate order/count and existing `What Changed` behavior remain unchanged.
- Validation recorded: opportunity-focused tests passed 200; identity staged-copy validation passed 3 source and 14 waiver identity/invariance tests; snap staged-copy validation passed 47 snap and 4 consumer tests. The post-publication read-only `/waivers` check returned 19 FRESH snap-share candidates.
- Remaining limits: eight non-waiver snap rows across three unresolved PFR identities remain excluded, and partial Week 4 snap evidence remains unpublished. Expected-role and opportunity-duration contracts remain unavailable. Production readiness, full PostgreSQL parity, failure injection, rollback/recovery, guarded cleanup, and repeatability remain unclaimed. Matchup Rank authority and unrelated Survivor, Command Center, navigation, trade, and lineup boundaries are unchanged.

####### Historical validated delivery boundary (2026-10-02)
- Completed commits reconcile current/recommended lineups; add informational waiver comparison and repair trust-panel candidate evidence; repair per-player GSIS/ESPN identity assignment and unmatched-roster injury status; expose preliminary matchup signal without authorizing rank; and stabilize nflverse matchup contract tests.
- Focused matchup (15), preliminary-context (8), lineup, identity/injury, and waiver tests passed together (148 total).
- Matchup Signal remains informational-only. Matchup Rank/publication remain fail-closed under `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`; no recommendation influence, full authority, production readiness, parity completion, or recovery completion is claimed.
- The Command Center milestone below remains supported; the immediate implementation batch is **Build Command Center decision-center aggregation boundary**.

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

####### Historical active milestone: UX.2 My Team Accuracy, Explainability, and League-Settings Validation

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

####### Historical UX.2 remediation evidence
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

####### Preserved UX.2.1: My Team Product Hardening and All-Season Usability (historical validation)

**Status: VALIDATED AT VISUAL HIERARCHY, CONTRADICTION, AND DISCLOSURE BOUNDARY.**

- Compact recommendation cards, trust summary, weekly risks, bench decisions, actionable Team Needs cards, and supported roster outlook are implemented from existing contracts.
- Related UX.2.1B validation currently passes 147 tests.
- Isolated browser captures for complete, healthy, multiple-monitor, no-urgent, unavailable, stale, blocked, bench-unavailable, and missing-league states passed at 1440px and 390px; no primary overflow or clipped cards remained after the Team Needs wrap repair.
- Personal-use verdict: YES for the tested My Team boundary.

####### Historical UX.3: Waiver Correctness and Availability Validation

**Status: VALIDATED AT THE SUPPORTED, READ-ONLY PUBLICATION BOUNDARY.**

Validated:
- Stable Sleeper player IDs control rostered-player exclusion and publication identity.
- Current Sleeper roster ownership is FRESH from successful `retrieved_at` under `integrity.roster.v1`; provider source-record time is unavailable and remains distinct from retrieval time.
- Configured roster coverage, unique roster IDs, missing IDs, and duplicate diagnostics fail closed when incomplete or contradictory.
- Availability is transparently derived from the supported player pool minus active-league rostered IDs, not from transaction history or a provider-declared addability field.
- `/waivers` and `/gm` share the evaluated source set and evidence; `/waivers` publishes nine stable IDs and `/gm` publishes the five-candidate prefix, with no published rostered ID.
- The focused UX.3 suite passes 78 tests; Python compilation, whitespace checks, and rendered supported-state verification pass.
- UXQA-001 is VALIDATED, not CLOSED.

Remaining enhancements at this historical boundary:
- Candidate-level role, opportunity duration, roster fit, confidence, risk, suggested drop, and evidence-backed FAAB sophistication.
- Formal browser validation and separate UX.3 enhancement review.
- Commit review, canonical synchronization, and continuity validation required before defect closure.

####### Historical validated UX.4: Trade Center Integrity and Freshness Provenance

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

####### Historical UX.5: Lineup Explainability and Bench Redesign

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
- A.13 Opportunity Metrics Engine: evidence foundation implemented; authoritative ingestion remains deferred
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine: market-signal and candidate evidence foundations implemented; recommendation logic remains deferred
- A.18 Trade Impact Simulator: deferred; the committed Trade Center provides roster-safe, need-improving package recommendations, while a broader impact simulator and rest-of-season outcome model remain deferred

####### Outstanding validation track
- PostgreSQL 1000-event/10-replay verification.
- Failure-injection validation.
- Rollback and recovery evidence.
- Guarded cleanup and repeatability proof.
- Live-route validation where required for later milestones.
- Production deployment and recovery proof are not claimed.

####### Preserved UX.8 Survivor Intelligence progress (historical validation; in-progress, not complete)

- History/eligibility contract implemented: Week 1 JAX (season 2026) recorded through a conflict-safe write (`SurvivorConflictError`) and a distinct history-read-failure signal (`SurvivorHistoryReadError`); used-team exclusion verified live and by test.
- Week-state contract implemented (`OPEN` / `PENDING_RESULT` / `COMPLETED` / `UNAVAILABLE` / `BLOCKED`); the occupied-week contradiction is fixed — a locked week no longer offers another actionable pick or “Record… pick” control.
- Future Value no longer fabricates a neutral 0.50 when future schedule/prediction evidence is missing; Survivor Score discloses a reduced-scope formula (`current_stability_only` / `current_only`) instead of silently substituting a value.
- Evidence Agreement Score (`stability_score`) no longer reports a fabricated 100% agreement when all three underlying signals are missing; renders Unavailable instead.
- Action-first template redesign is live: hero, pick-this-week, alternatives, risk center, save-for-later, roadmap, used-teams/history, and collapsed rankings/metrics/lineage; locked-week, blocked, unavailable, degraded, and completed states are rendered through the real template (not only unit-tested).
- Added a “Refresh Market Intelligence for Week N” button wired to the existing `/api/market-intelligence/refresh` endpoint; fixed two defects surfaced while wiring it: the endpoint had no auth/CSRF protection (added `@admin_required`), and the running server never loaded `.env.market`/`.env.pickem` (added `load_dotenv` calls in `app.py`), which had silently blocked refresh at runtime.
- Root-caused the Week 2 `SURVIVOR_WEEK_EVIDENCE_MISSING` state: the sandbox schedule is correctly sourced from the real 2026 schedule; the external odds provider has not yet posted Week 2 lines (a temporal data-availability limit, not a code defect).
- Focused survivor + related security tests: 68 passed, 1 xfailed (up from 43/49 recorded earlier this session).
- `docs/PAGE_REQUIREMENTS.md` and `docs/METRIC_DEFINITIONS.md` updated with Survivor Intelligence page and metric contracts.
- Fixed a real Update-result dropdown bug (it always visually reset to “pending” regardless of the actual recorded status); added a Reset-pick control (`delete_selection()`, `/survivor/reset`) so a manager can clear a recorded pick and reopen the week for a fresh recommendation.
- Added manual team selection (“PICK A DIFFERENT TEAM”): a manager can record any eligible team as their pick, not only the algorithmic top recommendation, including teams with no market data; validated against the real team universe and recorded without fabricating a probability.
- Added CSRF protection to `/survivor/select` and `/survivor/status` (previously unprotected, same class of gap fixed earlier on the market-refresh endpoint).
- Added `_verified_current_week()` using Sleeper's `get_nfl_state()` to replace the hardcoded default week only when no week is explicitly requested; fails closed (never guesses) on network error or season mismatch.
- Focused survivor + security tests: 84 passed, 1 xfailed (up from 68 earlier this session).
- UX.8 is not yet formally complete; remaining boundary work is tracked under the Next milestone below.

####### Preserved UX.9 My Team + Weekly Lineup Consolidation (complete at recorded validation boundary)

- `/lineup` is retired as a rendered page and now returns HTTP 302 to `/team#lineup`; verified live and by test, preserving existing bookmarks.
- `/team` is now the single roster command center: hero (verdict/action/projected score/confidence/biggest risk) → Next Best Team Action → Lineup Snapshot → Recommended Starting Lineup (formation, now also carrying the authoritative START/SIT/FLEX/MONITOR call and a bench-swap flag per slot) → Bench Priority → Biggest Risks → Team Needs → Roster Outlook → What Changed This Week → Why This Lineup Is Trusted → collapsed diagnostics.
- Removed duplicate surfaces: the old plain hero, the separate “Recommended Starters” section, “Bench Plan”, the separate “Start/Sit Decisions” card grid, and Lineup's own risk/diagnostics blocks.
- No recommendation engine, lineup scoring, Team Needs, Team Health, Team Accuracy, waiver, trade, survivor, or database logic was changed; only route wiring and template presentation.
- Focused team/lineup route-contract tests: 20 passed (5 pre-existing, unrelated `/trades` failures unchanged).
- Completion check answered: no functionality on `/lineup` still justifies a separate page.

####### Historical NFL Intelligence MVP snapshot (implemented; recorded data coverage bounded)

- Read-only `/nfl-intelligence` is implemented with Top Picks, Top Risk Games, All Games, Insights, Blockers, and collapsed Diagnostics. The primary experience is manager-facing; raw Elo, matchup edge, injury totals, and weather values are confined to Diagnostics.
- All scheduled games for the selected loaded week render. Prediction absence is explicit as `INSUFFICIENT EVIDENCE`; no prediction is fabricated.
- The existing protected market-refresh endpoint is available through a per-week refresh button. It refreshes only provider games that match the stored schedule; it does not create unsupported predictions.
- Verified current coverage: Week 1 has 16 scheduled games and 7 provider-matched predictions; Week 2 has 16 scheduled games and 0 provider-matched predictions. The complete 2026 source schedule (`nfl_schedule`) contains Weeks 1-18, but only Weeks 1-2 are currently seeded into `yahoo_pickem_games`.
- Matching uses the complete provider full-name-to-standard-abbreviation map and exact away/home pairs. Recorded runs show Week 1 received/matched/wrote 7/7/7; Week 2 received 6 provider games and matched/wrote 0/0. This is a current provider-slate versus stored-schedule mismatch, not a verified naming failure.
- Focused NFL Intelligence validation: 29 passed. Python compilation for `nfl_intelligence.py` and `nfl_intelligence_routes.py`, whitespace validation, and live Week 1/Week 2 rendering passed. Desktop and 390px renders had no horizontal overflow.
- Historical repository checkpoint: 2026-09-14, branch `feature/evidence-bundle-pipeline`, HEAD `e5285b1918a97e6df7b9e74cd94385ecf489b721`. NFL Intelligence implementation and canonical documentation were committed at that snapshot; this is not the active branch or HEAD.

####### Verified product architecture and roadmap

- Primary in-season destinations are proposed as Decision Center, My Team, Waivers, Trades, NFL Intelligence, and Survivor. My Team remains the authoritative lineup destination; `/lineup` remains only as a redirect to `/team#lineup` for existing bookmarks.
- `/gm` duplicates lineup, waiver, and matchup summary behavior and exposes unsupported grades, scores, and modifiers. Its safe retirement path is to move cross-page prioritization to the rebuilt Dashboard, retain detail in the owning pages, then redirect `/gm` after route and bookmark validation.
- Draft, import, readiness, Sleeper administration, Pick'em, and technical diagnostics are not primary in-season destinations. Preserve useful routes until separately validated for redirection, secondary research, Draft Mode, or Admin placement.
- Current weekly-data boundary: Sleeper supplies live league, roster, ownership, and supplemental player-status facts; The Odds API supplies partial matched market context; nflverse and Open-Meteo supply automated NFL Intelligence enrichment. Schedule and bye inputs are now owned by the automated nflverse schedule import (see the current schedule and kickoff-evidence boundary); default weekly enrichment can still read CSV-derived matchup inputs. The no-CSV test covers an explicitly disabled path, not the default route.
- Phase 0: reconcile in-season navigation and retire duplicate manager destinations without losing `/lineup` bookmark behavior. Phase 1: establish automated, timestamped schedule, bye, injury, matchup, and projection inputs or fail closed. Phase 2: rebuild Dashboard as a Decision Center that links to, rather than duplicates, owning pages.
- Phase 3: add trusted player opportunity data and a multi-week What Changed engine. Phase 4: add market-aware buy/low, sell/high, breakout, and regression intelligence only after market-value and opportunity contracts exist. Phase 5: persist immutable pre-decision snapshots for post-week Process versus Results and narrative manager learning. Phase 6: add rest-of-season, playoff, and championship scenario planning only after trusted inputs exist.
- Opportunity trends, buy/sell labels, post-week grades, Manager Report Card grades, and playoff strategy are blocked by missing automated source, freshness, identifier, historical-baseline, metric-authority, or decision-time snapshot evidence. Do not infer them from box scores or stale CSV inputs.

####### Decision-first priority override

- Priority 1: make weekly START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, and TRADE AWAY decisions trustworthy with current, league-specific, explained evidence. This outranks navigation work, dashboards, new models, and season strategy.
- Priority 2: establish automated player opportunity and role evidence, then build What Changed from documented multi-week baselines. Breakout, regression, Buy Low, and Sell High labels remain blocked until source, identifier, history, freshness, metric authority, and market evidence are verified.
- Priority 3: rebuild Dashboard as the Decision Center, summarizing Must Act, Start/Sit, Waivers, Trades, Opportunity Alerts, Risk Alerts, and No Action Needed while linking to owning pages instead of duplicating their engines.
- Priority 4: persist immutable pre-decision snapshots before Process versus Results evaluation. Priority 5: provide narrative manager learning before any Manager Report Card grade. Rest-of-season and playoff strategy follow only after these decision foundations are trusted.

####### Historical Schedule and Bye Provenance installation boundary

- The additive provenance contract is installed and validated: 24 focused tests, Python compilation, `git diff --check`, `git diff --cached --check`, and live route inspection passed.
- Verified schedule state: all 272 2026 `nfl_schedule` rows are owned by `csv:nfl-2026-UTC.csv`, with `source_recorded_at=2026-05-14T00:00:00Z` and preserved import time. CSV fallback is disclosed and cannot overwrite automated, verified-cache, unknown, or differently-owned CSV rows.
- Verified bye state: all 32 2026 `bye_weeks` rows retain legacy source attribution (`Gridiron Games bye-week PDF; cross-checked against nfl-2026-UTC.csv`) but have no source-recorded, retrieval, or import timestamp. The verified bootstrap correctly refused to infer CSV ownership for these non-null legacy rows.
- Schedule and bye freshness thresholds are currently unset. Therefore schedule/bye provenance is installed and schedule source time is recorded, but neither domain is yet authoritative for live recommendations; the correct contract state remains `UNAVAILABLE`, not fabricated `FRESH`.
- Live route evidence: `/team` rendered `FRESH`, `MONITOR`, and `UNAVAILABLE`; `/waivers` rendered `FRESH`; `/trades` rendered `FRESH`, `AGING`, and `BLOCKED`. These route markers do not override the unset schedule/bye freshness configuration.
- Remaining blockers: approved schedule/bye freshness thresholds, timestamped bye provenance through a controlled source-specific workflow, current matchup evidence, and authoritative projection/ranking evidence. No defect is closed by this installation alone.
- Superseded (2026-11-16): the CSV-owned schedule, legacy-attributed byes, unset schedule threshold, and schedule non-authority described above are historical. The current schedule and kickoff-evidence boundary records automated nflverse ownership, `schedule.evidence.v1` = 86400 seconds, and schedule-owned lineup locks. Current matchup evidence and authoritative projection/ranking evidence remain open blockers.

####### Current in-season priorities

- Reconcile the season navigation: remove the retired `/lineup` navigation entry, keep `/team#lineup` as the authoritative lineup destination, and move duplicate GM/technical surfaces out of the primary manager workflow.
- CSV and manual imports are last-resort bootstrap, recovery, or test-fixture mechanisms only. They must not be required for routine weekly decisions; stale or unrefreshable inputs must be explicit `UNAVAILABLE` or `BLOCKED`.
- Replace default CSV-derived weekly matchup inputs with automated, timestamped sources before using them authoritatively. Until then, preserve fail-closed recommendation behavior.
- Do not add advanced player opportunity, buy/sell, post-week process, or playoff-strategy features until their source, freshness, metric authority, and missing-data contracts are defined and validated.

####### Historical end-of-day evidence reconciliation (2026-09-14)

- The Schedule/Bye Threshold Registry is installed and validated: 40 focused tests, Python compilation, `git diff --check`, and `git diff --cached --check` passed. Its stable IDs are `schedule.evidence.v1` and `bye.evidence.v1`; absent, malformed, zero, and negative environment values fail closed without a numeric default.
- Automated nflverse matchup implementation: VALIDATED at official retrieval, provenance, Full-PPR calculation, `LA` to `LAR` normalization, completeness, freshness, fail-closed publication, and PostgreSQL transaction boundaries. Migration `013_nflverse_defense_matchups.sql` is applied and idempotent.
- Source: `stats_player`; artifact: `stats_player_week_{season}.csv.gz`. Refreshed real 2026 Week 1 calculation reached 128 rows and 32-of-32 defenses for QB, RB, WR, and TE. `KC` and `DEN` are present; identity resolution is complete. Rank directionality is `LOWER_IS_HARDER`. Preliminary context is informational-only and does not influence recommendations.
- Current publication remains BLOCKED by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`. Automated 2026 rows remain 0; 136 historical 2025 CSV rows remain preserved and historical-only. Current consumers may show preliminary context but cannot use authoritative Matchup Rank; production readiness, full current-season authority, and milestone completion remain unclaimed.

## Next milestone

**Validate My Team weekly START/SIT/FLEX decision quality with persisted pre-kickoff decision snapshots and post-week outcome review before expanding Command Center or other infrastructure.**

The decision-first priority override ranks trustworthy weekly START/SIT/FLEX decisions above dashboards and navigation. Whole-lineup decisions and schedule-owned locks now exist, but the Weekly Score and league-scored projections remain PRELIMINARY, and the projection action threshold is UNAPPROVED. Neither can be strengthened without forward evidence, and none is being captured because `pre_decision_snapshots` does not exist; every played week without capture is lost evidence.

The next implementation batch is **Persist pre-kickoff My Team lineup decision snapshots**:
1. Apply `014_pre_decision_snapshots.sql` after a database backup.
2. Add an explicit, read-only pre-kickoff capture step.
3. Add a post-week comparison against actual Sleeper points.

This batch must not change selection, invent thresholds, or submit transactions. Command Center aggregation, opportunity detection, Process versus Results, manager development, and season strategy follow in that order. UX.8 retains its recorded in-progress boundary. Existing defects retain their evidence-supported statuses; production readiness, PostgreSQL parity, recovery, and defect closure remain unclaimed. This reconciliation authorizes no defect closure.
