# Fantasy Intelligence Project Audit

Generated from `/home/deeoriginalone/fantasy-intelligence`.

## Executive Summary

- Active Python files: **41**
- Active templates: **28**
- SQL files: **8**
- Discovered routes: **60**
- Active syntax errors: **0**
- Database connected: **True**

## Capability Inventory

- ✅ **Draft Board**: 44 code references
- ✅ **Draft Coach**: 56 code references
- ✅ **Draft Now/Wait**: 52 code references
- ✅ **League Tendencies**: 105 code references
- ✅ **Mock Draft Lab**: 67 code references
- ✅ **Monte Carlo**: 132 code references
- ✅ **Opponent Model**: 107 code references
- ✅ **Owner Operations**: 26 code references
- ✅ **Predraft Lab**: 4 code references
- ✅ **Recommendation Engine**: 154 code references
- ✅ **Sleeper Hub**: 26 code references
- ✅ **Sleeper Intelligence**: 22 code references
- ✅ **Tier Engine**: 70 code references
- ✅ **Trades**: 7 code references
- ✅ **Waivers**: 7 code references
- ✅ **Weekly Intelligence**: 19 code references

## Duplicate / Overlap Findings

### Duplicate routes
```json
{
  "/": [
    "app.py:dashboard",
    "sleeper_hub.py:home",
    "sleeper_intelligence_routes.py:home"
  ]
}
```
### Duplicate significant function names
```json
{
  "run": [
    "audit_fantasy_intelligence.py",
    "mocklab/routes.py"
  ],
  "backup": [
    "consolidate_sleeper_architecture.py",
    "patch_owner_operations.py",
    "patch_package_d.py",
    "patch_season_sandbox.py"
  ],
  "require": [
    "upgrade_draft_coach.py",
    "upgrade_draft_now_wait.py",
    "upgrade_expected_value.py",
    "upgrade_league_tendencies.py",
    "upgrade_monte_carlo.py",
    "upgrade_opponent_model.py",
    "upgrade_position_targets.py",
    "upgrade_recommendation_engine.py",
    "upgrade_round_planner.py",
    "upgrade_strategy_profiles.py",
    "upgrade_tier_engine.py",
    "upgrade_value_gap.py"
  ],
  "patch_app": [
    "upgrade_draft_coach.py",
    "upgrade_draft_now_wait.py",
    "upgrade_expected_value.py",
    "upgrade_league_tendencies.py",
    "upgrade_monte_carlo.py",
    "upgrade_opponent_model.py",
    "upgrade_position_targets.py",
    "upgrade_recommendation_engine.py",
    "upgrade_round_planner.py",
    "upgrade_strategy_profiles.py",
    "upgrade_tier_engine.py",
    "upgrade_value_gap.py"
  ],
  "patch_template": [
    "upgrade_draft_coach.py",
    "upgrade_draft_now_wait.py",
    "upgrade_expected_value.py",
    "upgrade_league_tendencies.py",
    "upgrade_monte_carlo.py",
    "upgrade_opponent_model.py",
    "upgrade_position_targets.py",
    "upgrade_recommendation_engine.py",
    "upgrade_round_planner.py",
    "upgrade_strategy_profiles.py",
    "upgrade_tier_engine.py",
    "upgrade_value_gap.py"
  ]
}
```
### Duplicate migration numbers
```json
{}
```

## Sleeper Architecture

- `cache_sleeper_players.py`
- `consolidate_sleeper_architecture.py`
- `services/sleeper_service.py`
- `sleeper_hub.py`
- `sleeper_intelligence.py`
- `sleeper_intelligence_routes.py`

### Sleeper-related imports in app.py
```
from sleeper_intelligence_routes import create_sleeper_intelligence_blueprint
from sleeper_hub import create_sleeper_hub_blueprint
from owner_operations import create_owner_operations_blueprint
from services.sleeper_service import (
    get_league,
    get_users,
    get_rosters,
    get_draft,
    get_draft_picks,
    get_all_players,
)
```

## Route Inventory

