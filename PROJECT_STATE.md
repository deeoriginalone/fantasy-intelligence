###### Project State

## Fantasy Intelligence 2.0 Direction

Fantasy Intelligence remains a personal league-specific decision assistant focused on better weekly and season decisions. The six primary destinations are Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence.

The six-page architecture is an approved target direction. Primary navigation has not yet been simplified; the Command Center target is not complete; no new redirect, route archive, or route removal has been completed. Supporting routes remain operational. `MERGE`, `REDIRECT`, and `ARCHIVE` are future route-disposition classifications.

## Evidence-first architecture boundary

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Matchup Signal remains context-only where its specific metric contract does not support recommendation use; Matchup Rank remains subject to its own contract.

Apply this model across Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. Preserve each page's specific identity, ownership, eligibility, contradiction, corruption, and transaction-safety protections.

These pending plans include navigation simplification, route merging, new redirects, and archive actions. Decision Journal, Process vs Results, and Season Planning are planned priorities, not delivered capabilities.

## Current My Team decision-first boundary

The committed `/team` template orders My Team header, Your Lineup, Health & Availability, Biggest Decisions, Why These Decisions, What Could Change, Supporting Roster Details, and collapsed Data/Model Diagnostics. Current Sleeper Lineup, Bench Priority, and Team Needs remain supporting details. This supersedes the earlier hero-first presentation description. Behavioral and rendered-page evidence for the current working tree is recorded under the current committed Starting Lineup Decision Intelligence and schedule-lock boundary below (`695ff74`, `a306f3a`).

## Navigation Reconciliation Target

Primary navigation is Command Center, My Team, Waivers, Trades, Survivor, NFL Intelligence, and What Changed. The Command Center is the planned primary landing page for League Overview, Must Act, Start/Sit Summary, Waiver Priorities, Trade Watch, Survivor Status, NFL Intelligence Highlights, What Changed, and Risk Alerts. League Overview is planned to merge into Command Center.

NFL Intelligence is the planned single NFL-wide intelligence destination for Top Picks, Top Risk Games, Game Predictions, Market Intelligence, Weather, Injury Context, Insights, Blockers, and Diagnostics. Market Intelligence is planned to merge into NFL Intelligence rather than remain a separate navigation item.

Draft Board and Mock Draft remain preserved and accessible for Season Planning. Sleeper Hub, Draft Day Readiness, Draft Intelligence & Learning Center, Imports, Readiness, and Diagnostics are planned Admin destinations.

The intended dispositions are: Command Center PRIMARY; League Overview MERGE into Command Center; My Team PRIMARY; Waivers PRIMARY; Trades PRIMARY; Survivor PRIMARY; NFL Intelligence PRIMARY; Market Intelligence MERGE into NFL Intelligence; What Changed PRIMARY / SECONDARY; Draft Board KEEP; Mock Draft KEEP; and Sleeper Hub, Draft Day Readiness, Draft Intelligence & Learning Center, Imports, Readiness, and Diagnostics ADMIN. These are planned navigation classifications, not completed implementation changes.

Recovery Ready is a planned mandatory standard, not a completed checkpoint. Recovery Ready planned work remains pending. It will require a runnable checkpoint, documented startup verification, database backup, canonical-memory snapshot, Notebook/reference export, and six-core-page verification. Preserve existing data, integrations, ownership logic, evidence, and read-only behavior.

####### Current state

Fantasy Intelligence has completed the Shared Integrity and Data Integrity track through A.10. UX.1 remains complete at its verified focused-test and rendered active-route boundary.

UX.2 My Team Accuracy, Explainability, and League-Settings Validation is validated at the focused and controlled active-route boundary. The route, contracts, recommendation evidence, health targeting, priority action, and collapsed lineage are preserved.

UX.2.1C presentation and disclosure repairs are recorded; owner acceptance remains pending per `docs/CURRENT_DEFECTS.md`. UX.3 is validated at a supported, read-only waiver-publication boundary. UX.4.1 through UX.4.12 are validated at focused, controlled-browser, and live nine-partner dropdown boundaries. The shared action-first visual system is implemented across Lineup, My Team, Waivers, and Trades. UX.5 has the formalized implementation and evidence boundary; formal definition-of-done review remains pending. UX.6 and UX.7 remain pending.

####### Current repository checkpoint
- Date: 2026-11-16
- Branch: test-weekly-evidence-trust
- HEAD: a306f3a210835ae9c9c5fb62a4295271ec69eb6a

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

####### Historical repository boundary (verified 2026-10-02)
- Current committed work completes lineup reconciliation; informational waiver comparison and trust-panel evidence repair; per-player GSIS/ESPN identity repair; unmatched-roster injury-status repair; preliminary matchup signal display; and nflverse matchup test stabilization.
- Matchup Signal is informational/context-only. Matchup Rank and publication remain fail-closed while the sample threshold is unverified (`MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`). No recommendation influence or full matchup authority is claimed.
- The matchup and preliminary-context tests pass 15 and 8 tests respectively. Related matchup, lineup, identity/injury, and waiver test files pass 148 tests combined.
- All defect statuses remain as documented in `docs/CURRENT_DEFECTS.md`. Full matchup authority, PostgreSQL parity, recovery, and production readiness remain unclaimed.

####### Historical evidence-layer foundation (validated 2026-09-15)
- Pure fail-closed contracts now exist for Opportunity Evidence, What Changed, Opportunity Classification, Market Value, Market Signal, Buy/Sell Candidates, and Trade Opportunity evidence.
- Dashboard Decision Center summarizes existing blockers, freshness, completeness, affected areas, and confidence impact across the required summary panels. It is informational only and does not create priority or recommendations.
- Dashboard, `/team`, `/waivers`, and `/trades` preserve their existing decision payloads. No START, SIT, FLEX, MONITOR, Weekly Score, confidence, waiver ranking, trade ranking, matchup, or transaction behavior consumes these layers.
- Focused validation passed 16 tests; compilation and working-tree/staged whitespace checks passed. Default live routes render the new summaries fail-closed; no live market or candidate source is configured.

