# F3-B.4 Readiness Gates Specification

## Objective

Provide one authoritative, read-only decision for whether downstream recommendations and reports may publish.

## Status precedence

```text
BLOCKED > WARNING > READY
```

Any blocked component blocks the overall report. Warnings block publication by default. A policy may explicitly allow warning-state publication.

## Required components

Default required components:

- `sleeper`
- `draft_state`
- `reconciliation`
- `recommendations`

Missing required components are synthesized as `BLOCKED` with code `REQUIRED_COMPONENT_MISSING`.

## Freshness

Policies may set `maximum_age_seconds` by component. A stale or unverifiable timestamp blocks that component. A future timestamp produces a warning.

## Publication contract

Consumers must use:

```python
report.publish_allowed
```

They must not infer publication permission from a single component or from `overall_status` strings copied elsewhere.

## Safety boundary

The engine does not fetch Sleeper data, query a database, generate recommendations, or publish. It evaluates explicit component results only. Runtime adapters will be a later integration batch.
