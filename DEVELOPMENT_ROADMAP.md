# Development Roadmap

## Checkpoint

- Date: 2026-09-03
- Branch: feature/draft-outcome-tracking
- HEAD: 7ff86c633b8a2f5c5c7b5b34667344d2fa14440b
- Working tree: review state includes modified [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) and untracked audit/discovery files. No production code changes were introduced during this review.

## Verified repository state

The repository is currently validated for implementation and unit/integration testing, but it is not live-route validated and not PostgreSQL-proven.

## Phase status

### F3-A through F3-D.4

- F3-A: Complete; code and tests validated
- F3-A.1: Complete; repository integration validated
- F3-A.2: Complete; runtime integration validated
- F3-B.1: Complete; replay validation evidence exists
- F3-B.2: Complete; reconciliation logic validated
- F3-B.3: Complete; live reconciliation logic validated unit-wise
- F3-B.4: Complete; readiness gate tests pass
- F3-C.1: Complete; publication gate tested
- F3-C.2: Complete; draft recommendation publication tested
- F3-D.1: Complete; waiver intelligence tested
- F3-D.2: Complete; FAAB intelligence tested
- F3-D.3: Complete; waiver action plan tested
- F3-D.4: Complete; dedicated integration verification passed (30 passed)

### PostgreSQL parity

- Incomplete
- Known issues documented in the repo: raw tuple state from PostgresDraftEventStore.ordered_state(), missing cleanup_test_draft(), and skipped Postgres parity tests

## Evidence and verification tiers

### Unit-tested
- ./scripts/test_fast.sh => 44 passed in 0.11s
- python -m pytest -q tests/test_f3_d1_sleeper_waiver_intelligence.py tests/test_f3_d2_faab_intelligence.py tests/test_f3_d3_waiver_action_plan.py tests/test_f3_d4_waiver_action_integration.py => 30 passed in 0.08s
- python scripts/verify_f3_d4_integration.py => 30 passed in 0.08s

### Integration-tested
- F3-D.4 waiver-action integration is passing in the repository test harness.
- F3-B.4, F3-C.1, and F3-C.2 are verified by targeted tests.

### Live-route tested
- Not proven in this review. The app was checked for availability and the ports were not accepting the expected Flask service, so no live route validation is claimed.

### PostgreSQL-proven
- Not proven. The repo documents parity checks as skipped on the PostgreSQL side and prohibits claiming PostgreSQL parity.

## Test-tier usage

- fast: ./scripts/test_fast.sh
- draft-layer: ./scripts/test_draft_layer.sh (configurable with F3_TEST_BATCH_SIZE, default 25)
- full regression: ./scripts/test_full_regression.sh (configurable with F3_TEST_BATCH_SIZE, default 1000)

## Known risks and technical debt

- The live application route /sleeper-intelligence/json was not validated because the application server was unavailable.
- Remaining FAAB budget source is not proven authoritative in the repo; do not guess from waiver_budget_used without verifying semantics.
- Publication gating for waiver outputs is still not implemented as a release gate.
- UI rendering for waiver action plans has not been runtime-verified.
- Local roster context currently labels the owner as "My Team" instead of an authoritative ownership record.
- Postgres parity remains incomplete and should be treated as blocked until isolated DB validation runs.

## Next milestone

- F3-D.5 Waiver Action Publication and UI
- Why next: it is the next evidence-based layer after F3-D.4 integration and the waiver intelligence stack were validated.
- Definition of done:
  - render waiver candidates and action plans in the Sleeper Intelligence page
  - include add player, drop player, urgency, FAAB percentage, unit bid when known, and explanation
  - preserve JSON output contract
  - fail closed when source data is stale, blocked, or missing
  - add route/template tests
  - do not submit transactions

## Stop conditions

- Missing authoritative FAAB field or semantics
- Database unavailable for isolation testing
- Route response differs from expected contract
- Starter/bench identity cannot be proven
- Readiness source is stale or missing
- Any publication path is allowed to fail open

This roadmap reflects the actual repository state and intentionally excludes the stale narrative from earlier pre-F3 phases.


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

# F3-B.1 COMPLETE

Evidence:
- 8 passed
- 10 subtests passed

Validated:
- Baseline large-batch import
- Replay idempotency
- Multi-replay stability
- Partial replay recovery
- Conflict rejection
- Failed-event replay
- Audit evidence generation

Scope:
DraftEventProcessor
InMemoryDraftEventStore

Next:
F3-B.2 Reconciliation Engine

Objectives:
- Compare Sleeper picks vs draft_events
- Compare Sleeper picks vs draft_selections
- Detect drift
- Produce reconciliation status and audit output

# F3-B.2 COMPLETE

Evidence:
- 11 passed
- Reconciliation engine verified

Validated:
- Count reconciliation
- Missing pick detection
- Extra pick detection
- Player drift detection
- Roster drift detection
- Event drift detection
- Status drift detection
- Duplicate source detection
- Foreign draft detection
- JSON reporting

Scope:
DraftReconciler
InMemoryDraftEventStore

Remaining:
- Live Sleeper adapter integration
- PostgreSQL parity validation
- Publication readiness integration