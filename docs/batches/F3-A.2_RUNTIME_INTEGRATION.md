# F3-A.2 Runtime Integration

## Install from Downloads
```bash
cd ~/fantasy-intelligence
cp ~/Downloads/F3-A.2_Runtime_Integration/draft_events/runtime.py draft_events/
cp ~/Downloads/F3-A.2_Runtime_Integration/draft_events/postgres_store.py draft_events/
cp ~/Downloads/F3-A.2_Runtime_Integration/scripts/apply_f3a2_runtime_patch.py scripts/
cp ~/Downloads/F3-A.2_Runtime_Integration/scripts/replay_failed_draft_events.py scripts/
cp ~/Downloads/F3-A.2_Runtime_Integration/tests/test_f3a2_runtime.py tests/
cp ~/Downloads/F3-A.2_Runtime_Integration/docs/batches/F3-A.2_RUNTIME_INTEGRATION.md docs/batches/
```

## Test before patching app.py
```bash
python -m unittest tests.test_f3a2_runtime -v
python -m unittest discover -s tests -v
```

## Apply the guarded app patch
```bash
python scripts/apply_f3a2_runtime_patch.py
python -m py_compile app.py
python -m unittest discover -s tests -v
```

## Verify with a manual sync
Use the existing protected `/sleeper/draft-picks/sync` route, then query counts in `draft_events` and `draft_selections`. Do not use synthetic production rows.

## Stage
```bash
git add draft_events/runtime.py draft_events/postgres_store.py   scripts/apply_f3a2_runtime_patch.py scripts/replay_failed_draft_events.py   tests/test_f3a2_runtime.py docs/batches/F3-A.2_RUNTIME_INTEGRATION.md app.py
```

## Rollback
Restore the timestamped `app.py.before_f3a2_*` backup and restore the prior `draft_events/postgres_store.py` from Git.
