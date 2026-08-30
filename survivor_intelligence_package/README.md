# Survivor Intelligence Package

Uses cached Market Intelligence predictions. Excludes teams already used, balances current win probability against future schedule value, measures model-component stability, and returns one primary plus two fallback picks.

## Install
```bash
unzip survivor_intelligence_package.zip
python survivor_intelligence_package/install_survivor_intelligence.py /home/deeoriginalone/fantasy-intelligence
```
Restart Flask and open `/survivor`.

## Workflow
1. Refresh Market Intelligence for the selected week.
2. Open Survivor Intelligence.
3. Review primary, fallbacks, future value, and stability.
4. Save the team you use.
5. Mark the result won, lost, or void after the game.

Saved teams are automatically excluded from later weeks in the same pool and season.
