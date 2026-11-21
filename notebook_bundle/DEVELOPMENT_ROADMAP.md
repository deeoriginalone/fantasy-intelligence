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

The committed `/team` template orders My Team header, Your Lineup, Health & Availability, Biggest Decisions, Why These Decisions, What Could Change, Supporting Roster Details, and collapsed Data/Model Diagnostics. Current Sleeper Lineup, Bench Priority, and Team Needs remain supporting details. This supersedes the earlier hero-first presentation description. Behavioral and rendered-page evidence for the committed lineup code is recorded under the current committed Starting Lineup Decision Intelligence and schedule-lock boundary below (`695ff74`, `a306f3a`). Committed pre-kickoff lineup decision snapshot capture, its scheduled automation, and the read-only post-week review (2026-11-19) are recorded under the current committed pre-kickoff lineup decision snapshot boundary below. The committed shadow Weekly Score v2 (`b8b8f6d`, 2026-11-19), shown on each starting slot as an informational "Weekly projection", is recorded under the current committed Weekly Score v2 shadow boundary below.

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
- Date: 2026-11-21
- Branch: test-weekly-evidence-trust
- HEAD: 4212a92d4cffe3605724d35370c65437dbd7e4c6
- Working tree: the W6 Waivers role and opportunity evidence implementation is committed in `4212a92` (8 files) on top of the pushed W1-W5 closeout (`79be2ff`, `4798bb0`, `38cd314`). This reconciliation commits the canonical sources and the stale product-reference documents (`docs/PAGE_REQUIREMENTS.md`, `docs/METRIC_DEFINITIONS.md`, and `docs/DATA_FRESHNESS_POLICY.md`), and a following continuity commit refreshes the generated continuity artifacts. The checkpoint HEAD above records the W6 implementation commit. The branch is pushed to `origin/test-weekly-evidence-trust` only after continuity validation passes, without force; the push result is recorded in the batch report, not in this text. Unrelated untracked local files (raw captures, generated artifact and audit outputs, patches, an old prompt, a temporary evidence script, and an unvalidated rollback script) are preserved and never staged.

## Current committed delivery boundary

- Branch: `test-weekly-evidence-trust`. Before this batch's push, `origin/test-weekly-evidence-trust` was at `38cd314` (the pushed W1-W5 closeout) and the branch was ahead only by `4212a92`, plus this reconciliation's documentation and continuity commits (2026-11-21). This batch pushes them without force only after continuity validation passes.
- Implementation HEAD: `4212a92d4cffe3605724d35370c65437dbd7e4c6` - `feat(waivers): add informational role and opportunity evidence`, on top of the W1-W5 Waivers commit `79be2ff` - `feat(waivers): add roster-safe decisions and league FAAB evidence` (reconciled in `4798bb0` and `38cd314`) and `9556268` - `chore(ai): add Fantasy Intelligence repository agents`. The My Team implementation commits remain `b8b8f6d` - `feat(team): add shadow Weekly Score v2`, `298c83b` - `feat(scheduler): automate pre-kickoff lineup snapshot capture`, and `95acb9c` - `feat(team): capture pre-kickoff lineup decision snapshots`; the lineup decision intelligence commit remains `a306f3a`. Commits after `4212a92` are documentation and continuity only.
- Commits after the historical My Team boundary `b75ed87`: `87a43ca` restores the action-first My Team hero and verified NFL week; `bff775f` adds evidence-gated waiver decisions and FAAB guidance; `3ddd37c` uses the configured timezone and authoritative week; `34c3498` adds schedule-backed waiver ranking, the automated nflverse schedule importer (`imports/import_nflverse_schedule.py`), and `services/schedule_bye_evidence.py`; `41dfe47` ranks visible Command Center lineup decisions; `c25e4f2` shares defensive health test assertions; `d37229b` adds an nflverse artifact watchdog; `beb5482` and `d478060` refresh reference and database documents; `ddd329d` ignores local generated artifacts; `695ff74` commits schedule automation (importer republish guards, systemd units, schedule tests); and `a306f3a` commits My Team lineup decision intelligence (services, route, template, and tests).
- Commits through `ddd329d` are recorded from Git history. `695ff74` and `a306f3a` were each revalidated in a clean worktree (see validation below). The 2026-11-16 reconciliation did not revalidate the earlier commits and claimed no defect closure, production readiness, PostgreSQL parity, or recovery readiness.
- Later commits: `5abe2fd` reconciles canonical memory to the lineup and schedule boundary and `1f641d1` refreshes continuity artifacts (documentation and continuity only); `95acb9c` commits the pre-kickoff snapshot capture and review (5 files); `298c83b` commits the capture automation (2 systemd units, 1 new test file, and 2 added capture tests); and `b8b8f6d` commits the shadow Weekly Score v2 (3 services, `templates/team.html`, 3 test files, and `docs/METRIC_DEFINITIONS.md`). `8774fa8` reconciles canonical memory to the Weekly Score v2 boundary and `b5b6cc6` refreshes continuity artifacts (documentation and continuity only); `9556268` adds the Architect, Auditor, and Implementer agent definitions under `.ai/agents/` (repository working rules only); and `79be2ff` commits W1-W5 Waivers (9 Python implementation files, 2 templates, and 6 test files). `4798bb0` reconciles canonical memory to the W1-W5 boundary and `38cd314` refreshes continuity artifacts (documentation and continuity only); the 2026-11-20 batch pushed every commit through `38cd314`. `4212a92` commits W6 role and opportunity evidence (3 new files: `services/waiver_role_evidence.py`, `refresh_opportunity_evidence.py`, and `tests/test_waiver_role_evidence.py`; 5 modified: `owner_operations.py`, `services/player_opportunity_reader.py`, `services/snap_share_reader.py`, `templates/waivers.html`, and `tests/test_waiver_availability.py`). Before this batch, `4212a92` was the only commit not pushed.

## Current committed Starting Lineup Decision Intelligence and schedule-lock boundary (2026-11-16)

State: IMPLEMENTED and VALIDATED at the focused, controlled-route, and live `/team` boundary. Schedule automation is OPERATIONALLY VERIFIED. COMMITTED in `695ff74` (schedule) and `a306f3a` (lineup).

