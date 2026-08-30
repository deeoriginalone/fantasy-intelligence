# Pick'em Weekly Bridge Fix

This batch fixes the two concrete integration gaps:

1. `weekly_routes.py` did not pass Pick'em context to `weekly.html`.
2. `templates/base.html` did not contain a safe Pick'em navigation link and contained a stray closing anchor near Sleeper Intelligence.

It also installs a validated CSV importer. It does not fabricate Yahoo percentages or market probabilities.

## Install

```bash
python install_pickem_weekly_bridge.py /home/deeoriginalone/fantasy-intelligence
```

## Verify

```bash
cd /home/deeoriginalone/fantasy-intelligence
python -m py_compile weekly_routes.py pickem_weekly_bridge.py import_pickem_csv.py
python -m unittest discover -s tests -p 'test_bridge.py'
```

Restart the existing Flask service, then open `/weekly` and `/pickem`.

## Load real weekly data

Fill `data/pickem_import_template.csv` with one row per game. Required percentages use decimal form, such as `0.68`. Then run:

```bash
python import_pickem_csv.py data/pickem_import_template.csv
```

Reload `/weekly`. The bridge calculates and persists recommendations for the selected week.

## Rollback

The installer prints a timestamped backup path under `backups/pickem-weekly-bridge-*` and writes `PICKEM_WEEKLY_BRIDGE_REPORT.txt`.
