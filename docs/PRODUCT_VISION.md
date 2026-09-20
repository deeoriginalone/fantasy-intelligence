# Fantasy Intelligence Product Vision

## Fantasy Intelligence 2.0

Fantasy Intelligence is a personal, league-specific fantasy football decision assistant. Its primary purpose is to help one manager make better weekly and season decisions.

Success means better lineup, waiver, trade, Survivor, and season-planning decisions. The product is not a commercial SaaS platform, enterprise architecture, or multi-user system.

The six primary destinations are Command Center, My Team, Waivers, Trades, Survivor, and NFL Intelligence. Existing league integrations, historical data, ownership logic, projections, opportunity evidence, matchup data, NFL intelligence, and trade intelligence remain valuable and must be preserved.

## Purpose

Fantasy Intelligence exists to help one fantasy football manager make trustworthy, timely, and explainable team-management decisions throughout the season.

## Primary user outcome

Every season-management page should help answer at least one of these questions:

1. Who should I start?
2. Who should I sit or monitor?
3. Who should I add?
4. Who should I drop?
5. Who should I trade for?
6. Who should I trade away?
7. What is the highest-impact action before the next deadline?
8. What risk could hurt my lineup, depth, playoff odds, or championship path?

## Product principles

- **Owner success:** The project exists to help the owner win fantasy leagues, not to maximize infrastructure completeness.
- **Primary progress measure:** The primary measure of progress is improved fantasy-football decision quality for the owner. Infrastructure is successful only when it directly improves START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, TRADE AWAY, or Survivor Selection decisions, or protects them from incorrect outputs.

- **Trust before sophistication:** current ownership, eligibility, health, matchup, and league settings must be correct before advanced recommendations are shown.
- **Sleeper-first where supported:** Sleeper should be the preferred live source for supported league, roster, ownership, draft, and matchup facts.
- **Fail closed:** unavailable or stale evidence must not be presented as verified truth.
- **Action before diagnostics:** the recommended team-management action and expected impact come before technical evidence.
- **Explain every metric:** scores, ranks, grades, baselines, confidence, and roster-fit values require a definition, scale, inputs, and decision use.
- **One shared league truth:** Dashboard, My Team, Lineup, Waivers, Trades, and Weekly Command Center should use the same roster, league-settings, ownership, and team-needs contracts.
- **One unified manager workflow:** Decision Center, My Team, Waivers, Trades, NFL Intelligence, and Survivor are primary in-season destinations within one read-only decision-support ecosystem. Shared ownership, freshness, roster-truth, and explanation contracts should be reused where applicable.
- **Read-only decision support:** the application may recommend actions but must not submit external fantasy transactions automatically.

## All-Season Page Quality Standard

The product must make every season-management page a page the manager actually wants to use throughout the season. Development proceeds one page at a time and does not advance merely because technical acceptance tests pass. Before advancing, the current page must demonstrate trustworthy facts, clear actions, explainable recommendations, useful degraded states, readable desktop and mobile presentation, repeat-use weekly value, and an affirmative answer to: “Is this a page I actually want to use all season?” This supplements, and does not replace, evidence-first tests, active-route validation, and milestone definitions of done.

## Current product priority

**Manager-facing weekly decision usefulness:** improve trustworthy START, SIT, FLEX, MONITOR, ADD, DROP, TRADE FOR, TRADE AWAY, or Survivor outcomes using verified league-specific evidence. Integrity foundations remain required, but infrastructure-only work may not indefinitely displace a useful decision workflow.

Before starting a substantial foundation, require a named decision, current consumer, prevented incorrect decision, next useful personal-season outcome, smallest safe implementation, and shortest evidence path. Defer foundations with no near-term consumer unless they repair a demonstrated correctness, privacy, security, data-integrity, or repository-recovery risk.

The required personal usefulness gate asks: (1) which manager-facing decision becomes better, (2) which page consumes it, (3) whether the owner can benefit from it this season, (4) whether it is required for the current roadmap priority, (5) which incorrect fantasy decision it prevents, (6) what the smallest safe implementation is, and (7) what the shortest evidence path is. If questions 1 through 4 cannot be answered, the default action is defer.

A foundation with no identified near-term consumer is normally deferred.

## Value Delivered Register

The primary measure of progress is improved fantasy-football decision quality. Every completed milestone should identify:

- manager-facing benefit
- improved or protected decision
- consuming workflow or page
- decision risk reduced

Implementation volume alone does not constitute progress. Record only supported delivered benefits; do not use this register for planned or speculative outcomes.

| Milestone | Manager-Facing Benefit | Decision Protected or Improved | Consumer |
|------------|------------|------------|------------|
| UX.3 Waiver correctness | Eliminates rostered-player waiver recommendations | ADD | Waivers |
| UX.2 My Team validation | Provides Full-PPR team-needs and priority-action context | ADD/DROP | My Team |
| UX.5 Lineup explainability | Presents explicit lineup calls with evidence and confidence | START/SIT/FLEX/MONITOR | My Team / Weekly Lineup |
| UX.4 Trade Center integrity | Provides read-only roster-fit and trade-impact context with blockers | TRADE FOR/TRADE AWAY | Trades |
| UX.8 Survivor foundation | Prevents recommendations for used or ineligible Survivor teams when eligibility evidence is unavailable or blocked | Survivor Selection | Survivor |

## Success criteria

- No rostered player appears as an available waiver recommendation.
- Team needs cover QB, RB, WR, TE, FLEX, K, and DEF using active Full-PPR league settings.
- Shared facts agree across all six season-management pages.
- Every visible value is current, explicitly stale, or explicitly unavailable.
- Every recommendation explains why it matters and what the manager should do next.
- Technical integrity and lineage details remain available but are secondary to fantasy impact.
