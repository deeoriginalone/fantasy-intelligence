# Data Freshness and Source Policy

## Status

This document defines the required freshness contract. Exact domain thresholds must be set from implementation and operational evidence. No unverified threshold is declared here.

## Source priority

1. Sleeper live data where the required fact is supported.
2. Verified local persistence or cache with source timestamp and age.
3. Supported enrichment source with disclosed provenance.
4. Explicitly unavailable.

A cached value must not silently override newer live truth.

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

## Threshold registry

Exact thresholds should be maintained in one implementation-owned registry and validated by tests. This document should link to that registry after it exists.
