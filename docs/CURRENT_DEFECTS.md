# Current Defects and QA Findings

## Status rules

- **REPORTED:** observed during hands-on QA but not yet reproduced in a controlled test.
- **REPRODUCED:** confirmed on the active route with evidence.
- **IN PROGRESS:** implementation work has started.
- **VALIDATED:** focused tests and active-route verification passed.
- **CLOSED:** repair is committed and continuity validation passed.
- **NOT REPRODUCIBLE:** investigated but not confirmed, with evidence recorded.

## P0: Trust and invalid-decision risk

### UXQA-001: Rostered players appear in waiver recommendations
- Status: REPORTED
- Page: Waiver and FAAB Center
- Risk: Invalid add advice and loss of trust.
- Required proof: Current league ownership map from Sleeper, service test, route test, and rendered-page verification.
- Acceptance: Every recommended player is absent from every active league roster; unverified ownership blocks the list.

### UXQA-002: Data freshness is unclear or stale across core pages
- Status: REPORTED
- Pages: All six season-management pages
- Risk: Lineup, waiver, trade, and injury decisions may use outdated facts.
- Required proof: Field-to-source inventory, retrieved-at timestamp, age, freshness state, stale threshold, and failure behavior.
- Acceptance: Every decision-critical field is current, explicitly stale, or unavailable.

### UXQA-003: Ownership, eligibility, health, matchup, and lineage contain unknown or stale states
- Status: REPORTED
- Pages: My Team, Weekly Lineup Intelligence, Waiver and FAAB Center, Weekly Command Center
- Risk: Recommendations may appear authoritative without required evidence.
- Acceptance: Unknown evidence reduces confidence or blocks the affected recommendation, with a manager-facing explanation.

## P1: Recommendation correctness and completeness

### UXQA-004: Team needs are incomplete or inconsistent
- Status: REPORTED
- Pages: My Team, Waiver and FAAB Center, Trade Target Center, Weekly Command Center
- Required positions: QB, RB, WR, TE, FLEX, K, DEF
- Strategy: Active Full-PPR league settings
- Acceptance: One shared team-needs result is used across all relevant pages and explains need drivers.

### UXQA-005: Lineup decisions use ambiguous language
- Status: REPORTED
- Page: Weekly Lineup Intelligence
- Problem: HOLD does not clearly mean start, sit, flex, or monitor.
- Acceptance: Decisions use START, SIT, FLEX, or MONITOR with explicit criteria and confidence.

### UXQA-006: Scores and ranks are not interpretable
- Status: REPORTED
- Metrics: Weekly Score, matchup rank, grade, baseline, roster fit, confidence, impact
- Acceptance: Each displayed metric links to a definition, scale, inputs, direction, missing-data behavior, and decision use.

## P2: Visual clarity and page design

### UXQA-007: Draft timestamp is shown as a raw value
- Status: REPORTED
- Page: Fantasy Intelligence Dashboard
- Acceptance: Month Day, Year, Time with an explicit Pacific Time zone label.

### UXQA-008: Unsupported season and draft states are confusing
- Status: REPORTED
- Page: Fantasy Intelligence Dashboard
- Acceptance: Supported evidence is shown, or the field is hidden/fails closed with a useful explanation.

### UXQA-009: Technical integrity and lineage panels do not explain fantasy impact
- Status: REPORTED
- Pages: My Team, Weekly Lineup Intelligence, Waiver and FAAB Center, Weekly Command Center
- Acceptance: Manager-facing impact is primary; technical details are collapsed and identify any blocked recommendation.

### UXQA-010: Weekly Command Center is not action-first
- Status: REPORTED
- Page: Weekly Command Center
- Acceptance: Prioritized Start/Sit, Waiver/Drop, Trade Watch, Injury/Availability, Upcoming Risk, and Data Alerts sections.

## Closure evidence required

A defect may move to VALIDATED only when its focused test evidence and active-route evidence are recorded. A defect may move to CLOSED only after the intended commit is reviewed and canonical and bundle validation pass.
