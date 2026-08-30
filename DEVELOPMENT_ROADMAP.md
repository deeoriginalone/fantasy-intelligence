# Development Roadmap

## Context

This roadmap is drafted for the current repository state. It prioritizes the draft path because the draft is time-sensitive and the project is already past the point where speculative output can be allowed to masquerade as live recommendation quality.

## Status legend

- VERIFIED
- IMPLEMENTED, NEEDS HARDENING
- PARTIALLY IMPLEMENTED
- PROTOTYPE, NOT INTEGRATED
- BLOCKED BY INPUTS
- PLANNED

## NOW: Draft readiness

### 1. Draft-session identity validation
- Objective: ensure one authoritative draft session is used and all local state is mapped to that session
- Evidence or dependency: active draft board and Sleeper sync logic exist in [app.py](app.py), but session validation is not yet fully enforced
- Completion criteria: a draft session must have an authoritative identity, and mismatched or disconnected sessions are rejected or quarantined
- Risk if skipped: local draft state can drift from live draft state
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: draft-state hardening branch

### 2. Live Sleeper sync reconciliation
- Objective: reconcile live Sleeper picks with local board, roster, and recommendation state
- Evidence or dependency: [app.py](app.py) contains sync functions; no formal reconciliation contract is documented as enforced
- Completion criteria: pick_no uniqueness and roster consistency are enforced; unresolved players are quarantined
- Risk if skipped: live data can silently overwrite or drift from local truth
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: sync hardening branch

### 3. Pick uniqueness and unresolved-player quarantine
- Objective: reject duplicates and flag unmatched player names instead of silently storing incomplete records
- Evidence or dependency: active sync code uses name matching but does not appear to enforce a strict unresolved-player quarantine contract
- Completion criteria: duplicate picks and unresolved players are explicitly trapped
- Risk if skipped: recommendation and roster surfaces can become noisy or wrong
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: sync-validation branch

### 4. Roster invariants
- Objective: enforce valid roster composition and prevent invalid local roster states
- Evidence or dependency: [app.py](app.py) contains roster-building and insert/delete logic, but invariants are not formally enforced
- Completion criteria: local roster state cannot become impossible by mutation or sync drift
- Risk if skipped: recommendation need scoring and lineup logic will be fed invalid state
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: roster-state branch

### 5. Undo correctness and mutation history
- Objective: guarantee that undo operations restore the correct board and roster state
- Evidence or dependency: [app.py](app.py) contains `undo_draft_pick`; independent guarantees are not documented as a test-backed contract
- Completion criteria: undo returns the state to a consistent pre-pick condition without stale board or roster rows
- Risk if skipped: manual edits can leave the system inconsistent
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: draft-tracking branch

### 6. ADP/rank/tier freshness and missing-data policy
- Objective: define what counts as stale or missing for ADP, ranking, tier, and player identity
- Evidence or dependency: recommendation logic in [candidate_filter.py](candidate_filter.py) and [dynamic_need_model.py](dynamic_need_model.py) uses defaults for missing values
- Completion criteria: missing values are explicit contract violations or are clearly marked as degraded
- Risk if skipped: stale or missing values silently distort rankings and recommendations
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: recommendation trust branch

### 7. Deterministic mock-draft seed and replay
- Objective: make mock-draft output deterministic and replayable for QA and comparison
- Evidence or dependency: [mocklab/simulator.py](mocklab/simulator.py) includes random scoring and no stated seed policy
- Completion criteria: same seed + same state = same draft outcome
- Risk if skipped: mock output cannot be trusted as a stable decision surface
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: mock-simulation branch

### 8. Dedicated draft regression tests
- Objective: add direct tests for board consistency, duplicate pick handling, unresolved-player quarantine, undo correctness, and deterministic behavior
- Evidence or dependency: current tests cover security, DB config, pick'em, survivor, and readiness; dedicated draft regression coverage is still incomplete
- Completion criteria: the draft path has a direct, repeatable regression suite
- Risk if skipped: draft-state regressions will not be caught before season
- Status: PARTIALLY IMPLEMENTED
- Suggested commit boundary: regression-test branch

