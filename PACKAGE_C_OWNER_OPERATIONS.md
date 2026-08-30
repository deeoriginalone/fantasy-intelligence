# Package C1-C5: Complete Owner Operations Suite

This single package adds My Team, Lineup, Waivers/FAAB, Trades and GM Center.

## Exact file locations
- `owner_operations.py` -> project root
- five HTML files -> `templates/`
- `003_owner_operations.sql` -> `migrations/`
- `patch_owner_operations.py` -> project root

## Validate
```bash
python -m py_compile owner_operations.py patch_owner_operations.py
```

## Migrate
```bash
psql -h localhost -p 5433 -U fantasy -d fantasy_intelligence -f migrations/003_owner_operations.sql
```

## Patch
```bash
python patch_owner_operations.py
python -m py_compile app.py owner_operations.py
```

## Run
```bash
python3 app.py
```

## Test URLs
- `/team`
- `/lineup`
- `/waivers`
- `/trades`
- `/gm`

Keep Season Sandbox active while testing. The active Mock #31008 roster will power all five pages.

## Commit
```bash
git add app.py templates/base.html owner_operations.py templates/team.html templates/lineup.html templates/waivers.html templates/trades.html templates/gm.html migrations/003_owner_operations.sql
git commit -m "Add complete owner operations suite"
```
