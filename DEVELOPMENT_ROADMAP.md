# Development Roadmap

## Current Review Checkpoint

- Date: 2026-09-04
- Branch: `feature/draft-outcome-tracking`
- HEAD: `cc888df5cc3de7ab20ff574b4725b432ba8240de`
- Upstream: no tracking branch; eight commits ahead of `origin/feature/draft-outcome-tracking`
- Working tree: uncommitted `templates/draftboard.html` and regenerated F3-D.4 verification JSON are modified; nothing is staged; untracked audit, discovery, rehearsal, documentation, script, source-capture, and test artifacts remain intentionally unstaged
- Validation: syntax passed; fast tier `44 passed in 0.11s`; F3-D.1 through F3-D.5 suite `38 passed in 0.26s`; F3-D.4 verifier `30 passed`; full suite `268 passed, 9 skipped, 2 xfailed, 20 subtests passed`; PostgreSQL parity `9 passed, 9 skipped, 10 subtests passed`
- F3-D.5: **COMPLETE** at repository level in `6e791be`; local route evidence exists, but no production claim

## Draft HQ Polling Status

- `templates/draftboard.html` is an uncommitted source change. It renders the session CSRF token with `tojson`, uses POST `/test-draft-picks`, sends `X-CSRF-Token`, and preserves polling/manual-refresh behavior.
- Classification: **IMPLEMENTED, LIVE-ROUTE VERIFIED, REGRESSION TEST MISSING**.
- Evidence: GET route `405`; anonymous POST `401`; two session-CSRF POSTs `200` with JSON array `[]`; `/draftboard` rendered with the CSRF token. No admin token was exposed.
- The route performs a read through `get_draft_picks`; this is a narrow configured-draft read proof, not proof of all Sleeper reads or production readiness.

Remaining Draft HQ rehearsal gaps: focused polling regression coverage, real pick-count change behavior, blocked/error-state rehearsal, broader Sleeper endpoint coverage, reconciliation/database proof, isolated PostgreSQL parity, and production-like validation.

## Local Runtime Validation

- Port 5050 verified listening.
- `/sandbox` returned HTTP 200.
- `/sleeper-intelligence/` returned HTTP 200.
- `/sleeper-intelligence/json` returned HTTP 200.
- Local Flask runtime: VERIFIED
- Local application routes: VERIFIED
- Sandbox route availability: VERIFIED
- Sleeper Intelligence route availability: VERIFIED
- JSON endpoint availability: VERIFIED

The configured Sleeper draft-picks read was locally exercised and returned a successful empty array. Broader Sleeper endpoint coverage, non-empty pick retrieval, Sleeper writes, and production behavior remain unproven. External transaction execution, PostgreSQL parity, and production deployment remain unproven.

## Current Readiness Verdicts

- Draft day: **READY WITH BLOCKERS** as a supervised copilot. Draft HQ polling is locally exercised, but live Sleeper breadth, live database, fresh-data, and full rehearsal evidence is missing.
- Post-draft: **READY WITH BLOCKERS** in the unit/integration harness. Live completion detection, schema, roster reconciliation, and restart/retry rehearsal remain unproven.
- Regular season: **NOT READY** for Week 1 operations. Local route availability is verified, but operational integration, freshness, recovery, and live evidence are incomplete.
- PostgreSQL: **CODE PRESENT, PARITY NOT PROVEN**. The isolated parity suite is environment-gated; `PostgresDraftEventStore.ordered_state()` returns tuples and no `cleanup_test_draft()` hook is present.
- Authoritative FAAB: **NOT PROVEN**. Do not infer remaining balance from usage fields or publish unit bids without an explicit verified budget.
- Automatic execution: **NOT IMPLEMENTED/PROVEN**. Treat all draft and season actions as recommendation or manual-assistance workflows.

## Exact Next Milestone: Draft-Day Operational Readiness Rehearsal

Definition of done: configure and verify the active league/draft/season/settings; prove owner and slot mapping; exercise fresh Sleeper reads and refresh after picks; validate readiness and reconciliation against the isolated database; open Draft HQ and confirm visible recommendations, next-pick forecast, roster needs, freshness, and blocked-error states; record HTTP responses and logs; perform no external writes.

Implementation/evidence surfaces: `app.py`, `config.py`, `services/sleeper_service.py`, `sleeper_draft_signals.py`, `draft_readiness.py`, `draft_events/live_reconciliation.py`, `draft_events/readiness.py`, and the Draft HQ templates.

Tests: existing draft readiness, live reconciliation, slot/owner, publication, and F3-D.5 suites; add route/runtime smoke coverage for the configured environment and run isolated PostgreSQL parity tests.

Stop conditions: missing or conflicting identity, stale/missing readiness source, database/schema failure, reconciliation drift, unavailable Sleeper reads, or any unexpected external write path.

## Historical checkpoint, superseded by the current review checkpoint above

- Date: 2026-09-03
- Branch: feature/draft-outcome-tracking
- HEAD: 7ff86c633b8a2f5c5c7b5b34667344d2fa14440b
- Working tree: review state included modified documentation and untracked audit/discovery files. No production code changes were introduced during that historical review.

## Historical verified repository state

The repository was validated for implementation and unit/integration testing at that historical checkpoint. Its current local route evidence is recorded above; PostgreSQL parity is still not proven.

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
- Local Flask route availability is verified on port 5050 for `/sandbox`, `/sleeper-intelligence/`, `/sleeper-intelligence/json`, and `/draftboard`; the POST-only `/test-draft-picks` contract was also exercised. Live Sleeper read validation beyond the configured draft-picks read and production route validation remain unproven.

### PostgreSQL-proven
- Not proven. The repo documents parity checks as skipped on the PostgreSQL side and prohibits claiming PostgreSQL parity.

## Test-tier usage

- fast: ./scripts/test_fast.sh
- draft-layer: ./scripts/test_draft_layer.sh (configurable with F3_TEST_BATCH_SIZE, default 25)
- full regression: ./scripts/test_full_regression.sh (configurable with F3_TEST_BATCH_SIZE, default 1000)

## Known risks and technical debt

- The local application routes and Draft HQ polling contract were validated on port 5050; only the configured draft-picks read was externally exercised, while other live Sleeper reads and production behavior remain unproven.
- Remaining FAAB budget source is not proven authoritative in the repo; do not guess from waiver_budget_used without verifying semantics.
- Waiver publication gating is implemented and unit/route/template tested, but runtime rendering has not been verified.
- Local roster context currently labels the owner as "My Team" instead of an authoritative ownership record.
- Postgres parity remains incomplete and should be treated as blocked until isolated DB validation runs.

## Historical next milestone record

Draft-day operational readiness rehearsal.

- Why it was next: F3-D.5 was complete in code and dedicated tests; live configured-league, database, and route behavior were the highest operational risks at that checkpoint. Current Draft HQ polling evidence narrows, but does not eliminate, those risks.
- Definition of done:
      - verify active league, draft, season, team count, rounds, and owner slot from live configuration/data
      - exercise fresh Sleeper reads, pick refresh, readiness, reconciliation, and Draft HQ error states
      - validate the configured database against the required schema in an isolated environment
      - capture route responses, logs, and a no-write rehearsal record
      - do not submit picks or season transactions

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