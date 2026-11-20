# Metric Definitions and Display Contract

## Fantasy Intelligence 2.0 Metric Direction

Metrics exist only to improve a league-specific manager decision. Keep metric displays understandable, informational where authority is incomplete, and fail closed when inputs are missing or contradictory. No metric may imply ranking, confidence, probability, FAAB, or recommendation authority beyond its documented contract.

## Evidence-first architecture

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe; prohibited or unpermitted use remains blocked. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Specific metric/page contracts may restrict an individual signal to context-only when that signal alone cannot safely support a recommendation.

## Rule

A metric must not be displayed as authoritative until its implementation documents the fields below and the related tests pass.

Required definition fields:

- Name
- Purpose
- Scale or unit
- Inputs
- Directionality
- Freshness requirement
- Missing-data behavior
- Decision use
- Owner service or contract
- Validation tests

Multi-source corroboration does not authorize a metric by itself. For every metric, document the source owner, permitted secondary sources, agreement rule, conflict behavior, identity join, freshness requirement, missing-data behavior, and recommendation effect. Source disagreement must remain visible and fail closed; values must not be averaged away. Yahoo-derived evidence is `UNKNOWN PENDING API VERIFICATION` and cannot change a metric, score, ranking, confidence, or recommendation until its consumer contract and tests authorize that effect.

## Weekly Score

- Status: Weekly Score v2 (`weekly-score.v2`) is PRELIMINARY / INFORMATIONAL_ONLY / SHADOW. It is defined and implemented as evidence only and is not authoritative.
- Purpose: Current-week projected fantasy output under the active Sleeper league scoring settings.
- Scale or unit: Fantasy points for the current NFL week (`fantasy_points`).
- Directionality: Higher projected fantasy points are better projected output.
- Inputs: Only the league-scored current-week provider projection from `build_player_projection`: the JerryGM `jgm_baseline` projected stat line rescored with the league's Sleeper scoring settings under `league-scored-projection.v1`, used as-is. It never divides a season projection by 17, never applies the matchup modifier or a second health multiplier, never converts ECR/rank to points, never averages sources, and never uses `players.projected_points`, historical data, or a stored snapshot as input.
- Identity: Exact Sleeper player ID through the existing JerryGM identity contract (team defenses by their documented `DST-<team>` GSIS ID); no name matching.
- Season/week: Must exactly match the verified current season and week of the lineup decision; a mismatch is BLOCKED.
- Timestamps: `source_generated_at` is the provider `generatedAt`; `retrieved_at` is the local retrieval time, kept separately.
- Freshness requirement: Age counts only under an explicitly supplied, verified JerryGM threshold. None is approved, so `freshness_state` is `UNAVAILABLE`, the threshold is `UNAPPROVED`, and the blocker `JERRYGM_FRESHNESS_THRESHOLD_UNVERIFIED` is exposed. No numeric threshold is set here.
- Exact versus partial scoring: An exact value exists only when league scoring is COMPLETE (normally QB/RB/WR/TE). When the stat line cannot reproduce a league rule exactly (commonly K and DEF), the state is DEGRADED, the value is null, and the existing range is shown (for example, 8.39–9.04 pts, partial scoring); a midpoint is never used as the score.
- Missing-data behavior: A missing, stale, blocked, or mismatched projection has a null value with state UNAVAILABLE, STALE, or BLOCKED and a manager-facing reason; it is never zero. A verified provider zero stays 0.0.
- Decision use: None. The score lives in its own `weekly_score_v2` field and never selects players, orders slots or the bench, changes decision confidence, ECR authority, kickoff locks, thresholds, or transactions. Before it could gain selection authority it needs an approved JerryGM freshness threshold, completed multi-week forward validation, and an explicit authority decision, including how partial K/DEF ranges would compete.
- Display: My Team shows it once per starting slot as "Weekly projection" (replacing the duplicate league-scored projection line) with "Preliminary" or "Partial scoring" and "informational only"; definition, coverage, freshness, and authority appear in collapsed diagnostics.
- Forward validation: Pre-kickoff snapshots (`lineup.forward_validation.snapshot.v2`) store the value or range, state, evidence level, recommendation impact, source, generated and retrieved times, season/week, scoring context and contract, completeness, freshness, blockers, and contract ID. The post-week review shows it beside final Sleeper points; because an exact v2 value is the league-scored projection, the existing projection difference is its difference. Ranges are never differenced, one week never rates projection quality, and snapshots captured before v2 show it as not captured.
- Legacy selection value (v1, `REPOSITORY_WEEKLY_SCORE`): season projection (`players.projected_points`) ÷ 17 × (1 + matchup modifier) × health multiplier, in weekly value points. It remains the only value lineup selection uses, and live My Team withholds it (`PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE`) because it has no approved automated weekly input. Its unit differs from v2, so the two are never compared, differenced, or substituted.
- Owner service or contract: `services.lineup_projection.build_weekly_score_v2` and `weekly_score_v2_basis`, attached by `services.lineup_decision_intelligence` as `players[].weekly_score_v2` and `weekly_score_v2_basis`.
- Validation tests: `tests/test_lineup_projection_foundation.py` (exact value, no ÷ 17, no matchup or health adjustment, K/DEF ranges, missing and verified zero, freshness and authority), `tests/test_lineup_decision_intelligence.py` (selection and confidence invariance, ECR display-only, `/team` display), and `tests/test_lineup_forward_validation.py` (snapshot contract, older snapshots, ranges never differenced).