- `app.route("/")` → `app.py:dashboard`
- `app.route("/predraft")` → `app.py:predraft`
- `app.route("/imports", methods=["GET", "POST"])` → `app.py:imports`
- `app.route("/agents")` → `app.py:agents`
- `app.route("/draftcenter")` → `app.py:draftcenter`
- `app.route("/draftboard/strategy", methods=["POST"])` → `app.py:set_draft_strategy`
- `app.route("/draftboard")` → `app.py:draftboard`
- `app.route("/draftboard/toggle-star", methods=["POST"])` → `app.py:toggle_star`
- `app.route("/draftboard/toggle-drafted", methods=["POST"])` → `app.py:toggle_drafted`
- `app.route("/draftboard/add-to-team", methods=["POST"])` → `app.py:add_to_team`
- `app.route("/draftboard/remove-from-team", methods=["POST"])` → `app.py:remove_from_team`
- `app.route("/position/<position>")` → `app.py:position_rankings`
- `app.route("/league")` → `app.py:league_manager`
- `app.route("/league-overview")` → `app.py:league_manager`
- `app.route("/league/sync-teams", methods=["POST"])` → `app.py:sync_league_teams`
- `app.route("/league/add-team", methods=["POST"])` → `app.py:add_league_team`
- `app.route("/league/delete-team", methods=["POST"])` → `app.py:delete_league_team`
- `app.route("/rosters")` → `app.py:league_rosters`
- `app.route("/trackdraft", methods=["GET", "POST"])` → `app.py:track_draft`
- `app.route("/trackdraft/undo", methods=["POST"])` → `app.py:undo_draft_pick`
- `app.route("/test-sleeper")` → `app.py:test_sleeper`
- `app.route("/test-sleeper-users")` → `app.py:test_sleeper_users`
- `app.route("/test-sleeper-rosters")` → `app.py:test_sleeper_rosters`
- `app.route("/create-sleeper-tables")` → `app.py:create_sleeper_tables`
- `app.route("/sleeper-sync")` → `app.py:sleeper_sync`
- `app.route("/sleeper-teams")` → `app.py:sleeper_teams`
- `app.route("/test-draft")` → `app.py:test_draft`
- `app.route("/sleeper/players/sync", methods=["GET", "POST"])` → `app.py:sleeper_player_map_sync`
- `app.route("/sleeper/draft-picks/sync", methods=["GET", "POST"])` → `app.py:sleeper_draft_picks_sync`
- `app.route("/test-draft-picks")` → `app.py:test_draft_picks`
- `app.route("/create-draft-tables")` → `app.py:create_draft_tables`
- `app.route("/draft-sync")` → `app.py:draft_sync`
- `app.route("/create-draft-picks-table")` → `app.py:create_draft_picks_table`
- `app.route("/agent/recommendation")` → `app.py:draft_recommendation`
- `app.route('/mockdraft')` → `app.py:mock_draft_lab`
- `app.route('/mockdraft/start',methods=['POST'])` → `app.py:start_mock_draft`
- `app.route('/mockdraft/live/<int:draft_id>')` → `app.py:mock_draft_live`
- `app.route('/mockdraft/live/<int:draft_id>/pick',methods=['POST'])` → `app.py:mock_draft_pick`
- `app.route('/mockdraft/live/<int:draft_id>/toggle-pause',methods=['POST'])` → `app.py:toggle_mock_pause`
- `app.route('/mockdraft/<int:draft_id>')` → `app.py:mock_draft_result`
- `app.route('/mockdraft/<int:draft_id>/delete',methods=['POST'])` → `app.py:delete_mock_draft`
- `mocklab_bp.get("/mocklab")` → `mocklab/routes.py:index`
- `mocklab_bp.post("/mocklab/run")` → `mocklab/routes.py:run`
- `mocklab_bp.get("/mocklab/<int:draft_id>")` → `mocklab/routes.py:detail`
- `bp.route("/team")` → `owner_operations.py:team_page`
- `bp.route("/lineup")` → `owner_operations.py:lineup_page`
- `bp.route("/waivers")` → `owner_operations.py:waivers_page`
- `bp.route("/trades")` → `owner_operations.py:trades_page`
- `bp.route("/gm")` → `owner_operations.py:gm_page`
- `bp.route("/sandbox")` → `season_sandbox.py:sandbox_home`
- `bp.route("/sandbox/activate/<int:draft_id>", methods=["POST"])` → `season_sandbox.py:activate_sandbox`
- `bp.route("/sandbox/live", methods=["POST"])` → `season_sandbox.py:exit_sandbox`
- `bp.get("/")` → `sleeper_hub.py:home`
- `bp.post("/sync")` → `sleeper_hub.py:sync`
- `bp.get("/status")` → `sleeper_hub.py:status`
- `bp.get("/latest/<resource_type>")` → `sleeper_hub.py:latest`
- `bp.get("/")` → `sleeper_intelligence_routes.py:home`
- `bp.get("/json")` → `sleeper_intelligence_routes.py:json_data`
- `bp.route('/weekly')` → `weekly_routes.py:weekly_home`
- `bp.route('/weekly/set',methods=['POST'])` → `weekly_routes.py:set_week`

## Database

### Key table counts
- `bye_weeks`: 32
- `defense_matchups`: 128
- `injury_reports`: 671
- `mock_drafts`: 31014
- `mock_picks`: 4682040
- `nfl_schedule`: 272
- `sleeper_api_snapshots`: 14
- `sleeper_sync_runs`: 1
### Sleeper snapshots
- `draft` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `draft_picks` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `drafts` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `draft_traded_picks` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `league` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `matchups` season 2026 week 1 fetched 2026-08-30 01:52:09.533819+00:00
- `nfl_state` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `players` season 2026 week 0 fetched 2026-08-30 02:38:14.857231+00:00
- `rosters` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `traded_picks` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `transactions` season 2026 week 1 fetched 2026-08-30 01:52:09.533819+00:00
- `trending_add` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `trending_drop` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00
- `users` season 2026 week 0 fetched 2026-08-30 01:52:09.533819+00:00

## Syntax / Compile Health

- compileall exit code: `0`

## Git State
```
M app.py
 D services/sleeper_full_service.py
 D sleeper_api_routes.py
 D sleeper_sync.py
 M templates/base.html
?? PROJECT_AUDIT.md
?? SLEEPER_CONSOLIDATION_REPORT.json
?? audit_fantasy_intelligence.py
?? cache_sleeper_players.py
?? consolidate_sleeper_architecture.py
?? project_audit.json
?? sleeper_intelligence.py
?? sleeper_intelligence_routes.py
?? templates/sleeper_intelligence.html
```

## Consolidation Decision Rules

1. Keep one canonical Sleeper HTTP client. Compatibility aliases may remain in that client.
2. Keep one canonical cached-sync implementation and one user-facing Sleeper Hub.
3. Treat Sleeper Intelligence as a reusable engine; existing Draft HQ, Waivers, Owner Operations, and Weekly pages should consume it rather than duplicate it.
4. Do not build a new Draft War Room until the route inventory proves Draft HQ lacks the required capability.
5. Preserve all numbered migrations and resolve duplicate migration numbers before merge.
6. Do not alter historical backups during active-code cleanup.

## Next Batch Gate

Use this audit to define one consolidation patch against the exact active files. Do not apply a blind rewrite before reviewing duplicate routes, existing feature references, and database state.
