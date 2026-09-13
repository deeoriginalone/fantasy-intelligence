## Current Defects and QA Findings

### Status rules
- **REPORTED:** observed during hands-on QA but not yet reproduced in a controlled test.
- **REPRODUCED:** confirmed on the active route with evidence.
- **IN PROGRESS:** implementation work has started.
- **VALIDATED:** focused tests and required active-route verification passed.
- **CLOSED:** repair is committed and continuity validation passed.
- **NOT REPRODUCIBLE:** investigated but not confirmed, with evidence recorded.

### P0: Trust and invalid-decision risk

#### UXQA-001: Rostered players appear in waiver recommendations
- Status: IN PROGRESS
- Page: Waiver and FAAB Center
- Risk: Invalid add advice and loss of trust.
- Required proof: Current league ownership map from Sleeper, service test, route test, and rendered-page verification.
- Acceptance: Every recommended player is absent from every active league roster; unverified ownership blocks the list.
- Current evidence: Shared stable-ID filtering, configured roster-coverage diagnostics, and fail-closed ownership/eligibility blockers are implemented and focused-tested. The active `/waivers` and `/gm` routes return blocked states with zero published candidates when required evidence is unsupported.
- Remaining proof: Complete fresh active-league ownership evidence, verified freshness thresholds, independent add-eligibility evidence, successful publication-path route tests, and rendered supported-state verification. This defect is not VALIDATED or CLOSED.

#### UXQA-002: Data freshness is unclear or stale across core pages
- Status: VALIDATED
- Pages: All six season-management pages
- Risk: Lineup, waiver, trade, and injury decisions may use outdated facts.
- Required proof: Field-to-source inventory, retrieved-at timestamp, age, freshness state, stale threshold, and failure behavior.
- Acceptance: Every decision-critical field is current, explicitly aging, stale, unavailable, or blocked.
- Additional My Team finding: The page must show health source, age or last-verified time, freshness, and the recommendation impact of stale or unavailable evidence.

#### UXQA-003: Ownership, eligibility, health, matchup, and lineage contain unknown or stale states
- Status: VALIDATED
- Pages: My Team, Weekly Lineup Intelligence, Waiver and FAAB Center, Weekly Command Center
- Risk: Recommendations may appear authoritative without required evidence.
- Additional My Team finding: Unknown health and missing matchup evidence are visible, but their manager-facing effect must be consistently targeted to each affected recommendation.
- Required repair: Reduce confidence, use MONITOR, make the affected component unavailable, or block the exact recommendation according to the evidence contract. Unknown health may not be displayed as healthy.
- Required proof: Health and matchup service tests, route-payload tests, defensive template tests, and rendered `/team` verification.
- Acceptance: Unknown evidence reduces confidence or blocks the affected recommendation, with a manager-facing explanation.

### P1: Recommendation correctness and completeness

#### UXQA-004: Team needs are incomplete or inconsistent
- Status: VALIDATED
- Pages: My Team, Waiver and FAAB Center, Trade Target Center, Weekly Command Center
- Required positions: QB, RB, WR, TE, FLEX, K, DEF
- Strategy: Active Full-PPR league settings
- Additional My Team finding: The rendered summary can identify a position as an add-depth priority while the detailed positional table presents the same position as unqualified COVERED.
- Required repair: Use one shared result and distinguish minimum starter coverage, desired depth, strategic weakness, injury-driven need, bye-week risk, FLEX competition, and unavailable analysis when supported.
- Required proof: Service consistency tests, route-payload tests, cross-page contract tests, and rendered `/team` verification.
- Acceptance: One shared Team Needs result is used across all relevant pages, explains need drivers, and cannot produce contradictory summary and detail states.

#### UXQA-005: Lineup decisions use ambiguous language
- Status: REPORTED
- Page: Weekly Lineup Intelligence
- Problem: HOLD does not clearly mean start, sit, flex, or monitor.
- Acceptance: Decisions use START, SIT, FLEX, or MONITOR with explicit criteria and confidence.

#### UXQA-006: Scores and ranks are not interpretable
- Status: VALIDATED
- Metrics: Weekly Score, matchup rank, grade, baseline, roster fit, confidence, impact
- Additional My Team finding: Overall Grade and aggregate Weekly Starter Score remain prominent without the complete authoritative metric contract. Missing weekly evidence must not be visually indistinguishable from verified zero.
- Required repair: Remove unsupported metrics or provide definition, scale, inputs, directionality, freshness requirement, missing-data behavior, decision use, owner service or contract, and validation tests.
- Required proof: Metric-contract tests, route-payload tests, defensive template tests, and rendered `/team` verification.
- Acceptance: Each displayed metric has a definition, scale or unit, inputs, directionality, freshness requirement, missing-data behavior, decision use, owner, and validation tests. Unavailable values are distinct from verified zero.

