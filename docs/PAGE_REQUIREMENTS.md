# Season-Management Page Requirements

## Shared requirements for all six pages

- Use shared league, roster, ownership, team-needs, freshness, and explanation contracts.
- Show decision-critical source and freshness in manager-friendly language.
- Fail closed for stale, unavailable, or contradictory evidence.
- Explain every displayed score, rank, baseline, grade, fit, confidence, and impact value.
- Put recommended action and fantasy impact before technical diagnostics.
- Preserve read-only decision support.

## All-Season Page Quality Standard

Each page must earn advancement independently. Technical tests are necessary but insufficient: the current page must also be trustworthy, action-oriented, explainable, useful in unavailable or degraded states, readable on desktop and mobile, and valuable during normal weekly use before work moves to another page.

## Fantasy Intelligence Dashboard

### Must show
- Current league and season context when verified
- Draft state and start time when verified
- Date/time formatted as Month Day, Year, Time with Pacific Time zone label
- Data last checked
- Highest-priority action or alert
- Agreement with overlapping My Team and Weekly Command Center facts

### Must not show
- Raw timestamps
- Unsupported states without explanation
- Hard-coded or stale values presented as current

## My Team

### Must show
- Full-PPR team needs for QB, RB, WR, TE, FLEX, K, and DEF
- Starter Strength, Depth, Risk, and Playoff Readiness when supported
- Recommended lineup with player, opponent, projection or supported weekly value, matchup context, health, confidence, and reason
- Current health source and age
- “Why this recommendation is trusted” summary

### Must explain or remove
- Overall grade
- Weekly Score
- Matchup rank
- Redundant slot and position presentation

## Weekly Lineup Intelligence

### Must show
- START, SIT, FLEX, or MONITOR decisions
- Manager-facing lineup readiness
- Baseline definition
- Weekly Score definition
- Matchup and health evidence
- Exact recommendation affected by each blocker
- League-slot-valid recommended lineup

### Must not show
- Ambiguous HOLD decisions
- Unknown values presented as neutral
- Technical integrity fields without fantasy impact

## Waiver and FAAB Center

### Must show
- Candidates verified as unrostered
- Ownership and eligibility source and freshness
- Shared team need
- Roster fit
- Suggested drop candidate when supported
- Expected role and duration of opportunity
- Recommendation risk and evidence confidence
- FAAB rationale rather than unsupported precision

### Blocking rule
- If ownership or eligibility cannot be verified, the candidate recommendation list is blocked.

## Trade Target Center

### Must show
- Why the target fits this roster
- Team weakness addressed
- Assets given up
- Weekly, depth, risk, and rest-of-season impact when supported
- Counterparty fit and feasibility when supported
- Schedule, bye-week, injury, and positional-surplus effects

### Must distinguish
- Good player
- Good trade value
- Good trade for this roster

## Weekly Command Center

### Primary sections
1. Start/Sit
2. Waiver/Drop
3. Trade Watch
4. Injury/Availability
5. Upcoming Risk
6. Data Alerts

### Must show
- Highest-impact action first
- Deadline
- Confidence
- Expected benefit
- Blocked or degraded recommendations and why

### Technical detail
- Integrity and lineage diagnostics should be secondary and collapsible.

## Survivor Intelligence (UX.8)

Survivor Intelligence is not one of the six season-management pages above but reuses the shared requirements (freshness, fail-closed, explainability, action-first ordering, read-only decision support).

### Must show
- Verified survivor season and week; never a guessed or hard-coded active week
- Used-team history, sourced from verified persistence, not inferred from an empty read
- Exact used-team exclusion from any current or future recommendation
- An explicit already-selected week state (`PENDING_RESULT` or `COMPLETED`) whenever a selection already exists for the requested week, showing the recorded team and result as the primary fact
- Exactly one supported current-week action, and only when the requested week is verified `OPEN` (no existing selection, verified schedule week)
- Alternatives only when they are actionable and eligible for an `OPEN` week
- Win probability displayed separately from evidence confidence; confidence must not be presented as a probability of correctness
- Future opportunity cost only when supported by verified future schedule and prediction evidence; otherwise Unavailable, never a neutral fallback value
- Truthful multi-week roadmap unavailability when no supported optimizer exists
- The exact recommendation effect (DEGRADED/BLOCKED/UNAVAILABLE) of stale or missing evidence, with a disclosed reason code
- Read-only behavior toward any external survivor platform; no external transaction is ever submitted
- Manager-friendly (Pacific Time) retrieval/verification time, with the raw source timestamp preserved only in collapsed lineage
- Collapsed-by-default full rankings, metric explanations, and data-quality/lineage sections; rankings for an already-selected week are labeled "Model snapshot for Week N (non-actionable)"

### Must not show
- A second actionable recommendation or "Record team as pick" control for a week that already has a recorded selection
- A neutral 50% (or other invented) Future Value when future schedule/prediction evidence is unavailable
- "Future cost: LOW/MEDIUM/HIGH" unless future evidence actually supports it
- A guessed next survivor week; if unverifiable, render "NEXT WEEK UNAVAILABLE"
- Public pick percentage or leverage data (not sourced from a supported provider)

### Blocking rule
- A history-read failure must render `ELIGIBILITY BLOCKED` and publish no recommendation; it must never be treated as "no teams used yet."