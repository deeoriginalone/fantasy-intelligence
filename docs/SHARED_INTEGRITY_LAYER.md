# Shared Integrity Layer

## Purpose

Provides centralized evidence measurement for:

- Injury status
- Weekly projections
- Matchup enrichment
- Weekly lineup intelligence
- Trade intelligence

## Design Goals

- No external writes
- No transaction submission
- Read-only evaluation
- Reuse existing evidence_gaps framework

## Outputs

build_integrity_report()

Returns:

- completeness_score
- confidence_score
- blockers
- unknown_health_players
- missing_matchups

## Initial Consumers

Future integrations:

- weekly_intelligence.py
- services/weekly_lineup_intelligence.py
- services/matchup_intelligence.py
- services/trade_intelligence.py

No integrations are included in Batch A.1.

## Batch A.2 Integration

The shared integrity report is now included in the aggregate contracts returned by:

- `services.matchup_intelligence.build_matchup_intelligence()`
- `services.weekly_lineup_intelligence.build_lineup_intelligence()`

The integration is read-only. It does not submit lineups, trades, waivers, or other external transactions. Existing blockers, confidence values, and evidence-gap behavior remain in place.

## Batch A.3 Freshness and Fail-Closed Confidence

Adds roster, injury, matchup, and projection freshness states and blockers. Missing required evidence caps confidence at LOW. Aggregate recommendation readiness fails closed when blockers exist. No route, template, database, migration, or external-write integration is included.