## Provider Full-PPR Projection (JerryGM)
- Status: PRELIMINARY, INFORMATIONAL_ONLY on changed `/team` slots. One live read-only response verified the endpoint and response shape; 13 of 14 current Sleeper roster IDs resolved uniquely. One was unmatched. The projection is shown as provider evidence only; it does not influence decisions or confidence.
- Purpose: Supply a provider-named per-game projection for explaining a changed-slot Start/Sit decision; it is not the repository Weekly Score.
- Scale or unit: `projectedPPG`, fantasy points per game, under the echoed `ppr`, `half`, or `standard` preset.
- Source: `GET https://api.jerrygm.com/api/ext/v1/projections` with `season`, `week`, `scoring`, explicit `ids`, and `idType=sleeper`; require response `source=jgm_baseline`, echoed season/week/scoring, `generatedAt`, non-degraded response, and exactly one row per requested Sleeper ID.
- Identity: Exact Sleeper ID only. No name matching. Missing IDs or duplicate returned mappings are unavailable/blocked.
- Freshness: Age from provider `generatedAt`, not local retrieval time. Current-use freshness is `UNAVAILABLE` unless a verified JerryGM-specific threshold ID and maximum age are explicitly supplied; no production threshold is approved in this batch. A failed refresh has no current projection and never refreshes an older timestamp.
- Completeness and conflicts: Require finite numeric `projectedPPG`, exact season/week/scoring, supported source, and source attribution. Missing, mismatched, degraded, ambiguous, nonnumeric, NaN, or infinite values are unavailable/blocked; preserve verified zero. No provider averaging or cross-week/scoring joins.
- Free use: The Free API plan documents 1,000 calls/month, up to 25 explicit player IDs/names per request, preset scoring only, and required attribution. Custom weights are not available on Free; the attribution returned by the API must accompany any displayed value. The live response advertised `Cache-Control: no-store, no-cache`, so the application does not cache it.
- Limitations: Yahoo API projections are not substituted; JerryGM's provider projection remains distinct from local `players.projected_points` and from Weekly Score (Weekly Score v2 uses the league-rescored stat line, not the preset `projectedPPG`). Preset points do not equal custom league scoring unless the preset exactly matches.
- Decision use: Informational explanation only. No effect on recommendation selection/order, confidence, lineup score, or transactions. The one unmatched roster ID remains unavailable; no name join is attempted.
- League-scored comparison (committed in `a306f3a`, 2026-11-16): the provider stat line is rescored locally with the league's Sleeper scoring settings (`services/league_scoring.py`, `league-scored-projection.v1`, unit fantasy points), which makes eligible FLEX positions comparable. Team defenses are requested by their documented `DST-<team>` GSIS ID. Stat-line components that cannot reproduce league scoring exactly (commonly K/DEF) keep scoring PARTIAL and are shown as a range; a missing projection is never zero. The comparison is PRELIMINARY and `INFORMATIONAL_ONLY`: the action threshold is UNAPPROVED, so a projected edge never selects players, raises decision confidence, or authorizes a lineup change. Weekly Score v2 exposes this exact value or range as a SHADOW current-week metric (see Weekly Score). Owner: `services/lineup_projection.py`; tests: `tests/test_lineup_projection_foundation.py`.
- Owner service or contract: `services.jerrygm_projections.JerryGMProjectionClient` and `build_projection_evidence`.
- Validation tests: `tests/test_jerrygm_projections.py` fixture tests for exact IDs, scoring/season/week, timestamps, explicit-threshold freshness, zero/missing/invalid values, degraded/ambiguous responses, request limits, and failed refresh; `tests/test_ux5_lineup_route_contract.py` covers Start/Sit attribution/freshness disclosure.

