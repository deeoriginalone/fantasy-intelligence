# F3-B.4 Batch 06 Runbook

## 1. Extract safely

```bash
mkdir -p ~/Downloads/F3_B4_BATCH_06
unzip F3_B4_BATCH_06_READINESS_GATES.zip -d ~/Downloads/F3_B4_BATCH_06
```

## 2. Confirm prior phases are committed

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git status --short --branch
```

Expected branch: `feature/draft-outcome-tracking`.

## 3. Install

```bash
bash ~/Downloads/F3_B4_BATCH_06/scripts/install_f3_b4_batch_06.sh
```

## 4. Validate syntax

```bash
python -m py_compile \
  draft_events/readiness.py \
  tests/test_f3_b4_readiness.py \
  scripts/run_f3_b4_readiness.py \
  scripts/verify_f3_b4_readiness.py
```

## 5. Run targeted tests

```bash
python -m pytest -q tests/test_f3_b4_readiness.py
```

Expected: `16 passed`.

## 6. Full trust-layer regression gate

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  tests/test_f3_b4_readiness.py
```

The optional PostgreSQL parity suite remains separate until its isolated adapter is ready.

## 7. Generate evidence

```bash
python scripts/verify_f3_b4_readiness.py
cat audit/f3_b4/verification/VERIFICATION_RESULTS.md
```

## 8. Exercise the CLI with explicit input

Copy the example so the tracked file stays unchanged:

```bash
cp docs/F3_B4_READINESS_INPUT.example.json /tmp/f3_b4_readiness.json
python scripts/run_f3_b4_readiness.py --input /tmp/f3_b4_readiness.json
```

The CLI exits `0` only when publication is allowed. `WARNING` and `BLOCKED` return a nonzero exit under the default policy.

## 9. Stage only Batch 06

```bash
git add \
  draft_events/readiness.py \
  tests/test_f3_b4_readiness.py \
  scripts/run_f3_b4_readiness.py \
  scripts/verify_f3_b4_readiness.py \
  docs/F3_B4_BATCH_06_RUNBOOK.md \
  docs/F3_B4_READINESS_SPEC.md \
  docs/F3_B4_READINESS_INPUT.example.json \
  audit/f3_b4/verification/VERIFICATION_RESULTS.md \
  audit/f3_b4/verification/pytest_output.txt \
  audit/f3_b4/verification/verification.json
```

```bash
git diff --cached --check
git diff --cached --stat
git commit -m "Add F3-B.4 centralized readiness gates"
git push origin feature/draft-outcome-tracking
```
