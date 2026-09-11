# Development Roadmap

## Current checkpoint
- Date: 2026-09-11
- Branch: feature/evidence-bundle-pipeline
- HEAD: 8c8480e49c4dfff1c857a5ffaa06c3e6f4c91e30
- Previously recorded HEAD: 6c97d30f20c4d9e9becf9ccf1007ef5b84e8b3d9
- Repository reality must be rechecked before the next completion claim or canonical synchronization.

## Completed verified track
- Data Integrity A.1 through A.10 remains complete or validated at its recorded boundaries.
- The UX.1 through UX.7 reconciliation foundation remains installed and previously validated.
- Those earlier validations do not close the new QA findings below.

## Highest-priority QA findings and product direction

The following items were reported during hands-on QA review on 2026-09-11. They are now the highest-priority workstream. They are treated as reported defects or usability findings until reproduced against the active routes and verified with repository and runtime evidence.

### Pages in scope
- Fantasy Intelligence Dashboard
- My Team
- Weekly Lineup Intelligence
- Waiver and FAAB Center
- Trade Target Center
- Weekly Command Center

### Cross-page requirements
1. **Eliminate stale or misleading data.** Every user-facing value must identify its source, refresh time, freshness state, and failure behavior. Values that cannot be verified must fail closed as unavailable rather than appearing current.
2. **Use Sleeper as the first-choice live source.** Sleeper league, roster, ownership, draft, matchup, and player-status data should be preferred where the API supports the required field. Local persistence may cache or enrich the response, but must not silently override newer Sleeper truth.
3. **Make team-needs analysis complete and Full-PPR aware.** Needs must evaluate QB, RB, WR, TE, FLEX, K, and DEF. No required roster position may be excluded. The model must derive roster slots from league settings and explain how Full-PPR strategy affects positional need.
4. **Prevent invalid waiver recommendations.** A player already rostered anywhere in the active league must not appear as an available waiver recommendation. If current ownership cannot be verified, recommendations must be blocked or clearly marked unverified.
5. **Translate technical evidence into fantasy impact.** Integrity, lineage, freshness, status, score, timestamp, age, domain, and blocker fields must explain what they mean, whether they affect a recommendation, and what the manager should do next.
6. **Make every score interpretable.** Weekly score, matchup rank, grade, baseline, confidence, roster fit, and impact metrics must show their scale, inputs, directionality, and decision use. Unsupported or partially populated scores must not be presented as authoritative.
7. **Keep the system read-only.** Recommendations may support team management decisions, but no external fantasy transaction may be submitted automatically.

### Product outcome
The application should prioritize trustworthy weekly team management: who to start, sit, monitor, add, drop, trade for, trade away, and protect against upcoming schedule, injury, depth, and playoff risk.


## New top milestone

**UX-QA.1: Live Data Trust, Ownership Correctness, and Cross-Page Decision Clarity**

This milestone supersedes the narrower UX.1-only next-step framing. Dashboard truth auditing remains included, but the active priority is now a coordinated correction across all six season-management pages.

### Workstream 1: Source and freshness audit
- Inventory every visible field on all six pages and map it to route, service, database field, API endpoint, timestamp, staleness threshold, and fallback.
- Verify Sleeper-first behavior for supported league, roster, ownership, draft, matchup, and player-status fields.
- Add a shared freshness contract with source, retrieved-at time, age, state, and blocker reason.
- Define freshness thresholds by domain instead of using one global threshold.
- Prevent cached data from being displayed as current when an attempted live refresh fails.
- Add page-level and cross-page tests proving values agree when they share the same underlying fact.

### Workstream 2: League and roster truth
- Rebuild the current ownership map from the active Sleeper league rosters before waiver or trade recommendations are generated.
- Exclude every owned player from waiver recommendations.
- Block recommendations when ownership or eligibility cannot be verified.
- Derive roster requirements from active league settings and normalize DST to DEF consistently.
- Calculate team need for QB, RB, WR, TE, FLEX, K, and DEF using Full-PPR strategy, starter quality, replacement value, depth, bye-week coverage, injury risk, and positional scarcity.
- Ensure My Team, Waivers, Trades, Lineup, Dashboard, and Weekly Command Center consume a shared team-needs result.

### Workstream 3: Page-specific corrections

#### Fantasy Intelligence Dashboard
- Format draft date and start time as `Month Day, Year, Time` in Pacific Time, with timezone label.
- Replace raw numeric timestamps.
- Support Season State and Draft State from verified evidence, or hide/fail closed with a useful explanation.
- Reconcile overlapping league and weekly facts with My Team and Weekly Command Center.
- Replace technical status clutter with a concise “Data last checked” and “Action required” presentation.