#### UXQA-011: My Team lineup recommendations lack complete manager-facing explanation
- Status: VALIDATED
- Page: My Team
- Risk: A recommended starter may be presented without enough evidence to understand why the player was selected or how uncertainty affects the decision.
- Required repair: Each supported recommendation must include player, assigned slot, opponent, supported weekly value, matchup context, health, confidence, reason, and any targeted blocker. Health uncertainty must reduce confidence or trigger MONITOR when appropriate.
- Required proof: Recommendation-service tests, route-payload tests, defensive template tests, and rendered `/team` verification.
- Acceptance: Every supported My Team recommendation explains what to do, why, evidence confidence, and the exact impact of missing or degraded evidence.

### P2: Visual clarity and page design

#### UXQA-007: Draft timestamp is shown as a raw value
- Status: REPORTED
- Page: Fantasy Intelligence Dashboard
- Acceptance: Month Day, Year, Time with an explicit Pacific Time zone label.

#### UXQA-008: Unsupported season and draft states are confusing
- Status: REPORTED
- Page: Fantasy Intelligence Dashboard
- Acceptance: Supported evidence is shown, or the field is hidden or fails closed with a useful explanation.

#### UXQA-009: Technical integrity and lineage panels do not explain fantasy impact
- Status: VALIDATED
- Pages: My Team, Weekly Lineup Intelligence, Waiver and FAAB Center, Weekly Command Center
- Additional My Team finding: Technical roster lineage is prominent and includes repeated unknown states without consistently making the fantasy impact primary.
- Required repair: Put action and impact first; collapse technical details by default; identify the exact affected recommendation; keep raw blocker codes secondary.
- Required proof: Template structure tests and rendered `/team` verification.
- Acceptance: Manager-facing impact is primary; technical details are collapsed and identify any blocked or degraded recommendation.

#### UXQA-010: Weekly Command Center is not action-first
- Status: REPORTED
- Page: Weekly Command Center
- Acceptance: Prioritized Start/Sit, Waiver/Drop, Trade Watch, Injury/Availability, Upcoming Risk, and Data Alerts sections.

### UX.2 validation matrix required for status changes

#### Metric authority
- Overall Grade is absent unless fully defined and validated.
- Aggregate Weekly Starter Score is absent unless fully defined and validated.
- Missing weekly evidence renders Unavailable, not numeric zero.
- Verified zero remains distinguishable from unavailable.
- Projection and evidence confidence render separately.
- Matchup Rank meaning, population, directionality, and unavailable behavior are explicit.

#### Team Needs
- QB, RB, WR, TE, FLEX, K, and DEF are represented for supported Full-PPR settings.
- Starter coverage and depth target are separate states.
- Summary and detail consume the same result and cannot contradict each other.
- League-settings or roster-truth failures make affected calculations unavailable.
- Need drivers are manager-facing and evidence-based.

#### Health and freshness
- Unknown health is not converted to healthy.
- Stale or unavailable health reduces confidence or blocks the affected recommendation.
- Health source, age, freshness, and last-verified information reach the template when available.
- Failed refreshes do not make stale cache appear current.
- Only affected recommendations are degraded.

#### Recommendation behavior
- Complete evidence produces a decision, confidence, and reason.
- Material health uncertainty produces MONITOR or reduced confidence.
- Missing required evidence blocks the affected recommendation.
- Route payloads carry supported player, slot, opponent, value, health, confidence, reason, and blockers.
- The recommended lineup respects active league slots.

### UX.2.1 hardening findings

- Compact recommendation, trust, risk, bench, Team Needs, and roster-outlook presentation is in progress for My Team.
- This hardening work supplements the validated UX.2 correctness boundary and does not reopen validated correctness defects.
- The All-Season Usability Gate passed with isolated fresh desktop and 390px browser captures for all required states; UX.2.1 remains separate from defect closure.

### UX.2.1C owner finding: health source freshness

- Root cause repaired: `/team` now wires the authoritative `injury_reports` source and latest `report_date` into Team Health instead of hard-coding unavailable freshness.
- Current repository data reports the latest injury report date as `2026-09-07`, so the page truthfully renders `STALE`; this is a source-freshness condition, not a UI placeholder.
- Owner acceptance remains pending.

#### Presentation and active-route proof
- The priority action appears before technical diagnostics.
- Technical lineage is collapsed by default.
- Manager-facing blocker impact is visible without opening raw lineage.
- `/team` renders supported, degraded, unavailable, and blocked states correctly.
- The final render contains no unexplained grade, undefined aggregate score, contradictory Team Needs message, or supported recommendation without confidence and reason.

### Closure evidence required

A defect may move to REPRODUCED only after controlled active-route evidence confirms it. A defect may move to IN PROGRESS only after implementation work starts. A defect may move to VALIDATED only when focused tests and required active-route verification pass. A defect may move to CLOSED only after the intended commit is reviewed and canonical and bundle validation pass.
