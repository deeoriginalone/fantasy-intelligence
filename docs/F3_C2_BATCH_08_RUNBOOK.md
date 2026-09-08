# F3-C.2 Batch 08 Runbook

## Install

```bash
mkdir -p ~/Downloads/F3_C2_BATCH_08
unzip F3_C2_BATCH_08_MOCKDRAFT_PUBLICATION.zip -d ~/Downloads/F3_C2_BATCH_08
cd /home/deeoriginalone/fantasy-intelligence
bash ~/Downloads/F3_C2_BATCH_08/scripts/install_f3_c2_batch_08.sh
```

## Test support modules before patching app.py

```bash
python -m pytest -q tests/test_f3_c2_draft_recommendation_publication.py
python scripts/verify_f3_c2_publication.py
```

Expected: `8 passed`.

## Apply the guarded app.py patch

```bash
python scripts/patch_f3_c2_mockdraft_route.py
python -m py_compile app.py
```

The patch creates `app.py.before_f3c2_<timestamp>` and refuses repeated or ambiguous application.

## Review the exact app change

```bash
git diff -- app.py
```

## Exercise legacy-compatible behavior

With the environment variable unset, the route continues to expose raw recommendations:

```bash
unset F3_READINESS_REPORT_PATH
```

## Exercise enforced READY behavior

```bash
export F3_READINESS_REPORT_PATH="$PWD/audit/f3_b4/readiness/readiness.json"
```

Restart the Flask application, then open the mock-draft live route. The file must contain a valid F3-B.4 report.

## Exercise fail-closed behavior

```bash
export F3_READINESS_REPORT_PATH="$PWD/does-not-exist.json"
```

After restart, the route must suppress recommendations and log the readiness-gate error.

## Regression gate

```bash
./scripts/test_fast.sh
python -m pytest -q tests/test_f3_c2_draft_recommendation_publication.py
```

## Stage Batch 08

```bash
git add app.py \
  services/draft_recommendation_publication.py \
  services/readiness_report_io.py \
  tests/test_f3_c2_draft_recommendation_publication.py \
  scripts/patch_f3_c2_mockdraft_route.py \
  scripts/verify_f3_c2_publication.py \
  docs/F3_C2_BATCH_08_RUNBOOK.md \
  docs/F3_C2_MOCKDRAFT_PUBLICATION_SPEC.md \
  audit/f3_c2/verification/VERIFICATION_RESULTS.md \
  audit/f3_c2/verification/pytest_output.txt \
  audit/f3_c2/verification/verification.json
```

Do not stage the timestamped app.py backup.
