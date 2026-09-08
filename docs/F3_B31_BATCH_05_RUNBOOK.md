# F3-B.3.1 Batch 05 Runbook

## 1. Extract safely

```bash
mkdir -p ~/Downloads/F3_B31_BATCH_05
unzip F3_B31_BATCH_05_POSTGRES_PARITY.zip -d ~/Downloads/F3_B31_BATCH_05
```

## 2. Confirm prior work

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git status --short --branch
```

Commit F3-B.3 before installing Batch 05.

## 3. Install

```bash
bash ~/Downloads/F3_B31_BATCH_05/scripts/install_f3_b31_batch_05.sh
```

## 4. Inspect the production store contract

```bash
python scripts/inspect_f3_postgres_store.py | tee audit_f3_b31_store_inspection.json
```

Review:

- constructor signature
- required methods
- whether `cleanup_test_draft` exists

## 5. Run reference tests without PostgreSQL

```bash
unset F3_POSTGRES_STORE_FACTORY
python -m pytest -q tests/test_f3_b31_postgres_parity.py
```

Expected behavior:

- all in-memory tests pass
- PostgreSQL tests skip because no factory is configured

A skipped PostgreSQL suite is not production parity completion.

## 6. Configure an isolated test store factory

The environment variable must identify a callable:

```bash
export F3_POSTGRES_STORE_FACTORY='package.module:create_test_draft_event_store'
```

The callable must return a fully configured `PostgresDraftEventStore` connected to an isolated test database. It must not target production.

The returned store must expose:

```python
cleanup_test_draft(draft_id)
```

Do not continue if the database target is uncertain.

## 7. Start with a reduced diagnostic run

```bash
export F3_PARITY_BATCH_SIZE=25
export F3_PARITY_REPLAY_PASSES=2
python -m pytest -vv tests/test_f3_b31_postgres_parity.py
```

Resolve any contract differences before the large run.

## 8. Run the full parity gate

```bash
export F3_PARITY_BATCH_SIZE=1000
export F3_PARITY_REPLAY_PASSES=10
python -m pytest -q tests/test_f3_b31_postgres_parity.py
```

## 9. Generate evidence

```bash
python scripts/verify_f3_b31_postgres_parity.py
cat audit/f3_b31/postgres_parity/VERIFICATION_RESULTS.md
```

The evidence must show:

```text
PostgreSQL factory configured: True
```

A pass with the factory unset validates only the reference store.

## 10. Full regression gate

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  tests/test_f3_b31_postgres_parity.py
```

## 11. Stage only Batch 05

```bash
git add \
  tests/test_f3_b31_postgres_parity.py \
  scripts/inspect_f3_postgres_store.py \
  scripts/verify_f3_b31_postgres_parity.py \
  docs/F3_B31_BATCH_05_RUNBOOK.md \
  docs/F3_B31_POSTGRES_PARITY_SPEC.md \
  audit/f3_b31/postgres_parity/VERIFICATION_RESULTS.md \
  audit/f3_b31/postgres_parity/pytest_output.txt \
  audit/f3_b31/postgres_parity/verification.json
```

```bash
git diff --cached --check
git diff --cached --stat
git commit -m "Add F3-B.3.1 PostgreSQL store parity validation"
git push origin feature/draft-outcome-tracking
```
