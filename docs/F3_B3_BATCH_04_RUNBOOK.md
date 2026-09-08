# F3-B.3 Batch 04 Runbook

## 1. Extract into a dedicated folder

```bash
mkdir -p ~/Downloads/F3_B3_BATCH_04
unzip F3_B3_BATCH_04_LIVE_SLEEPER_RECONCILIATION.zip -d ~/Downloads/F3_B3_BATCH_04
```

If currently at an overwrite prompt, enter `N` and extract again using the command above.

## 2. Confirm F3-B.2 is committed

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git status --short --branch
```

Expected branch: `feature/draft-outcome-tracking`.

## 3. Install

```bash
bash ~/Downloads/F3_B3_BATCH_04/scripts/install_f3_b3_batch_04.sh
```

## 4. Syntax validation

```bash
python -m py_compile \
  draft_events/live_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  scripts/run_f3_b3_live_reconciliation.py \
  scripts/verify_f3_b3_live_reconciliation.py
```

## 5. Targeted tests

```bash
python -m pytest -q tests/test_f3_b3_live_reconciliation.py
```

Expected: `12 passed`.

## 6. Full F3 regression gate

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py
```

## 7. Generate test evidence

```bash
python scripts/verify_f3_b3_live_reconciliation.py
cat audit/f3_b3/verification/VERIFICATION_RESULTS.md
```

## 8. Identify the concrete store factory before a live run

The live CLI requires a callable returning the configured local store:

```text
module.path:factory_function
```

Do not guess this symbol. Locate it from repository evidence:

```bash
rg -n "PostgresDraftEventStore|DraftEventStore|def .*store|store_factory" . \
  --glob '!.git/**' --glob '!audit/**'
```

A live command has this form:

```bash
python scripts/run_f3_b3_live_reconciliation.py \
  --league-id "$LEAGUE_ID" \
  --draft-id "$SLEEPER_DRAFT_ID" \
  --store-factory package.module:create_store
```

If no concrete store factory exists, stop. Mocked-boundary verification may still pass, but production reconciliation is not yet available.

## 9. Stage only Batch 04 after tests pass

```bash
git add \
  draft_events/live_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  scripts/run_f3_b3_live_reconciliation.py \
  scripts/verify_f3_b3_live_reconciliation.py \
  docs/F3_B3_BATCH_04_RUNBOOK.md \
  docs/F3_B3_LIVE_RECONCILIATION_SPEC.md \
  audit/f3_b3/verification/VERIFICATION_RESULTS.md \
  audit/f3_b3/verification/pytest_output.txt \
  audit/f3_b3/verification/verification.json
```

```bash
git diff --cached --check
git diff --cached --stat
git commit -m "Add F3-B.3 live Sleeper reconciliation"
git push origin feature/draft-outcome-tracking
```
