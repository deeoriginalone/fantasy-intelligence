###### Project State

####### Current state

Fantasy Intelligence has completed the Shared Integrity and Data Integrity track through A.10. UX.1 remains complete at its verified focused-test and rendered active-route boundary.

UX.2 My Team Accuracy, Explainability, and League-Settings Validation is validated at the focused and controlled active-route boundary. The route, contracts, recommendation evidence, health targeting, priority action, and collapsed lineage are preserved.

UX.2.1C is owner-accepted as of 2026-09-13 (`APPROVED: MY TEAM UI`). UX.3 is validated at a supported, read-only waiver-publication boundary. UX.4.1 through UX.4.12 are validated at focused, controlled-browser, and live nine-partner dropdown boundaries. The shared action-first visual system is implemented across Lineup, My Team, Waivers, and Trades. UX.5 has the formalized implementation and evidence boundary; formal definition-of-done review remains pending. UX.6 and UX.7 remain pending.

####### Last recorded repository checkpoint
- Date: 2026-09-15
- Branch: test-weekly-evidence-trust
- HEAD: a8684f99626356659643ec297bf47980d6dc0cf3

####### Current evidence-layer foundation (validated 2026-09-15)
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
- Fixed a real Update-result dropdown bug (it always visually reset to “pending” regardless of the actual recorded status); added a Reset-pick control (`delete_selection()`, `/survivor/reset`) so a manager can clear a recorded pick and reopen the week for a fresh recommendation.
- Added manual team selection (“PICK A DIFFERENT TEAM”): a manager can record any eligible team as their pick, not only the algorithmic top recommendation, including teams with no market data; validated against the real team universe and recorded without fabricating a probability.
- Added CSRF protection to `/survivor/select` and `/survivor/status` (previously unprotected, same class of gap fixed earlier on the market-refresh endpoint).
- Added `_verified_current_week()` using Sleeper's `get_nfl_state()` to replace the hardcoded default week only when no week is explicitly requested; fails closed (never guesses) on network error or season mismatch.
- Focused survivor + security tests: 84 passed, 1 xfailed (up from 68 earlier this session).
- UX.8 is not yet formally complete; remaining boundary work is tracked under the Next milestone below.

####### UX.9 My Team + Weekly Lineup Consolidation (complete at verified boundary)

- `/lineup` is retired as a rendered page and now returns HTTP 302 to `/team#lineup`; verified live and by test, preserving existing bookmarks.
- `/team` is now the single roster command center: hero (verdict/action/projected score/confidence/biggest risk) → Next Best Team Action → Lineup Snapshot → Recommended Starting Lineup (formation, now also carrying the authoritative START/SIT/FLEX/MONITOR call and a bench-swap flag per slot) → Bench Priority → Biggest Risks → Team Needs → Roster Outlook → What Changed This Week → Why This Lineup Is Trusted → collapsed diagnostics.
- Removed duplicate surfaces: the old plain hero, the separate “Recommended Starters” section, “Bench Plan”, the separate “Start/Sit Decisions” card grid, and Lineup's own risk/diagnostics blocks.
- No recommendation engine, lineup scoring, Team Needs, Team Health, Team Accuracy, waiver, trade, survivor, or database logic was changed; only route wiring and template presentation.
- Focused team/lineup route-contract tests: 20 passed (5 pre-existing, unrelated `/trades` failures unchanged).
- Completion check answered: no functionality on `/lineup` still justifies a separate page.

####### NFL Intelligence MVP (implemented; operational data coverage remains bounded)

- Read-only `/nfl-intelligence` is implemented with Top Picks, Top Risk Games, All Games, Insights, Blockers, and collapsed Diagnostics. The primary experience is manager-facing; raw Elo, matchup edge, injury totals, and weather values are confined to Diagnostics.
- All scheduled games for the selected loaded week render. Prediction absence is explicit as `INSUFFICIENT EVIDENCE`; no prediction is fabricated.
- The existing protected market-refresh endpoint is available through a per-week refresh button. It refreshes only provider games that match the stored schedule; it does not create unsupported predictions.
- Verified current coverage: Week 1 has 16 scheduled games and 7 provider-matched predictions; Week 2 has 16 scheduled games and 0 provider-matched predictions. The complete 2026 source schedule (`nfl_schedule`) contains Weeks 1-18, but only Weeks 1-2 are currently seeded into `yahoo_pickem_games`.
- Matching uses the complete provider full-name-to-standard-abbreviation map and exact away/home pairs. Recorded runs show Week 1 received/matched/wrote 7/7/7; Week 2 received 6 provider games and matched/wrote 0/0. This is a current provider-slate versus stored-schedule mismatch, not a verified naming failure.
- Focused NFL Intelligence validation: 29 passed. Python compilation for `nfl_intelligence.py` and `nfl_intelligence_routes.py`, whitespace validation, and live Week 1/Week 2 rendering passed. Desktop and 390px renders had no horizontal overflow.
- Current repository checkpoint: 2026-09-16, branch `test-weekly-evidence-trust`, HEAD `a8684f99626356659643ec297bf47980d6dc0cf3`. Preserve unrelated working-tree changes.

