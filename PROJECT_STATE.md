# Project State

## Current state

Fantasy Intelligence has completed the recorded Data Integrity work through A.10 and has an installed UX evidence and lineage foundation. A new hands-on QA review has identified unresolved live-data, ownership, explanation, and visual usability problems across the core season-management experience. The project is therefore in an active UX trust-and-correctness remediation phase, not a completed UX state.

## Current checkpoint
- Date: 2026-09-11
- Branch: feature/evidence-bundle-pipeline
- HEAD: 8c8480e49c4dfff1c857a5ffaa06c3e6f4c91e30
- Previously recorded HEAD: 6c97d30f20c4d9e9becf9ccf1007ef5b84e8b3d9

## Verified foundation retained from the prior checkpoint
- Shared evidence, freshness, blocker, confidence, and lineage contracts exist.
- Dashboard evidence integration, owned-player filtering helpers, roster requirement normalization, template evidence wiring, and focused validation were previously recorded.
- These capabilities are foundations only. Runtime and active-route behavior must be revalidated against the new QA findings.

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


## Current product boundary

### Dashboard
Requires verified date formatting, supported or useful fail-closed season/draft states, freshness visibility, and agreement with related pages.

### My Team
Requires complete Full-PPR team needs, clearer roster-strength concepts, defined scoring, current health and matchup context, a less redundant lineup presentation, and manager-facing lineage impact.

### Weekly Lineup Intelligence
Requires actionable START/SIT/FLEX/MONITOR decisions, defined baseline and scores, current health and matchup evidence, resolved integrity blockers, and a manager-readable readiness presentation.

### Waiver and FAAB Center
Requires current league ownership, exclusion of rostered players, shared team needs, verified eligibility, and actionable availability/FAAB evidence.

### Trade Target Center
Requires correct roster fit, shared team needs, counterparty context, and an explanation of how each trade changes weekly and season strategy.

### Weekly Command Center
Requires an action-first redesign that prioritizes lineup decisions, waiver/drop moves, trade watch, injuries, risk, deadlines, and data alerts.

## Data policy under review
- Sleeper is the preferred live source where it supports the required fact.
- Local data may enrich or cache but must show age and must not silently displace fresher source truth.
- Unsupported or unverified values must fail closed.
- Ownership and eligibility uncertainty must block waiver recommendations.

## Known boundaries
- The reported defects have not yet been marked resolved.
- Current runtime freshness and cross-page consistency require active-route verification.
- PostgreSQL parity, failure injection, rollback, recovery, cleanup, repeatability, and production signoff remain outstanding.
- No automatic external fantasy transaction submission is enabled.

## Next milestone

**Complete UX-QA.1: Live Data Trust, Ownership Correctness, and Cross-Page Decision Clarity.**
