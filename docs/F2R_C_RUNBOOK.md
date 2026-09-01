# F2R-C Runbook

## Safety boundary

- No live Sleeper draft polling
- No database writes
- No migration execution
- Mapping failures block the event
- Ambiguous names are not auto-selected
- Recommendation snapshots retain both local and source identity

## Install

```bash
python install_f2r_c.py --repo /home/deeoriginalone/fantasy-intelligence --dry-run
python install_f2r_c.py --repo /home/deeoriginalone/fantasy-intelligence --apply
```

## Test

```bash
cd /home/deeoriginalone/fantasy-intelligence
python -m pytest -q tests/test_f2r_c_identity_bridge.py
python -m pytest -q
```

## Read-only database validation

```bash
set -a
source .env
set +a
python tools/validate_f2r_c.py
```

## Migration

`migrations/F2R_C_001_sleeper_local_identity.sql` is a reviewed proposal only. Do not run it as part of this batch.
