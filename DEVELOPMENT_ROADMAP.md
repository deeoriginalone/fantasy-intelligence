# Development Roadmap

## Remediation Checkpoint (2026-09-05)

- Branch/HEAD: `feature/draft-outcome-tracking` / `bbf6295f1694285fc4e1d420fcf42f09ee61a65e`; 0 ahead and 11 behind upstream; no staged changes; 16 modified tracked paths, 52 untracked paths, 0 deleted, 0 renamed.
- Corrections: forward migration 010 for existing schemas; authoritative PostgreSQL `ordered_state()` metadata; migration, polling, and verifier tests; fail-closed parity verifier.
- Current validation: migration contracts `2 passed`; polling/verifier/remediation tests `8 passed`; reduced isolated PostgreSQL parity `18 passed, 0 skipped, 4 subtests in 12.23s`. Clean-install migration validation, upgrade validation, row and constraint preservation, migration repeatability, and guarded cleanup passed in isolated databases. The full verifier remains pending.
- An isolated test/parity PostgreSQL environment is configured and reachable. The reduced 25-event/2-replay parity gate passed with 18 tests, zero skips, and 4 subtests. Clean-install migration execution, upgrade execution, row preservation, constraint preservation, migration repeatability, and guarded cleanup all passed in isolated databases. Full parity and production PostgreSQL behavior remain unproven.
- Next database milestone: run the full 1000-event/10-replay verifier when full audit evidence is required; add failure-injection/rollback validation; reconcile documentation again after those results.

## Current Evidence-Based Roadmap (2026-09-05)

- Checkpoint: `feature/draft-outcome-tracking` at `bbf6295f1694285fc4e1d420fcf42f09ee61a65e`; 11 commits behind upstream, no staged changes, 16 modified tracked files, 52 untracked files, no deletes/renames. Current readiness is **READY WITH BLOCKERS** for supervised draft work and **NOT READY** for production operations.
- Cumulative phase map: F3-A/A.1/A.2 event pipeline and runtime; F3-B.1/B.2 replay and reconciliation; F3-B.3 live-read reconciliation; F3-B.4 readiness; F3-C.1/C.2 publication; F3-D.1-D.5 waiver intelligence, action plans, integration, and gated UI. All are implemented and focused-tested; tiers do not imply production proof.
- PostgreSQL: source implementation, migration 010, metadata fidelity, and fixture cleanup are present and source-contract tested. Reduced isolated parity **PASSED** with 18 tests and zero skips. Clean-install and upgrade execution, row/constraint preservation, repeatability, and guarded cleanup also **PASSED** in isolated databases. Full parity and rollback proof are **VERIFICATION PENDING**; production PostgreSQL remains **NOT PROVEN**.
- Live routes: local `/sandbox`, `/sleeper-intelligence/`, `/sleeper-intelligence/json`, `/draftboard`, and the authenticated draft-picks read were exercised; broader external reads and production routes remain unproven.
- Security: CSRF and authorization boundaries are present; external writes are not proven and must remain disabled/manual. Rehearsal captures may contain sensitive session material and stay excluded.
- Immediate database milestone: run the full 1000-event/10-replay verifier when full audit evidence is required, then perform failure-injection/rollback validation.
- Next operational milestone: no-write draft-day operational readiness rehearsal.
- Definition of done: no skipped configured parity tests, cleanup zero rows, executed clean-install and upgrade proof, fresh route evidence, and synchronized documentation. Focused polling regression coverage is already present.

## Cumulative Capabilities

Rankings/player intelligence, identity bridge, draft board/tier/VBD/scarcity, strategy simulation, Mock Draft Lab, draft recommendations, event capture/replay/idempotency, reconciliation/readiness/publication, Draft HQ polling and post-draft transition, Sleeper/waiver/FAAB/action plans/publication UI, weekly/lineup/market/Pick'em/Survivor/reporting, sandbox MOCK/LIVE controls, PostgreSQL persistence/migrations, and audit/rehearsal infrastructure exist in the repository. Their proven tiers range from unit-tested to local-route-tested; none are production-proven by this review.

## Commit Gate