## Weekly Consensus Rank (Lineup Comparator)
- Status: CONTEXT ONLY on live `/team` (`owner_operations.py` passes `consensus_authority=False`; `consensus_basis.recommendation_impact` is `DISPLAY_ONLY`); never ESTABLISHED. The same-position comparator below is implemented only behind an explicit `consensus_authority=True` caller flag and is not enabled for live lineup decisions. Waiver ordering remains the separately documented use (Roster Fit).
- Purpose: Display this week's positional consensus as reference context; when explicitly enabled, order START/SIT choices between players at the same position when the repository Weekly Score selection value (legacy v1) is unavailable.
- Scale or unit: FantasyPros average expert rank within one position for the current NFL week (QB, PPR RB/WR/TE, K, and DST pages). Lower is better. It is not projected points, expected gain, or player value, and it is never converted to points; published rank-to-points fields are ignored.
- Inputs: The evaluated `this_week` horizon from `services/dynastyprocess_rankings.py`, keyed by exact Sleeper ID through its published crosswalk, exact team-defense IDs, or the owner-approved unique name/position/team rule, with season, week, PPR scoring, and source date.
- Freshness: Source date (day precision) within the 48-hour weekly limit, and season and week equal to the lineup's verified week. Ranks for games already started are withheld; ranking or started-game diagnostics never lock a player (kickoff locks come only from the automated nflverse schedule, `services/game_lock.py`). A failed refresh never makes old ranks current.
- Missing-data behavior: Missing, stale, undated, wrong-week, wrong-scoring, position-conflicting, or invalid ranks are unranked: never zero, never worse, never inferred. Unranked or different-position alternatives are not compared; the current starter is kept.
- Decision use: None on live `/team`. Only when `consensus_authority=True` is explicitly enabled does it become the second evidence tier after a supported weekly value: within one position, a better-ranked available bench player replaces a starter who has no weekly value. An open slot is filled only when every eligible option plays one position, all are ranked, and the best rank is unique. Cross-position FLEX choices, ties, and unranked comparisons stay unresolved. Decision confidence is at most PRELIMINARY, and DEGRADED for uncertain availability or uncompared alternatives.
- Conflicts: No averaging or weights. The JerryGM provider projection stays informational; its agreement or disagreement with the deciding evidence is displayed and never changes selection or confidence.
- Owner service or contract: `services.lineup_decision_intelligence.apply_consensus_ranks` and the `consensus_basis` contract field, consuming `services.dynastyprocess_rankings`.
- Validation tests: `tests/test_lineup_decision_intelligence.py`.

