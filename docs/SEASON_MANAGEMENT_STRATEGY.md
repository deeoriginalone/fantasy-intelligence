# Season Management Strategy

## Scope

This document defines the intended decision philosophy for a Full-PPR fantasy football team-management assistant. It is a product requirement, not proof that every strategy is implemented.

## Strategic priorities

1. Protect weekly starting-lineup quality.
2. Maintain enough depth to survive injuries and bye weeks.
3. Use waivers to improve both immediate opportunity and rest-of-season value.
4. Trade from surplus to address meaningful roster weakness.
5. Adjust risk posture as playoff position becomes clearer.
6. Avoid false precision when evidence is incomplete.

## Full-PPR team-needs model

Team need must evaluate every required position:

- QB
- RB
- WR
- TE
- FLEX
- K
- DEF

The model should consider:

- Active league roster slots and scoring settings
- Starter quality
- Bench depth
- Replacement-level availability
- Injury and availability risk
- Bye-week conflicts
- Positional scarcity
- Expected opportunity and role stability
- Schedule and playoff-week outlook when supported
- FLEX competition among eligible RB, WR, and TE players

No position may be omitted merely because it usually has lower replacement cost. K and DEF may receive lower strategic weight when supported by league context, but they must still be evaluated and explained.

## Lineup philosophy

- Use START, SIT, FLEX, and MONITOR as manager-facing decisions.
- Separate projected output from certainty.
- Distinguish an unavailable matchup rank from a poor matchup.
- Health and availability uncertainty must reduce confidence or trigger MONITOR.
- Recommendations must conform to active league slots.

## Waiver and FAAB philosophy

- Verify current ownership and eligibility before candidate scoring.
- Never recommend a player rostered anywhere in the active league.
- Rank candidates by roster need, role, opportunity, expected duration of value, schedule, replacement value, and evidence confidence.
- FAAB guidance must show whether it reflects an immediate starter, depth addition, short-term injury replacement, or speculative upside add.
- Do not present precise FAAB guidance when ownership, role, or opportunity evidence is unavailable.

## Trade philosophy

- Evaluate whether a trade improves this roster, not whether the target is merely a good player.
- Compare weekly lineup impact, rest-of-season impact, depth, positional surplus, bye-week interaction, injury risk, and playoff schedule when supported.
- Include counterparty need and likely trade feasibility when evidence exists.
- Explain what weakness is addressed and what new risk the trade creates.

## Weekly management cycle

1. Refresh league, roster, ownership, matchup, and supported player-status facts.
2. Identify lineup availability and health risks.
3. Set the best supported starting lineup.
4. Identify waiver and drop opportunities.
5. Review trades that address real team needs.
6. Review bye-week, depth, and upcoming schedule risks.
7. Recheck evidence before transaction and lineup deadlines.

## Read-only boundary

The application provides recommendations only. It must not automatically submit lineup, waiver, drop, or trade transactions.
