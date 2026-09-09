# Repository Documentation Map

## Repository source of truth

Repository metadata must be regenerated from the repository itself:

```bash
cd /home/deeoriginalone/fantasy-intelligence
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -20
git status --short --branch
git diff --stat
```

## Canonical project-memory files

- `PROJECT_STATUS.md`
- `PROJECT_STATE.md`
- `DEVELOPMENT_ROADMAP.md`
- `docs/NEXT_SESSION_HANDOFF.md`

These files must describe the same current branch, HEAD, active milestone, outstanding validation, and deferred strategic modules.

## Continuity pipeline

Run:

```bash
./scripts/end_of_day.sh
```

Expected continuity outputs include:

- repository checkpoint
- bundle manifest and validation
- change report
- canonical sync validation
- session-start recovery pack
- working-tree classification
- commit candidates
- migration, parity, and schema inventories

## Current documentation rules

- Historical F3-D.4/F3-D.5 evidence remains historical.
- Current work is the Shared Integrity and data-integrity repair track.
- PostgreSQL parity remains outstanding validation work.
- Deferred strategic intelligence modules must remain listed.
- Do not claim Batch A.3 complete without its executed test evidence.
- Do not claim live-route or production readiness without explicit evidence.
