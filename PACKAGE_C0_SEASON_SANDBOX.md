# Package C0: Season Sandbox Foundation

## Put files in these exact locations

```text
~/fantasy-intelligence/season_sandbox.py
~/fantasy-intelligence/templates/season_sandbox.html
~/fantasy-intelligence/migrations/002_season_sandbox.sql
~/fantasy-intelligence/patch_season_sandbox.py
```

## Copy commands after downloading

```bash
cd ~/fantasy-intelligence
mkdir -p templates migrations
cp ~/Downloads/season_sandbox.py ./season_sandbox.py
cp ~/Downloads/season_sandbox.html ./templates/season_sandbox.html
cp ~/Downloads/002_season_sandbox.sql ./migrations/002_season_sandbox.sql
cp ~/Downloads/patch_season_sandbox.py ./patch_season_sandbox.py
```

Adjust `~/Downloads` if the browser uses a different download directory.

## Validate downloaded files before changes

```bash
python -m py_compile season_sandbox.py patch_season_sandbox.py
```

## Apply database migration

```bash
psql -h localhost -p 5433 -U fantasy -d fantasy_intelligence \
  -f migrations/002_season_sandbox.sql
```

## Patch app and navigation

```bash
python patch_season_sandbox.py
python -m py_compile app.py season_sandbox.py
```

## Start app

```bash
python3 app.py
```

Open:

```text
http://192.168.0.85:5050/sandbox
```

## Use

1. Complete a 10-team draft from slot 5 in Mock Draft Lab if none exists.
2. Open Season Sandbox.
3. Click `Use as Season Sandbox` on a completed mock.
4. Confirm the orange MOCK banner and saved roster.
5. Click `Exit Sandbox and Return to Live` to restore live mode.

## Database verification

```sql
SELECT * FROM application_state;

SELECT COUNT(*)
FROM recommendation_history;
```

## Commit

```bash
git add \
  app.py \
  templates/base.html \
  season_sandbox.py \
  templates/season_sandbox.html \
  migrations/002_season_sandbox.sql

git commit -m "Add saved mock season sandbox foundation"
```