## Matchup Rank
- Status: CONTRACT DEFINED; AUTHORITATIVE DISPLAY REQUIRES SUPPLIED POPULATION, DIRECTIONALITY, FRESHNESS, AND VALIDATION TESTS.
- Name: Matchup Rank.
- Purpose: Describe opponent difficulty for the player's fantasy position in the active scoring context.
- Scale or unit: Ordinal rank expressed as rank N of a documented comparison population. The population must identify the compared opponents, player position, and scoring context.
- Inputs: Supported opponent identity, player position, scoring context, matchup source, source timestamp, and source-provided rank or deterministic rank inputs.
- Directionality: The supplying contract must state whether a lower rank is easier or harder. The UI must display that direction. No default is assumed.
- Freshness requirement: Source, source timestamp or retrieved-at time, age, and freshness state are required.
- Missing-data behavior: If rank, population, directionality, source, or freshness evidence is absent or stale, display Matchup Rank as unavailable and disclose the gap. A recommendation using other supported inputs may remain PRELIMINARY if safe; use INSUFFICIENT or BLOCKED only when the remaining evidence cannot support a safe recommendation or a hard safety condition fails.
- Decision use: Provide context for START, SIT, FLEX, or MONITOR. Matchup Rank must not independently determine a decision.
- Owner service or contract: Matchup evidence supplied through the UX.2 Team Accuracy contract.
- Validation tests: Population and directionality contract tests, missing and stale evidence tests, template tests, route-payload tests, and active /team rendered-page verification.

## Matchup Signal

- Status: INFORMATIONAL ONLY until the Matchup Rank authority contract is complete.
- Purpose: Show supported directional matchup context without presenting it as an authoritative rank.
- Scale or unit: A disclosed signal such as “5th easiest defense,” tied to the supplied population, directionality, scoring context, and sample.
- Inputs: The supported matchup evidence used by Matchup Rank, including source, retrieval time, freshness, completed-game sample, and limitations.
- Evidence level: `PRELIMINARY` when current evidence is useful but the authority threshold or another rank contract field is incomplete; `ESTABLISHED` only when the governing contract permits authoritative use.
- Missing-data behavior: Show `INSUFFICIENT` or `UNAVAILABLE` when evidence cannot support a meaningful signal. Never substitute a neutral signal.
- Decision use: Matchup Signal is context only while preliminary and must not independently drive START, SIT, FLEX, MONITOR, or another recommendation. Other supported inputs may still support a separate PRELIMINARY recommendation with disclosure.
- Historical behavior: Historical evidence may inform stability, governance, baselines, and trends but may not become current-season Matchup Signal or Rank automatically.

## Roster Strength

- Preferred replacement for an unexplained overall grade.
- Components should be shown separately when supported: Starter Strength, Depth, Risk, and Playoff Readiness.
- An overall letter grade should be removed unless its formula and interpretation are documented and validated.

## Baseline

- Status: DEFINITION REQUIRED BEFORE DISPLAY
- Required meaning: The comparison population must be named, such as current starter, replacement-level player, waiver baseline, positional average, or projection baseline.
- Decision use: Show the expected advantage or disadvantage relative to the named comparison.

## Waiver Selected-Player Production Comparison

- Consumer: the selected roster player's same-position waiver cards.
- Basis: up to three latest overlapping season/week observations from the published production reader for both players, with `FULL_PPR` scoring and `FRESH` or `AGING` evidence.
- Calculation: each player's arithmetic mean over exactly those same observations; difference is candidate mean minus selected roster-player mean, in observed Full-PPR points per game.
- Verified zero is retained. Missing, non-finite, mismatched-format, or stale observations are not used; duplicate observations block the comparison. The matched seasons/weeks and sample count are displayed.
- Identity: owned roster reads reuse the same deterministically resolved Sleeper-to-GSIS identity mapping used for waiver discovery. No new name-based join is introduced.
- Authority: `PRELIMINARY`, `INFORMATIONAL_ONLY`. This is a historical comparison, not a forecast, waiver rank, confidence score, definitive ADD/DROP conclusion, or FAAB model. Candidate source order and transaction behavior remain unchanged.
- Recommendation blocker: the production reader permits informational use only. Definitive move advice still requires a separately validated valuation model and evidence contract; numeric bid guidance also requires supported valuation inputs and an actual remaining budget.

