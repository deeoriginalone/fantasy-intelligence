###### Development Roadmap

####### Last recorded repository checkpoint
- Date: 2026-09-15
- Branch: test-weekly-evidence-trust
- HEAD: 46109c569182eaf110f032db0fc31c4744abf79e

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
- A.13 Opportunity Metrics Engine: evidence foundation implemented; authoritative ingestion remains deferred
- A.14 Schedule and Matchup Forecaster
- A.15 Correlation Engine
- A.16 Vegas Integration
- A.17 Market Mispricing Engine: market-signal and candidate evidence foundations implemented; recommendation logic remains deferred
- A.18 Trade Impact Simulator: deferred; no trade recommendation or ranking consumption exists

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
- Current repository checkpoint: 2026-09-16, branch `test-weekly-evidence-trust`, HEAD `46109c569182eaf110f032db0fc31c4744abf79e`. Preserve unrelated working-tree changes.

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
- Automated nflverse matchup implementation: VALIDATED at official retrieval, provenance, Full-PPR calculation, `LA` to `LAR` normalization, completeness, freshness, fail-closed publication, and PostgreSQL transaction boundaries. Migration `013_nflverse_defense_matchups.sql` is applied and idempotent.
- Source: `stats_player`; artifact: `stats_player_week_{season}.csv.gz`. Refreshed real 2026 Week 1 calculation reached 128 rows and 32-of-32 defenses for QB, RB, WR, and TE. `KC` and `DEN` are present; identity resolution is complete. Rank directionality is `LOWER_IS_HARDER`. Preliminary context is informational-only and does not influence recommendations.
- Current publication remains BLOCKED by `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`. Automated 2026 rows remain 0; 136 historical 2025 CSV rows remain preserved and historical-only. Current consumers may show preliminary context but cannot use authoritative Matchup Rank; production readiness, full current-season authority, and milestone completion remain unclaimed.

####### Current verified matchup authority boundary (2026-09-16)
- Automated NFLverse matchup calculation and publication are present. Publication metadata propagation is complete for source authority, source-recorded time, retrieved-at time, version, checksum, lineage, and completed games.
- Implementation-backed informational publication contracts now exist for threshold metadata, population metadata, and directionality metadata. They do not grant Matchup Rank authority.
- Matchup Rank remains non-authoritative. The blockers `MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED`, `MATCHUP_POPULATION_UNVERIFIED`, and `MATCHUP_DIRECTIONALITY_UNVERIFIED` remain active in shared lineup evidence.
- Snapshot capture remains blocked. Recommendation behavior remains unchanged, including START, SIT, FLEX, MONITOR, Weekly Score, confidence, waiver, trade, matchup, and transaction behavior.
- Focused authority tests passed 37 tests; focused evidence and consumer regression validation passed 146 tests. Python compilation, `git diff --check`, and `git diff --cached --check` passed.

####### FantasyPros projection evidence foundation (2026-09-16)
- FantasyPros automated source integration and non-authoritative projection evidence contract are implemented. Live projections and Players endpoints, provider identifiers, and deterministic identifier overlap were validated.
- The contract preserves `authority_state = NON_AUTHORITATIVE` and `decision_effect = NONE`; recommendation behavior is unchanged and no projection persistence or snapshot capture exists.
- Projection authority remains blocked by `PROJECTION_SOURCE_USE_UNVERIFIED`, `PROJECTION_UNIT_UNVERIFIED`, `PROJECTION_SOURCE_TIMESTAMP_UNAVAILABLE`, `PROJECTION_FRESHNESS_THRESHOLD_UNVERIFIED`, and `PROJECTION_LINEAGE_VERSION_UNAVAILABLE`.
- Focused FantasyPros evidence validation passed 16 tests; Python compilation, `git diff --check`, and `git diff --cached --check` passed.
- The five active blockers publish structured blocker metadata: blocker ID, description, affected capability, recommendation impact, and authority impact. The compatibility string blocker list remains available.

## Next milestone

**Make the evidence foundations authoritative with automated, timestamped sources or explicit unavailable states before any recommendation consumption.**

Navigation reconciliation supports this milestone but does not outrank decision quality. Opportunity detection is the next competitive advantage after weekly trust; Decision Center, Process versus Results, manager development, and season strategy follow in that order. UX.8 retains its recorded in-progress boundary. Existing defects retain their evidence-supported statuses; production readiness, PostgreSQL parity, recovery, and defect closure remain unclaimed.
