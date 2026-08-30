# Project Status

## Document metadata

- Reviewed branch: `feature/draft-outcome-tracking`
- Reviewed HEAD commit: `bde5025` — `Add Survivor behavior and specification-gap tests`
- Verification commands used:
  - `git status --short`
  - `git log --oneline -8`
  - `git diff --name-status`
  - `./venv/bin/python -m pytest -q`
  - `git ls-files --error-unmatch readiness.py`
  - `git ls-files --error-unmatch tests/test_readiness.py`
- Latest verified test result: 80 passed, 2 xfailed
- Scope note: These results describe the current repository state at the time of review and do not infer a different or future runtime state.

## Status definitions

- VERIFIED: active runtime code exists, direct tests exercise the behavior, and the documented behavior matches the implementation.
- IMPLEMENTED, NEEDS HARDENING: active runtime exists but requires additional validation, state safeguards, or source freshness enforcement.
- PARTIALLY IMPLEMENTED: runtime exists but behavior is incomplete or only partially validated.
- PROTOTYPE, NOT INTEGRATED: code exists in a prototype or helper form but is not integrated into the active runtime contract.
- BLOCKED BY INPUTS: the runtime exists but required source data is missing or disconnected from the live environment.
- PLANNED: subsystem is referenced or expected but not yet implemented as a verified runtime component.

## Implementation matrix

| Subsystem | Status | Active files | Verified behavior | Unverified behavior | Blockers | Next action |
|---|---|---|---|---|---|---|
| Flask application | IMPLEMENTED, NEEDS HARDENING | [app.py](app.py), [config.py](config.py), [auth.py](auth.py) | Flask runtime and route registration exist; runtime boots in project context | Full runtime behaviors beyond basic route exposure | environment and source connectivity | confirm active runtime startup and route integrity |
| Security/auth/CSRF | VERIFIED | [auth.py](auth.py), [tests/test_security_and_validation.py](tests/test_security_and_validation.py) | admin auth and CSRF protections are directly tested | broader auth edge cases beyond current tests | none directly observed | keep current contract coverage |
| DB configuration | VERIFIED | [config.py](config.py), [tests/test_db_config_contract.py](tests/test_db_config_contract.py) | configuration contract exists and is directly tested | non-runtime DB edge cases beyond contract | none directly observed | keep contract tests current |
| Draft recommendation engine | PARTIALLY IMPLEMENTED | [candidate_filter.py](candidate_filter.py), [dynamic_need_model.py](dynamic_need_model.py), [scarcity_model.py](scarcity_model.py), [balanced_recommendation_score.py](balanced_recommendation_score.py), [app.py](app.py) | ranking, need, and scarcity logic exist in runtime code | freshness and invalid-data handling still partial | stale ADP/rank/tier values and missing-source policy | add explicit freshness checks |
| Draft board | PARTIALLY IMPLEMENTED | [app.py](app.py) | local board tracking and toggles exist | board/state reconciliation with live picks is not fully enforced | sync drift and local-only state | enforce source-of-truth contract |
| Draft tracking | PARTIALLY IMPLEMENTED | [app.py](app.py), [draft_outcome_tracker.py](draft_outcome_tracker.py) | draft assessment and outcome logging exist | persistent state invariants, replay, and undo correctness are not fully enforced | local drift and session disconnects | add invariant tests |
| Live Sleeper synchronization | PARTIALLY IMPLEMENTED | [app.py](app.py), [services/sleeper_service.py](services/sleeper_service.py), [sleeper_hub.py](sleeper_hub.py), [sleeper_intelligence.py](sleeper_intelligence.py) | sync functions exist and use live Sleeper API data | unresolved-player detection, uniqueness, and draft-session validation remain partial | name-match drift, stale snapshots, disconnected draft sessions | harden source reconciliation |
| Roster construction | PARTIALLY IMPLEMENTED | [app.py](app.py) | roster-building helpers exist | roster invariant enforcement and mutation safety are incomplete | invalid roster states and undo inconsistencies | add roster invariant checks |
| Mock draft | PARTIALLY IMPLEMENTED | [mocklab/simulator.py](mocklab/simulator.py), [app.py](app.py) | simulation engine and route logic exist | deterministic replay and outcome stability are not guaranteed | nondeterministic random scoring | add seed and replay contracts |
| Draft outcome tracking | PARTIALLY IMPLEMENTED | [draft_outcome_tracker.py](draft_outcome_tracker.py) | prediction logging and outcome resolution exist | historical accuracy calibration and contract enforcement are still evolving | data resolution and actual-availability tracking | formalize full outcome contract |
| Pick'em | VERIFIED | [yahoo_pickem.py](yahoo_pickem.py), [tests/test_yahoo_pickem.py](tests/test_yahoo_pickem.py) | direct contract and boundary tests exist and pass | no live data connectivity in this repository state | real Yahoo/market feeds not connected in this audit scope | keep tests aligned with authoritative design |
| Survivor | BLOCKED BY INPUTS | [survivor_intelligence.py](survivor_intelligence.py), [survivor_routes.py](survivor_routes.py), [tests/test_survivor_intelligence.py](tests/test_survivor_intelligence.py) | spec-gap tests document the missing-input problem | live Survivor output still not fully supportable | missing ownership, QB-status, and weather sources | establish real input sources and freshness policy |
| Weekly intelligence | PARTIALLY IMPLEMENTED | [weekly_intelligence.py](weekly_intelligence.py), [weekly_routes.py](weekly_routes.py) | weekly intelligence and routes exist | live weekly recommendation publication stays gated by source inputs | Yahoo, market, ratings, injury, weather inputs not connected | integrate input feeds before publication |
| Fantasy projection correlation | PLANNED | [import_players.py](import_players.py), [import_draft_intelligence.py](import_draft_intelligence.py) | imports exist in active runtime | cross-source correlation and validation are not fully represented as a dedicated subsystem | missing correlation contract | formalize source correlation checks |
| Readiness validator | PROTOTYPE, NOT INTEGRATED | [readiness.py](readiness.py), [draft_readiness.py](draft_readiness.py) | helper logic exists and tests exist in the working tree, but only as untracked files | no active runtime integration in HEAD | not committed and not integrated | integrate with runtime or keep as isolated helper |
| Providers | PARTIALLY IMPLEMENTED | [providers/](providers/), [services/](services/) | provider-oriented modules exist | provider dependency contracts and freshness validation are not fully formalized | provider disconnects and stale data | define provider contract and failure policy |
| Templates/UI | IMPLEMENTED, NEEDS HARDENING | [templates/](templates/) | UI and route surfaces exist | not all runtime surfaces are validated by tests | drift between backend state and UI expectations | add UI-state regression checks |
| Testing | VERIFIED | [tests/](tests/) | full suite currently passes in the repository state | coverage gaps remain for draft/session invariants and source freshness | no dedicated draft regression suite | add draft-specific regression tests |

