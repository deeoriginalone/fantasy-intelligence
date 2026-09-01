# Batch F2R-A Runbook

## Purpose

Correct the Phase F local identity path so the recommendation query uses the verified PostgreSQL key `players.id`, not the nonexistent `players.player_id`.

## Safety boundary

- No migrations
- No Sleeper writes or polling
- No database writes
- Validator uses a read-only transaction and rolls back
- Installer creates a timestamped `app.py` backup only when a patch is needed
- Installer refuses an unexpected source shape

## Commands

From the extracted package directory, run the installer against the repository.

### Dry run

```bash
python install_f2r_a.py \
  --repo /home/deeoriginalone/fantasy-intelligence \
  --dry-run
```

### Apply

```bash
python install_f2r_a.py \
  --repo /home/deeoriginalone/fantasy-intelligence \
  --apply
```

### Focused test

```bash
cd /home/deeoriginalone/fantasy-intelligence
python -m pytest -q tests/test_f2r_a_local_identity.py
```

### Load environment and run read-only PostgreSQL validation

```bash
set -a
source .env
set +a
python tools/validate_f2r_a.py
```

Do not print the password or full database URL.

### Full suite

```bash
python -m pytest -q
```

### Review changes

```bash
git diff -- app.py phase_f/repository_adapter.py services/draft_recommendation_service.py tests/test_f2r_a_local_identity.py tools/validate_f2r_a.py docs/F2R_A_RUNBOOK.md

git status --short
```

## Expected validator result

The validator should report:

```text
STATUS=PASSED
LOCAL_ID_TYPE=int
LOCAL_ID_PRESENT=True
TRANSACTION_READ_ONLY=True
```

Other informational fields depend on current live data.

## Stop conditions

Stop if:

- the dry run refuses the source shape;
- `players.id` is not an integer;
- `players.player_id` unexpectedly exists;
- no draftable player row exists;
- focused or full tests fail;
- any database write occurs.
