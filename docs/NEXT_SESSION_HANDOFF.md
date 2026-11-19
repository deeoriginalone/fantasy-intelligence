##### Fantasy Intelligence Session Handoff

## Fantasy Intelligence 2.0 Direction

The product is a personal, league-specific fantasy decision assistant. Keep the six primary destinations: Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. The six-page architecture is an approved target direction, not completed navigation work. Primary navigation has not yet been simplified; the Command Center target is not complete; no redirect, route archive, or route removal has been completed. Supporting routes remain operational. `MERGE`, `REDIRECT`, and `ARCHIVE` are future classifications.

These pending plans include navigation simplification, route merging, new redirects, and archive actions. Decision Journal, Process vs Results, and Season Planning are planned priorities, not delivered capabilities.

###### Evidence-first handoff rule

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Matchup Signal remains context-only where its specific metric contract does not support recommendation use; Matchup Rank remains subject to its own contract.

Apply this model across Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. Preserve each page's specific identity, ownership, eligibility, contradiction, corruption, and transaction-safety protections.

###### Current My Team handoff boundary

The committed `/team` template orders My Team header, Your Lineup, Health & Availability, Biggest Decisions, Why These Decisions, What Could Change, Supporting Roster Details, and collapsed Data/Model Diagnostics. Current Sleeper Lineup, Bench Priority, and Team Needs remain supporting details. This supersedes the earlier hero-first presentation description. Behavioral and rendered-page evidence for the committed lineup code is recorded under the current committed Starting Lineup Decision Intelligence and schedule-lock boundary below (`695ff74`, `a306f3a`). Committed pre-kickoff lineup decision snapshot capture, its scheduled automation, and the read-only post-week review (2026-11-19) are recorded under the current committed pre-kickoff lineup decision snapshot boundary below. The committed shadow Weekly Score v2 (`b8b8f6d`, 2026-11-19), shown on each starting slot as an informational "Weekly projection", is recorded under the current committed Weekly Score v2 shadow boundary below.

## Navigation Reconciliation Target

Primary navigation is planned as Command Center, My Team, Waivers, Trades, Survivor, NFL Intelligence, and What Changed. Command Center will summarize League Overview, Must Act, Start/Sit Summary, Waiver Priorities, Trade Watch, Survivor Status, NFL Intelligence Highlights, What Changed, and Risk Alerts without duplicating owning page engines. League Overview will merge into Command Center.

NFL Intelligence will be the single NFL-wide intelligence destination, absorbing Market Intelligence alongside Top Picks, Top Risk Games, Game Predictions, Weather, Injury Context, Insights, Blockers, and Diagnostics. Draft Board and Mock Draft remain preserved for Season Planning. Sleeper Hub, Draft Day Readiness, Draft Intelligence & Learning Center, Imports, Readiness, and Diagnostics are planned Admin destinations.

The intended disposition is: Command Center PRIMARY; League Overview MERGE; My Team PRIMARY; Waivers PRIMARY; Trades PRIMARY; Survivor PRIMARY; NFL Intelligence PRIMARY; Market Intelligence MERGE; What Changed PRIMARY / SECONDARY; Draft Board KEEP; Mock Draft KEEP; and the listed Sleeper, readiness, import, and diagnostic destinations ADMIN. This remains planned navigation work and does not change the current milestone, validation evidence, defect statuses, or recovery claims.

Recovery Ready is a planned mandatory standard, not a completed checkpoint. Recovery Ready planned work remains pending. It will require a runnable checkpoint, documented startup verification, database backup, canonical-memory snapshot, Notebook/reference export, and six-core-page verification. Preserve existing data and integrations.

###### Operational verdict

The Data Integrity sequence remains complete through A.10, and UX.1 remains complete at its recorded boundary.

UX.2 My Team Accuracy, Explainability, and League-Settings Validation is validated at its focused and controlled active-route boundary. Its route, league-settings, Full-PPR Team Needs, Team Health, Team Accuracy, recommendation evidence, priority action, unavailable-matchup, and collapsed lineage behavior are preserved.

UX.2.1C presentation and disclosure repairs are recorded; owner acceptance remains pending per `docs/CURRENT_DEFECTS.md`. UX.3 is validated at its supported, read-only waiver-publication boundary. UX.4.1 through UX.4.12 are validated at focused implementation, controlled-browser, and live nine-partner dropdown boundaries. The shared action-first visual system is now applied across Lineup, My Team, Waivers, and Trades. UX.5 has the formalized implementation and evidence boundary; formal definition-of-done review remains pending.

My Team forward validation (2026-11-19): migration 014 is applied, and committed code captures pre-kickoff lineup decision snapshots on a Pacific-time systemd timer before the Thursday, Sunday, and Monday kickoff windows and reviews them read-only against final Sleeper points. The shadow Weekly Score v2 (`b8b8f6d`) adds a current-week league-scored projection that is PRELIMINARY, INFORMATIONAL_ONLY, and SHADOW and never selects players or changes confidence; snapshots captured from the first scheduled run onward carry it (`lineup.forward_validation.snapshot.v2`). The Week 11 cohort (39 `snapshot.v1` rows) is stored and awaiting final results; the first scheduled capture is pending; decision-quality validation remains in progress (see the Next milestone). UXQA-005 is VALIDATED, not CLOSED.