## NEXT: Recommendation trust

### 1. Integrate readiness.py into draft recommendations
- Objective: make draft recommendation publication depend on explicit readiness state
- Evidence or dependency: [readiness.py](readiness.py) exists in the working tree but is not in HEAD and not integrated into runtime
- Completion criteria: draft recommendation surfaces can show READY / APPROXIMATE / INCOMPLETE / STALE / BLOCKED states
- Risk if skipped: recommendation output can look valid while sources are stale or incomplete
- Status: PROTOTYPE, NOT INTEGRATED
- Suggested commit boundary: recommendation publication gate branch

### 2. Add visible READY / APPROXIMATE / INCOMPLETE / STALE / BLOCKED states
- Objective: expose the actual state machine to the user instead of implied confidence
- Evidence or dependency: design states are defined; runtime gating is not yet integrated
- Completion criteria: every publication path has a valid state label and explanation
- Risk if skipped: users receive opaque or confident outputs with no source-quality context
- Status: PROTOTYPE, NOT INTEGRATED
- Suggested commit boundary: recommendation-state branch

### 3. Add recommendation source timestamps
- Objective: attach refresh times to the underlying values driving a recommendation
- Evidence or dependency: the design requires source and freshness handling; this is not yet enforced in runtime code
- Completion criteria: each recommendation output lists relevant source timestamps and freshness windows
- Risk if skipped: recommendation trust cannot be evaluated quickly
- Status: PLANNED
- Suggested commit boundary: source-traceability branch

### 4. Add traceability/explanation payloads
- Objective: make recommendation decisions explainable and auditable
- Evidence or dependency: some diagnostic helpers exist, but no enforced recommendation payload is present
- Completion criteria: explanation payloads include rank, ADP, need, scarcity, tier, and source freshness state
- Risk if skipped: recommendations remain hard to defend or audit
- Status: PLANNED
- Suggested commit boundary: explainability branch

### 5. Add publication gates
- Objective: prevent incomplete or synthetic recommendations from being presented as live
- Evidence or dependency: design document explicitly says live weekly recommendations remain blank until the required inputs are connected
- Completion criteria: the system blocks publication when required sources are absent or stale
- Risk if skipped: false confidence may be exposed to users
- Status: PLANNED
- Suggested commit boundary: publication-gate branch

## LATER: Survivor v2

### 1. Establish real ownership source
- Objective: create a real, trusted ownership input for Survivor analysis
- Evidence or dependency: current runtime is blocked by missing ownership source information
- Completion criteria: ownership is present, refreshed, and tied to the active decision window
- Risk if skipped: Survivor recommendations cannot be trusted
- Status: BLOCKED BY INPUTS
- Suggested commit boundary: Survivor source branch

### 2. Establish QB-status source
- Objective: provide explicit QB uncertainty and live QB-status context to the model
- Evidence or dependency: active design requires QB-status input, but this source is currently absent
- Completion criteria: the model can distinguish stable, uncertain, and unavailable QB states
- Risk if skipped: QB uncertainty is silently mis-modeled
- Status: BLOCKED BY INPUTS
- Suggested commit boundary: Survivor source branch

### 3. Establish injury/weather stability source
- Objective: provide explicit injury and weather stability signals to the model
- Evidence or dependency: the design requires injury and weather inputs to avoid approximating critical missing data
- Completion criteria: the model uses explicit and fresh injury/weather data
- Risk if skipped: recommendations are built off synthetic proxies and not valid live intelligence
- Status: BLOCKED BY INPUTS
- Suggested commit boundary: Survivor source branch

### 4. Add freshness contracts
- Objective: define how old ownership, QB, weather, and injury data are handled
- Evidence or dependency: repository design documents mention refresh sequence and validation requirements
- Completion criteria: each source has defined freshness thresholds and decay behavior
- Risk if skipped: stale information is treated as live
- Status: PLANNED
- Suggested commit boundary: source-freshness branch

