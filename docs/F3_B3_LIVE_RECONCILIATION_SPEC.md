# F3-B.3 Live Sleeper Reconciliation Specification

## Objective

Fetch Sleeper draft metadata and picks, normalize each pick through the existing provider, compare them with local draft state, and produce a read-only operational report.

## Safety properties

- The orchestration service never calls store write methods.
- No inserts, updates, deletes, syncs, or repairs are performed.
- A live CLI run requires an explicit `module:symbol` store factory.
- The CLI refuses to guess database configuration.
- Fetching, normalization, and persistence boundaries remain independently testable.

## Operational statuses

- `READY_WAITING_FOR_PICKS`: Sleeper is `pre_draft`, no source picks exist, and local state is empty.
- `PASS`: normalized source and local state reconcile exactly.
- `BLOCKED`: metadata, normalization, or reconciliation has a material issue.

## Scope boundary

Automated tests mock Sleeper network calls and validate a 1,000-pick normalized boundary. A real operational run still requires the repository's concrete local store factory. If no production store exists, do not substitute `InMemoryDraftEventStore` and describe the result as production reconciliation.