Do not treat the current tree as one commit. Partition implementation, tests/docs, evidence, and excluded captures separately. Migration 010 provides the forward upgrade path; clean-install and upgrade execution have passed in isolated databases. Rollback and full parity remain required before release readiness.

## Historical Checkpoint (superseded)

- Date: 2026-09-04
- Branch: `feature/draft-outcome-tracking`
- HEAD: `cc888df5cc3de7ab20ff574b4725b432ba8240de`
- Upstream: no tracking branch; eight commits ahead of `origin/feature/draft-outcome-tracking`
- Working tree: uncommitted `templates/draftboard.html` and regenerated F3-D.4 verification JSON are modified; nothing is staged; untracked audit, discovery, rehearsal, documentation, script, source-capture, and test artifacts remain intentionally unstaged
- Validation: syntax passed; fast tier `44 passed in 0.11s`; F3-D.1 through F3-D.5 suite `38 passed in 0.26s`; F3-D.4 verifier `30 passed`; full suite `268 passed, 9 skipped, 2 xfailed, 20 subtests passed`; PostgreSQL parity `9 passed, 9 skipped, 10 subtests passed`
- F3-D.5: **COMPLETE** at repository level in `6e791be`; local route evidence exists, but no production claim

## Draft HQ Polling Status

- `templates/draftboard.html` is an uncommitted source change. It renders the session CSRF token with `tojson`, uses POST `/test-draft-picks`, sends `X-CSRF-Token`, and preserves polling/manual-refresh behavior.
- Classification: **IMPLEMENTED, LIVE-ROUTE VERIFIED, SOURCE-CONTRACT AND DETERMINISTIC REGRESSION TESTED**.
- Evidence: GET route `405`; anonymous POST `401`; two session-CSRF POSTs `200` with JSON array `[]`; `/draftboard` rendered with the CSRF token. No admin token was exposed.
- The route performs a read through `get_draft_picks`; this is a narrow configured-draft read proof, not proof of all Sleeper reads or production readiness.

Remaining Draft HQ rehearsal gaps: real pick-count change behavior, blocked/error-state rehearsal, broader Sleeper endpoint coverage, reconciliation/database proof, isolated PostgreSQL parity, and production-like validation.

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
- PostgreSQL: **REDUCED GATE PASSED, MIGRATION VALIDATION PASSED, FULL VERIFICATION PENDING**. An isolated test/parity PostgreSQL environment is configured and reachable. `ordered_state()` returns authoritative `DraftEvent` metadata and `cleanup_test_draft()` is restricted to `f3b31-` fixtures. Rollback and production PostgreSQL behavior remain unproven.
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

- Implemented in source; reduced isolated verification passed and full verification remains pending.
- Migration 010, authoritative event metadata reconstruction, and `f3b31-`-guarded cleanup are source-contract tested. No full 1000-event/10-replay no-skip PostgreSQL result or production PostgreSQL proof is claimed.

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

### PostgreSQL validation
- Reduced isolated parity passed with 18 tests, zero skips, and 4 subtests.
- Clean-install and upgrade migration validation, row and constraint preservation, repeatability, and guarded cleanup passed in isolated databases.
- Full 1000-event/10-replay verification and failure-injection/rollback proof remain pending; production PostgreSQL behavior is not proven.

## Test-tier usage

- fast: ./scripts/test_fast.sh
- draft-layer: ./scripts/test_draft_layer.sh (configurable with F3_TEST_BATCH_SIZE, default 25)
- full regression: ./scripts/test_full_regression.sh (configurable with F3_TEST_BATCH_SIZE, default 1000)

## Known risks and technical debt

- The local application routes and Draft HQ polling contract were validated on port 5050; focused deterministic polling tests also pass. Only the configured draft-picks read was externally exercised, while other live Sleeper reads and production behavior remain unproven.
- Remaining FAAB budget source is not proven authoritative in the repo; do not guess from waiver_budget_used without verifying semantics.
- Waiver publication gating is implemented and unit/route/template tested, but runtime rendering has not been verified.
- Local roster context currently labels the owner as "My Team" instead of an authoritative ownership record.
- Reduced PostgreSQL parity and migration validation have passed in isolated databases; full parity and failure-injection/rollback proof remain pending.

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