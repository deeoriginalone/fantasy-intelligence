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
