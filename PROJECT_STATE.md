# Project State

## Current Checkpoint
- Date: 2026-09-06
- Branch: feature/draft-outcome-tracking
- HEAD: 01377e74cc181b368e0ced79d8916f80f8ab8a39 (plus uncommitted working-tree repairs below)
- League ID: 1398094330668797952
- Protected real draft ID: 1398094331272794112
- Target mock draft ID: 1402282512738185216

## Current State

**CONDITIONAL PASS — internal repair verified; awaiting actual Sleeper mock selections**

The rotate/activation HTTP 500 defect is fixed and verified live against the real Postgres instance. The target mock draft (`1402282512738185216`) resolves to league `1398094330668797952`, reports `mock_draft=true`, and is the sole authoritative session. Draft HQ (`/draftboard`) returns HTTP 200 with no blocked-session banner. The protected live draft (`1398094331272794112`) has no session row and was never contacted during this rotation. The only remaining requirement is making actual picks in the Sleeper mock draft to exercise the live pick-ingestion path end-to-end (see "Required Sleeper Mock Selections" below).

## Root Cause Found and Fixed (this session)
1. `rotate_draft_environment()` committed the new authoritative session, then ran
   `remote_pick_count` / `synchronize` / `refresh_health` in a second block that
   **re-raised** on any exception. The route only caught `RuntimeError`/`ValueError`
   as 409; everything else became an uncaught 500 **after** authority had already
   changed — an ambiguous partial-success state.
2. `refresh_active_draft_health()` (app.py) never called `ensure_schema()`, so a
   fresh/incompletely-bootstrapped database raised `UndefinedTable` for
   `draft_decision_outcomes` / `sleeper_api_snapshots`.
3. `model_calibration.calibration_metrics()` caught that missing-table exception
   but did not roll back the connection, leaving the shared Postgres transaction
   aborted for every later query in the same request (masking the true error).
4. Three tables used by the activation/Draft HQ path had **no CREATE TABLE
   anywhere in the repository**: `league_teams` (manual pick tracking),
   `draft_events`, and `draft_selections` (event-sourced pick pipeline used by
   `/draftboard`). This caused `/draftboard` to 500 with
   `relation "draft_events" does not exist` even after rotation succeeded.
5. The polling / "Check now" endpoint (`/test-draft-picks`) only fetched raw
   Sleeper picks to detect a count change and reload the page — it never
   persisted picks into `draft_board` / `league_rosters` / `my_roster`. That is
   the root cause behind "board not updating after picks" and "polling vs Check
   now divergence": the reload showed stale local data because nothing had
   synced it.

## Fixes Applied (uncommitted, on disk, ready to commit)
- `draft_state_hardening.py`: `ensure_schema()` now also creates `league_teams`,
  `draft_events`, `draft_selections` (with indexes matching their real query
  patterns). `rotate_draft_environment()` no longer raises after the authority
  commit — post-commit steps (`remote_pick_count`, `synchronize`,
  `refresh_health`) are each wrapped independently; failures are recorded as
  `result["warnings"]` with `result["degraded"]=True` and an audit row of status
  `ROTATION_HEALTH_DEGRADED` (non-fatal). The route always returns HTTP 200 with
  the full result once authority has committed.
- `app.py`: `refresh_active_draft_health()` now calls `ensure_schema(cur)` first.
  `/test-draft-picks` now triggers the hardened `sync_sleeper_draft_picks()`
  before returning the raw pick array, so polling/Check now keep local derived
  tables current.
- `model_calibration.py`: `calibration_metrics()` rolls back the connection when
  the outcome-tracking table is missing, instead of leaving the transaction
  aborted for subsequent queries.
- `draft_readiness.py`: table-existence guards (already present from prior
  session work) verified against a corrected test fixture.