####### Verified product architecture and roadmap

- Primary in-season destinations are proposed as Decision Center, My Team, Waivers, Trades, NFL Intelligence, and Survivor. My Team remains the authoritative lineup destination; `/lineup` remains only as a redirect to `/team#lineup` for existing bookmarks.
- `/gm` duplicates lineup, waiver, and matchup summary behavior and exposes unsupported grades, scores, and modifiers. Its safe retirement path is to move cross-page prioritization to the rebuilt Dashboard, retain detail in the owning pages, then redirect `/gm` after route and bookmark validation.
- Draft, import, readiness, Sleeper administration, Pick'em, and technical diagnostics are not primary in-season destinations. Preserve useful routes until separately validated for redirection, secondary research, Draft Mode, or Admin placement.
- Current weekly-data boundary: Sleeper supplies live league, roster, ownership, and supplemental player-status facts; The Odds API supplies partial matched market context; nflverse and Open-Meteo supply automated NFL Intelligence enrichment. Default weekly enrichment can still read local schedule, bye, and CSV-derived matchup inputs. The no-CSV test covers an explicitly disabled path, not the default route.
- Phase 0: reconcile in-season navigation and retire duplicate manager destinations without losing `/lineup` bookmark behavior. Phase 1: establish automated, timestamped schedule, bye, injury, matchup, and projection inputs or fail closed. Phase 2: rebuild Dashboard as a Decision Center that links to, rather than duplicates, owning pages.
- Phase 3: add trusted player opportunity data and a multi-week What Changed engine. Phase 4: add market-aware buy/low, sell/high, breakout, and regression intelligence only after market-value and opportunity contracts exist. Phase 5: persist immutable pre-decision snapshots for post-week Process versus Results and narrative manager learning. Phase 6: add rest-of-season, playoff, and championship scenario planning only after trusted inputs exist.
- Opportunity trends, buy/sell labels, post-week grades, Manager Report Card grades, and playoff strategy are blocked by missing automated source, freshness, identifier, historical-baseline, metric-authority, or decision-time snapshot evidence. Do not infer them from box scores or stale CSV inputs.

####### Decision-first priority override

- Priority 1: make weekly START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, and TRADE AWAY decisions trustworthy with current, league-specific, explained evidence. This outranks navigation work, dashboards, new models, and season strategy.
- Priority 2: establish automated player opportunity and role evidence, then build What Changed from documented multi-week baselines. Breakout, regression, Buy Low, and Sell High labels remain blocked until source, identifier, history, freshness, metric authority, and market evidence are verified.
- Priority 3: rebuild Dashboard as the Decision Center, summarizing Must Act, Start/Sit, Waivers, Trades, Opportunity Alerts, Risk Alerts, and No Action Needed while linking to owning pages instead of duplicating their engines.
- Priority 4: persist immutable pre-decision snapshots before Process versus Results evaluation. Priority 5: provide narrative manager learning before any Manager Report Card grade. Rest-of-season and playoff strategy follow only after these decision foundations are trusted.

####### Schedule and Bye Provenance Contract (installed; not yet authoritative for live decisions)

