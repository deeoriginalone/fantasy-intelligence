# Fantasy Intelligence Platform Maturity

## Fantasy Intelligence 2.0 Maturity Rule

Maturity is measured by manager value and trustworthy page behavior, not enterprise scale. A capability is mature when its owning page renders useful supported states, preserves data truth, exposes freshness and limitations, fails closed on unsafe authority, and has proportional validation.

Commercial deployment, multi-tenant support, and enterprise governance are out of scope unless explicitly reintroduced. Recovery capability is part of maturity.

## Purpose

This model separates feature presence from trust and decision quality. A level is not complete until its exit criteria have evidence.

## Evidence-first maturity rule

Maturity evaluates both trust and usefulness. The architecture path is `DATA -> EVIDENCE -> CONFIDENCE -> MODEL -> DECISION`. A capability must fail closed for unsupported authority, but it should expose supported preliminary evidence rather than collapse to “no data.” Evidence levels are `ESTABLISHED`, `PRELIMINARY`, and `INSUFFICIENT`; each displayed result must disclose its level, confidence, sample, freshness, limitations, and recommendation impact. Preliminary evidence is informational and cannot independently drive recommendations.

## Level 1: Data Available

### Goal
Required facts can be retrieved or stored.

### Exit criteria
- Sources are identified.
- Required fields are mapped.
- Missing data is visible.

## Level 2: Data Trusted

### Goal
Current data, source, ownership, freshness, and failure behavior are reliable.

### Exit criteria
- Sleeper-first behavior is proven for supported fields.
- Roster and ownership truth are current.
- Stale data fails closed.
- Shared facts agree across pages.
- Freshness and failure tests pass.

## Level 3: Recommendations Trusted

### Goal
Lineup, waiver, drop, and trade recommendations are correct, explainable, and league-aware.

### Exit criteria
- Waiver candidates are verified unrostered.
- Team needs cover QB, RB, WR, TE, FLEX, K, and DEF for active Full-PPR settings.
- Scores and decisions are defined.
- Recommendation blockers behave correctly.
- Active-route tests pass.

## Level 4: Season Strategy Trusted

### Goal
The application supports rest-of-season roster construction and playoff planning.

### Exit criteria
- Rest-of-season inputs have verified sources.
- Schedule, depth, bye-week, injury, and trade effects are explainable.
- Strategic recommendations include uncertainty and alternatives.

## Level 5: Championship Optimization

### Goal
The platform consistently prioritizes actions with the greatest supported effect on playoff and championship outcomes.

### Exit criteria
- Scenario and impact models are validated.
- Recommendations are calibrated against outcomes.
- Production, recovery, and repeatability evidence is complete.

## Current claim boundary

The current canonical project memory places the project in UX-QA.1 trust-and-correctness remediation. This maturity document does not assign a completed level until the corresponding exit evidence is recorded.

## Personal-application rigor boundary

Production-level rigor for this personal, read-only application means reliable decision-critical data, defined metrics, freshness, provenance, fail-closed behavior, focused tests, and truthful unsupported states. It does not automatically require commercial scalability, multi-user architecture, production deployment, exhaustive recovery testing, broad observability, or enterprise process for every feature. Safety-critical and security-sensitive behavior still receives full relevant validation; read-only investigation receives proportional validation.

The primary measure of progress is improved fantasy-football decision quality for the owner. Infrastructure completeness is secondary and must be tied to a current decision consumer or to an explicit integrity, security, ownership, freshness, identity, or data-corruption risk.