The branch, HEAD, and working-tree state must be reverified from the repository before import, staging, validation, or commit.

####### Preserved verified capabilities
- Shared completeness, confidence, freshness, blocker, evidence-state, and lineage contracts previously recorded.
- Dashboard state, freshness, Pacific-time draft presentation, truth-audit, and fail-closed cross-page agreement evidence.
- League-settings-derived roster requirements with DST-to-DEF normalization.
- Full-PPR Team Needs evaluation for QB, RB, WR, TE, FLEX, K, and DEF.
- Team Health and Team Accuracy contracts wired into the active `/team` route.
- Explicit unavailable-state and blocker handling for unsupported health and matchup evidence.
- Tested owned-player waiver filtering and fail-closed eligibility evidence remain preserved within the current committed waiver boundary above.
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

####### Historical known boundaries and validation snapshot
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

####### Historical validated UX.5 boundary
- Weekly Lineup Intelligence emits explicit `START`, `FLEX`, `MONITOR`, and bench `SIT` decisions; ambiguous `HOLD`/`SWAP` output is no longer rendered.
- Bench players receive deterministic `bench_order` values and manager-facing reason, confidence, opponent, health, and weekly-value evidence.
- Missing weekly or matchup evidence renders as `Unavailable`, not verified zero or neutral evidence; blocker impacts and baseline/Weekly Score definitions are visible.
- Focused UX.5 service/template/route-contract validation passed 10 tests. Related integrity and UX.2 route validation passed 27 tests. Compilation, diagnostics, and whitespace checks passed.
- Live `/lineup` returned HTTP 200 and rendered Start/Sit Decisions, Bench Order, START/FLEX/MONITOR/SIT labels, metric definitions, and Unavailable states with no HOLD text. Desktop and 390px mobile inspection passed without primary horizontal overflow.
- The redesigned page prioritizes a weekly verdict and manager action, then decision cards, lineup risks, formation slots, bench priority, unavailable change history, collapsed metric explanations, and bottom-only data quality/lineage diagnostics.
- UX.5 remains read-only. Formal definition-of-done review and canonical continuity validation remain pending.

####### Historical cross-page action-first presentation boundary
- My Team uses the shared verdict/action shell, modern evidence cards, responsive grids, and bottom diagnostics while preserving Team Health, Team Accuracy, Team Needs, starter, bench, and lineage contracts. Focused validation passed 34 tests; live `/team` returned HTTP 200 and passed desktop/390px overflow checks.
- Waivers uses a waiver verdict, Priority Adds cards, FAAB guidance, blocked ownership/eligibility states, and retained availability/lineage evidence. Focused validation passed 47 tests; live `/waivers` returned HTTP 200 and passed desktop/390px overflow checks.
- Trades uses a trade verdict, partner selector, roster-fit summary, one-for-one/two-for-one package cards, feasibility visibility, and collapsed integrity/identity diagnostics. Focused validation passed 27 tests; live `/trades` returned HTTP 200 and passed desktop/390px overflow checks.
- These pages remain read-only. No route, database, ownership, eligibility, health, matchup, trade, waiver, or transaction logic was changed by the visual rollout.

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
- Automated nflverse matchup evidence is implemented and validated through official-source retrieval, provenance, Full-PPR calculation, `LA` to `LAR` normalization with regression coverage, completeness evaluation, fail-closed publication, and PostgreSQL transaction behavior. Migration `013_nflverse_defense_matchups.sql` is applied and idempotent.
- The source is `stats_player` with artifact pattern `stats_player_week_{season}.csv.gz`. Refreshed real 2026 Week 1 calculation produced 128 rows and 32-of-32 defense coverage for QB, RB, WR, and TE; `KC` and `DEN` are present. Source timestamps, retrieval time, compressed/decompressed checksums, release version, and CC BY 4.0 attribution are captured.
- Preliminary matchup context is fresh, complete, Full-PPR, sample-disclosed, and informational-only in memory. Current matchup authority remains BLOCKED by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`; automated 2026 rows remain 0; 136 historical 2025 CSV rows remain preserved and cannot satisfy current-season authority. Preliminary context does not influence recommendations, and production readiness or full current matchup authority is not claimed.

## Next milestone

**Validate My Team weekly START/SIT/FLEX decision quality with persisted pre-kickoff decision snapshots and post-week outcome review before expanding Command Center or other infrastructure.**

The decision-first priority override ranks trustworthy weekly START/SIT/FLEX decisions above dashboards and navigation. Whole-lineup decisions and schedule-owned locks now exist, but the Weekly Score and league-scored projections remain PRELIMINARY, and the projection action threshold is UNAPPROVED. Neither can be strengthened without forward evidence, and none is being captured because `pre_decision_snapshots` does not exist; every played week without capture is lost evidence.

The next implementation batch is **Persist pre-kickoff My Team lineup decision snapshots**:
1. Apply `014_pre_decision_snapshots.sql` after a database backup.
2. Add an explicit, read-only pre-kickoff capture step.
3. Add a post-week comparison against actual Sleeper points.

This batch must not change selection, invent thresholds, or submit transactions. Command Center aggregation, opportunity detection, Process versus Results, manager development, and season strategy follow in that order. UX.8 retains its recorded in-progress boundary. Existing defects retain their evidence-supported statuses; production readiness, PostgreSQL parity, recovery, and defect closure remain unclaimed. This reconciliation authorizes no defect closure.
