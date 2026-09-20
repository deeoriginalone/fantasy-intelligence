# Data Freshness and Source Policy

## Fantasy Intelligence 2.0 Application

Freshness exists to protect personal fantasy decisions. Show supported evidence quickly, disclose age and limitations, and use proportional validation. Missing, stale, unresolved, or contradictory evidence remains `UNAVAILABLE`, `BLOCKED`, or `INSUFFICIENT_EVIDENCE`; it must never become fabricated certainty.

Freshness policy does not authorize ranking, confidence, FAAB, probability, or transaction behavior by itself. Recovery snapshots must preserve freshness metadata and validation evidence.

## Status

This document defines the required freshness contract. Exact domain thresholds must be set from implementation and operational evidence. No unverified threshold is declared here.

## Source priority

1. Sleeper live data where the required fact is supported.
2. Verified local persistence or cache with source timestamp and age.
3. Supported enrichment source with disclosed provenance.
4. CSV or manual import only for a one-time bootstrap, controlled recovery, or test fixture.
5. Explicitly unavailable.

A cached value must not silently override newer live truth.

## CSV and manual-data rule

Routine weekly decisions must not require a manager-maintained CSV or manual upload. CSV-backed inputs must identify their source and import time, carry an explicit freshness state, and become `UNAVAILABLE` or `BLOCKED` when they cannot be refreshed by a supported automated process. A CSV is never a silent fallback for live data.

## Required freshness fields

Every decision-critical payload should expose:

- Domain
- Source
- Source record time when available
- Retrieved-at time
- Age
- Freshness threshold identifier
- Freshness state
- Completeness state
- Blocker reason
- Fallback used
- Recommendation impact

## Required freshness states

- **FRESH:** Within the verified domain threshold.
- **AGING:** Near the threshold and should be refreshed.
- **STALE:** Beyond the threshold and not safe for authoritative use.
- **UNAVAILABLE:** No supported value exists.
- **BLOCKED:** Required evidence is missing or invalid and the associated recommendation must not be produced.

## Domain requirements

### League settings
- Preferred source: Sleeper where supported.
- Impact: Roster slots, scoring context, FLEX eligibility, and team-needs calculations.

### Rosters and ownership
- Preferred source: Current Sleeper league rosters.
- Impact: Waiver availability, trade context, roster identity, and team needs.
- Safety rule: Unverified ownership blocks waiver recommendations.

### Draft state and start time
- Preferred source: Sleeper draft and league data where supported.
- Impact: Dashboard state and date/time presentation.

### Matchups
- Preferred source: Sleeper where supported, plus disclosed enrichment where required.
- Impact: Lineup context and opponent difficulty.

### Health and availability
- Source: Must be explicitly documented by the implementation.
- Impact: START, SIT, FLEX, MONITOR, waiver, and trade confidence.
- Safety rule: Unknown health may not be displayed as healthy.

### Projections and opportunity metrics
- Source: Must be disclosed and licensed or otherwise permitted.
- Impact: Weekly Score, baseline, waiver value, and trade impact.
- Safety rule: No invented projection or opportunity value.

## Failure behavior

- A failed live refresh must not make an old cache appear current.
- Stale or unavailable inputs must reduce confidence or block the affected recommendation.
- The page must present a useful manager-facing explanation and the last verified time when available.

## Multi-source and Yahoo policy

Each field must have a source owner, allowed secondary sources, conflict policy, freshness requirement, identity contract, missing-data behavior, and recommendation effect. A secondary source may fill a documented gap, corroborate a fact, or add source-specific context; it may not silently replace the owning source. Agreement improves confidence only through a defined and tested contract. Disagreement is not averaged away.

The owner reports approved Yahoo API access and a Yahoo Survivor league. Yahoo is a planned read-only source candidate, not verified capability. Survivor endpoints, fields, scopes, authentication, identifiers, rate limits, licensing, league access, and source timestamps are **UNKNOWN PENDING API VERIFICATION**. League-specific Yahoo facts should prefer Yahoo when supported, while local state remains disclosed cache/recovery/derived state only. Conflicts and unsupported or incomplete responses become `UNAVAILABLE`, `DEGRADED`, or `BLOCKED` as appropriate.

## Threshold registry

Exact thresholds should be maintained in one implementation-owned registry and validated by tests. This document should link to that registry after it exists.
