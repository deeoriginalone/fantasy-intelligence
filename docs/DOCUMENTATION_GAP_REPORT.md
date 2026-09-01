# Documentation Gap Report

Date: 2026-09-01

## Missing documentation

The following required project documents were missing before this audit:

- [PROJECT_STATE.md](PROJECT_STATE.md)
- [BATCH_STATUS.md](BATCH_STATUS.md)
- [F3_ROADMAP.md](F3_ROADMAP.md)
- [TEST_AUDIT.md](TEST_AUDIT.md)
- [DOCUMENTATION_GAP_REPORT.md](DOCUMENTATION_GAP_REPORT.md)
- [NEXT_SESSION_HANDOFF.md](NEXT_SESSION_HANDOFF.md)
- [WORKLOG_2026-09-01.md](WORKLOG_2026-09-01.md)

These were created as part of the completion audit.

## Outdated documentation

The following documentation is stale relative to the current state of the repository:

- [../README.md](../README.md): the README states a previous repo-level verification result of 102 passed and indicates Postgres availability issues. The current repository state verified in this session is 151 passed, 2 xfailed, with PostgreSQL reachable and the live draft still pre_draft.
- Repository docs that discuss live recommendation readiness too strongly should be treated as stale if they imply a live active draft without evidence of actual picks.

## Conflicting documentation

The repository includes a mix of active code and historical legacy references. The relevant conflicts are:

- Real runtime path: [../app.py](../app.py) and [../draft_events/runtime.py](../draft_events/runtime.py) are active and verified.
- Legacy names: some code and schema still reference `yahoo_pickem_games` and `yahoo_*` fields, even though the live source path is market/odds providers rather than a direct Yahoo API.
- Historical packages and archive folders provide prior Yahoo cleanup experiments, but those are not active runtime sources.

## Deprecated documentation

The following documentation is best treated as historical, not current operational guidance:

- archive and backup packages under [../archive](../archive) and [../backups](../backups)
- legacy Yahoo cleanup notes and batch ZIP material
- audit and discovery reports that reference older, non-canonical architectures

## Unused or low-value documentation

- Many discovery and audit texts in [../docs/discovery](../docs/discovery) are historical and not current production runbooks.
- Backup and archive artifacts are useful for archaeology but should not be treated as active runtime files.

## Yahoo documentation warning

The repository still contains documentation and code references to Yahoo names, but the verified live runtime does not show a direct Yahoo API dependency. The live source of truth is the Sleeper draft and feed providers, while `yahoo_*` identifiers remain as legacy table/field names in the codebase.

This should be treated as a documentation debt item, not as live source verification.