## Roster Fit

- Waiver ordering is based on fresh current-week FantasyPros PPR positional consensus ranks (ECR) delivered by DynastyProcess. Lower ECR ranks higher. It shows consensus rank, not projected points, expected gain, or player value.
- Stale ECR blocks ranking. A candidate with missing ECR remains unranked; one unranked candidate is not thereby worse than another. Historical production and usage are informational only and never fill in for missing or stale ECR or change the ordering.
- Use the manager-facing waiver recommendation vocabulary defined in the Waiver and FAAB Center section of `PAGE_REQUIREMENTS.md` for best supported, comparable, slot-fill, blocked, and player-specific outcomes.
- Weekly review compares against an actual current starter; ROS review compares against the selected roster player. Automatic starter drops and external transactions are not supported.
- FAAB guardrails, where shown, are provisional and separate from player valuation; they are not winning bids. Winning-bid estimation and player-value-to-FAAB conversion are unavailable.
- The manager-facing meanings and evidence requirements for **BEST SUPPORTED OPTION**, **COMPARABLE OPTION**, **SLOT-FILL OPTION**, **BLOCKED OPTION**, and **PLAYER-SPECIFIC OUTCOME** are defined in the Waiver and FAAB Center section of `PAGE_REQUIREMENTS.md`.

- Purpose: Explain how an add or trade addresses this team's needs.
- Required inputs: Shared Full-PPR team need, active roster slots, starter quality, depth, injury, bye week, replacement value, and positional scarcity when available.
- Missing-data behavior: Must not claim strong fit if current roster or league settings are unverified.

## Waiver Rest-of-Season Value, Materiality, and Replacement Context

- Contracts: `waiver.ros_value.v1`, `waiver.ros_materiality.v1`, and `waiver.replacement_context.v1`, owned by `services/waiver_roster_decision.py`.
- Basis: fresh FantasyPros PPR rest-of-season positional consensus (ECR) with its published best and worst expert ranks, delivered by DynastyProcess under the seven-day source-age limit in `DATA_FRESHNESS_POLICY.md`. Ranks are ordinal and position-specific (lower is better); they are never converted to points or compared across positions.
- Player states: RANKED, UNRANKED, STALE, IDENTITY_UNRESOLVED, POSITION_CONFLICT, SCORING_UNSUPPORTED, SOURCE_UNAVAILABLE, or BLOCKED. Only RANKED players are compared, and an unranked player is not thereby worse.
- Materiality: CLEAR ROS EDGE only when the candidate's worst published expert rank is better than the roster player's best. Overlapping ranges are CLOSE ROS CALL; other outcomes are COMPARABLE ROS VALUE, ROSTER PLAYER AHEAD, MATERIALITY UNVERIFIED, NOT COMPARABLE, or NOT APPLICABLE. Only CLEAR ROS EDGE can support a release.
- Replacement context: per position, the number of healthy, addable available players whose fresh expert range reaches a player's range (best published rank at or ahead of that player's worst). STRONG: two or more; LIMITED: one; SCARCE (shown as NO COMPARABLE REPLACEMENT): none; UNVERIFIED when the evidence is missing.
- Decision use: a release also requires the same position, an unprotected player whose game lock is open or a bye, and the post-move lineup check (every starting slot, including FLEX, still fillable this week and for the rest of the season). Replacement context is informational only. None of these measures produce points, percentages, a value score, or a FAAB amount.

