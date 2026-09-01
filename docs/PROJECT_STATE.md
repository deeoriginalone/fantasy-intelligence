# Project State

Date: 2026-09-01

## Verified facts

The following facts were verified from running code, migrations, and live API calls in this session:

- Draft Event Pipeline work was performed.
- Migration 007 exists at [../migrations/007_draft_event_pipeline.sql](../migrations/007_draft_event_pipeline.sql).
- The table `draft_events` exists in PostgreSQL.
- The table `draft_selections` exists in PostgreSQL.
- F3-A implemented.
- F3-A.1 implemented.
- F3-A.2 runtime integration work performed.
- Sleeper connectivity verified.
- Sleeper draft ID is `1398094331272794112`.
- Sleeper draft metadata returned successfully.
- Draft status is `pre_draft`.
- The picks endpoint returned zero picks.
- `sync_sleeper_draft_picks()` executed successfully and returned:
  {
    "received": 0,
    "stored": 0,
    "matched_to_rankings": 0,
    "my_team_picks": 0,
    "identity_valid": true,
    "quarantined": 0
  }
- `draft_events` count is 0.
- `draft_selections` count is 0.

## Architecture overview

The repository is a hybrid fantasy intelligence application with five major runtime domains:

1. Draft intelligence and recommendation logic in [../app.py](../app.py)
2. Draft event pipeline in [../draft_events](../draft_events)
3. Weekly intelligence and schedule/injury data in [../weekly_intelligence.py](../weekly_intelligence.py)
4. Market and pick’em intelligence in [../market_refresh.py](../market_refresh.py), [../pickem_auto_feed.py](../pickem_auto_feed.py), and [../yahoo_pickem.py](../yahoo_pickem.py)
5. Survivor intelligence in [../survivor_intelligence.py](../survivor_intelligence.py)

The active source of truth is domain-specific:

- Sleeper league and draft metadata: live Sleeper API
- Draft selection persistence: PostgreSQL `draft_events` and `draft_selections`
- Roster and draft-board state: application DB tables and live Sleeper sync
- Market probability and odds data: live Odds API/HTTP JSON providers
- Rankings and player snapshots: imported local data and DB-backed map tables

## Current active modules

- [../app.py](../app.py): Flask app, routes, local league context, and draft synchronization
- [../draft_events/runtime.py](../draft_events/runtime.py): runtime event processing
- [../draft_events/postgres_store.py](../draft_events/postgres_store.py): PostgreSQL persistence for draft events
- [../draft_events/repository_integration.py](../draft_events/repository_integration.py): repository callback bridge
- [../draft_events/service.py](../draft_events/service.py): processing logic for event validation and mutation
- [../draft_events/sleeper_ingestion.py](../draft_events/sleeper_ingestion.py): Sleeper payload adapter
- [../services](../services): repository service interfaces and integration helpers
- [../imports](../imports): data import scripts and loaders
- [../migrations](../migrations): database schema changes
- [../tests](../tests): repository test suite

## Draft Intelligence status

Draft intelligence remains active and validated by tests, but the live draft data source is currently empty because the draft is still in `pre_draft` state.

The runtime sync path is present and executing successfully; it is not failing. It is simply operating with zero available picks.

## Draft Event Pipeline status

Status: operational but not currently populated with live selections.

Evidence:

- Migration 007 exists and creates `draft_events` and `draft_selections`.
- Runtime code is wired in [../app.py](../app.py) and [../draft_events/runtime.py](../draft_events/runtime.py).
- Unit tests pass: 18 F3-A-related tests passed in the verification run.
- Live database query result: `draft_events` = 0, `draft_selections` = 0.
- Live Sleeper API result: draft status = `pre_draft`; picks list length = 0.

Conclusion:

The draft event pipeline is functional, but it is presently waiting for draft picks to exist. There is no evidence of a broken pipeline; the repository is behaving correctly for an unstarted draft.

## Market Intelligence status

The market intelligence stack remains active in code but is not the same as a direct Yahoo runtime source. The current market data path is through odds feed providers writing to the pick’em tables, with legacy Yahoo-named fields still present in the schema and model logic.

## Survivor status

Survivor logic is present and active in the codebase, but it is not the current active blocker for the draft event pipeline. It remains separated from the live draft-event state by source freshness and league state assumptions.

## Open workstreams

- F3-B handoff from draft event state to recommendation or post-draft decision layers
- Runtime verification when the draft transitions out of `pre_draft`
- End-to-end validation of draft picks once picks exist
- Refreshing stale documentation that says the repository is fully live when the current verified state is still pre-draft and empty

## Blocked workstreams

- Live draft outcome processing is blocked until pick data exists
- Any workflow that expects non-empty draft selections is blocked by `status = pre_draft`
- Any report that claims “draft is active” without live picks is unsupported by evidence

## Database status

Verified database status:

- PostgreSQL service is reachable at localhost:5433.
- The `draft_events` and `draft_selections` tables exist.
- Both tables currently contain zero rows.

## Source of truth determination

The repository does not have one universal source of truth for every domain. The verified source-of-truth split is:

- Sleeper API: live league metadata, draft metadata, draft status, and pick list
- PostgreSQL tables: persisted draft audit rows and selection rows
- Local DB and imported data: rankings, player snapshots, schedule, injuries, and other imported intelligence inputs
- Odds feed providers: live market input data

This is the only source of truth arrangement supported by the code and runtime verification.
