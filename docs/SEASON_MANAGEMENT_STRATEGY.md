# Season Management Strategy

## Fantasy Intelligence 2.0 Strategy

Strategy exists to improve one manager's weekly and season decisions in a specific league. Prioritize manager value over generalized platform process. Recommendations are read-only; distinguish authority from usefulness and do not block a supported, disclosed preliminary recommendation solely because authority is incomplete.

## Evidence-first strategy rule

The product follows `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. Fantasy Intelligence is a personal, single-manager, read-only decision-support application. Authority and usefulness are separate; authority completion alone is not a recommendation prerequisite.

Repository-wide recommendation states:
- **ESTABLISHED** -> **RECOMMENDATION** when the applicable supporting contract is complete.
- **PRELIMINARY** -> **RECOMMENDATION WITH DISCLOSURE** when useful, truthful inputs exist but authority is incomplete.
- **INSUFFICIENT** -> **NO RECOMMENDATION** when inputs cannot support a meaningful recommendation.
- **CONTRADICTORY** -> **BLOCKED** when supported facts conflict.

A `PRELIMINARY` recommendation requires verified identity and ownership, disclosed evidence level, freshness, and limitations, and a read-only presentation that cannot create an incorrect fantasy decision. Disclose confidence rationale when available; never fabricate confidence, freshness, probability, authority, identity, or evidence. `BLOCKED` is reserved for unresolved identity or ownership, contradictory or corrupted evidence, unsafe recommendation risk, or transaction-safety risk. Missing authority paperwork or a threshold sign-off alone is not a blocker when the underlying evidence may truthfully be used and the preliminary recommendation remains safe; prohibited or unpermitted use remains blocked. Use `INSUFFICIENT` when evidence is too weak or missing for a meaningful recommendation. Specific metric/page contracts may restrict an individual signal to context-only when that signal alone cannot safely support a recommendation.

Matchup Rank remains subject to its authority contract; an unavailable rank does not automatically suppress a safe preliminary recommendation supported by other inputs. The Matchup Signal metric remains context-only unless its own contract supports decision use. Historical evidence may inform stability, governance, baselines, and trends, but never automatically becomes current-season authority.

The Command Center summarizes decisions; My Team, Waivers, Trades, Survivor, and NFL Intelligence remain the owning decision pages.

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
- Current waiver ordering uses fresh current-week consensus rank (ECR); lower ECR ranks higher, stale ECR blocks ranking, and candidates without ECR remain unranked. Historical production and usage are informational only, not ranking inputs or fallbacks.
- Ranking candidates by roster need, role, opportunity, expected duration of value, schedule, replacement value, and evidence confidence remains a strategic goal; these are not current waiver-ranking inputs.
- Use the manager-facing waiver recommendation vocabulary defined in the Waiver and FAAB Center section of `PAGE_REQUIREMENTS.md`.
- Any displayed FAAB guardrails are provisional, not player-value estimates. Winning-bid estimation and player-value-to-FAAB conversion are unavailable.

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

## Yahoo Survivor planning boundary

The owner reports approved Yahoo API access and a Yahoo Survivor league. Evaluate Yahoo as a possible supported source for Survivor season state, used-team history, current eligibility, selection state, league settings, and contest information, but classify each category as **UNKNOWN PENDING API VERIFICATION** until official documentation, approved scopes, credentials, and controlled live responses prove the fields. Do not assume a Survivor endpoint.

If Yahoo supplies authoritative league-specific Survivor state, prefer it for that domain. Local state may remain a disclosed cache, recovery layer, or derived state and must not silently override newer Yahoo truth. Conflicts, stale responses, incomplete history, identity mismatches, unsupported contest types, missing scopes, and rate limits fail closed. Yahoo remains read-only and must not affect rankings, confidence, scores, recommendations, or transactions until a tested consumer contract authorizes that effect.

The active delivery pace must keep at least one manager-facing weekly decision improvement in progress; unsupported role evidence without a named near-term consumer is deferred.

The primary measure of progress is improved fantasy-football decision quality for the owner. The project exists to help the owner win fantasy leagues, not to maximize infrastructure completeness. Yahoo Survivor verification is a user-value milestone and should first evaluate Survivor state, Survivor history, Survivor eligibility, Survivor selections, and contest truth. Do not assume Yahoo support until each capability is verified.