- Tests added/fixed: `tests/test_model_calibration.py` (new),
  `tests/test_draft_environment_rotation.py` (+2 degraded-health/-sync tests),
  `tests/test_draft_state_hardening.py` (fresh-schema assertion now includes
  `league_teams`), `tests/test_draft_day_readiness.py` (fixed a pre-existing
  broken fake-cursor fixture that didn't account for `to_regclass` guard calls).

## Live Verification Evidence (real Postgres + running Flask dev server)
- `GET /draft-hardening/session-status` → `200`, `valid=true`,
  `identity.mock_draft=true`, `identity.league_id=1398094330668797952`,
  `derived_state={draft_board:0, league_rosters:0, my_roster:0}`.
- `POST /draft-hardening/rotate` (`draft_id=1402282512738185216`, `mode=MOCK`) →
  **HTTP 200**, `degraded=false`, `warnings=[]`, `mode=MOCK`,
  `identity.valid=true`, `identity.mock_draft=true`,
  `reset.validation={draft_board:0, league_rosters:0, my_roster:0}`,
  `synchronization.identity_valid=true`, `health.reconciliation.overall=READY`.
- `GET /draftboard` → **HTTP 200** (was 500 before the `draft_events` /
  `draft_selections` schema fix). No blocked-session banner text present.
- `POST /test-draft-picks` → **HTTP 200**, `[]` (0 remote picks, consistent with
  a mock draft with no selections made yet), sync ran with no exception logged.
- DB check: `draft_sessions` has exactly **one** row —
  `('1402282512738185216','1398094330668797952', authoritative=true,
  'pre_draft')`. No row exists for the protected live draft
  `1398094331272794112` — it was never touched.

## Final Draft State (verified via live DB query, before any picks)
- Authoritative draft: `1402282512738185216` (target mock)
- Authoritative session count: `1`
- `draft_board` drafted rows: `0`
- `league_rosters` rows: `0`
- `my_roster` rows: `0`
- Latest draft sync audit status: `SUCCESS`
- Protected live draft `1398094331272794112`: no session row, untouched.

## Validation Results (this session)
- `python -m py_compile app.py draft_state_hardening.py model_calibration.py draft_readiness.py draft_operations_hardening.py`: **passed**
- Focused suite (`test_draft_state_hardening.py`, `test_draft_environment_rotation.py`,
  `test_model_calibration.py`, `test_draft_day_readiness.py`, `test_draftboard_polling.py`):
  **33 passed, 0 failed, 0 skipped**
- Fast suite (`tests/` minus the 1000-pick large-batch replay/parity/reconciliation
  simulations, excluded at the user's request for turnaround time):
  **288 passed, 2 xfailed, 0 failed, 0 skipped**
- The 1000-event large-batch replay/parity suites were intentionally **not run**
  this session (explicit user instruction to stop running them). They were not
  touched by any of this session's changes.
- `git diff --check`: **passed** (no whitespace/conflict-marker issues)

## Known Boundaries / Not Yet Proven
- No actual Sleeper mock selections have been made yet — the pick-ingestion,
  board-update, roster-attribution, and recommendation paths have only been
  exercised with zero real picks.
- Item-11 legacy defects (duplicate `my_roster` counts, opponent picks
  affecting `my_roster`, stale/inconsistent recommendations, refresh/restart
  inconsistency, old mock-state contamination) have **not** been reproduced or
  fixed yet — they require live picks in the mock draft to observe. The
  `my_roster_ids` attribution in `sync_sleeper_draft_picks()` depends on
  Sleeper's `is_owner` flag per roster; this is the most likely source of any
  "opponent picks affecting my roster" defect and should be checked first if it
  recurs after real picks are made.
- Production deployment and process-manager-level recovery (outside the Flask
  dev server) is not proven.
- Two historical mock player quarantine records mentioned in prior state still
  require investigation (carried over from before this session).

## Required Sleeper Mock Selections (to close out remaining validation)
1. In the Sleeper app/site, make **at least 2-3 picks** in mock draft
   `1402282512738185216` (one from "my" slot, one from another team, to
   exercise both `league_rosters` and `my_roster` attribution).
2. After each pick, click **Check now** (or wait for the 10s poll) on
   `/draftboard` and confirm: the pick appears on the board as drafted, it
   disappears from the "available" pool, and it appears under the correct
   team's roster (not duplicated, not attributed to the wrong team).
3. Re-open/refresh `/draftboard` from a fresh page load and confirm the state
   matches what polling showed (no refresh/restart divergence).
4. Report back pick counts and any mismatch observed; that will drive the next
   round of item-11 defect fixes.

## Historical Initiatives

### Historical Major Initiative, Completed
Mock Draft Lab

### Historical Initiative, Completed Planning State
Draft Assistant v2

### Historical Milestone
F3-D.5 Waiver Action Publication and UI

Historical database credentials are intentionally omitted. Historical completion statements do not constitute current production-readiness claims.
