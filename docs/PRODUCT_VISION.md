# Fantasy Intelligence Product Vision

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

- **Trust before sophistication:** current ownership, eligibility, health, matchup, and league settings must be correct before advanced recommendations are shown.
- **Sleeper-first where supported:** Sleeper should be the preferred live source for supported league, roster, ownership, draft, and matchup facts.
- **Fail closed:** unavailable or stale evidence must not be presented as verified truth.
- **Action before diagnostics:** the recommended team-management action and expected impact come before technical evidence.
- **Explain every metric:** scores, ranks, grades, baselines, confidence, and roster-fit values require a definition, scale, inputs, and decision use.
- **One shared league truth:** Dashboard, My Team, Lineup, Waivers, Trades, and Weekly Command Center should use the same roster, league-settings, ownership, and team-needs contracts.
- **Read-only decision support:** the application may recommend actions but must not submit external fantasy transactions automatically.

## Current product priority

**UX-QA.1: Live Data Trust, Ownership Correctness, and Cross-Page Decision Clarity**

## Success criteria

- No rostered player appears as an available waiver recommendation.
- Team needs cover QB, RB, WR, TE, FLEX, K, and DEF using active Full-PPR league settings.
- Shared facts agree across all six season-management pages.
- Every visible value is current, explicitly stale, or explicitly unavailable.
- Every recommendation explains why it matters and what the manager should do next.
- Technical integrity and lineage details remain available but are secondary to fantasy impact.