#### My Team
- Replace or rename the unexplained grade with actionable dimensions such as Starter Strength, Depth, Risk, and Playoff Readiness. Remove the grade if its calculation cannot be explained and validated.
- Document Weekly Score, including scale, formula inputs, and effect on lineup recommendations.
- Remove redundant lineup columns and emphasize opponent, projection, matchup context, health, confidence, and explanation.
- Repair missing matchup ranks and distinguish unavailable data from a poor matchup.
- Refresh health data from supported sources and expose source and age.
- Redesign Roster Identity and Data Lineage into a manager-facing “Why this recommendation is trusted” summary, with technical details collapsed by default.

#### Weekly Lineup Intelligence
- Replace the technical Lineup Data Integrity section with a manager-facing readiness summary and an optional technical detail view.
- Resolve integrity blockers or identify the exact recommendation each blocker disables.
- Explain domain, status, score, timestamp, and age in context.
- Replace ambiguous HOLD decisions with START, SIT, FLEX, or MONITOR, supported by explicit criteria.
- Define baseline, Weekly Score, matchup rank, health state, and confidence.
- Replace “rank unavailable,” “injury unknown,” and “ownership unknown” with fail-closed explanations and next actions.
- Ensure the recommended starting lineup conforms to league slots and excludes unavailable evidence from unsupported scoring claims.

#### Waiver and FAAB Center
- Refresh league rosters before candidate selection.
- Exclude all rostered players and test this invariant at the service and route layers.
- Use the shared Full-PPR team-needs model for ranking and FAAB guidance.
- Explain availability evidence, eligibility, source age, roster fit, drop candidate, expected role, opportunity path, and recommendation risk.
- Prevent FAAB precision when the supporting role, projection, ownership, or market evidence is missing.

#### Trade Target Center
- Use the shared Full-PPR team-needs model for roster fit.
- Explain why each target helps, what weakness it addresses, what is being given up, and the expected weekly and rest-of-season effect.
- Add counterparty fit, positional surplus, schedule, injury, bye-week, and depth consequences.
- Distinguish “good player” from “good trade for this roster.”

#### Weekly Command Center
- Redesign around weekly management actions rather than raw integrity output.
- Primary sections: Start/Sit, Waiver/Drop, Trade Watch, Injury/Availability, Upcoming Risk, and Data Alerts.
- Show the highest-impact action first, with evidence, confidence, deadline, and expected benefit.
- Keep integrity diagnostics secondary and connect every blocker to a disabled or reduced-confidence recommendation.

### Workstream 4: Missing data and strategic enhancements
- Rest-of-season projections and rankings with source and update time.
- Opportunity metrics: snaps, routes, targets, carries, red-zone usage, and role trend where licensed/available.
- Opponent and schedule strength by position.
- Injury practice participation and game-status trend.
- Bye-week and roster-depth exposure.
- Replacement-level and waiver-wire baseline by position.
- League transaction and manager tendency history.
- Trade value, roster surplus, and counterparty need.
- Playoff schedule and scenario analysis.
- Projection disagreement and uncertainty ranges.

### Suggested additional pages
1. **Season Strategy Center:** playoff outlook, remaining schedule, roster strengths, weak points, and recommended strategic posture.
2. **Roster Risk and Depth Map:** starter quality, backup quality, injury exposure, bye-week conflicts, and replacement options by position.
3. **Rest-of-Season Planner:** rankings, schedule, role trend, playoff-week outlook, and hold/sell/buy guidance.
4. **Transaction Planner:** prioritized add/drop, FAAB, and trade actions with dependencies and deadlines.
5. **Opponent and Matchup Scout:** likely opposing lineup, positional strengths, projected matchup leverage, and contingency planning.

## Definition of done for UX-QA.1
- Every reported issue is reproduced or explicitly closed as not reproducible with evidence.
- All six pages display current or explicitly unavailable data.
- Sleeper-first source priority is proven for supported fields.
- Recommended waiver players are not rostered in the active league.
- Team need covers QB, RB, WR, TE, FLEX, K, and DEF and reflects active Full-PPR settings.
- Shared facts agree across pages.
- Every user-facing score and status has an explanation and scale.
- Technical evidence is linked to its fantasy-management impact.
- Focused route, service, template, stale-data, failure, and cross-page agreement tests pass.
- Python compile checks and both Git whitespace checks pass.
- Canonical synchronization and bundle validation pass after the final update.

## Deferred until trust milestone closes
- New advanced intelligence engines should not take precedence over ownership correctness, freshness, lineup clarity, waiver validity, and cross-page consistency.
- PostgreSQL replay/parity, failure injection, rollback, recovery, cleanup, repeatability, and production proof remain outstanding validation tracks.

## Next milestone

**Complete UX-QA.1: Live Data Trust, Ownership Correctness, and Cross-Page Decision Clarity.**
