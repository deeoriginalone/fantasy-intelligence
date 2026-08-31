# Development Roadmap

## Context

This roadmap reflects the current repository state, not aspirational future status. The runtime is code-valid and test-valid, but it is not yet proven as a live database-backed production system. The next direction is therefore pragmatic and evidence-based: validate the recommendation publication gate and then move to the next operational layer.

## Status legend

- VERIFIED
- IMPLEMENTED, NEEDS HARDENING
- PARTIALLY IMPLEMENTED
- PROTOTYPE, NOT INTEGRATED
- BLOCKED BY INPUTS
- PLANNED

## Current direction: Batch D Recommendation Publishing

### 1. Recommendation publication gate
- Objective: ensure that recommendation output is only published when readiness, source freshness, and data validity checks pass
- Evidence: [draft_readiness.py](draft_readiness.py) contains readiness scoring and a publication gate, and [draft_health_routes.py](draft_health_routes.py) exposes health checks
- Completion criteria: publication is blocked when source data is missing, stale, or invalid
- Risk if skipped: output can look authoritative without proving source quality
- Status: PARTIALLY IMPLEMENTED
- Suggested next milestone: Batch D

### 2. Recommendation source traceability
- Objective: attach source timestamps and traceability to recommendation output
- Evidence: the project documents the need for source freshness and quality gating, but live traceability is not yet proven in the active runtime
- Completion criteria: each surfaced recommendation can be tied back to its source and freshness window
- Risk if skipped: recommendations cannot be defended or audited
- Status: PLANNED

### 3. Recommendation explainability payloads
- Objective: keep recommendation decisions explainable and reviewable
- Evidence: the repo includes explainability-oriented modules and tests, but this remains a supporting layer rather than a proven production contract
- Completion criteria: recommendation output includes rank, scarcity, need, and source-context metadata
- Risk if skipped: confidence becomes opaque and hard to trust
- Status: PARTIALLY IMPLEMENTED

## Immediate next steps (before the next milestone)

### 1. Database validation
- Objective: bring PostgreSQL online and validate the live schema and object set
- Evidence: live DB checks are blocked right now because the service is unavailable
- Completion criteria: the critical tables and state objects are confirmed in the active environment
- Risk if skipped: code/test success does not equal runtime validity
- Status: BLOCKED

### 2. Draft-day end-to-end validation
- Objective: validate identity, uniqueness, reconciliation, and roster invariants in a live draft flow
- Evidence: Batch A/B/C show the logic is present and passing tests, but not DB-proven
- Completion criteria: no mismatches, duplicate picks, or orphan roster states remain
- Risk if skipped: local and live state can drift
- Status: PARTIALLY IMPLEMENTED

### 3. Recommendation publication enforcement
- Objective: gate release of recommendation surfaces behind readiness and freshness checks
- Evidence: readiness logic exists in [draft_readiness.py](draft_readiness.py)
- Completion criteria: readiness state is explicit and publication happens only in READY or validated states
- Risk if skipped: users can interpret incomplete outputs as live intelligence
- Status: PARTIALLY IMPLEMENTED

## Short-term (next sprint)

### 1. Finalize recommendation trust layer
- Add explicit readiness labels and source-freshness windows
- keep stale or synthetic data from being presented as live intelligence

### 2. Harden Draft HQ state transitions
- confirm the transition from draft to season-active state remains idempotent and safe
- ensure no duplicate-player or stale-state conditions survive initialization

### 3. Improve batch hygiene and release boundaries
- distinguish traceability artifacts from canonical runtime files
- keep backup and archive output outside the core runtime path unless intentionally tracked

## Medium-term

### 1. Historical outcome calibration
- compare forecast outputs with resolved draft outcomes once real data exists
- calibrate reliability estimates against evidence instead of assumptions

### 2. Survivor input contract
- define explicit ownership, QB-status, injury, and weather source contracts
- keep Survivor outputs blocked until the required inputs are verified

### 3. Market and weekly ingestion maturity
- validate no-vig calculations, confidence scoring, and provider data quality under real schedules
- define ingestion failure and repair procedures

## Long-term

### 1. Multi-season and multi-session support
- support multiple drafts and multiple years without cross-session drift
- isolate historical behavior tables from active season state

### 2. Provider abstraction layer
- normalize provider inputs behind a common interface for ratings, injuries, weather, and market data
- reduce provider-specific coupling and fragile adapters

### 3. Operational observability
- add consistent metrics and diagnostics for ingestion, reconciliation, and publication state
- make release gates observable and explainable to operators

## Completion criteria for season-readiness

The repo should only be treated as season-ready when all of the following are true:
- draft session identity is enforced and authoritative
- pick uniqueness and unresolved-player quarantine are active
- roster invariants are enforced and recoverable
- recommendation publication is gated by readiness and source freshness
- live database validation is complete
- Survivor and weekly intelligence inputs are real and validated
- no synthetic output is presented as live data

## Current recommendation

The immediate direction should be:
1. database validation
2. draft-day end-to-end validation
3. recommendation publication gate enforcement
4. Batch D Recommendation Publishing

This is the evidence-based next phase. It is intentionally narrower than post-draft readiness, week-one operations, or broader automation work until the trust layer is proven.