###### Historical evidence-layer foundation (validated 2026-09-15)
- Opportunity Evidence, What Changed, Opportunity Classification, Market Value, Market Signal, Buy/Sell Candidate, and Trade Opportunity contracts are implemented as pure fail-closed evidence layers.
- Dashboard Decision Center summarizes existing evidence into the required informational panels without generating recommendations or priority.
- Dashboard, `/team`, `/waivers`, and `/trades` retain their existing decision payloads. No lineup, waiver, trade, matchup, ranking, confidence, Weekly Score, or transaction behavior consumes these layers.
- Focused validation passed 16 tests; compilation and both whitespace checks passed. Fresh route checks returned HTTP 200 at desktop and 390px with default evidence fail-closed.
- No live market or candidate source is configured. Buy Low, Sell High, Breakout, Regression, and trade-action recommendations remain deferred.

###### Historical UX.5 validation boundary
- Weekly Lineup Intelligence emits explicit `START`, `FLEX`, `MONITOR`, and bench `SIT` decisions; `HOLD` and `SWAP` are not rendered.
- Bench Order is deterministic and labeled. Explanations include reason, confidence, opponent, health, weekly value, and metric definitions.
- Missing weekly or matchup evidence is visibly `Unavailable`, not zero or neutral. The page remains read-only.
- Focused UX.5 service/template/route-contract validation passed 10 tests; related integrity and UX.2 route validation passed 27 tests; compilation, diagnostics, and whitespace checks passed.
- Live `/lineup` returned HTTP 200 and passed desktop and 390px mobile inspection with no primary horizontal overflow. Rendered text contained Start/Sit Decisions, Bench Order, START/FLEX/MONITOR/SIT, and Unavailable, with no HOLD.
- The action-first redesign now leads with a weekly verdict and manager action, followed by decision cards, risks, formation slots, bench priority, unavailable change history, collapsed metric explanations, and bottom-only data quality/lineage diagnostics.
- Formal UX.5 definition-of-done review and canonical continuity validation remain outstanding.

###### Historical cross-page presentation boundary
- My Team: 34 focused tests; live HTTP 200 desktop/390px verification; priority action remains before roster evidence and diagnostics.
- Waivers: 47 focused tests; live HTTP 200 desktop/390px verification; verdict, Priority Adds, FAAB guidance, blocked evidence, and availability lineage are visible.
- Trades: 27 focused tests; live HTTP 200 desktop/390px verification; verdict, partner control, roster fit, package cards, feasibility, and collapsed integrity/identity evidence are visible.
- No transaction, ownership, eligibility, health, matchup, FAAB, feasibility, or database logic changed in these visual batches.

###### Historical UX.3 foundation boundary
- Stable Sleeper player IDs, complete current roster ownership, and the supported player pool drive read-only waiver publication. Availability is explicitly derived from current Sleeper rosters and the supported player pool, not provider-declared addability or transaction history.
- Ownership freshness uses successful `retrieved_at` under `integrity.roster.v1`; source-record time is unavailable when not supplied and remains distinct from retrieval time.
- The focused UX.3 suite passes 78 tests; Python compilation and staged/working-tree whitespace validation pass.
- Flask test-client and rendered-route checks return HTTP 200 for `/waivers` and `/gm`, with FRESH/COMPLETE ownership and DERIVED/FRESH/COMPLETE availability. `/waivers` publishes nine stable IDs, `/gm` publishes its five-candidate prefix, and no published ID intersects active roster ownership.
- Supported render surfaces ownership source, freshness, completeness, availability source/authority, unavailable optional candidate values, and collapsed identity diagnostics. Unsupported inputs remain fail-closed.
- UXQA-001 is VALIDATED, not CLOSED.

###### Preserved UX.4 boundary (historical validation)
- Trade Center integrity uses shared roster, injury, matchup, and projection freshness domains. It publishes only when all required evidence is complete and FRESH; AGING is visible as DEGRADED; stale, expired, unknown, unavailable, incomplete, or contradictory evidence blocks with domain-specific reasons.
- `migrations/011_trade_evidence_freshness.sql` is applied. Writer-owned matchup/projection retrieval times are populated only by successful imports, and canonical team aliases plus deterministic suffix-aware joins complete supported current-partner coverage.
- A TESTING-only in-memory scenario harness renders READY, READY-empty, DEGRADED, BLOCKED, unsupported partner fit, and identity ambiguity through the live template without database writes, source timestamp changes, or external calls. Desktop and 390px checks passed; diagnostics are collapsed by default.
- The normal `/trades` app was restarted and the visible selector exercised all nine opponents. Every selection remained selected, matched the displayed partner, rendered READY with separated package types and explicit `Feasibility: UNAVAILABLE`, and omitted acceptance-like verdicts. Collapsed identity lineage exposes stable and local identity fields when supplied.
- Focused UX.4 validation passed 90 tests; compilation and both whitespace checks passed. Do not claim transaction acceptance, negotiation, rest-of-season impact, production readiness, or defect closure.

