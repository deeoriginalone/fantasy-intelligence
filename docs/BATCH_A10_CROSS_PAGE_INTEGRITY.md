# Batch A.10 Cross-Page Integrity Display

## Scope

This batch renders the existing Shared Integrity contract in the two active templates already proven to receive `lineup_intelligence`:

- `templates/lineup.html`
- `templates/gm.html`

A reusable `templates/_integrity_summary.html` component displays recommendation readiness, completeness, confidence, freshness, player counts, health counts, missing matchup counts, blockers, and the four freshness domains.

## Boundary

This batch does not alter integrity calculations, routes, services, schema, migrations, persistence, or fantasy transactions. It does not wire My Team, Waivers, or Trades because their discovered render calls did not include a verified shared-integrity payload.

## Fail-closed display

Unknown, stale, expired, and blocked states are rendered from the existing contract. The template does not infer timestamps or recalculate scores.
