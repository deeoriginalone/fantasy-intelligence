# Metric Definitions and Display Contract

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

## Weekly Score

- Status: DEFINITION REQUIRED BEFORE AUTHORITATIVE DISPLAY
- Purpose: Summarize weekly starting value.
- Required scale: Must explicitly state whether it is 0-100, points, percentile, or another unit.
- Required inputs: Projection, opportunity, matchup, health, and evidence confidence only when those inputs are available and supported.
- Missing-data behavior: Must not silently substitute a neutral value. Reduce confidence, show unavailable, or block the score.
- Decision use: Support START, SIT, FLEX, or MONITOR decisions.

## Matchup Rank
- Status: CONTRACT DEFINED; AUTHORITATIVE DISPLAY REQUIRES SUPPLIED POPULATION, DIRECTIONALITY, FRESHNESS, AND VALIDATION TESTS.
- Name: Matchup Rank.
- Purpose: Describe opponent difficulty for the player's fantasy position in the active scoring context.
- Scale or unit: Ordinal rank expressed as rank N of a documented comparison population. The population must identify the compared opponents, player position, and scoring context.
- Inputs: Supported opponent identity, player position, scoring context, matchup source, source timestamp, and source-provided rank or deterministic rank inputs.
- Directionality: The supplying contract must state whether a lower rank is easier or harder. The UI must display that direction. No default is assumed.
- Freshness requirement: Source, source timestamp or retrieved-at time, age, and freshness state are required.
- Missing-data behavior: If rank, population, directionality, source, or freshness evidence is absent or stale, display “Unavailable” and reduce confidence or block only the affected matchup-sensitive recommendation.
- Decision use: Provide context for START, SIT, FLEX, or MONITOR. Matchup Rank must not independently determine a decision.
- Owner service or contract: Matchup evidence supplied through the UX.2 Team Accuracy contract.
- Validation tests: Population and directionality contract tests, missing and stale evidence tests, template tests, route-payload tests, and active /team rendered-page verification.

## Roster Strength

- Preferred replacement for an unexplained overall grade.
- Components should be shown separately when supported: Starter Strength, Depth, Risk, and Playoff Readiness.
- An overall letter grade should be removed unless its formula and interpretation are documented and validated.

## Baseline

- Status: DEFINITION REQUIRED BEFORE DISPLAY
- Required meaning: The comparison population must be named, such as current starter, replacement-level player, waiver baseline, positional average, or projection baseline.
- Decision use: Show the expected advantage or disadvantage relative to the named comparison.

## Roster Fit

- Purpose: Explain how an add or trade addresses this team's needs.
- Required inputs: Shared Full-PPR team need, active roster slots, starter quality, depth, injury, bye week, replacement value, and positional scarcity when available.
- Missing-data behavior: Must not claim strong fit if current roster or league settings are unverified.

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
