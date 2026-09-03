# F3-D.4 Batch 12 Runbook

```bash
mkdir -p ~/Downloads/F3_D4_BATCH_12
unzip F3_D4_BATCH_12_ACTION_PLAN_INTEGRATION.zip -d ~/Downloads/F3_D4_BATCH_12
cd /home/deeoriginalone/fantasy-intelligence
bash ~/Downloads/F3_D4_BATCH_12/scripts/install_f3_d4_batch_12.sh
python scripts/patch_f3_d4_action_plan_integration.py
python -m py_compile app.py sleeper_intelligence.py sleeper_intelligence_routes.py services/roster_slots.py
python scripts/verify_f3_d4_integration.py
```

Review:

```bash
git diff -- app.py sleeper_intelligence.py sleeper_intelligence_routes.py services/roster_slots.py
```

Then call `/sleeper-intelligence/json` with a configured league. Confirm these keys appear:

```text
waiver_candidates
waiver_action_plans
local_roster_context
```

Do not stage the timestamped backups.
