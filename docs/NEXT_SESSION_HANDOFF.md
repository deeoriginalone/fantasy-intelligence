# Fantasy Intelligence Session Handoff

## Operational verdict

Do not begin lower-priority strategic engine work before addressing the new QA findings. The next session should treat data freshness, ownership correctness, complete Full-PPR team needs, and clear weekly decision support as the highest priority. Earlier UX reconciliation tests remain useful evidence for the contracts they covered, but they do not close the active-route issues reported on 2026-09-11.

## Current checkpoint
- Date: 2026-09-11
- Branch: feature/evidence-bundle-pipeline
- HEAD: 8c8480e49c4dfff1c857a5ffaa06c3e6f4c91e30
- Previously recorded HEAD: 6c97d30f20c4d9e9becf9ccf1007ef5b84e8b3d9
- Repository: /home/deeoriginalone/fantasy-intelligence

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


## Immediate next work

### 1. Preserve and classify the working tree
- Capture current branch, HEAD, status, staged diff, unstaged diff, and untracked inventory.
- Do not use `git add .` or `git add -A`.
- Keep canonical-doc updates separate from source fixes, generated bundles, and cleanup changes.

### 2. Reproduce the QA findings
- Open each of the six active routes with the current league.
- Record every visible field, value, source, timestamp, and apparent contradiction.
- Capture examples of rostered players in waiver recommendations, missing matchup rank, stale health, unknown ownership, unsupported states, raw draft time, and unclear scoring.
- Convert each confirmed issue into a focused failing test before repair where practical.

### 3. Build the shared live-data truth layer
- Create or consolidate a Sleeper-first source adapter for league, rosters, ownership, draft, matchup, and supported player status.
- Attach source, retrieved-at timestamp, age, freshness state, and blocker to page payloads.
- Define per-domain stale thresholds.
- Fail closed when live refresh fails and cached data is beyond threshold.

### 4. Repair ownership and waiver correctness first
- Build the active-league ownership map before recommendations.
- Exclude every owned player.
- Block the list if ownership or eligibility cannot be verified.
- Add service, route, and rendering tests proving no recommended player is rostered.

### 5. Rebuild shared Full-PPR team needs
- Derive active slots and requirements from league settings.
- Include QB, RB, WR, TE, FLEX, K, and DEF.
- Account for starter quality, depth, injury, bye week, replacement value, positional scarcity, and Full-PPR weighting.
- Reuse one result across My Team, Waivers, Trades, Lineup, Dashboard, and Weekly Command Center.

### 6. Fix pages in decision-risk order
1. Waiver and FAAB Center
2. Weekly Lineup Intelligence
3. My Team
4. Weekly Command Center
5. Fantasy Intelligence Dashboard
6. Trade Target Center

This order prioritizes invalid transaction advice and starting-lineup risk before broader visual modernization.

### 7. Improve explanations and visuals
- Define all scores, ranks, baselines, confidence states, and grades.
- Rename or remove metrics that do not support a decision.
- Use START, SIT, FLEX, and MONITOR instead of HOLD.
- Put manager action and expected impact first.
- Collapse lineage and integrity diagnostics behind a “Why this is trusted” detail view.
- Format draft date/time in Pacific Time.

### 8. Add strategic management capability after trust is restored
- Rest-of-season planner.
- Roster risk and depth map.
- Season strategy and playoff outlook.
- Transaction planner.
- Opponent and matchup scout.

## Validation required before completion claims
- Current ownership and eligibility tests.
- Stale, missing, partial, and API-failure tests.
- Full-PPR roster requirement tests for QB, RB, WR, TE, FLEX, K, and DEF.
- Cross-page agreement tests.
- Score/explanation rendering tests.
- Date/time and timezone rendering tests.
- Active-route checks for all six pages.
- Python compile validation.
- `git diff --check` and `git diff --cached --check`.
- Canonical synchronization and bundle validation after installation.

## Completion boundary
- Treat every new QA item as open until it is reproduced, fixed, tested, and verified on the active route.
- Do not claim the six-page UX scope complete solely because prior focused tests passed.
- No external fantasy transaction submission is authorized.

## Next milestone

**Complete UX-QA.1: Live Data Trust, Ownership Correctness, and Cross-Page Decision Clarity.**