- The additive provenance contract is installed and validated: 24 focused tests, Python compilation, `git diff --check`, `git diff --cached --check`, and live route inspection passed.
- Verified schedule state: all 272 2026 `nfl_schedule` rows are owned by `csv:nfl-2026-UTC.csv`, with `source_recorded_at=2026-05-14T00:00:00Z` and preserved import time. CSV fallback is disclosed and cannot overwrite automated, verified-cache, unknown, or differently-owned CSV rows.
- Verified bye state: all 32 2026 `bye_weeks` rows retain legacy source attribution (`Gridiron Games bye-week PDF; cross-checked against nfl-2026-UTC.csv`) but have no source-recorded, retrieval, or import timestamp. The verified bootstrap correctly refused to infer CSV ownership for these non-null legacy rows.
- Schedule and bye freshness thresholds are currently unset. Therefore schedule/bye provenance is installed and schedule source time is recorded, but neither domain is yet authoritative for live recommendations; the correct contract state remains `UNAVAILABLE`, not fabricated `FRESH`.
- Live route evidence: `/team` rendered `FRESH`, `MONITOR`, and `UNAVAILABLE`; `/waivers` rendered `FRESH`; `/trades` rendered `FRESH`, `AGING`, and `BLOCKED`. These route markers do not override the unset schedule/bye freshness configuration.
- Remaining blockers: approved schedule/bye freshness thresholds, timestamped bye provenance through a controlled source-specific workflow, current matchup evidence, and authoritative projection/ranking evidence. No defect is closed by this installation alone.

####### Current in-season priorities

- Reconcile the season navigation: remove the retired `/lineup` navigation entry, keep `/team#lineup` as the authoritative lineup destination, and move duplicate GM/technical surfaces out of the primary manager workflow.
- CSV and manual imports are last-resort bootstrap, recovery, or test-fixture mechanisms only. They must not be required for routine weekly decisions; stale or unrefreshable inputs must be explicit `UNAVAILABLE` or `BLOCKED`.
- Replace default CSV-derived weekly matchup inputs with automated, timestamped sources before using them authoritatively. Until then, preserve fail-closed recommendation behavior.
- Do not add advanced player opportunity, buy/sell, post-week process, or playoff-strategy features until their source, freshness, metric authority, and missing-data contracts are defined and validated.

####### End-of-day evidence reconciliation (2026-09-14)

- The Schedule/Bye Threshold Registry is installed and validated: 40 focused tests, Python compilation, `git diff --check`, and `git diff --cached --check` passed. Its stable IDs are `schedule.evidence.v1` and `bye.evidence.v1`; absent, malformed, zero, and negative environment values fail closed without a numeric default.
- Automated nflverse matchup evidence is implemented and validated through official-source retrieval, provenance, Full-PPR calculation, `LA` to `LAR` normalization with regression coverage, completeness evaluation, fail-closed publication, and PostgreSQL transaction behavior. Migration `013_nflverse_defense_matchups.sql` is applied and idempotent.
- The source is `stats_player` with artifact pattern `stats_player_week_{season}.csv.gz`. Refreshed real 2026 Week 1 calculation produced 128 rows and 32-of-32 defense coverage for QB, RB, WR, and TE; `KC` and `DEN` are present. Source timestamps, retrieval time, compressed/decompressed checksums, release version, and CC BY 4.0 attribution are captured.
- Preliminary matchup context is fresh, complete, Full-PPR, sample-disclosed, and informational-only in memory. Current matchup authority remains BLOCKED by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`; automated 2026 rows remain 0; 136 historical 2025 CSV rows remain preserved and cannot satisfy current-season authority. Preliminary context does not influence recommendations, and production readiness or full current matchup authority is not claimed.

####### Current verified matchup authority boundary (2026-09-16)
- Automated NFLverse matchup calculation and publication are present. Publication metadata propagation is complete for source authority, source-recorded time, retrieved-at time, version, checksum, lineage, and completed games.
- Implementation-backed informational publication contracts now exist for threshold metadata, population metadata, and directionality metadata. They do not grant Matchup Rank authority.
- Matchup Rank remains non-authoritative. The blockers `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`, `MATCHUP_POPULATION_UNVERIFIED`, and `MATCHUP_DIRECTIONALITY_UNVERIFIED` remain active in shared lineup evidence.
- Snapshot capture remains blocked. Recommendation behavior remains unchanged, including START, SIT, FLEX, MONITOR, Weekly Score, confidence, waiver, trade, matchup, and transaction behavior.
- Focused authority tests passed 37 tests; focused evidence and consumer regression validation passed 146 tests. Python compilation, `git diff --check`, and `git diff --cached --check` passed.

## Next milestone

**Make the evidence foundations authoritative with automated, timestamped sources or explicit unavailable states before any recommendation consumption.**

Navigation reconciliation supports this milestone but does not outrank decision quality. Opportunity detection is the next competitive advantage after weekly trust; Decision Center, Process versus Results, manager development, and season strategy follow in that order. UX.8 retains its recorded in-progress boundary. Existing defects retain their evidence-supported statuses; production readiness, PostgreSQL parity, recovery, and defect closure remain unclaimed.
