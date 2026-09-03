# F3-B.2 Batch 03 Runbook

## 1. Extract the download

The files may unzip directly into `~/Downloads`, producing `docs/`, `scripts/`, `tests/`, and `draft_events/` directories.

Locate the installer:

```bash
find ~/Downloads -name "install_f3_b2_batch_03.sh" 2>/dev/null
```

Use the exact path returned by `find`.

## 2. Confirm repository state

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git status --short --branch
```

Expected branch:

```text
feature/draft-outcome-tracking
```

Commit or preserve the completed F3-B.1 work before installing Batch 03.

## 3. Install

If the installer is at `~/Downloads/scripts/install_f3_b2_batch_03.sh`:

```bash
bash ~/Downloads/scripts/install_f3_b2_batch_03.sh
```

The installer refuses to overwrite existing files.

## 4. Syntax checks

```bash
python -m py_compile \
  draft_events/reconciliation.py \
  tests/test_f3_b2_reconciliation.py \
  scripts/verify_f3_b2_reconciliation.py
```

## 5. Run targeted F3-B.2 validation

```bash
python -m pytest -q tests/test_f3_b2_reconciliation.py
```

Expected test count:

```text
11 passed
```

## 6. Run the combined F3 regression gate

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py
```

## 7. Generate evidence

```bash
python scripts/verify_f3_b2_reconciliation.py
cat audit/f3_b2/reconciliation/VERIFICATION_RESULTS.md
```

## 8. Review changes

```bash
git status --short
git diff --check
```

For untracked files, inspect directly:

```bash
sed -n '1,280p' draft_events/reconciliation.py
sed -n '1,300p' tests/test_f3_b2_reconciliation.py
```

## 9. Stage only Batch 03

```bash
git add \
  draft_events/reconciliation.py \
  tests/test_f3_b2_reconciliation.py \
  scripts/verify_f3_b2_reconciliation.py \
  docs/F3_B2_BATCH_03_RUNBOOK.md \
  docs/F3_B2_RECONCILIATION_SPEC.md \
  audit/f3_b2/reconciliation/VERIFICATION_RESULTS.md \
  audit/f3_b2/reconciliation/pytest_output.txt \
  audit/f3_b2/reconciliation/verification.json
```

Review:

```bash
git diff --cached --check
git diff --cached --stat
```

Suggested commit:

```bash
git commit -m "Add F3-B.2 draft-state reconciliation"
git push origin feature/draft-outcome-tracking
```

## 10. Rollback before commit

```bash
rm -f draft_events/reconciliation.py
rm -f tests/test_f3_b2_reconciliation.py
rm -f scripts/verify_f3_b2_reconciliation.py
rm -f docs/F3_B2_BATCH_03_RUNBOOK.md
rm -f docs/F3_B2_RECONCILIATION_SPEC.md
rm -rf audit/f3_b2/reconciliation
```