- Owners: `services/lineup_decision_intelligence.py` (`lineup-decision.v1`), `services/game_lock.py` (`lineup.game_lock.v1`), `services/lineup_projection.py`, `services/league_scoring.py` (`league-scored-projection.v1`), `services/team_codes.py`, `scheduler/nflverse-schedule-refresh.service`, and `scheduler/nflverse-schedule-refresh.timer`. Tests: `tests/test_lineup_decision_intelligence.py`, `tests/test_lineup_projection_foundation.py`, and `tests/test_lineup_week_lock_state.py`. Updated owners: `owner_operations.py` (`/team` wiring), `templates/team.html`, `services/jerrygm_projections.py`, `services/team_needs.py`, `imports/import_nflverse_schedule.py`, and four tests.
- Lineup decisions: whole-lineup assignment uses the league's Sleeper slots and FLEX eligibility, so one slot change cannot silently weaken another. The page reconciles the current and recommended lineups, shows the best eligible alternatives, uses only START, SIT, FLEX, and MONITOR (no HOLD), and includes manager-facing reasons, What Could Change triggers, and missing-evidence lists. Health and availability gate eligibility; unknown health is never treated as healthy.
- Selection authority: the legacy repository Weekly Score (v1: season projection / 17, adjusted for matchup and health) at PRELIMINARY evidence level. Projection confidence and decision confidence are separate categorical states. No projection-accuracy model exists, so projection reliability is not rated. Floor, ceiling, and volatility remain UNSUPPORTED. Verified 2026-11-19: on live `/team` the legacy Weekly Score is withheld for every player, because `weekly_intelligence.py` marks its projection input `PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE` (no automated weekly input is approved for lineup selection). No supported value comparison can therefore favor a change, and current starters stay unless availability, eligibility, or lock rules require one. The shadow Weekly Score v2 (`b8b8f6d`) is a separate current-week projection metric with no selection authority (see the current committed Weekly Score v2 shadow boundary below).
- League-scored projections: JerryGM `jgm_baseline` stat lines are rescored with the league's Sleeper scoring settings in fantasy points, so FLEX-eligible positions can be compared. Unreproducible K/DEF components keep scoring PARTIAL and are shown as ranges; a missing projection is never zero. These comparisons are PRELIMINARY and `INFORMATIONAL_ONLY`. The action threshold is UNAPPROVED, so a projected edge never selects players, raises confidence, or authorizes a change.
- Weekly consensus (ECR): live `/team` passes `consensus_authority=False`. ECR is DISPLAY_ONLY context: it is never converted to points, never compared across positions, and never selects or locks a player.
- Workload and opportunity evidence (nflverse usage and snap share) is `INFORMATIONAL_ONLY` supporting evidence. Stale rows are labelled; rows that fail validation are withheld.
- Kickoff locks are owned only by the automated nflverse schedule. Player states are OPEN, LOCKED, LOCK_UNVERIFIED, and BYE (NOT_APPLICABLE in Season Sandbox). Week states are PRE_KICKOFF, IN_PROGRESS, MOSTLY_LOCKED, COMPLETE, and LOCK_COVERAGE_INCOMPLETE. Locked starters stay pinned, locked bench players cannot enter, and LOCK_UNVERIFIED players are never moved in or out. Lock state does not depend on ECR, projections, or opportunity rows.
- Forward-validation snapshots are built per decision; `a306f3a` never persists them. Superseded 2026-11-19: migration `014_pre_decision_snapshots.sql` is applied, `95acb9c` adds an explicit pre-kickoff capture step and a read-only post-week review, and `298c83b` runs capture on a schedule (see the current committed pre-kickoff lineup decision snapshot boundary below).
- Read-only boundary: no lineup is submitted. No waiver, trade, Survivor, or draft transaction behavior changed.

## Current schedule and kickoff-evidence boundary (operationally verified 2026-11-16)

- Source: the automated nflverse `schedules` release (`games.csv.gz`), published by `imports/import_nflverse_schedule.py --publish`; byes are derived from the same artifact. A read-only query of persisted 2026 state found 272 `nfl_schedule` rows and 32 `bye_weeks` rows, each owned by a single automated source. `source_recorded_at=2026-11-16 05:16:26+00` and `retrieved_at=2026-11-16 05:20:50+00` remain distinct.
- Threshold: `schedule.evidence.v1` = 86400 seconds, set by `SCHEDULE_EVIDENCE_MAX_AGE_SECONDS` in the local, git-ignored environment config (no code default). Byes use the season-static contract `bye.season_static.v1`.
- Republish guards (committed in `695ff74`): ownership from an earlier automated derived-bye artifact no longer blocks the next artifact; unknown or foreign bye owners still fail. `NFLVERSE_SCHEDULE_GAME_WEEK_MOVED` rejects a home/away pair that moves to another week instead of duplicating it. LA/LAR and JAC/JAX normalization is tested.
- Refresh: the user systemd timer `nflverse-schedule-refresh.timer` (00/06/12/18:00 America/Los_Angeles, Persistent) is enabled and active, the installed unit files match `scheduler/`, and `Linger=yes`. The latest service run (manual start, 2026-11-16 05:20:51 UTC) succeeded with `authoritative=true`, `blockers=[]`, COMPLETE, 272 games, 32 byes, and schedule FRESH. Timer-triggered runs are now observed: the user journal shows 13 consecutive successful runs from 2026-11-16 08:00 UTC through 2026-11-19 08:00 UTC (latest exit status 0).
- Failure behavior: stale, missing, contradictory, or unsupported evidence makes affected players LOCK_UNVERIFIED. A failed refresh writes nothing and never renews freshness.
- Consumer and impact: My Team START/SIT/FLEX lock safety only. Schedule freshness is not player-performance authority. External transactions: none.

## Current committed pre-kickoff lineup decision snapshot boundary (2026-11-19)

State: IMPLEMENTED and VALIDATED at the focused, controlled-route, live-route, and database boundary. COMMITTED in `95acb9c` (capture and review), `298c83b` (automation), and `b8b8f6d` (snapshot content `lineup.forward_validation.snapshot.v2` with the shadow Weekly Score v2), not pushed as of 2026-11-19. Scheduled capture is OPERATIONALLY VERIFIED as installed and enabled, and a manual run through the systemd service succeeded; `FIRST_SCHEDULED_SNAPSHOT_V2_CAPTURE = PENDING` (the first timer-triggered run is due 2026-11-19 21:00 UTC, after this reconciliation).