## Test inventory

### Current test files
- [tests/test_security_and_validation.py](tests/test_security_and_validation.py)
- [tests/test_db_config_contract.py](tests/test_db_config_contract.py)
- [tests/test_yahoo_pickem.py](tests/test_yahoo_pickem.py)
- [tests/test_survivor_intelligence.py](tests/test_survivor_intelligence.py)
- [tests/test_readiness.py](tests/test_readiness.py)

### Current verified summary
- Collected tests: 82
- Passing tests: 80
- Xfails: 2
- Command run: `./venv/bin/python -m pytest -q`
- Result: 80 passed, 2 xfailed

### Coverage grouping
- security: yes
- pickem: yes
- survivor: yes
- readiness: yes
- database: yes
- draft: partial

### Major uncovered areas
- live draft session identity validation
- Sync reconciliation after partial failure
- roster invariant validation
- undo/replay correctness
- deterministic mock-draft review
- source freshness and missing-data policy for recommendation inputs
- explicit runtime publication gate for live weekly recommendations

## Recent meaningful commit history

### 9a3259c
- Summary: `Harden Flask admin auth and CSRF protections`
- Why it exists: secure the Flask runtime by tightening admin access and request validation
- What problem it solved: session and request protection around admin/restricted routes
- What remains afterward: draft/session integrity and source freshness remain separate concerns

### 77c367b
- Summary: `Unify active database configuration`
- Why it exists: remove active runtime split between DB_* and FI_DB_* style patterns
- What problem it solved: standardized config contract for the active runtime
- What remains afterward: live-source freshness and session reconciliation are still not fully enforced

### de7c9a1
- Summary: `Add Pick'em contract and boundary tests`
- Why it exists: validate pick'em behavior under contract definitions and boundary cases
- What problem it solved: made pick'em semantics explicit and testable
- What remains afterward: real external market/Yahoo inputs still need to be connected or intentionally gated

