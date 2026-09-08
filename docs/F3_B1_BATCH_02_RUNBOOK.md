# F3-B.1 Batch 02 Runbook

## 1. Preconditions

Run every command below from:

```text
/home/deeoriginalone/fantasy-intelligence
```

Confirm the branch and preserve current work:

```bash
git branch --show-current
git status --short --branch
```

Expected branch:

```text
feature/draft-outcome-tracking
```

Do not stage the earlier source-capture ZIP or audit artifacts.

## 2. Install from Downloads

Assuming this package is extracted to `~/Downloads/F3_B1_BATCH_02_REPLAY_IMPLEMENTATION`:

```bash
cd /home/deeoriginalone/fantasy-intelligence
bash ~/Downloads/F3_B1_BATCH_02_REPLAY_IMPLEMENTATION/scripts/install_f3_b1_batch_02.sh
```

The installer refuses to overwrite an existing target file.

## 3. Review installed changes

```bash
git status --short
git diff -- tests/test_f3_b1_replay_validation.py
git diff -- scripts/verify_f3_b1_replay.py
git diff -- docs/F3_B1_BATCH_02_RUNBOOK.md
git diff -- docs/F3_B1_REPLAY_TEST_SPEC.md
```

Because the files are new and untracked, `git diff` may show no content until staged. To inspect without staging:

```bash
sed -n '1,260p' tests/test_f3_b1_replay_validation.py
sed -n '1,240p' scripts/verify_f3_b1_replay.py
```

## 4. Run the existing regression test first

```bash
python -m pytest -q tests/test_draft_event_pipeline.py
```

Stop if this existing F3-A test fails. Record the failure without changing F3-B.1 tests to conceal it.

## 5. Run F3-B.1

```bash
python -m pytest -q tests/test_f3_b1_replay_validation.py
```

For detailed names:

```bash
python -m pytest -vv tests/test_f3_b1_replay_validation.py
```

## 6. Run regression plus F3-B.1 together

```bash
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py
```

## 7. Generate evidence

```bash
python scripts/verify_f3_b1_replay.py
```

Generated evidence:

```text
audit/f3_b1/replay_validation/verification.json
audit/f3_b1/replay_validation/pytest_output.txt
audit/f3_b1/replay_validation/VERIFICATION_RESULTS.md
```

Inspect it:

```bash
cat audit/f3_b1/replay_validation/VERIFICATION_RESULTS.md
```

## 8. Interpretation

A passing Batch 02 proves replay behavior for the existing executable in-memory reference store. It does not prove PostgreSQL idempotency, SQL transaction behavior, or database concurrency. Those require the production PostgreSQL store implementation and an isolated test database.

## 9. Commit scope

Review before staging:

```bash
git status --short
```

Stage only implementation files when results pass:

```bash
git add \
  tests/test_f3_b1_replay_validation.py \
  scripts/verify_f3_b1_replay.py \
  docs/F3_B1_BATCH_02_RUNBOOK.md \
  docs/F3_B1_REPLAY_TEST_SPEC.md
```

Do not stage generated evidence automatically. Evidence can be committed separately if that matches the repository's existing audit policy.

Suggested commit message:

```bash
git commit -m "Add F3-B.1 large-batch replay validation"
```

## 10. Rollback before commit

```bash
rm -f tests/test_f3_b1_replay_validation.py
rm -f scripts/verify_f3_b1_replay.py
rm -f docs/F3_B1_BATCH_02_RUNBOOK.md
rm -f docs/F3_B1_REPLAY_TEST_SPEC.md
rm -rf audit/f3_b1/replay_validation
```