###### Current repository checkpoint
- Date: 2026-11-19
- Branch: test-weekly-evidence-trust
- HEAD: b8b8f6d06ef9e3f3d226c721e21fd7152ca660b3
- Working tree: the snapshot implementation (`95acb9c`), capture automation (`298c83b`), and shadow Weekly Score v2 (`b8b8f6d`) are committed locally and not pushed. This reconciliation commits the canonical sources and `docs/CURRENT_DEFECTS.md`, and a following continuity commit refreshes the generated continuity artifacts. Unrelated untracked local files are preserved and never staged.
- Repository: /home/deeoriginalone/fantasy-intelligence

## Current committed delivery boundary

- Branch: `test-weekly-evidence-trust`, ahead of `origin/test-weekly-evidence-trust` (at `1f641d1`) by the implementation commits `95acb9c`, `298c83b`, and `b8b8f6d` plus this reconciliation's documentation and continuity commits, as of 2026-11-19; nothing is pushed.
- Implementation HEAD: `b8b8f6d06ef9e3f3d226c721e21fd7152ca660b3` - `feat(team): add shadow Weekly Score v2`, on top of `298c83b` - `feat(scheduler): automate pre-kickoff lineup snapshot capture` and `95acb9c` - `feat(team): capture pre-kickoff lineup decision snapshots`. The lineup decision intelligence commit remains `a306f3a`. Commits after `b8b8f6d` are documentation and continuity only.
- Commits after the historical My Team boundary `b75ed87`: `87a43ca` restores the action-first My Team hero and verified NFL week; `bff775f` adds evidence-gated waiver decisions and FAAB guidance; `3ddd37c` uses the configured timezone and authoritative week; `34c3498` adds schedule-backed waiver ranking, the automated nflverse schedule importer (`imports/import_nflverse_schedule.py`), and `services/schedule_bye_evidence.py`; `41dfe47` ranks visible Command Center lineup decisions; `c25e4f2` shares defensive health test assertions; `d37229b` adds an nflverse artifact watchdog; `beb5482` and `d478060` refresh reference and database documents; `ddd329d` ignores local generated artifacts; `695ff74` commits schedule automation (importer republish guards, systemd units, schedule tests); and `a306f3a` commits My Team lineup decision intelligence (services, route, template, and tests).
- Commits through `ddd329d` are recorded from Git history. `695ff74` and `a306f3a` were each revalidated in a clean worktree (see validation below). This reconciliation did not revalidate the earlier commits and claims no defect closure, production readiness, PostgreSQL parity, or recovery readiness.
- Later commits: `5abe2fd` reconciles canonical memory to the lineup and schedule boundary and `1f641d1` refreshes continuity artifacts (documentation and continuity only); `95acb9c` commits the pre-kickoff snapshot capture and review (5 files); `298c83b` commits the capture automation (2 systemd units, 1 new test file, and 2 added capture tests); and `b8b8f6d` commits the shadow Weekly Score v2 (3 services, `templates/team.html`, 3 test files, and `docs/METRIC_DEFINITIONS.md`). No implementation commit is pushed.

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

State: IMPLEMENTED and VALIDATED at the focused, controlled-route, live-route, and database boundary. COMMITTED in `95acb9c` (capture and review), `298c83b` (automation), and `b8b8f6d` (snapshot content `lineup.forward_validation.snapshot.v2` with the shadow Weekly Score v2), not pushed. Scheduled capture is OPERATIONALLY VERIFIED as installed and enabled, and a manual run through the systemd service succeeded; `FIRST_SCHEDULED_SNAPSHOT_V2_CAPTURE = PENDING` (the first timer-triggered run is due 2026-11-19 21:00 UTC, after this reconciliation).

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
- Remaining limits: no captured game has a final result yet; the legacy Weekly Score still has no approved automated weekly input and stays withheld on live `/team`, while the shadow Weekly Score v2 has no selection authority; the coverage limits above apply; and no implementation commit is pushed.

## Current committed Weekly Score v2 shadow boundary (2026-11-19)

State: IMPLEMENTED and VALIDATED at the focused, before/after-contract, live-route, and stored-snapshot boundary. COMMITTED in `b8b8f6d` (8 files), not pushed. Weekly Score v2 is PRELIMINARY / INFORMATIONAL_ONLY / SHADOW and is not authoritative.

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