### e4a0df7
- Summary: `Clarify Pick'em signals and add confidence-band coverage`
- Why it exists: clarify signal names and confidence-band behavior
- What problem it solved: removed semantic ambiguity in the pick'em contract
- What remains afterward: the design still distinguishes between authoritative logic and live input connectivity

### bde5025
- Summary: `Add Survivor behavior and specification-gap tests`
- Why it exists: clarify exactly where Survivor design diverges from the available runtime inputs
- What problem it solved: exposed the missing ownership/QB/weather-source problem
- What remains afterward: real source procurement and a formal source-freshness contract are still required

### Readiness-related working files
- [readiness.py](readiness.py): exists in the working tree but is absent from HEAD
- [tests/test_readiness.py](tests/test_readiness.py): exists in the working tree but is absent from HEAD
- Verified status: untracked and not part of the current HEAD commit
- Interpretation: prototype-level readiness validation exists, but is not part of the committed runtime contract

## Design-versus-runtime comparison

### Pick'em
- Design status: the authoritative design defines formulas, confidence-point assignment, signal names, and QA requirements
- Runtime status: the active code and tests align to the documented behavior in the current repository state
- Classification: VERIFIED
- Important caveat: live weekly recommendations remain blank until real Yahoo, market, ratings, injury, and weather data are connected

### Survivor
- Design status: the design specifies a 60/20/10/10 target and a refresh sequence, but the runtime is blocked by missing inputs
- Runtime status: active implementation exists but is explicitly limited by missing ownership, QB-status, and weather/injury sources
- Classification: BLOCKED BY INPUTS
- Evidence: [tests/test_survivor_intelligence.py](tests/test_survivor_intelligence.py) documents the specification-gap state

### Readiness
- Design status: the design expects explicit READY / APPROXIMATE / INCOMPLETE / STALE / BLOCKED states
- Runtime status: helper logic exists in the working tree but not in the current HEAD commit and not integrated into the active runtime path
- Classification: PROTOTYPE, NOT INTEGRATED

### Draft
- Design status: the draft design expects session identity validation, pick reconciliation, roster invariants, undo correctness, ADP/rank/tier freshness handling, and deterministic mock-draft behavior
- Runtime status: draft logic exists in the active runtime but not all of the design controls are enforced or tested
- Classification: PARTIALLY IMPLEMENTED

## Known risks

### Critical
- Draft sync drift between live Sleeper state and local draft_board or roster state
- Missing ownership source for Survivor
- Missing explicit QB uncertainty source for Survivor
- Missing explicit weather source for Survivor
- Roster inconsistency across draft_board, league_rosters, my_roster, and sync output

### High
- Stale recommendation outputs without source freshness enforcement
- Missing ADP/rank/tier handling that silently defaults to large fallback values
- Mock draft nondeterminism and lack of deterministic replay contract
- Partial validation of local undo and replay behavior

### Medium
- Draft tracking invariants still under tested
- Provider contracts are not fully formalized for all live surfaces
- Recommendation audit is informative but not yet a blocking gate

### Low
- UI surfaces are present but not fully regression-tested for every state transition
- Some project documentation remains aspirational rather than runtime-backed

### Design decision
- Live weekly recommendations should remain blank until the required Yahoo, market, ratings, injury, and weather inputs are connected; this cannot be treated as a live recommendation surface in the current repository state.

## Explicit blocked-input section

- Survivor ownership source: missing in active runtime
- Explicit QB uncertainty source: missing in active runtime
- Explicit weather source: missing in active runtime
- Freshness policy: not yet hardened across recommendation inputs

## Draft-readiness section

The following draft-readiness concerns remain active:
- session identity validation: not fully enforced
- pick reconciliation: partial and not standardized
- roster invariants: not fully enforced
- undo behavior: present but not fully certified across all state transitions
- missing ranking/ADP/tier handling: present but not formalized as a contract violation
- mock determinism: not fully established
- dedicated tests: incomplete around draft-session integrity and local mutation history

## Where to resume

One concrete next task:
- add a strict draft-session identity and pick-uniqueness validation layer before any recommendation publication, with explicit quarantine behavior for unresolved or duplicate picks.

This is the clearest next step because it closes the gap between the live Sleeper state and the local draft logic without changing the underlying formulas.