- Owners: `services/lineup_forward_validation.py` (new; capture `lineup.forward_validation.capture.v1` and review `lineup.forward_validation.review.v1`), `services/lineup_projection.py` (snapshot content `lineup.forward_validation.snapshot.v2` since `b8b8f6d`, `snapshot.v1` before it; decision type `MY_TEAM_LINEUP_DECISION`), `services/lineup_decision_intelligence.py` (copies each player's finished decision into his snapshot after selection), and `owner_operations.py` (`team_lineup_state`, shared by `/team` and capture, plus the Flask CLI commands `owner_ops capture-lineup-snapshots` and `owner_ops review-lineup-snapshots`). Reused foundation committed in `8b6b679`: `services/pre_decision_snapshots.py` (`pre-decision-snapshot.v1`) and `migrations/014_pre_decision_snapshots.sql`. Automation: `scheduler/lineup-snapshot-capture.service` and `scheduler/lineup-snapshot-capture.timer`. Tests: `tests/test_lineup_forward_validation.py` (12 since `b8b8f6d`), `tests/test_lineup_snapshot_capture_units.py` (4), and `tests/test_pre_decision_snapshots.py` (7).
- Database: migration 014 was applied on 2026-11-19 after it was verified unapplied and after a verified pre-migration `pg_dump` (custom format, 48 tables, SHA-256 checked) was stored in the git-ignored `.batch_backups/pre-014-pre-decision-snapshots-20261119T075043Z/`. PostgreSQL shows `pre_decision_snapshots` (20 columns; primary key `snapshot_id`; subject index; CHECK `decision_effect = 'NONE'`; evidence, freshness, and completeness state checks) and the row-level `BEFORE UPDATE OR DELETE` trigger `pre_decision_snapshots_immutable`. Rolled-back UPDATE and DELETE attempts on real rows were rejected as append-only. The trigger does not block TRUNCATE or DROP by the table owner.
- Snapshot contract: one row per identified player whose schedule-verified kickoff is still ahead. It copies, without deriving, season and week, Sleeper identity, the START/SIT/FLEX/MONITOR decision, recommended and current slot, slot status, decision confidence, reason, related slots, the legacy Weekly Score (value, state, evidence level, blocker), the league-scored projection (value or range, evidence state, `INFORMATIONAL_ONLY` impact), team and opponent, Sleeper health and availability evidence, the schedule-owned lock (state, kickoff, freshness, threshold ID), lineup context (decision contract version, week state, value and projection basis, action threshold UNAPPROVED), blockers, missing-evidence domains, capture time, and contract versions. Missing values stay null with their blockers and are never zero; a verified zero stays 0.0. Since `b8b8f6d`, new snapshots (`lineup.forward_validation.snapshot.v2`) also copy `decision_output.weekly_score_v2` (value or range, state, evidence level, authority, recommendation impact, source, generated and retrieved times, season and week, scoring context and contract, completeness, freshness, blockers, and contract ID), `contract_versions.weekly_score = weekly-score.v2`, and the lineup-level `weekly_score_v2_basis`. Earlier `snapshot.v1` rows are never rewritten and remain readable; the review reports their Weekly Score v2 as NOT_CAPTURED.
- Capture: `venv/bin/flask --app app owner_ops capture-lineup-snapshots` builds the same decision as `/team` and appends only LIVE snapshots whose lock is OPEN with decision authority and whose kickoff is still ahead, rechecked at write time. Locked, bye, LOCK_UNVERIFIED, unresolved-identity, Season Sandbox, and altered snapshots are never stored. Writes use `ON CONFLICT (snapshot_id) DO NOTHING`: identical evidence is a no-op, stored rows are never updated, and a failed write rolls back without touching stored rows. The command exits 1 on a failed or partial capture and on any error. Viewing `/team` never writes.
- Rerun boundary: the snapshot ID hashes the decision-time evidence, including retrieval timestamps, so a rerun with refreshed health or projection retrieval times appends a new row instead of overwriting the earlier one. Each scheduled run therefore appends one row per eligible player. The review uses each player's latest pre-kickoff snapshot and reports how many exist.
- Automation (`298c83b`): the user systemd units are installed as copies in `~/.config/systemd/user/` (identical to `scheduler/`, the same model as the nflverse schedule refresh), and the timer was enabled on 2026-11-19 at 13:41 UTC. The oneshot service runs `venv/bin/flask --app app owner_ops capture-lineup-snapshots` in the repository working directory with `TimeoutStartSec=15min`; the timer only triggers that command. A failed or partial capture marks the unit failed, and the JSON result stays in the journal. The timer uses America/Los_Angeles with `Persistent=true` and `RandomizedDelaySec=0`: Thursday 13:00, Sunday 09:00, and Monday 13:00, before the 2026 TNF (17:15), Sunday early-slate (10:00), and MNF (17:15) kickoffs, plus 2026 Week 12 one-offs on Wed Nov 25 at 15:00 and Thu Nov 26 at 08:00. A persistent catch-up run is safe because capture rechecks every kickoff at write time. `systemd-analyze --user verify` reported no diagnostics. Next runs: 2026-11-19 21:00, 2026-11-22 17:00, and 2026-11-23 21:00 UTC.
- Coverage limits (2026 schedule): GB at LAR (Wed Nov 25 17:00) is covered only if Sleeper already reports Week 12 at the Wednesday run, because Sleeper's week-advance time is not recorded; CHI at DET (Thanksgiving 10:00) is covered by the Thanksgiving-morning run. DEN at PIT (Black Friday 12:00), the two Week 15 Saturday games, and the three Week 16 Christmas games are captured only by the preceding Thursday run, not on game day. Week 18 kickoff times in the source are not yet set (all 16 games show Sunday 10:00). A run that finds no eligible player (for example, all remaining games locked, or every lock unverified because schedule evidence is stale) exits 0 with state UNAVAILABLE and per-player reasons only in the journal.
- Review: `venv/bin/flask --app app owner_ops review-lineup-snapshots --season 2026 --week N` is read-only (database SELECTs and a Sleeper matchups GET). It places each player's latest pre-kickoff decision beside Sleeper `players_points` only after the automated nflverse schedule publishes that game's result. Before then, Sleeper zeros are placeholders reported NOT_FINAL; players missing from Sleeper are UNAVAILABLE; conflicting values are CONTRADICTORY; a zero after a final result stays a verified 0.0. Projection differences use only an exact league-scored value and stay PRELIMINARY and INFORMATIONAL_ONLY; a partial-scoring (K/DEF) range is never differenced. The legacy Weekly Score (v1) is shown beside actual points but never differenced (different units). Since `b8b8f6d` the review also shows each snapshot's Weekly Score v2 (NOT_CAPTURED for `snapshot.v1` rows); because an exact v2 value is the league-scored projection, the existing projection difference is its difference, and there is no second review engine. Post-game stat corrections are not tracked.
- Authority: evidence collection only (`decision_effect = NONE`). Capture and review do not change lineup selection, decision confidence, ranking, locks, or the projection action threshold (UNAPPROVED), and submit no Sleeper or other fantasy transaction. The legacy Weekly Score (v1) remains PRELIMINARY selection evidence and is withheld on live `/team`; league-scored projections and the shadow Weekly Score v2 remain PRELIMINARY and INFORMATIONAL_ONLY, and v2 is SHADOW; ECR remains DISPLAY_ONLY on live `/team`. Weeks without snapshots (Week 10 and earlier) cannot be reconstructed as authentic pre-kickoff evidence.
- Week 11 cohort (2026): three runs stored 39 `MY_TEAM_LINEUP_DECISION` rows, 13 players each; they are the only rows in the table. Two manual CLI runs ran at 2026-11-19 08:08:31 and 08:09:05 UTC, and a manual run through the systemd service ran at 13:42:20 UTC. All 39 were captured before their kickoffs (the earliest Week 11 kickoff is 2026-11-20 01:15 UTC), with OPEN locks holding decision authority, FRESH schedule (`schedule.evidence.v1`) and FRESH health evidence, `decision_effect = NONE`, and valid content hashes. Each run recorded 8 START, 1 FLEX, 3 SIT, and 1 MONITOR, and no decision changed between runs; one bye player was not eligible (NO_GAME). Runs differed only in retrieval and provider-board timestamps, and earlier rows were unchanged by later runs. Every row has the legacy Weekly Score UNAVAILABLE (`PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE`); league-scored projections are PRELIMINARY in 33 rows and DEGRADED (partial K/DEF scoring) in 6. All 39 rows are `lineup.forward_validation.snapshot.v1` and predate Weekly Score v2, so they carry no `weekly_score_v2` field (the review reports NOT_CAPTURED). Their exact league-scored values are the quantity Weekly Score v2 now names, so Week 11 can compare 11 exact league-scored projections per run with final points (K/DEF ranges stay uncompared) but cannot test the legacy Weekly Score. Week 11 rows captured from the first scheduled run onward will be `snapshot.v2`. Verified read-only at this reconciliation: the table holds only these 39 rows, all captured before their kickoffs with `decision_effect = NONE`; all 39 content hashes match their snapshot IDs; the 26 rows recorded at 08:09 UTC still have byte-identical payloads; and the append-only trigger and the `decision_effect = 'NONE'` check are present.
- Review state (2026-11-19): `WEEK_11_OUTCOME_REVIEW = PENDING`. At this reconciliation the automated schedule records no result for any of the 13 Week 11 games (first kickoff 2026-11-20 01:15 UTC, last 2026-11-24 01:15 UTC), so the review was not rerun; earlier runs showed all 13 players NOT_FINAL (`GAME_RESULT_NOT_PUBLISHED`), using each player's latest of 3 snapshots. Week 10 has no snapshots. A whole-table fingerprint was unchanged across live `/team` views and review runs.
- Live page: the live HTTPS `/team` served committed code (the serving process started at 08:07:02 UTC, after the last code change, and no tracked code differs from HEAD). At 13:38 UTC it returned HTTP 200 for Week 11 before kickoff (13 open, 1 bye): all 9 lineup slots showed START or FLEX with a status criterion and decision confidence, the 5 contested slots showed "Why this player" reasons, and HOLD did not appear. This satisfies the UXQA-005 VALIDATED gate. Independently re-verified at 18:08:01 UTC on committed `b8b8f6d` (serving process started 17:03:45 UTC; no tracked code differs from HEAD): HTTP 200, Pre-kickoff · 13 open · 1 bye, 8 START and 1 FLEX decision chips each with a status criterion and decision confidence, 5 "Why this player" reasons, and no HOLD. Bench SIT and MONITOR decisions exist in the decision contract but are not rendered as chips. The page does not show whether the current decisions have been captured.
- Remaining limits: no captured game has a final result yet; the legacy Weekly Score still has no approved automated weekly input and stays withheld on live `/team`, while the shadow Weekly Score v2 has no selection authority; the coverage limits above apply; and, as of 2026-11-19, no implementation commit was pushed.

## Current committed Weekly Score v2 shadow boundary (2026-11-19)

State: IMPLEMENTED and VALIDATED at the focused, before/after-contract, live-route, and stored-snapshot boundary. COMMITTED in `b8b8f6d` (8 files), not pushed as of 2026-11-19. Weekly Score v2 is PRELIMINARY / INFORMATIONAL_ONLY / SHADOW and is not authoritative.

- Origin: the 2026-11-19 projection-source feasibility audit found the existing JerryGM league-scored projection to be the best automated, exact-Sleeper-ID, week-scoped candidate, but the legacy Weekly Score (season projection / 17) had to be redefined before any weekly source could be connected. Weekly Score v2 is that redefinition, delivered in shadow mode; the feasibility investigation is complete and is no longer a next step.
- Definition (`weekly-score.v2`, documented in `docs/METRIC_DEFINITIONS.md`): current-week projected fantasy points under the active Sleeper league scoring (`fantasy_points`; higher is better), taken as-is from the existing league-scored projection, i.e. the JerryGM `jgm_baseline` stat line rescored with `league-scored-projection.v1`. Identity is the exact Sleeper ID through the existing JerryGM contract; season and week must match the decision's verified week (a mismatch is BLOCKED); `source_generated_at` is the provider `generatedAt`, kept separate from `retrieved_at`. Owners: `services/lineup_projection.py` (`build_weekly_score_v2`, `weekly_score_v2_basis`), attached by `services/lineup_decision_intelligence.py`, displayed by `templates/team.html`, and reported by `services/lineup_forward_validation.py`.
- Formula boundary: no season projection ÷ 17, no matchup modifier, no second health multiplier, no ECR/rank conversion, no source averaging, and no `players.projected_points`, historical data, or stored snapshot as a current input. COMPLETE scoring gives an exact value; PARTIAL scoring (commonly K and DEF) is DEGRADED with a null exact value and the existing range, never a midpoint; a missing, stale, blocked, or mismatched projection stays null with a manager-facing reason, never zero; a verified provider zero stays 0.0.
- Freshness: `freshness_state` is UNAVAILABLE and the threshold UNAPPROVED, with blocker `JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED`; a provider freshness claim without an explicitly supplied threshold ID stays UNAVAILABLE. No numeric threshold exists or was invented.
- Authority: v2 lives in its own `players[].weekly_score_v2` field with a lineup-level `weekly_score_v2_basis`. It does not select starters, rank or order bench players, change decision confidence, change ECR authority (DISPLAY_ONLY on live `/team`), change kickoff locks, approve an action threshold, or submit transactions; `_value_of()`, `rankable()`, slot and bench ordering, and decision confidence read only the legacy value.
- Legacy Weekly Score (v1): its calculation and selection role are unchanged, and live `/team` still withholds it (`PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE`). Its missing-evidence text now reads "no automated weekly input is approved for lineup selection (the weekly projection shown is informational only)". v1 (weekly value points) and v2 (fantasy points) are never compared, differenced, or substituted.
- Display: each `/team` starting slot shows one "Weekly projection" line (an exact value with "Preliminary · informational only", or a K/DEF range with "Partial scoring · informational only"), replacing the duplicate league-scored projection line; definition, coverage, freshness, and authority are in collapsed diagnostics. The live page at 17:08 UTC (code byte-identical to `b8b8f6d`, committed at 17:57:55 UTC) showed 7 exact values and 2 K/DEF ranges on the 9 slots and "exact 11, range 2 of 14 players" in diagnostics, with all 9 starters' decision, slot, and value identical to the last pre-v2 capture.
- Snapshots and review: see the snapshot boundary above (`snapshot.v2` for new rows, NOT_CAPTURED for `snapshot.v1` rows, K/DEF ranges never differenced, review read-only). Validation: see the Weekly Score v2 entry in the validation section below.
- Remaining blockers before any v2 selection authority: an approved JerryGM freshness threshold; multi-week forward-validation evidence; an explicit authority decision; a policy for K/DEF ranges versus exact values; and permitted-use verification for provider-derived selection use.
- Cosmetic note (not a defect, not fixed): the reworded legacy missing-evidence text renders nested parentheses in the "Missing evidence" list.

## Current committed W1-W5 Waiver and FAAB decision boundary (2026-11-20)

State: IMPLEMENTED and VALIDATED at the focused-test, live read-only route, and stored-history boundary. COMMITTED in `79be2ff` (17 files) on 2026-11-20. Recommendation-only: the roster decision carries `decision_effect = RECOMMENDATION_ONLY` and `submits_transactions = False`, and league FAAB market evidence is `INFORMATIONAL_ONLY`. No Sleeper write, claim, drop, or bid is submitted.

- W1 current-week decision support (`waiver.roster_decision.v1`, `services/waiver_roster_decision.py`): verified available players are compared only with same-position players on the manager's own Sleeper roster and lineup. Current-week ordering uses fresh FantasyPros PPR positional consensus (ECR) via DynastyProcess: lower is better, ranks are ordinal and never converted to points or compared across positions, stale ECR blocks, and an unranked player is never treated as worse. Byes and kickoff locks come from the automated schedule evidence; locked players are not compared or released. IR and taxi players never count as active depth (`services/team_needs.py`). Each move is ADD + DROP, ADD — OPEN ROSTER SPOT, or MONITOR with its exact reason (for example NO SAFE DROP VERIFIED, CLOSE ROS CALL, HEALTH DESIGNATION, or CROSS-POSITION CHOICE REQUIRED). A position whose starters rank ahead of every ranked available player, or with no verified, healthy, unlocked available player with a current game, is HOLD. The verdict is ACT, OPTIONAL, NO WAIVER MOVE RECOMMENDED (PASS; "Save FAAB." only when rest-of-season depth and its materiality were also evaluated), INSUFFICIENT EVIDENCE, or BLOCKED.
- W2 candidate universe and ownership safety (`waiver.candidate_universe.v1`, `services/waiver_candidate_universe.py`): in LIVE mode `/waivers` builds candidates from Sleeper's current player catalog by exact Sleeper player ID, minus every player on any league roster (including reserve and taxi). Unavailable, incomplete, stale, or duplicate ownership blocks publication. Every catalog entry is accounted for (malformed, unsupported position, or a classified stage such as rostered or candidate), and candidate counts reconcile by position. Local preseason rows are lineage diagnostics only, never a discovery source. `/gm` still uses the earlier UX.3 waiver pool (`waiver_pool_with_evidence`, unchanged by `79be2ff`), so the two routes no longer share one candidate set; both were re-verified to publish no rostered player (see the validation section).
- W3 safe ADD + DROP and post-move protection (`waiver.ros_value.v1`): a release must be at the same position and supported by fresh rest-of-season consensus for both players (seven-day source-age limit in `docs/DATA_FRESHNESS_POLICY.md`). The best bench backup for each unlocked Questionable or Doubtful starter is protected, a player whose game is locked or whose lock is unverified is never released, and one player is never the drop for two moves. The post-move lineup check must show that every starting slot, including FLEX, can still be filled this week and for the rest of the season, both on its own and after the higher-priority moves.
- W4 rest-of-season materiality and replacement context (`waiver.ros_materiality.v1`, `waiver.replacement_context.v1`): an ordinal rest-of-season edge supports a release only as CLEAR ROS EDGE, when the candidate's worst published expert rank is better than the roster player's best; overlapping ranges are CLOSE ROS CALL and stay MONITOR or HOLD. Replacement context counts healthy, addable, same-position available players whose fresh expert range reaches a player's range (STRONG: two or more; LIMITED: one; SCARCE: none; otherwise UNVERIFIED) and is informational. Neither produces points, percentages, a value score, or a FAAB amount.
- W5 league FAAB market evidence (`waiver.faab_market.v1`, `services/waiver_market_evidence.py`): a pure, descriptive reading of stored Sleeper transaction weeks (`GET /v1/league/{league_id}/transactions/{week}`) written only by the explicit command `python refresh_sleeper_transactions.py` (`services/sleeper_snapshots.py`; tables `sleeper_api_snapshots` and `sleeper_sync_runs`). It shows completed and failed claims with failure reasons; contested and uncontested claims, grouped only by the same player, week, and waiver run; observed bid ranges and medians with N for the exact player, the same position, and league-wide only when a position has no completed sample; and current team budgets (league budget minus each roster's `waiver_budget_used`). Only weeks proven closed or final by later-week Sleeper transactions count, the open current week never counts, and a failed latest refresh makes coverage PARTIAL. Viewing `/waivers` reads stored history only; it never fetches or stores transactions.
- Manager-facing result: Waivers explains the supported candidate and any supported drop, current-week and rest-of-season context, whether the rest-of-season edge is materially separated, replacement depth, move safety, and actual league waiver-market history (completed and failed claims, contested context, and team budgets where supported). "Value-based bid unavailable" and "Advanced FAAB valuation is not yet supported." stay visible.
- Unsupported, not claimed: opportunity- or role-driven ranking; current role and opportunity trend (added as informational evidence in W6, `4212a92`) and expected duration of value (still unverified); an integrated player-value score; winning-bid estimates, recommended or maximum bids, winning probability, and player-value-to-FAAB conversion; cross-position drops; automatic waiver, drop, or bid submission; waiver decision snapshots; production readiness; full PostgreSQL parity; and recovery readiness.
- Owners: `owner_operations.py` (`/waivers` wiring), `services/waiver_roster_decision.py`, `services/waiver_candidate_universe.py`, `services/waiver_market_evidence.py`, `services/sleeper_snapshots.py`, `services/dynastyprocess_rankings.py` (current-week and rest-of-season consensus with expert ranges), `services/team_needs.py`, `sleeper_hub.py` (uses the shared snapshot store), `refresh_sleeper_transactions.py`, `templates/waivers.html`, and `templates/_waiver_trust_panel.html`. Tests: `tests/test_waiver_roster_decision.py` (84), `tests/test_waiver_candidate_universe.py` (27), `tests/test_waiver_market_evidence.py` (63), `tests/test_waiver_availability.py` (237), `tests/test_dynastyprocess_rankings.py` (41), and `tests/test_snap_share_publication.py` (12).
- Stored history (verified read-only on 2026-11-20): `sleeper_api_snapshots` holds 11 transaction weeks for 2026 (Weeks 1-11, 192 transactions), retrieved 2026-11-20 12:22:10-12:22:13 UTC by refresh run #5 (scope `transaction_history`, `success`; run #4 also succeeded). The market reads through Week 10 because Week 11 is the open week. Run `python refresh_sleeper_transactions.py` after each weekly waiver run so the newly closed week is included.
- Defect status: UXQA-001 (rostered players in waiver recommendations) is CLOSED (2026-11-20); its closure evidence is recorded in `docs/CURRENT_DEFECTS.md`. UXQA-005 and every other defect keep their evidence-supported statuses.
- Validation: see the W1-W5 entries in the validation section below.

## Current committed W6 Waiver role and opportunity evidence boundary (2026-11-21)

State: IMPLEMENTED and VALIDATED at the focused-test, mutation, live read-only route, and stored-evidence boundary. COMMITTED in `4212a92` (8 files) on 2026-11-21. PRELIMINARY and INFORMATIONAL_ONLY: every role result carries `recommendation_impact = INFORMATIONAL_ONLY` and `decision_effect = NONE` and is attached only after every waiver decision is final. No Sleeper write, claim, drop, or bid is submitted.

- Observed role and opportunity (`waiver.opportunity_observation.v1`, `services/waiver_role_evidence.py`): each completed game is read from stored nflverse rows, offensive snap share from `snap_counts` (`snap_share_evidence`) and targets and carries from `stats_player_week` (`player_opportunity_evidence`). Metrics by position: QB snap share and carries; RB snap share, carries, and targets; WR and TE snap share and targets. Players link only through the route's existing exact GSIS identity (`opportunity_identity_state = RESOLVED`); names never match, an unresolved identity shows UNAVAILABLE, and an ambiguous or conflicting one is CONTRADICTORY. A game counts only when the automated schedule marks it final; a stored game that is not final is excluded and disclosed. A missing row is never zero, a bye is shown as a bye (never a zero or a decline), and conflicting duplicate rows are CONTRADICTORY, never averaged.
- Direction and persistence (`waiver.opportunity_trend.v1`, `waiver.role_persistence.v1`): over a player's latest supported completed games (up to 3), each metric rises, falls, moves both ways, or stays unchanged, giving DIRECTION UP, DIRECTION DOWN, MIXED (both directions, or metrics disagree), FLAT, or CURRENT ROLE ONLY (one supported game). Direction is the sign of change, not its size; no magnitude threshold exists. OBSERVED PERSISTENCE (PERSISTED ACROSS OBSERVED GAMES or DURATION UNVERIFIED) looks back only; FUTURE DURATION is always UNVERIFIED, and the reserved TEMPORARY_ROLE_RISK state is never produced. Full-PPR production for the same games is shown beside the role and never blended into it. K and DEF are NOT APPLICABLE.
- Currency: role evidence is CURRENT only when each source covers every completed game through the latest completed week and is FRESH or AGING under its threshold (`snap_share.evidence.v1` and `opportunity.evidence.v1`, both 86,400 seconds in the live environment); otherwise the player's stored games are HISTORICAL ONLY and no current role or trend is claimed. See `docs/DATA_FRESHNESS_POLICY.md` and `docs/METRIC_DEFINITIONS.md`.
- Manager-facing result: move cards, position cards, and the player lookup (current candidates and the manager's roster; other teams' players are NOT EVALUATED) show ROLE / OPPORTUNITY with per-game values, byes, and gaps, plus OBSERVED PERSISTENCE and FUTURE DURATION; a ROLE EVIDENCE coverage line counts current evidence by position against the published candidate population; and What Changed lists current supported role changes for the comparison candidates. The page labels all of it informational only.
- Read-only route and manual refresh: GET `/waivers` adds exactly 5 parameterized SELECTs (2 batched exact-ID reads, 2 coverage reads, and 1 schedule read) and no write, and it never fetches nflverse data. Only the explicit command `python refresh_opportunity_evidence.py` publishes completed weeks, through the existing nflverse importers and atomic publishers; no refresh automation exists.
- Unchanged by W6: current-week ECR ordering, availability and ownership, ADD/DROP, safe-drop rules, rest-of-season comparison and materiality, replacement context, confidence, W5 FAAB market evidence, FAAB amounts, and transaction behavior.
- Unsupported, not claimed: Opportunity Score, Role Score, Upside Score, Breakout, Regression, Buy Low / Sell High, next-week workload forecasts, future role-duration prediction, an integrated player-value score, role- or opportunity-driven waiver ranking, recommended, expected winning, or maximum bids, winning probability, automatic transactions, and route participation, target share, rush share, red-zone usage, and air yards (not in the stored sources).
- Owners: `services/waiver_role_evidence.py`, `services/player_opportunity_reader.py` (`read_opportunity_observations`), `services/snap_share_reader.py` (`read_snap_share_observations`), `owner_operations.py` (`/waivers` wiring, `read_season_game_results`, and `waiver_role_for`), `templates/waivers.html`, and `refresh_opportunity_evidence.py`. Tests: `tests/test_waiver_role_evidence.py` (54) and 5 W6 route tests in `tests/test_waiver_availability.py` (now 242).
- Stored evidence (verified read-only 2026-11-21 00:38 UTC): `player_opportunity_evidence` holds 3,358 rows and `snap_share_evidence` 13,978 rows for 2026, Weeks 1-10, all FRESH, COMPLETE, and PUBLISHED, retrieved 2026-11-20 18:34:07 and 18:34:28 UTC from nflverse releases recorded at 17:51:39 and 12:01:45 UTC. Before that refresh the stored evidence ended at Week 4 (retrieved 2026-10-06). The completed-week boundary is Week 10 (Week 11 had 1 of 13 games final), and both sources were CURRENT. Without another refresh they become HISTORICAL ONLY after 2026-11-21 18:34 UTC, and again once Week 11 is final.
- Coverage (live, 2026-11-20 23:02 UTC): 381 of 715 skill-position candidates (761 published) had current role evidence; 83 were historical only, 180 had no stored evidence, 71 had no resolved GSIS identity, none were contradictory or blocked, and 46 K and DEF were not applicable.
- Validation: see the W6 entries in the validation section below.

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

- W6 role and opportunity validation (2026-11-20, on code byte-identical by SHA-256 to the 8 files committed in `4212a92`): the six W1-W5 focused files plus `tests/test_waiver_role_evidence.py` passed 523 of 523 (41 + 12 + 242 + 27 + 63 + 84 + 54). Twelve deliberate mutations (a missing value or a bye becoming zero, an incomplete or stale pipeline claiming a current role, a waiver reorder, an ADD/DROP change, a confidence change, a FAAB number, a non-exact identity join, one observation claiming a direction, observed persistence becoming future duration, and a production-based breakout label) were each caught, and the originals were restored and verified by SHA-256. Seven changed or new Python files compiled, `templates/waivers.html` parsed in Jinja, and `git diff --check` passed; at commit, `git diff --cached --check` passed and the 8 staged files matched the validated hashes. Nine affected opportunity and snap-share test files gave 163 passed and 6 failed, and the 23-file related set gave 365 passed, 11 failed, and 1 collection error; both failure sets reproduce identically at clean `38cd314` and are pre-existing and outside this boundary. The 6 are `tests/test_player_opportunity_reader.py::test_adapter_delegates_comparison_and_preserves_reader_blockers` and `::test_reader_freshness_fails_closed_for_missing_or_invalid_inputs`, `tests/test_player_opportunity_calculation.py::test_publication_contract_never_invents_a_threshold_default`, `tests/test_opportunity_consumer_contract.py::test_templates_include_opportunity_evidence_without_conclusions`, and the 2 `tests/test_team_opportunity_integration.py` template-source assertions recorded below.
- W6 live read-only route checks (2026-11-20 23:02-23:14 UTC, on code byte-identical to `4212a92`; Flask test client against the app database in a read-only PostgreSQL session, with live Sleeper reads recorded and then replayed): 11 `/waivers` requests returned HTTP 200 (the default view and lookups for move, monitor, roster, K, DEF, other-team, selected-comparison, historical-only, no-evidence, and unresolved-identity cases). Against clean `38cd314` with the same recorded inputs and a frozen clock, 8 of 8 requests were identical outside W6 (36 context keys, HTML with the W6 elements removed, database statements, HTTP calls, and 0 commits); W6 added exactly 5 SELECTs and no write. The only non-SELECT statement on both trees is the pre-existing app-wide `CREATE TABLE IF NOT EXISTS application_state`. Both role sources were CURRENT, COMPLETE, and FRESH through Week 10.
- W1-W5 Waivers validation (2026-11-20, on the code committed in `79be2ff`): the six-file focused set (`tests/test_dynastyprocess_rankings.py`, `tests/test_snap_share_publication.py`, `tests/test_waiver_availability.py`, `tests/test_waiver_candidate_universe.py`, `tests/test_waiver_market_evidence.py`, and `tests/test_waiver_roster_decision.py`) passed 464 of 464. Twenty-three directly related test files (Team Needs and My Team lineup consumers, DynastyProcess identity, decision ranking, F3 opportunity, active-week route, opportunity-consumer, and UX.1.7 contracts) gave 365 passed, 11 failed, and 1 collection error, and all 12 reproduce identically at the previous HEAD `b5b6cc6` in a clean temporary worktree: the 2 `tests/test_lineup_evidence.py` failures, `tests/test_ux2_1b_presentation.py::test_print_hides_navigation_and_closed_diagnostics`, `tests/test_opportunity_consumer_contract.py::test_templates_include_opportunity_evidence_without_conclusions`, and `tests/test_ux_1_7_completion.py::test_dashboard_truth` (all recorded below), 6 `tests/test_active_week_degraded_routes.py` route tests that fail on URL building, and the `tests/test_ux2_team_needs.py` collection error (`apply_waiver_ranking` does not exist). They are pre-existing and outside this boundary. Fifteen changed or new Python files compiled; `templates/waivers.html`, `templates/_waiver_trust_panel.html`, `templates/_opportunity_evidence.html`, and `templates/sleeper_hub.html` parsed in Jinja; `git diff --check` and `git diff --cached --check` passed; and the 17 staged files were byte-identical to the validated working files. During W5 development, 10 deliberate mutations of the market and refresh code were each detected by the tests (recorded then; not rerun at this reconciliation).
- W1-W5 live read-only route checks (2026-11-20 17:41-17:42 UTC, committed `79be2ff` with no tracked change; Flask test client against the app database in a read-only PostgreSQL session, with live Sleeper reads): `/waivers` returned HTTP 200 with the candidate universe COMPLETE and reconciled, 761 published candidates, and none on any of the 10 league rosters (141 rostered IDs, including reserve and taxi); moves TE "MONITOR — CLOSE ROS CALL" and K "MONITOR — NO SAFE DROP VERIFIED", verdict OPTIONAL, and RB depth note CLOSE ROS CALL; `RECOMMENDATION_ONLY` with `submits_transactions = False`; league market AVAILABLE through Week 10 and `INFORMATIONAL_ONLY`, with 2 LEAGUE MARKET lines, no bid-like phrase, and both FAAB disclosures visible. `/gm` returned HTTP 200 with Sleeper ownership FRESH and COMPLETE, 20 published and 5 shown waiver candidates, and none rostered. Both views made only GET requests, requested no transaction history, and wrote nothing to the database (the only non-SELECT statement issued is the pre-existing app-wide `season_sandbox` `CREATE TABLE IF NOT EXISTS`).
- Pre-kickoff snapshot validation (2026-11-19, on the code committed in `95acb9c`): the six-file focused set (`tests/test_lineup_forward_validation.py`, `tests/test_pre_decision_snapshots.py`, `tests/test_lineup_projection_foundation.py`, `tests/test_lineup_decision_intelligence.py`, `tests/test_lineup_week_lock_state.py`, `tests/test_ux5_lineup_route_contract.py`) passed 182 of 182. Seven further `/team` route test files (`tests/test_ux2_team_route_matrix.py`, `tests/test_team_opportunity_integration.py`, `tests/test_lineup_evidence.py`, `tests/test_team_health_routes.py`, `tests/test_ux2_health_route_freshness.py`, `tests/test_ux2_team_accuracy_route.py`, `tests/test_ux1_dashboard_truth_completion.py`) gave 117 passed and 4 failed. All 4 failures reproduce at clean HEAD `1f641d1`: the 2 `tests/test_lineup_evidence.py` failures recorded below, and 2 `tests/test_team_opportunity_integration.py` template-source assertions (`test_team_template_does_not_default_missing_snap_values_to_zero` and `test_team_route_and_template_preserve_informational_what_changed_boundary`) that expect the strings `snap_value is not none` and `NON_ADJACENT`, which `dda3dbe` removed from `templates/team.html`. These are pre-existing test-expectation drift outside this boundary, not a recorded defect. The four changed implementation files and the new test file compiled, and `git diff --check` passed.
- Capture automation validation (2026-11-19, committed in `298c83b`): `tests/test_lineup_snapshot_capture_units.py`, `tests/test_lineup_forward_validation.py`, `tests/test_pre_decision_snapshots.py`, and `tests/test_ux5_lineup_route_contract.py` passed 45 of 45. `systemd-analyze --user verify` reported no diagnostics, and `systemd-analyze calendar` accepted all five timer expressions. The changed test files compiled; `git diff --check` and `git diff --cached --check` passed.
- Weekly Score v2 validation (2026-11-19, committed in `b8b8f6d`): `tests/test_jerrygm_projections.py`, `tests/test_lineup_projection_foundation.py`, `tests/test_lineup_decision_intelligence.py`, and `tests/test_lineup_forward_validation.py` passed 169 of 169 (151 at the previous HEAD; 18 new tests), on the working tree before commit and again in the commit review. The six changed Python files compiled; `git diff --check` and `git diff --cached --check` passed; the staged diff was byte-identical to the reviewed diff, and the exact eight-file commit scope contained no unrelated file. A 12-scenario before/after comparison against the previous HEAD produced byte-identical lineup contracts (only the reworded legacy blocker text differs), and real, inverted, and absent v2 values give identical selection and decision confidence. Across 13 affected lineup, projection, and `/team` test files, 334 passed and 7 failed; the same 7 fail with identical messages at the previous HEAD `298c83b`: the 2 `tests/test_lineup_evidence.py` and 2 `tests/test_team_opportunity_integration.py` failures already recorded in this section, `tests/test_opportunity_consumer_contract.py::test_templates_include_opportunity_evidence_without_conclusions`, `tests/test_ux_1_7_completion.py::test_dashboard_truth`, and `tests/test_ux2_1b_presentation.py::test_print_hides_navigation_and_closed_diagnostics`. They are pre-existing and outside this boundary.
- Historical focused validation on the 2026-11-16 working tree: 384 passed and 2 failed across 16 lineup, lock, schedule, JerryGM, and My Team route test files. The 2 failures (`tests/test_lineup_evidence.py::test_identity_fix_preserves_current_lineup_fields` and `::test_team_opportunity_changes_receives_player_specific_identity`) reproduce identically at clean HEAD `ddd329d`; that identity-route fixture does not supply `WEEK_AUTHORITY_ACQUIRER`. `tests/test_ux2_team_needs.py` fails collection at HEAD because `apply_waiver_ranking` does not exist. Both are pre-existing test defects outside this boundary. The same 16-file set reproduced 384 passed and the same 2 failures on committed `a306f3a` in a clean worktree, and `tests/test_schedule_bye_source_contract.py` passed (39) on `695ff74` alone.
- All 16 changed Python files compiled. `git diff --check` and `git diff --cached --check` passed.
- Historical live `/team` check (2026-11-16; HTTPS, served by code reloaded at 04:47 UTC) returned HTTP 200: Week 10, Week complete, 14 LOCKED from the automated schedule, START/FLEX decisions, no HOLD, league-scored projections labelled PRELIMINARY, and consensus labelled context only. The only remaining Week 10 game (LAC at BAL) has no rostered player. No live pre-kickoff open-window render had been observed at that time; the 2026-11-19 pre-kickoff render on committed code is recorded under the snapshot boundary above.
- Canonical sources are reconciled to implementation HEAD `4212a92` (W6 Waivers role and opportunity evidence) as of 2026-11-21, on top of the W1-W5 Waivers (`79be2ff`) and My Team commits recorded above. Bundle and canonical-sync results come from the continuity run, not from this text.

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
- Superseded (2026-11-20): W1-W5 (`79be2ff`) delivered roster-relative move decisions, supported same-position drops with post-move safety and rest-of-season materiality, replacement context, and descriptive league FAAB market history. `/waivers` now uses the W2 Sleeper-catalog candidate universe, while `/gm` keeps the pool described here. Candidate-level observed role and opportunity trend were added as informational evidence in W6 (`4212a92`, 2026-11-21); forward-looking opportunity duration and value-based FAAB bidding remain unsupported. UXQA-001 is CLOSED (2026-11-20). See the current committed W1-W5 and W6 boundaries.

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
- A.13 Opportunity Metrics Engine: evidence foundation implemented; authoritative ingestion remains deferred. W6 (`4212a92`) shows stored completed-game role evidence on Waivers as informational evidence, refreshed only by the manual `python refresh_opportunity_evidence.py`; automating that refresh is the next milestone
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
- Phase 3: add trusted player opportunity data and a multi-week What Changed engine. Phase 4: add market-aware buy/low, sell/high, breakout, and regression intelligence only after market-value and opportunity contracts exist. Phase 5: persist immutable pre-decision snapshots for post-week Process versus Results and narrative manager learning (My Team lineup-decision snapshots persist and are captured on a schedule as of 2026-11-19, in `95acb9c` and `298c83b`; Process versus Results is not implemented). Phase 6: add rest-of-season, playoff, and championship scenario planning only after trusted inputs exist.
- Opportunity trends, buy/sell labels, post-week grades, Manager Report Card grades, and playoff strategy are blocked by missing automated source, freshness, identifier, historical-baseline, metric-authority, or decision-time snapshot evidence. Do not infer them from box scores or stale CSV inputs.

####### Decision-first priority override

- Priority 1: make weekly START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, and TRADE AWAY decisions trustworthy with current, league-specific, explained evidence. This outranks navigation work, dashboards, new models, and season strategy.
- Priority 2: establish automated player opportunity and role evidence, then build What Changed from documented multi-week baselines. Breakout, regression, Buy Low, and Sell High labels remain blocked until source, identifier, history, freshness, metric authority, and market evidence are verified.
- Priority 3: rebuild Dashboard as the Decision Center, summarizing Must Act, Start/Sit, Waivers, Trades, Opportunity Alerts, Risk Alerts, and No Action Needed while linking to owning pages instead of duplicating their engines.
- Priority 4: persist immutable pre-decision snapshots before Process versus Results evaluation; as of 2026-11-19, My Team lineup-decision snapshots persist and are captured on a schedule (`95acb9c`, `298c83b`), waiver and trade decisions are not captured, and Process versus Results is not implemented. Priority 5: provide narrative manager learning before any Manager Report Card grade. Rest-of-season and playoff strategy follow only after these decision foundations are trusted.

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

**Automate W6 opportunity-evidence refresh so completed-game role evidence stays current without manual intervention while preserving exact identity, completed-game boundaries, freshness, fail-closed behavior, INFORMATIONAL_ONLY authority, and read-only Waivers.**

W6 (`4212a92`) put observed completed-game role and opportunity evidence on Waivers. Its dominant remaining weakness is operational: the evidence is current only while both stored nflverse sources cover every completed game and were retrieved within 24 hours (`opportunity.evidence.v1`, `snap_share.evidence.v1`), and the only refresh is the manual `python refresh_opportunity_evidence.py`. Before W6 the stored evidence had stopped at Week 4 (last retrieved 2026-10-06) while Weeks 5-10 were complete, so no candidate had current role evidence. After the 2026-11-20 18:34 UTC refresh, the evidence expires at 2026-11-21 18:34 UTC and again whenever a new week completes. The batch should run the existing refresh on a schedule tied to completed games and the 24-hour limit (the repository's systemd pattern is `scheduler/nflverse-schedule-refresh.timer`), record each run's per-source outcome, and keep a failed run from making old evidence current.

Opportunity materiality calibration, future role-duration evidence, and W7 integrated waiver player value all depend on role evidence that is trustworthy only while current, and none has a verified source contract yet; each would lose value while the evidence expires daily without manual action.

This milestone must not change W1-W6 ordering, move states, drop safety, materiality, replacement context, FAAB market evidence, confidence, or transaction behavior; must not add a page-time fetch or write to `/waivers`; must not relax exact GSIS identity, the completed-game boundary, or the freshness thresholds; and keeps opportunity-driven ranking, role scores, workload forecasts, future-duration claims, bid estimation, and automatic transactions unsupported.

Operational follow-ups carried forward (not the milestone; not checked by this reconciliation):
1. Until refresh is automated, run `python refresh_opportunity_evidence.py` after each week's games are final and at least every 24 hours while current role evidence is needed; the Waivers page never fetches it itself.
2. After final supported Week 11 results exist (the last game is Monday Night Football on Nov 23 Pacific), execute and record the read-only `owner_ops review-lineup-snapshots --season 2026 --week 11` outcome review without changing selection, confidence, thresholds, or projections. Sleeper pre-final zeros are not final zeros.
3. Confirm the scheduled lineup snapshot captures in the journal and database: Thu Nov 19 13:00, Sun Nov 22 09:00, and Mon Nov 23 13:00 Pacific, and whether the Wed Nov 25 15:00 Pacific run saw Week 12. Continue accumulating `snapshot.v2` evidence before proposing any Weekly Score freshness threshold or authority change; no model-quality judgment is made from one week.
4. After each weekly waiver run, run `python refresh_sleeper_transactions.py` so league FAAB market history includes the newly closed week; the Waivers page never fetches transactions itself.

UX.8 retains its recorded in-progress boundary. UXQA-001 is CLOSED (2026-11-20; closure evidence in `docs/CURRENT_DEFECTS.md`); every other defect keeps its evidence-supported status, and UXQA-005 is VALIDATED, not CLOSED. Production readiness, full PostgreSQL parity, and recovery readiness remain unclaimed.
