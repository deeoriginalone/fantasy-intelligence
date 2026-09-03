# F3-B.3.1 PostgreSQL Store Parity Specification

## Objective

Prove that the concrete PostgreSQL draft-event store honors the same observable contract already validated against `InMemoryDraftEventStore`.

## No-guessing controls

- The test suite loads PostgreSQL only from `F3_POSTGRES_STORE_FACTORY=module:symbol`.
- It does not invent a connection string or import an assumed application factory.
- It never prints credentials.
- Destructive cleanup is allowed only through an explicit `cleanup_test_draft(draft_id)` method.
- PostgreSQL tests skip rather than run against an unisolated store.

## Parity scenarios

Each store runs the same scenarios:

1. Required contract methods exist
2. Large baseline import
3. Identical replay
4. Ten-pass repeated replay
5. Partial replay
6. Duplicate pick rejection
7. Duplicate player rejection
8. Exact reconciliation
9. Missing-local-pick reconciliation

Default batch size is 1,000 events. Override only when needed:

```bash
export F3_PARITY_BATCH_SIZE=250
export F3_PARITY_REPLAY_PASSES=3
```

## Isolation requirement

The production store must expose:

```python
cleanup_test_draft(draft_id)
```

This method must delete only records owned by the supplied synthetic draft ID and must be safe only in an isolated test database. If the method is absent, PostgreSQL tests skip. Do not add ad hoc SQL to the test suite.
