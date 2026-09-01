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


# Phase F - Draft Day and Season Automation Sandbox

## Objective

Create a fully automated testing environment capable of simulating:

- Draft Day operations
- Live draft recommendations
- Post-draft roster management
- Weekly waiver workflows
- Start/Sit optimization
- Survivor workflows
- Pick'em workflows
- End-of-season analysis

before live deployment.

This phase builds upon the existing Draft Intelligence, Recommendation Engine, Intelligence Operations, Ingestion Pipeline, Survivor Intelligence, and Pick'em Intelligence systems already implemented in the platform. 【1-853541】

---

# Phase F1 - Draft Day Sandbox

## Goal

Allow complete draft simulations without requiring a live league.

## Components

### Mock Draft Engine

Create:

```text
simulator/
├── mock_draft.py
├── draft_simulator.py
```

### Responsibilities

- Generate draft picks
- Simulate opponents
- Simulate multiple draft strategies
- Feed picks into the draft board
- Trigger recommendation updates

---

### Live Recommendation Testing

Draft flow:

```text
Mock Pick
      ↓
Board Update
      ↓
Roster Update
      ↓
Positional Scarcity Recalculation
      ↓
Draft Outcome Tracking
      ↓
Recommendation Engine
      ↓
UI Dashboard Refresh
```

### Validate

- Draft board accuracy
- Recommendation quality
- Scarcity model behavior
- Draft outcome tracking

---

### Draft Strategy Testing

Simulate:

- Hero RB
- Zero RB
- RB Heavy
- WR Heavy
- Elite QB
- Balanced

### Track

- Roster Strength
- Projected Points
- Draft Grade
- Recommendation Accuracy

---

# Phase F2 - Automation Scheduler

Create:

```text
scheduler/
├── draft_day.py
├── daily.py
├── weekly.py
├── seasonal.py
```

## Purpose

Automate all intelligence workflows.

---

# Phase F3 - Weekly Intelligence Automation

## Daily Workflow

```text
Refresh Injuries
Refresh Market Data
Refresh Weather
Refresh Projections
Run Intelligence Pipeline
Update Dashboard
Generate Reports
```

### Validate

- Scheduler reliability
- Freshness logic
- Readiness gating
- Report generation

---

# Phase F4 - Pick'em Automation Sandbox

## Validate Existing Workflow

The documented Pick'em workflow currently follows:

```text
Schedule
     ↓
Crowd Data
     ↓
Odds
     ↓
No-Vig Probabilities
     ↓
Game Model
     ↓
Signal Classification
     ↓
Confidence Ranking
     ↓
Weekly Report
```

This follows the overall refresh and recommendation pipeline already defined in the project architecture. 【1-853541】

### Test

- Lock identification
- Best upset detection
- Public traps
- Contrarian picks
- Confidence assignments
- Weekly intelligence report generation

---

# Phase F5 - Survivor Automation Sandbox

## Simulate

```text
Week 1
Week 2
Week 3
...
Week 18
```

### Validate

- Survivor scoring
- Future value preservation
- Ownership leverage
- Recommendation quality
- Fallback recommendation generation

---

# Phase F6 - Full Season Simulation

## Create

```text
simulator/
└── season_simulator.py
```

## Run Complete League Lifecycle

```text
Draft
   ↓
Week 1
   ↓
Waivers
   ↓
Week 2
   ↓
Trades
   ↓
Week 3
...
Week 18
```

### Track

- Wins
- Losses
- Playoff Odds
- Recommendation Accuracy
- Waiver Success Rate
- Trade Success Rate
- Draft ROI

---

# Draft Day Automation Roadmap

## Future Live Draft Watcher

Create:

```text
scheduler/
└── live_draft_watcher.py
```

### Live Workflow

```text
Sleeper Draft Event
        ↓
Draft Pick Detected
        ↓
Draft Board Updated
        ↓
Roster Updated
        ↓
Scarcity Recalculated
        ↓
Recommendation Rebuilt
        ↓
Dashboard Refreshed
```

### Goal

Near real-time draft assistance with minimal manual refreshes.

---

# Season Automation Roadmap

## Nightly Intelligence Pipeline

Create:

```text
scheduler/
└── nightly_intelligence.py
```

### Pipeline

```text
Refresh Players
      ↓
Refresh Injuries
      ↓
Refresh Market Data
      ↓
Refresh Weather Data
      ↓
Update Projections
      ↓
Run Intelligence Engine
      ↓
Generate Reports
      ↓
Update Dashboard
```

---

# Success Criteria

Sandbox environment can successfully execute:

## Draft Day

- ✅ Complete 15-round mock draft
- ✅ Update recommendations in real time
- ✅ Track draft outcomes
- ✅ Validate scarcity logic
- ✅ Generate draft grades
- ✅ Compare draft strategies

---

## Weekly Operations

- ✅ Generate waiver recommendations
- ✅ Generate start/sit recommendations
- ✅ Generate Pick'em recommendations
- ✅ Generate survivor recommendations
- ✅ Generate intelligence reports
- ✅ Validate readiness gates

---

## Season Simulation

- ✅ Complete full season replay
- ✅ Evaluate recommendation accuracy
- ✅ Measure draft strategy performance
- ✅ Produce end-of-season report
- ✅ Measure waiver performance
- ✅ Measure survivor performance
- ✅ Measure Pick'em performance

---

# Future Vision

## Personal Fantasy Operations Center

Long-term target:

```text
Draft Starts
      ↓
Draft Watcher
      ↓
Recommendation Engine
      ↓
Roster Intelligence
      ↓
Waiver Intelligence
      ↓
Pick'em Intelligence
      ↓
Survivor Intelligence
      ↓
Weekly Reports
      ↓
Season Analysis
```

with minimal manual intervention while preserving the recommendation, reporting, validation, explainability, intelligence, and refresh workflows already defined throughout the platform. 【1-853541】

---

# Immediate Next Steps

## Phase F1 MVP

Priority implementation order:

1. Create `simulator/mock_draft.py`
2. Create 