## League FAAB Market Evidence

- Contract: `waiver.faab_market.v1`, owned by `services/waiver_market_evidence.py`; recommendation impact `INFORMATIONAL_ONLY`.
- Source: stored Sleeper transaction weeks (`GET /v1/league/{league_id}/transactions/{week}`), written only by `python refresh_sleeper_transactions.py`. The Waivers page reads stored history and never fetches transactions.
- Measures: completed and failed waiver claims with failure reasons such as a lost competing claim or a roster limit; contested and uncontested claims, grouped only by the same Sleeper player, week, and waiver run (identical Sleeper processing time), where a competing claim is another team's failed claim that Sleeper marks as claimed by another owner; observed bid distributions (lowest, highest, and median with N; a single observation is labelled) for completed, failed, contested, and uncontested claims; exact-player and same-position history, with league-wide history only when a position has no completed sample; and current team budgets (league budget minus each roster's `waiver_budget_used`).
- Bids: a bid counts only as a whole, non-negative amount within a known league budget; a missing bid is never zero. Completed bids are what Sleeper charged; failed bids were not charged. Sleeper does not publish its tie-break rule.
- Coverage: only weeks proven closed or final by later-week Sleeper transactions count; see League Transaction History in `DATA_FRESHNESS_POLICY.md`.
- Decision use: descriptive only. It never changes an ADD, DROP, MONITOR, HOLD, or PASS decision and never produces a bid amount, bid range, winning estimate, probability, or demand score.

## Confidence

- Purpose: Express evidence certainty, not player quality.
- Must be separate from projected outcome.
- Required inputs: Source availability, freshness, completeness, agreement, and blocker state.
- A high-quality player may still have low evidence confidence.

## Impact

- Purpose: Estimate how a recommendation changes weekly lineup, depth, risk, or rest-of-season outlook.
- Required presentation: Name the affected area and direction of change.
- Missing-data behavior: Do not present precise impact values without supported inputs.

## Integrity and lineage fields

- **Domain:** Data area being evaluated.
- **Status:** Whether that domain is ready, degraded, blocked, stale, or unavailable.
- **Timestamp:** When the source fact or refresh was recorded.
- **Age:** Time elapsed since the recorded timestamp.
- **Blocker:** Missing or invalid evidence that disables or lowers confidence in a recommendation.
- **Lineage:** Source and transformation path used to produce the displayed fact.

Manager-facing pages must explain which recommendation is affected. Technical detail should be collapsible.

## Survivor Win Probability

- Purpose: Estimated probability the recommended team wins its game outright this week.
- Scale: 0-100%, higher is better.
- Inputs: Market, Elo, and situational win-probability blend from `market_intelligence_predictions.model_probability`.
- Directionality: Higher is more favorable.
- Source: `market_refresh.py` / The Odds API-derived market intelligence predictions.
- Freshness: Tied to `market_updated_at` on the matched game; threshold `survivor-market-intelligence-v1` (FRESH ≤12h, AGING ≤24h, STALE beyond).
- Missing-data behavior: If the current week has no matched prediction row, the recommendation is `UNAVAILABLE`, not a neutral probability.
- Decision use: Primary driver of the current-week pick when the week is `OPEN`.
- Owner contract: `survivor_intelligence.build_recommendations`.
- Tests: `tests/test_survivor_intelligence.py`, `tests/test_survivor_status_contract.py`.

## Survivor Evidence Confidence (displayed as "Evidence Agreement Score")

