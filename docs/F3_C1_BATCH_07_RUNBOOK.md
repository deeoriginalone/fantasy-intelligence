# F3-C.1 Batch 07 Runbook

## 1. Extract safely

```bash
mkdir -p ~/Downloads/F3_C1_BATCH_07
unzip F3_C1_BATCH_07_PUBLICATION_GATE.zip -d ~/Downloads/F3_C1_BATCH_07
```

## 2. Confirm F3-B.4 is committed

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git status --short --branch
```

Expected branch: `feature/draft-outcome-tracking`.

## 3. Install

```bash
bash ~/Downloads/F3_C1_BATCH_07/scripts/install_f3_c1_batch_07.sh
```

## 4. Syntax validation

```bash
python -m py_compile \
  services/publication_gate.py \
  tests/test_f3_c1_publication_gate.py \
  scripts/run_f3_c1_publication_decision.py \
  scripts/verify_f3_c1_publication_gate.py
```

## 5. Targeted gate tests

```bash
python -m pytest -q tests/test_f3_c1_publication_gate.py
```

Expected: `15 passed`.

## 6. Trust and publication regression gate

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  tests/test_f3_b4_readiness.py \
  tests/test_f3_c1_publication_gate.py
```

## 7. Generate verification evidence

```bash
python scripts/verify_f3_c1_publication_gate.py
cat audit/f3_c1/verification/VERIFICATION_RESULTS.md
```

## 8. Generate a publication decision from the F3-B.4 CLI output

First ensure this file exists:

```text
audit/f3_b4/readiness/readiness.json
```

Then use module execution so repository imports resolve:

```bash
python -m scripts.run_f3_c1_publication_decision \
  --readiness audit/f3_b4/readiness/readiness.json \
  --workflow draft_recommendations
```

Outputs:

```text
audit/f3_c1/publication/publication_decision.json
audit/f3_c1/publication/PUBLICATION_DECISION.md
```

The CLI returns `0` only when publication is allowed.

## 9. Stage only Batch 07

```bash
git add \
  services/publication_gate.py \
  tests/test_f3_c1_publication_gate.py \
  scripts/run_f3_c1_publication_decision.py \
  scripts/verify_f3_c1_publication_gate.py \
  docs/F3_C1_BATCH_07_RUNBOOK.md \
  docs/F3_C1_PUBLICATION_GATE_SPEC.md \
  audit/f3_c1/verification/VERIFICATION_RESULTS.md \
  audit/f3_c1/verification/pytest_output.txt \
  audit/f3_c1/verification/verification.json
```

Optionally stage the sample decision evidence separately after reviewing it.

```bash
git diff --cached --check
git diff --cached --stat
git commit -m "Add F3-C.1 publication readiness integration"
git push origin feature/draft-outcome-tracking
```
