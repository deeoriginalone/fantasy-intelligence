# F3 Roadmap

Date: 2026-09-01

## Current verified milestone

The repository has reached the F3-A and F3-A.1/F3-A.2 implementation milestone. The package is in place and verified by tests and live runtime checks.

## Verified status by milestone

### F3-A: Draft Event Pipeline

Status: complete in implementation and validation.

Completed:
- canonical draft event model
- event persistence to `draft_events`
- selection persistence to `draft_selections`
- duplicate and invalid event handling
- replay support
- repository callback contract

### F3-A.1: Repository Integration

Status: complete in implementation and validation.

Completed:
- PostgreSQL connection factory integration
- repository callback bridge
- Sleeper ingestion adapter
- repository contract tests

### F3-A.2: Runtime Integration

Status: complete in implementation and validation.

Completed:
- runtime integration into [../app.py](../app.py)
- live sync execution path
- runtime verification contract
- zero-pick pre_draft handling

## Current runtime condition

The active draft is in `pre_draft` state and the picks endpoint currently returns zero picks. This means the draft event pipeline is not blocked by a broken implementation; it is blocked only by missing draft activity.

## Recommended next milestone

The next milestone should be F3-B only after live pick data exists. Until then, the repository should continue to treat the event pipeline as operational but empty.

## F3 roadmap sequence

1. F3-A: draft event capture and persistence
2. F3-A.1: repository contract and ingestion integration
3. F3-A.2: runtime wiring and verification
4. F3-B: downstream recommendation and decision consumption
5. Post-draft outcome analysis and live decision publication

## Immediate next work item

Re-run the draft import and sync when the draft transitions out of `pre_draft` and verify the resulting counts in `draft_events` and `draft_selections` before proceeding to downstream F3-B work.