- Purpose: Measures how closely market, Elo, and situational signals agree for this matchup. It is evidence certainty, not team quality, and is not a probability of the pick being correct.
- Scale: 0-100%, computed as `1 - (max(component) - min(component)) * 2`, clamped to [0,1]. Higher means more agreement.
- Inputs: `market_home_probability`, `elo_home_probability`, `situation_home_probability`.
- Directionality: Higher is more agreement (not higher win chance).
- Source: `survivor_intelligence.stability_score`.
- Freshness: Inherits the matched game's `market_updated_at`.
- Missing-data behavior: If any of the three components (`market_home_probability`, `elo_home_probability`, `situation_home_probability`) is missing, `stability_score()` returns `None` and the UI shows "Unavailable" — it no longer defaults missing components to 0.5, which previously produced a misleading 100% "agreement" when all three were absent.
- Decision use: Secondary risk signal in the Survivor Risk Center; never used to override Win Probability.
- Owner contract: `survivor_intelligence.stability_score`.
- Tests: `tests/test_survivor_intelligence.py`.

## Future Value

- Purpose: Average win probability across a team's strongest remaining scheduled games this season, to support save-for-later decisions.
- Scale: 0-100% when available; otherwise `None`/Unavailable. Never a neutral 0.50 substitute.
- Inputs: `nfl_schedule` rows for weeks after the active week, matched to `market_intelligence_predictions` via `future_predictions()`.
- Directionality: Higher means more valuable to preserve for a later week.
- Source: `survivor_intelligence.remaining_schedule_value`, which returns `{available, value, weeks, missing_reason}`.
- Freshness: Same market-intelligence freshness window as Win Probability, evaluated per matched future game.
- Missing-data behavior: `available=False`, `value=None`, `missing_reason='SURVIVOR_FUTURE_EVIDENCE_UNAVAILABLE'`. The UI shows "Unavailable" and must not say "limited future value" or "Future cost: LOW" in this case.
- Decision use: Drives Save For Later and the future-preservation term of Survivor Score, only when available.
- Owner contract: `survivor_intelligence.remaining_schedule_value`.
- Tests: `tests/test_survivor_intelligence.py::test_missing_future_evidence_is_none_not_fifty_percent`.

## Survivor Score

- Purpose: Overall strategy-weighted ranking value used to order candidates.
- Scale: 0-100%, strategy-dependent weights, higher is a stronger pick.
- Inputs and directionality:
  - When Future Value is available (`survivor_score_basis='current_future_stability'`): `current_probability * w0 + future_preservation * w1 + stability * w2`, weights per strategy (Protect Lead 0.78/0.12/0.10, Balanced 0.72/0.18/0.10, Gain Ground 0.66/0.24/0.10).
  - When Future Value is unavailable (`survivor_score_basis='current_stability_only'`): recalculated from supported components only — `current_probability * w0 + stability * w1` (Protect Lead 0.90/0.10, Balanced 0.88/0.12, Gain Ground 0.85/0.15). This is a disclosed, reduced-scope formula, not the same score with a hidden neutral substitute.
- Missing-data behavior: The `survivor_score_basis` field must always be disclosed alongside the score so the manager knows whether future preservation was included.
- Decision use: Determines candidate ranking/ordering.
- Owner contract: `survivor_intelligence.build_recommendations`.
- Tests: `tests/test_survivor_intelligence.py::test_strategy_names_resolve_to_current_implemented_weights`.

## Future Opportunity Cost

- Purpose: Manager-facing statement of the cost of using a team now versus saving it, derived only from Future Value.
- Scale: LOW / MEDIUM / HIGH (thresholds: HIGH ≥70%, MEDIUM ≥58%, otherwise LOW) — only when Future Value is available. Otherwise "Unavailable".
- Inputs: `future_available`, `future_value`.
- Directionality: HIGH means a greater cost to using the team now (more valuable to save).
- Missing-data behavior: Must render "Unavailable", never "LOW", when Future Value is unavailable.
- Decision use: Displayed in the Pick This Week hero as "Future cost".
- Owner contract: `templates/survivor_intelligence.html` primary-card block, `survivor_intelligence.build_recommendations`.
- Tests: `tests/test_survivor_intelligence.py::test_missing_future_evidence_is_none_not_fifty_percent`.
