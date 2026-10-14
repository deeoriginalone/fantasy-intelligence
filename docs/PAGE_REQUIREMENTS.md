# Season-Management Page Requirements

## Fantasy Intelligence 2.0 Page Direction

The six primary destinations are Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. The Command Center summarizes Start/Sit, Waivers, Trades, Survivor, What Changed, and alerts, then links to owning pages instead of duplicating their engines.

Page work is decision-first, league-specific, personal-use, informational-first, and proportional to manager value. Existing page contracts and read-only behavior remain preserved.

## Evidence-first page rule

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe; prohibited or unpermitted use remains blocked. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Specific metric/page contracts may restrict an individual signal to context-only when that signal alone cannot safely support a recommendation.

## Navigation Reconciliation Target

Primary navigation is planned as Command Center, My Team, Waivers, Trades, Survivor, NFL Intelligence, and What Changed. Command Center summarizes League Overview, Must Act, Start/Sit Summary, Waiver Priorities, Trade Watch, Survivor Status, NFL Intelligence Highlights, What Changed, and Risk Alerts, then links to owning pages without duplicating their engines.

League Overview is planned to merge into Command Center. Market Intelligence is planned to merge into NFL Intelligence, which owns Top Picks, Top Risk Games, Game Predictions, Market Intelligence, Weather, Injury Context, Insights, Blockers, and Diagnostics. Draft Board and Mock Draft remain preserved for Season Planning; Sleeper Hub, Draft Day Readiness, Draft Intelligence & Learning Center, Imports, Readiness, and Diagnostics are planned Admin destinations.

Navigation, merge, redirect, archive, and Admin placement work remains pending implementation and validation.

## Shared requirements for all six pages

- Use shared league, roster, ownership, team-needs, freshness, and explanation contracts.
- Show decision-critical source and freshness in manager-friendly language.
- Fail closed for stale, unavailable, or contradictory evidence.
- Explain every displayed score, rank, baseline, grade, fit, confidence, and impact value.
- Put recommended action and fantasy impact before technical diagnostics.
- Preserve read-only decision support.
- Do not require a manager-maintained CSV or manual upload for routine weekly decisions. CSV-backed evidence is a disclosed last-resort bootstrap or recovery input and must fail closed when stale.

## All-Season Page Quality Standard

Each page must earn advancement independently. Technical tests are necessary but insufficient: the current page must also be trustworthy, action-oriented, explainable, useful in unavailable or degraded states, readable on desktop and mobile, and valuable during normal weekly use before work moves to another page.

## Product usefulness gate

Every substantial page or evidence batch must name the manager-facing decision it enables or protects, the current workflow that consumes it, the incorrect decision it prevents, the next useful personal-season outcome, and the smallest safe implementation. A foundation without a planned near-term consumer is normally deferred unless it repairs a demonstrated correctness, privacy, security, data-integrity, or repository-recovery risk.

At least one active priority must materially improve a manager-facing START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, TRADE AWAY, or Survivor decision. Infrastructure-only work may not indefinitely displace those outcomes.

The primary measure of progress is improved fantasy-football decision quality for the owner. A foundation with no identified near-term consumer is normally deferred. If the required usefulness questions cannot be answered, defer unless the work protects repository integrity, security, ownership correctness, freshness correctness, identity correctness, or prevents major data corruption.

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

### Current verified behavior
- Validate player ownership and eligibility before showing add options; explain player-specific outcomes, including why a player is unavailable. For example, Isaiah Likely and Kaimi Fairbairn are explained as rostered.
- Use fresh current-week ECR for waiver ordering: lower ECR ranks higher. Stale ECR blocks ranking; candidates without ECR remain unranked. Comparable candidates may remain tied.
- Keep historical production and usage informational; they do not create or override a waiver rank.
- Use the recommendation vocabulary below. Display order alone does not communicate player quality.
- Distinguish slot-fill recommendations and their provisional guardrails from best-player rankings. A slot-fill result does not prove which player is best.
- State that any shown FAAB guardrails are provisional, not winning bids. Winning-bid estimation and player-value-to-FAAB conversion are unavailable.

### Recommendation vocabulary

- **BEST SUPPORTED OPTION** — A player whose fresh authoritative evidence supports ranking above available alternatives. Disclose the ranking basis; this is not a guarantee of fantasy points.
- **COMPARABLE OPTION** — An available candidate among others that current supported evidence cannot separate. Comparable options are not ranked by display position; display order is not player quality.
- **SLOT-FILL OPTION** — Addresses a verified roster problem, such as a bye week, empty starter slot, or verified absence. It does not imply that the player is the best player available.
- **BLOCKED OPTION** — A recommendation cannot be safely produced. Examples include stale ranking evidence, ownership uncertainty, unresolved identity, or unsupported health evidence. Explain the blocker.
- **PLAYER-SPECIFIC OUTCOME** — Gives the exact reason a player is rostered, excluded, unavailable, blocked, stale, unsupported, or unrankable. For example, explain that Isaiah Likely or Kaimi Fairbairn is rostered rather than showing only a general list-level message.

Stale ECR blocks ranking. Missing ECR produces **UNRANKED**; it does not mean the candidate is worse than another unranked player. Historical production and historical usage are informational only and do not create or replace a rank. Provisional guardrails are not winning bids. Winning-bid estimation and player-value-to-FAAB conversion are unavailable.

### Future requirements—not current behavior
- Role-duration or opportunity-driven ranking.
- Player-value scoring or other ranking based on team need, schedule, or replacement value.
- Suggested drop recommendations unless separately verified as supported.
- Winning-bid estimation and player-value-to-FAAB conversion.

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

Survivor Intelligence is a primary in-season destination within the same manager workflow as Decision Center, My Team, Waivers, Trades, and NFL Intelligence. It is not one of the six season-management pages listed above, but it reuses the shared requirements (freshness, fail-closed behavior, explainability, action-first ordering, and read-only decision support).

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