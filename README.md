# Fantasy Intelligence

A Flask-based fantasy football intelligence platform for draft strategy, live Sleeper coordination, weekly intelligence, pick'em validation, and survivor planning.

## Project overview

This repository contains the active runtime for the current project state. It includes the main Flask application, draft intelligence modules, mock-draft tooling, Sleeper integration, pick'em verification, Survivor analysis, weekly intelligence, readiness validation, and the current test suite.

The active runtime is intentionally documented as a working engineering baseline, not as a complete season-ready system. Design artifacts and runtime behavior are separated in this repository state.

## Supported runtime scope

The current repository logically covers:
- Flask application runtime and route layer
- Draft recommendation engine and draft tracking
- Draft board and roster construction helpers
- Live Sleeper synchronization and caching
- Mock draft simulation
- Pick'em validation and signal handling
- Survivor analysis and spec-gap validation
- Weekly intelligence and projection-oriented imports
- Security and database configuration validation
- Templates and provider-oriented UI surfaces

Excluded from the active runtime documentation here:
- backups
- archives
- installers
- copied package versions
- generated files
- virtual environments

## Current status summary

This repository is in a partially validated state. The current evidence shows the project is runnable as a Flask application and the active test suite passes, but some subsystems still depend on source inputs that are not yet connected in production.

Latest verified full-suite result:
- Command: `./venv/bin/python -m pytest -q`
- Result: 80 passed, 2 xfailed

## Quick-start prerequisites

Based only on the repository evidence:
- Python environment with the project dependencies from the repository
- PostgreSQL-compatible database matching the DB_* environment variables used by [config.py](config.py)
- Environment variables defined in [config.py](config.py)
- Access to a local or configured Flask runtime environment
- The project virtual environment under [venv/](venv/)

## Required environment variables

The active runtime config requires these names without values:
- FLASK_SECRET_KEY
- DB_HOST
- DB_PORT
- DB_NAME
- DB_USER
- DB_PASSWORD
- ADMIN_TOKEN
- SLEEPER_LEAGUE_ID
- SLEEPER_DRAFT_ID

See [config.py](config.py) for the current runtime contract.

## How to run the application

No single repository-verified startup command is present in the active runtime. The repository contains a Flask application and a defined environment contract, but the startup command is not documented as a verified, project-wide bootstrap command in the active files.

## How to run tests

Verified test command from the repository state:

```bash
./venv/bin/python -m pytest -q
```

## Architecture map

### Application runtime
- [app.py](app.py): main Flask runtime, route definitions, draft logic, mock-draft routes, and integration endpoints
- [auth.py](auth.py): admin authentication and CSRF validation
- [config.py](config.py): centralized configuration contract and required environment validation

### Draft and recommendation engine
- [candidate_filter.py](candidate_filter.py)
- [dynamic_need_model.py](dynamic_need_model.py)
- [scarcity_model.py](scarcity_model.py)
- [balanced_recommendation_score.py](balanced_recommendation_score.py)
- [recommendation_engine_audit.py](recommendation_engine_audit.py)
- [draft_decision_plan.py](draft_decision_plan.py)
- [reconciled_draft_decision.py](reconciled_draft_decision.py)

### Draft board and tracking
- [app.py](app.py)
- [draft_outcome_tracker.py](draft_outcome_tracker.py)
- [owner_operations.py](owner_operations.py)
- [season_sandbox.py](season_sandbox.py)

### Sleeper integration
- [services/sleeper_service.py](services/sleeper_service.py)
- [sleeper_hub.py](sleeper_hub.py)
- [sleeper_intelligence.py](sleeper_intelligence.py)
- [sleeper_intelligence_routes.py](sleeper_intelligence_routes.py)
- [cache_sleeper_players.py](cache_sleeper_players.py)

### Pick'em and Survivor
- [yahoo_pickem.py](yahoo_pickem.py)
- [pickem_routes.py](pickem_routes.py)
- [pickem_inputs_routes.py](pickem_inputs_routes.py)
- [survivor_intelligence.py](survivor_intelligence.py)
- [survivor_routes.py](survivor_routes.py)

### Weekly and data import
- [weekly_intelligence.py](weekly_intelligence.py)
- [weekly_routes.py](weekly_routes.py)
- [import_players.py](import_players.py)
- [import_draft_intelligence.py](import_draft_intelligence.py)

### Readiness and testing
- [draft_readiness.py](draft_readiness.py)
- [readiness.py](readiness.py)
- [tests/](tests/)

## Subsystem status table

| Subsystem | Status |
|---|---|
| Flask application | IMPLEMENTED, NEEDS HARDENING |
| Security/auth/CSRF | VERIFIED |
| DB configuration | VERIFIED |
| Draft recommendation engine | PARTIALLY IMPLEMENTED |
| Draft board | PARTIALLY IMPLEMENTED |
| Draft tracking | PARTIALLY IMPLEMENTED |
| Live Sleeper synchronization | PARTIALLY IMPLEMENTED |
| Roster construction | PARTIALLY IMPLEMENTED |
| Mock draft | PARTIALLY IMPLEMENTED |
| Draft outcome tracking | PARTIALLY IMPLEMENTED |
| Pick'em | VERIFIED |
| Survivor | BLOCKED BY INPUTS |
| Weekly intelligence | PARTIALLY IMPLEMENTED |
| Fantasy projection correlation | PLANNED |
| Readiness validator | PROTOTYPE, NOT INTEGRATED |
| Providers | PARTIALLY IMPLEMENTED |
| Templates/UI | IMPLEMENTED, NEEDS HARDENING |
| Testing | VERIFIED |

## Important operational limitations

- The active runtime includes draft and Sleeper logic, but the live recommendation and weekly recommendation surfaces are still limited by connected-source availability.
- The authoritative design document states that live weekly recommendations remain blank until real Yahoo, market, ratings, injury, and weather inputs are connected.
- The current repository does not treat synthetic or partial recommendations as live outputs.
- The Survivor design is constrained by missing ownership, QB-status, and weather/injury inputs.
- The readiness helper exists as a prototype and is not integrated into the active runtime path in the current HEAD state.

## Data safety warning

- Never commit `.env` files or environment files with real secrets.
- Do not present synthetic, partial, or unconnected recommendations as live data.
- Keep generated, installer, archive, and copied package content out of the active runtime documentation and version history.

## Draft-season priority note

Before the season, the highest-priority work is draft-session identity validation, live Sleeper sync reconciliation, roster invariant enforcement, pick uniqueness validation, and ADP/rank/tier freshness checks. The project should not present live recommendation outputs until their source inputs are valid and fresh.

## Related documents

- [PROJECT_STATUS.md](PROJECT_STATUS.md)
- [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)
