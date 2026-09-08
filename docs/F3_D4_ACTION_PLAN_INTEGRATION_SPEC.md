# F3-D.4 Sleeper Waiver Action Plan Integration

- Extracts `build_roster_slots()` into `services/roster_slots.py` and imports it from `app.py`.
- Queries the existing `my_roster` schema from `sleeper_intelligence.build()`.
- Builds authoritative local counts, needs, starter slots, and bench rows.
- Uses the local context for waiver ranking and action-plan generation.
- Adds `waiver_action_plans` and a compact `local_roster_context` to the existing Sleeper Intelligence JSON/HTML payload.
- Hardens the blueprint connection cleanup with `try/finally`.
- Does not submit transactions or recommend dropping starters.