### 5. Design migrations
- Objective: formalize the schema and runtime assumptions for the Survivor v2 source model
- Evidence or dependency: migration work is explicitly deferred in the design guidance
- Completion criteria: source tables and contracts are documented before implementation
- Risk if skipped: the system will patch around missing schema or input assumptions
- Status: PLANNED
- Suggested commit boundary: schema-design branch

### 6. Implement documented 60/20/10/10 formula
- Objective: implement the formal Survivor weighting once the required inputs exist
- Evidence or dependency: the authoritative design defines the target weighting and refresh sequence
- Completion criteria: runtime formula matches the documented target behavior without drift
- Risk if skipped: the runtime will continue to use approximation proxies rather than true design behavior
- Status: PLANNED
- Suggested commit boundary: Survivor formula branch

### 7. Back-test weights
- Objective: validate the formula against historical or simulation data once the live source model is available
- Evidence or dependency: design calls for QA and acceptance criteria, but no historical calibration is currently documented in the active runtime state
- Completion criteria: weights are validated under a defined back-test and acceptance framework
- Risk if skipped: formula confidence is not evidence-based
- Status: PLANNED
- Suggested commit boundary: measurement branch

## FUTURE

### 1. Historical draft outcome calibration
- Objective: compare recommendation outputs to actual draft outcomes and calibrate the model
- Evidence or dependency: [draft_outcome_tracker.py](draft_outcome_tracker.py) exists but a full historical calibration framework is not documented as implemented
- Completion criteria: historical outcome data is used to validate recommendation quality
- Risk if skipped: recommendation quality remains subjective
- Status: PLANNED
- Suggested commit boundary: calibration branch

### 2. Mock strategy evaluation
- Objective: compare strategy profiles across a shared simulation baseline
- Evidence or dependency: [mocklab/simulator.py](mocklab/simulator.py) provides simulation logic but not a full comparative evaluation framework
- Completion criteria: strategy performance is clearly measured by consistent criteria
- Risk if skipped: mock output remains anecdotal
- Status: PLANNED
- Suggested commit boundary: strategy-evaluation branch

### 3. Recommendation calibration
- Objective: align model outputs with historical data and publish confidence bands only when supported by source quality
- Evidence or dependency: design includes confidence points and QA requirements, but live recommendation publication is gated by data availability
- Completion criteria: recommendation quality is calibrated to actual outcomes and source quality
- Risk if skipped: confidence and recommendation quality become unreliable
- Status: PLANNED
- Suggested commit boundary: calibration branch

### 4. Multi-draft session support
- Objective: support multiple live or test draft sessions without cross-session contamination
- Evidence or dependency: active runtime uses a single active draft ID pattern in [config.py](config.py)
- Completion criteria: session ownership is isolated and visible
- Risk if skipped: session drift can corrupt recommendation output and local board state
- Status: PLANNED
- Suggested commit boundary: session-management branch

### 5. Expanded weather and injury providers
- Objective: add richer provider coverage for weather and injury state
- Evidence or dependency: design calls for real weather and injury inputs; current runtime does not document a verified provider contract
- Completion criteria: provider lifecycle and freshness are defined and validated
- Risk if skipped: recommendation surfaces remain dependent on incomplete proxies
- Status: PLANNED
- Suggested commit boundary: provider-integration branch

## Suggested commit boundaries

- Draft-state hardening branch: sessions, picks, roster invariants, undo correctness
- Recommendation trust branch: readiness gating, source freshness, publication checks
- Survivor source branch: ownership, QB, weather/injury input contracts
- Mock determinism branch: seeding, replay, and strategy evaluation
- Calibration branch: historical outcome validation and recommendation quality measurement

## Completion criteria for the overall roadmap

The project can be considered season-ready only when:
- draft session identity is valid and enforced
- pick uniqueness and unresolved-player handling are enforced
- roster state is valid and recoverable after undo
- source freshness is checked before recommendation publication
- mock drafting is deterministic and replayable
- Survivor inputs and weighting are backed by real source contracts
- live weekly recommendations remain blank until all required inputs are actually connected
