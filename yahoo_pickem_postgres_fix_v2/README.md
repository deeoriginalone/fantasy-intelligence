# PostgreSQL-native Yahoo Pick'em fix

This replaces the disconnected SQLite runtime path with PostgreSQL, using the same connection defaults as the existing Fantasy Intelligence app.

## Install

```bash
python yahoo_pickem_postgres_fix/install_pickem_postgres_fix.py /home/deeoriginalone/fantasy-intelligence
```

The installer migrates PostgreSQL, seeds game shells from `nfl_schedule`, connects `/weekly` and `/pickem` to PostgreSQL, and safely adds the nav item when absent.

## Verify

```bash
cd /home/deeoriginalone/fantasy-intelligence
python -m py_compile pickem_pg_store.py pickem_pg_context.py pickem_routes.py weekly_routes.py
python - <<'PY'
from pickem_pg_store import connect
c=connect(); cur=c.cursor()
for t in ['yahoo_pickem_games','yahoo_pickem_predictions','yahoo_pickem_outcomes','yahoo_survivor_history']:
    cur.execute('SELECT COUNT(*) FROM '+t); print(t,cur.fetchone()[0])
cur.close(); c.close()
PY
```

## Load real inputs

Fill `data/pickem_pg_import_template.csv` with Yahoo public percentages and no-vig market probabilities, then run:

```bash
python import_pickem_pg_csv.py data/pickem_pg_import_template.csv
```

The importer refuses unmatched schedule rows and invalid probabilities. No synthetic picks are inserted.