- Pre-kickoff snapshot validation (2026-11-19, on the code committed in `95acb9c`): the six-file focused set (`tests/test_lineup_forward_validation.py`, `tests/test_pre_decision_snapshots.py`, `tests/test_lineup_projection_foundation.py`, `tests/test_lineup_decision_intelligence.py`, `tests/test_lineup_week_lock_state.py`, `tests/test_ux5_lineup_route_contract.py`) passed 182 of 182. Seven further `/team` route test files (`tests/test_ux2_team_route_matrix.py`, `tests/test_team_opportunity_integration.py`, `tests/test_lineup_evidence.py`, `tests/test_team_health_routes.py`, `tests/test_ux2_health_route_freshness.py`, `tests/test_ux2_team_accuracy_route.py`, `tests/test_ux1_dashboard_truth_completion.py`) gave 117 passed and 4 failed. All 4 failures reproduce at clean HEAD `1f641d1`: the 2 `tests/test_lineup_evidence.py` failures recorded below, and 2 `tests/test_team_opportunity_integration.py` template-source assertions (`test_team_template_does_not_default_missing_snap_values_to_zero` and `test_team_route_and_template_preserve_informational_what_changed_boundary`) that expect the strings `snap_value is not none` and `NON_ADJACENT`, which `dda3dbe` removed from `templates/team.html`. These are pre-existing test-expectation drift outside this boundary, not a recorded defect. The four changed implementation files and the new test file compiled, and `git diff --check` passed.
- Capture automation validation (2026-11-19, committed in `298c83b`): `tests/test_lineup_snapshot_capture_units.py`, `tests/test_lineup_forward_validation.py`, `tests/test_pre_decision_snapshots.py`, and `tests/test_ux5_lineup_route_contract.py` passed 45 of 45. `systemd-analyze --user verify` reported no diagnostics, and `systemd-analyze calendar` accepted all five timer expressions. The changed test files compiled; `git diff --check` and `git diff --cached --check` passed.
- Weekly Score v2 validation (2026-11-19, committed in `b8b8f6d`): `tests/test_jerrygm_projections.py`, `tests/test_lineup_projection_foundation.py`, `tests/test_lineup_decision_intelligence.py`, and `tests/test_lineup_forward_validation.py` passed 169 of 169 (151 at the previous HEAD; 18 new tests), on the working tree before commit and again in the commit review. The six changed Python files compiled; `git diff --check` and `git diff --cached --check` passed; the staged diff was byte-identical to the reviewed diff, and the exact eight-file commit scope contained no unrelated file. A 12-scenario before/after comparison against the previous HEAD produced byte-identical lineup contracts (only the reworded legacy blocker text differs), and real, inverted, and absent v2 values give identical selection and decision confidence. Across 13 affected lineup, projection, and `/team` test files, 334 passed and 7 failed; the same 7 fail with identical messages at the previous HEAD `298c83b`: the 2 `tests/test_lineup_evidence.py` and 2 `tests/test_team_opportunity_integration.py` failures already recorded in this section, `tests/test_opportunity_consumer_contract.py::test_templates_include_opportunity_evidence_without_conclusions`, `tests/test_ux_1_7_completion.py::test_dashboard_truth`, and `tests/test_ux2_1b_presentation.py::test_print_hides_navigation_and_closed_diagnostics`. They are pre-existing and outside this boundary.
- Historical focused validation on the 2026-11-16 working tree: 384 passed and 2 failed across 16 lineup, lock, schedule, JerryGM, and My Team route test files. The 2 failures (`tests/test_lineup_evidence.py::test_identity_fix_preserves_current_lineup_fields` and `::test_team_opportunity_changes_receives_player_specific_identity`) reproduce identically at clean HEAD `ddd329d`; that identity-route fixture does not supply `WEEK_AUTHORITY_ACQUIRER`. `tests/test_ux2_team_needs.py` fails collection at HEAD because `apply_waiver_ranking` does not exist. Both are pre-existing test defects outside this boundary. The same 16-file set reproduced 384 passed and the same 2 failures on committed `a306f3a` in a clean worktree, and `tests/test_schedule_bye_source_contract.py` passed (39) on `695ff74` alone.
- All 16 changed Python files compiled. `git diff --check` and `git diff --cached --check` passed.
- Historical live `/team` check (2026-11-16; HTTPS, served by code reloaded at 04:47 UTC) returned HTTP 200: Week 10, Week complete, 14 LOCKED from the automated schedule, START/FLEX decisions, no HOLD, league-scored projections labelled PRELIMINARY, and consensus labelled context only. The only remaining Week 10 game (LAC at BAL) has no rostered player. No live pre-kickoff open-window render had been observed at that time; the 2026-11-19 pre-kickoff render on committed code is recorded under the snapshot boundary above.
- Canonical sources are reconciled to implementation HEAD `b8b8f6d` (three local implementation commits ahead of origin, plus this reconciliation's documentation and continuity commits) as of 2026-11-19. Bundle and canonical-sync results come from the continuity run, not from this text.

###### Historical waiver recovery boundary (through ee451ca; verified 2026-10-03)
- Recovery commits: `98dee6a` corrects candidate health from live Sleeper status; `34e55d3` publishes source-backed snap share; `ee451ca` restores exact waiver GSIS identity from DynastyProcess player IDs.
- Manager-facing result: `/waivers` returned HTTP 200 with 19 candidates. The 13 candidates previously lacking GSIS identity now resolve through exact `sleeper_id` to `gsis_id` from `DynastyProcess/files/db_playerids.csv` (GPL-3.0); names, team/position, and similarity do not authorize identity. Source artifact, version, checksum, schema, source/retrieval times, completeness, and reconciliation remain in lineage; the artifact is not committed. Live Sleeper health fails closed when missing, unresolved, contradictory, or unsupported; supported injured-reserve variants do not render healthy, and the local "Healthy / Not listed" placeholder is not verified health.
- Evidence boundary: all 19 candidates have fresh current-season production and opportunity evidence; `What Changed` consumes published multiweek opportunity rows. All 19 also have source-backed snap-share evidence from nflverse `offense_pct`, joined by exact PFR-to-GSIS identity with CC BY 4.0 attribution. Snap share remains informational only.
- Operational database state: the week 1-3 refresh published 1,078 opportunity rows and 4,480 resolved snap-share rows; 51 snap rows cover the 19 waiver candidates. `opportunity.evidence.v1` and `snap_share.evidence.v1` retain their 86,400-second contracts. Source and retrieval times remain distinct; stale evidence expires normally and requires legitimate reacquisition/republication, never timestamp copying. Database publications are not Git content.
- Decision authority: these identity, opportunity, and snap-share changes do not alter ranking, priority, confidence, FAAB, ownership, eligibility, or health, add formulas, or authorize external fantasy transactions. The health repair corrects health evidence only. Candidate order/count and existing `What Changed` behavior remain unchanged.
- Validation recorded: opportunity-focused tests passed 200; identity staged-copy validation passed 3 source and 14 waiver identity/invariance tests; snap staged-copy validation passed 47 snap and 4 consumer tests. The post-publication read-only `/waivers` check returned 19 FRESH snap-share candidates.
- Remaining limits: eight non-waiver snap rows across three unresolved PFR identities remain excluded, and partial Week 4 snap evidence remains unpublished. Expected-role and opportunity-duration contracts remain unavailable. Production readiness, full PostgreSQL parity, failure injection, rollback/recovery, guarded cleanup, and repeatability remain unclaimed. Matchup Rank authority and unrelated Survivor, Command Center, navigation, trade, and lineup boundaries are unchanged.

###### Historical verified handoff boundary (2026-10-02)
- New commits since the previous canonical boundary: `c934b64` lineup reconciliation; `c78da0a` informational waiver comparison; `859fd9e` per-player GSIS/ESPN identity; `33d48c8` unmatched-roster injury status; `27de2a6` waiver trust-panel evidence placeholders; `dc5da8f` preliminary matchup signal; `00716b2` nflverse matchup test stabilization.
- Matchup Rank remains fail-closed and Matchup Signal remains informational/context-only. Matchup authority is blocked by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`; do not claim recommendation influence or full authority.
- Trust-panel, injury-status, identity, and lineup-reconciliation repairs are committed. The nflverse test stabilization is complete: 15 matchup tests and 8 preliminary-context tests pass. The related matchup, lineup, identity/injury, and waiver suites pass 148 tests together.
- Defect statuses remain exactly as documented in `docs/CURRENT_DEFECTS.md`; no new CLOSED status is supported. Production readiness, parity completion, and recovery completion are not claimed.
- Next milestone remains **Build the Fantasy Intelligence 2.0 Command Center and simplify the experience around six core destinations.** Recommended next implementation batch: **Build Command Center decision-center aggregation boundary**.

The branch, HEAD, and working-tree state must be reverified from the repository before import, staging, validation, or commit.

###### Preserved verified UX.2 foundation
- Active `/team` route wiring for league settings, Team Needs, Team Health, and Team Accuracy.
- Full-PPR positional coverage for QB, RB, WR, TE, FLEX, K, and DEF.
- Explicit unavailable-matchup handling.
- Recommendation-blocker support.
- Historical Team Health template and route validation: 14 passed in 0.38 seconds.
- Historical focused UX.2 validation: 35 passed in 0.47 seconds.
- Historical compile, whitespace, rendered-page, notebook-bundle, and canonical-synchronization evidence remains recorded for the earlier foundation.
- Read-only decision support remains in effect.

###### Historical implementation batch
1. Reconcile repository reality and inspect exact staged, unstaged, and untracked layers.
2. Identify the actual My Team route, service, template, and test files from repository evidence.
3. Remove unsupported Overall Grade authority.
4. Remove unsupported aggregate Weekly Starter Score authority.
5. Differentiate unavailable weekly evidence from verified zero.
6. Complete Matchup Rank definition and fail-closed presentation.
7. Unify Team Needs summary and detail through one shared result.
8. Separate starter coverage, depth target, and strategic need.
9. Add confidence and reasons to lineup recommendations.
10. Target health and matchup blockers to the exact recommendation.
11. Show health source, age, freshness, and recommendation impact.
12. Put the highest-priority supported action before technical diagnostics.
13. Collapse technical lineage by default.

###### Required UX.2 acceptance criteria
- Active Full-PPR league settings and current supported roster truth drive the page.
- QB, RB, WR, TE, FLEX, K, and DEF remain represented.
- Team Needs summary and detail agree and explain their drivers.
- Minimum starter coverage, depth target, and strategic need are distinct.
- Overall Grade and Weekly Score are removed unless their definitions and tests satisfy the metric contract.
- Missing weekly evidence does not silently become zero.
- Matchup Rank identifies meaning, population, directionality, and unavailable behavior.
- Every supported recommendation includes player, slot, opponent, supported weekly value, matchup context, health, confidence, reason, and targeted blockers.
- Unknown health is never displayed as healthy.
- Stale or unavailable evidence reduces confidence, produces MONITOR, makes a component unavailable, or blocks the exact affected recommendation.
- The manager-facing action and expected fantasy impact appear before diagnostics.
- Technical data remains available but is secondary and collapsible.

###### Required validation
- Focused metric, Team Needs, health, recommendation, route, and template tests.
- Active `/team` rendered-page verification for supported, degraded, unavailable, and blocked states.
- Python compile checks for changed Python files.
- `git diff --check`.
- `git diff --cached --check` when staged.
- Exact changed-file and staged-file review.
- Relevant defect-status review at the evidence-supported level.
- Canonical synchronization.
- Notebook bundle validation.
- Narrow UX.2 commit review using exact paths.

###### Historical completion and validation boundary (superseded snapshot)
- Focused UX.2 validation passed with 85 tests.
- Controlled active `/team` state matrix passed with 11 tests covering health, weekly-value, and missing league-settings states.
- The related UX.2, health, integrity, matchup, and lineup suite passed with 133 tests.
- Fresh live `/team` on port 5051 returned HTTP 200 with action-first ordering, explicit unavailable freshness and impact, visible recommendation evidence, and collapsed lineage.
- Defect closure still requires a reviewed commit boundary; no commit is claimed here.
- The current evidence proves the revised UX.2 criteria at the focused, controlled active-route, and live current-state boundaries.
- Defect closure still requires a reviewed commit boundary.
- Do not claim UX.3 completion; only its milestone is next.
- UX.2.1B related validation passes 147 tests; isolated browser captures for all required states passed at desktop and 390px with no primary-content overflow or clipped cards. The simplified page now presents one action, snapshot, grouped risks, concise Bench Plan, truthful actionable needs, and closed diagnostics.
- No production, database migration, external transaction, PostgreSQL parity, or full recovery claim is made.

###### Working-tree safety
- Preserve unrelated changes.
- Do not use `git add .` or `git add -A`.
- Inspect both staged and unstaged versions of files present in both layers.
- Stage exact files only.
- Keep generated bundles, backups, exports, archives, and broad audit captures outside the UX.2 implementation commit unless separately reviewed.

###### Continuity sequence after validated implementation

```bash
python scripts/update_canonical_head.py
./scripts/end_of_day.sh

cat notebook_bundle/BUNDLE_VALIDATION.md
cat notebook_bundle/CANONICAL_SYNC_VALIDATION.md
cat notebook_bundle/CHANGE_REPORT.md

git status --short --branch
git diff --cached --stat
git diff --cached --name-status
```

A synchronization PASS confirms documentation consistency only. It does not prove feature completion beyond the recorded test and rendered-route boundary.

###### Preserved UX.8 Survivor Intelligence progress (historical validation; in-progress, not complete)

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

###### Preserved UX.9 My Team + Weekly Lineup Consolidation (complete at recorded validation boundary)

- `/lineup` is retired as a rendered page and now returns HTTP 302 to `/team#lineup`; verified live and by test, preserving existing bookmarks.
- `/team` is now the single roster command center: hero (verdict/action/projected score/confidence/biggest risk) → Next Best Team Action → Lineup Snapshot → Recommended Starting Lineup (formation, now also carrying the authoritative START/SIT/FLEX/MONITOR call and a bench-swap flag per slot) → Bench Priority → Biggest Risks → Team Needs → Roster Outlook → What Changed This Week → Why This Lineup Is Trusted → collapsed diagnostics.
- Removed duplicate surfaces: the old plain hero, the separate “Recommended Starters” section, “Bench Plan”, the separate “Start/Sit Decisions” card grid, and Lineup's own risk/diagnostics blocks.
- No recommendation engine, lineup scoring, Team Needs, Team Health, Team Accuracy, waiver, trade, survivor, or database logic was changed; only route wiring and template presentation.
- Focused team/lineup route-contract tests: 20 passed (5 pre-existing, unrelated `/trades` failures unchanged).
- Completion check answered: no functionality on `/lineup` still justifies a separate page.

###### Historical NFL Intelligence MVP snapshot (implemented; recorded data coverage bounded)

- Read-only `/nfl-intelligence` is implemented with Top Picks, Top Risk Games, All Games, Insights, Blockers, and collapsed Diagnostics. The primary experience is manager-facing; raw Elo, matchup edge, injury totals, and weather values are confined to Diagnostics.
- All scheduled games for the selected loaded week render. Prediction absence is explicit as `INSUFFICIENT EVIDENCE`; no prediction is fabricated.
- The existing protected market-refresh endpoint is available through a per-week refresh button. It refreshes only provider games that match the stored schedule; it does not create unsupported predictions.
- Verified current coverage: Week 1 has 16 scheduled games and 7 provider-matched predictions; Week 2 has 16 scheduled games and 0 provider-matched predictions. The complete 2026 source schedule (`nfl_schedule`) contains Weeks 1-18, but only Weeks 1-2 are currently seeded into `yahoo_pickem_games`.
- Matching uses the complete provider full-name-to-standard-abbreviation map and exact away/home pairs. Recorded runs show Week 1 received/matched/wrote 7/7/7; Week 2 received 6 provider games and matched/wrote 0/0. This is a current provider-slate versus stored-schedule mismatch, not a verified naming failure.
- Focused NFL Intelligence validation: 29 passed. Python compilation for `nfl_intelligence.py` and `nfl_intelligence_routes.py`, whitespace validation, and live Week 1/Week 2 rendering passed. Desktop and 390px renders had no horizontal overflow.
- Historical repository checkpoint: 2026-09-14, branch `feature/evidence-bundle-pipeline`, HEAD `e5285b1918a97e6df7b9e74cd94385ecf489b721`. NFL Intelligence implementation and canonical documentation were committed at that snapshot; this is not the active branch or HEAD.

###### Verified product architecture and roadmap

- Primary in-season destinations are proposed as Decision Center, My Team, Waivers, Trades, NFL Intelligence, and Survivor. My Team remains the authoritative lineup destination; `/lineup` remains only as a redirect to `/team#lineup` for existing bookmarks.
- `/gm` duplicates lineup, waiver, and matchup summary behavior and exposes unsupported grades, scores, and modifiers. Its safe retirement path is to move cross-page prioritization to the rebuilt Dashboard, retain detail in the owning pages, then redirect `/gm` after route and bookmark validation.
- Draft, import, readiness, Sleeper administration, Pick'em, and technical diagnostics are not primary in-season destinations. Preserve useful routes until separately validated for redirection, secondary research, Draft Mode, or Admin placement.
- Current weekly-data boundary: Sleeper supplies live league, roster, ownership, and supplemental player-status facts; The Odds API supplies partial matched market context; nflverse and Open-Meteo supply automated NFL Intelligence enrichment. Schedule and bye inputs are now owned by the automated nflverse schedule import (see the current schedule and kickoff-evidence boundary); default weekly enrichment can still read CSV-derived matchup inputs. The no-CSV test covers an explicitly disabled path, not the default route.
- Phase 0: reconcile in-season navigation and retire duplicate manager destinations without losing `/lineup` bookmark behavior. Phase 1: establish automated, timestamped schedule, bye, injury, matchup, and projection inputs or fail closed. Phase 2: rebuild Dashboard as a Decision Center that links to, rather than duplicates, owning pages.
- Phase 3: add trusted player opportunity data and a multi-week What Changed engine. Phase 4: add market-aware buy/low, sell/high, breakout, and regression intelligence only after market-value and opportunity contracts exist. Phase 5: persist immutable pre-decision snapshots for post-week Process versus Results and narrative manager learning (My Team lineup-decision snapshots persist and are captured on a schedule as of 2026-11-19, in `95acb9c` and `298c83b`; Process versus Results is not implemented). Phase 6: add rest-of-season, playoff, and championship scenario planning only after trusted inputs exist.
- Opportunity trends, buy/sell labels, post-week grades, Manager Report Card grades, and playoff strategy are blocked by missing automated source, freshness, identifier, historical-baseline, metric-authority, or decision-time snapshot evidence. Do not infer them from box scores or stale CSV inputs.

###### Decision-first priority override

- Priority 1: make weekly START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, and TRADE AWAY decisions trustworthy with current, league-specific, explained evidence. This outranks navigation work, dashboards, new models, and season strategy.
- Priority 2: establish automated player opportunity and role evidence, then build What Changed from documented multi-week baselines. Breakout, regression, Buy Low, and Sell High labels remain blocked until source, identifier, history, freshness, metric authority, and market evidence are verified.
- Priority 3: rebuild Dashboard as the Decision Center, summarizing Must Act, Start/Sit, Waivers, Trades, Opportunity Alerts, Risk Alerts, and No Action Needed while linking to owning pages instead of duplicating their engines.
- Priority 4: persist immutable pre-decision snapshots before Process versus Results evaluation; as of 2026-11-19, My Team lineup-decision snapshots persist and are captured on a schedule (`95acb9c`, `298c83b`), waiver and trade decisions are not captured, and Process versus Results is not implemented. Priority 5: provide narrative manager learning before any Manager Report Card grade. Rest-of-season and playoff strategy follow only after these decision foundations are trusted.

###### Historical Schedule and Bye Provenance installation boundary

- The additive provenance contract is installed and validated: 24 focused tests, Python compilation, `git diff --check`, `git diff --cached --check`, and live route inspection passed.
- Verified schedule state: all 272 2026 `nfl_schedule` rows are owned by `csv:nfl-2026-UTC.csv`, with `source_recorded_at=2026-05-14T00:00:00Z` and preserved import time. CSV fallback is disclosed and cannot overwrite automated, verified-cache, unknown, or differently-owned CSV rows.
- Verified bye state: all 32 2026 `bye_weeks` rows retain legacy source attribution (`Gridiron Games bye-week PDF; cross-checked against nfl-2026-UTC.csv`) but have no source-recorded, retrieval, or import timestamp. The verified bootstrap correctly refused to infer CSV ownership for these non-null legacy rows.
- Schedule and bye freshness thresholds are currently unset. Therefore schedule/bye provenance is installed and schedule source time is recorded, but neither domain is yet authoritative for live recommendations; the correct contract state remains `UNAVAILABLE`, not fabricated `FRESH`.
- Live route evidence: `/team` rendered `FRESH`, `MONITOR`, and `UNAVAILABLE`; `/waivers` rendered `FRESH`; `/trades` rendered `FRESH`, `AGING`, and `BLOCKED`. These route markers do not override the unset schedule/bye freshness configuration.
- Remaining blockers: approved schedule/bye freshness thresholds, timestamped bye provenance through a controlled source-specific workflow, current matchup evidence, and authoritative projection/ranking evidence. No defect is closed by this installation alone.
- Superseded (2026-11-16): the CSV-owned schedule, legacy-attributed byes, unset schedule threshold, and schedule non-authority described above are historical. The current schedule and kickoff-evidence boundary records automated nflverse ownership, `schedule.evidence.v1` = 86400 seconds, and schedule-owned lineup locks. Current matchup evidence and authoritative projection/ranking evidence remain open blockers.

###### Current in-season priorities

- Reconcile the season navigation: remove the retired `/lineup` navigation entry, keep `/team#lineup` as the authoritative lineup destination, and move duplicate GM/technical surfaces out of the primary manager workflow.
- CSV and manual imports are last-resort bootstrap, recovery, or test-fixture mechanisms only. They must not be required for routine weekly decisions; stale or unrefreshable inputs must be explicit `UNAVAILABLE` or `BLOCKED`.
- Replace default CSV-derived weekly matchup inputs with automated, timestamped sources before using them authoritatively. Until then, preserve fail-closed recommendation behavior.
- Do not add advanced player opportunity, buy/sell, post-week process, or playoff-strategy features until their source, freshness, metric authority, and missing-data contracts are defined and validated.

###### Historical end-of-day evidence reconciliation (2026-09-14)

- The Schedule/Bye Threshold Registry is installed and validated: 40 focused tests, Python compilation, `git diff --check`, and `git diff --cached --check` passed. Its stable IDs are `schedule.evidence.v1` and `bye.evidence.v1`; absent, malformed, zero, and negative environment values fail closed without a numeric default.
- Automated nflverse matchup evidence is implemented and validated through official-source retrieval, provenance, Full-PPR calculation, `LA` to `LAR` normalization and regression coverage, completeness, freshness, fail-closed publication, and PostgreSQL transaction behavior. Migration `013_nflverse_defense_matchups.sql` is applied and idempotent.
- Use source `stats_player` and artifact pattern `stats_player_week_{season}.csv.gz`. Refreshed real 2026 Week 1 calculation produced 128 rows and 32-of-32 defense coverage for QB, RB, WR, and TE; `KC` and `DEN` are present. Preliminary context is fresh, complete, Full-PPR, sample-disclosed, informational-only, and does not change recommendations.
- Authority remains BLOCKED by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`. Automated 2026 rows remain 0; 136 historical 2025 CSV rows remain preserved and historical-only. Current consumers keep authoritative Matchup Rank unavailable while preliminary context remains informational-only; production readiness and full current matchup authority remain unclaimed.

## Next milestone

**Validate My Team weekly START/SIT/FLEX decision quality with forward evidence: capture pre-kickoff decision snapshots before every weekly kickoff window and complete read-only post-week outcome reviews against final Sleeper points, starting with Week 11, before expanding Command Center or other infrastructure.**

The decision-first priority override ranks trustworthy weekly START/SIT/FLEX decisions above dashboards and navigation. Pre-kickoff decision snapshot capture is committed (`95acb9c`) and automated (`298c83b`): migration `014_pre_decision_snapshots.sql` is applied, a Pacific-time systemd timer runs capture before the Thursday, Sunday, and Monday kickoff windows, a read-only post-week review exists, and the Week 11 cohort (13 players, 3 `snapshot.v1` snapshots each) is stored. The shadow Weekly Score v2 (`b8b8f6d`) now names the current-week league-scored projection and is captured in `snapshot.v2` from the first scheduled run onward. The decision-quality milestone is not complete merely because snapshots exist, capture is automated, or Weekly Score v2 exists: no captured game has a final result, the first scheduled capture is still pending, and outcome evidence is still required. The legacy Weekly Score stays withheld on live `/team`; Weekly Score v2 and league-scored projections remain PRELIMINARY and INFORMATIONAL_ONLY (v2 is SHADOW); the projection freshness threshold and action threshold remain UNAPPROVED; none can be strengthened without accumulated forward evidence, and no model-quality judgment is made from one week. Weeks before Week 11 cannot be reconstructed.

The next batch is **Record the first Week 11 outcome review and confirm scheduled capture**:
1. After final supported Week 11 results exist (the automated schedule records every Week 11 result; the last game is Monday Night Football on Nov 23 Pacific), execute and record the read-only `owner_ops review-lineup-snapshots --season 2026 --week 11` outcome review without changing selection, confidence, thresholds, or projections. Sleeper pre-final zeros are not final zeros.
2. Confirm the scheduled capture runs in the journal and database: Thu Nov 19 13:00, Sun Nov 22 09:00, and Mon Nov 23 13:00 Pacific, and whether the Wed Nov 25 15:00 Pacific run saw Week 12.
3. Continue accumulating `snapshot.v2` evidence across additional weeks before proposing any freshness threshold or Weekly Score authority change.

No model-quality judgment is made from one week, and no threshold or authority is promoted.

This batch must not change selection, invent or approve thresholds, raise confidence, or submit transactions. Command Center aggregation, opportunity detection, Process versus Results, manager development, and season strategy follow in that order. UX.8 retains its recorded in-progress boundary. Existing defects retain their evidence-supported statuses; UXQA-005 is VALIDATED, not CLOSED. Production readiness, PostgreSQL parity, recovery, and defect closure remain unclaimed. This reconciliation authorizes no defect closure.
