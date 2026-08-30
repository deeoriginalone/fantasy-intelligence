# Yahoo Pick'em Large-Batch Integration for Fantasy Intelligence

Built for the Flask/Jinja repository rooted at `/home/deeoriginalone/fantasy-intelligence`.

## Install

From the server, place and extract this package, activate the existing virtual environment, then run:

```bash
python install_yahoo_pickem.py /home/deeoriginalone/fantasy-intelligence
```

The installer:

- creates a timestamped backup under `backups/yahoo-pickem-*`
- adds the model engine and persistence layer
- adds and registers a Flask Blueprint when the global `app = Flask(...)` pattern is detected
- adds the Pick'em panel to `templates/weekly.html`
- adds the summary card to `templates/dashboard.html`
- links the stylesheet from `templates/base.html`
- writes `YAHOO_PICKEM_INSTALL_REPORT.txt`

## Verify

```bash
cd /home/deeoriginalone/fantasy-intelligence
python -m unittest tests/test_yahoo_pickem.py
python audit_yahoo_pickem.py
python -m py_compile yahoo_pickem.py pickem_store.py pickem_routes.py
```

Start the existing application and check:

```text
/pickem
/api/pickem/health
/api/pickem?season=2026&week=1&strategy=balanced
```

## Load a game

```bash
curl -X POST http://127.0.0.1:5000/api/pickem/games \
  -H 'Content-Type: application/json' \
  -d @data/pickem_games.example.json
```

The example file is an array and is synthetic. For the endpoint, submit one object at a time after removing `_notice`.

## Data-source boundary

This package does not scrape Yahoo. It accepts normalized Yahoo public percentages through the POST endpoint or database. Connect your permitted ingestion workflow later. Market probabilities should be no-vig values.

## Existing weekly route integration

The package provides `build_pickem_context(season, week, strategy)` in `pickem_routes.py`. If `weekly_routes.py` already builds a shared context dictionary, merge it there:

```python
from pickem_routes import build_pickem_context
context.update(build_pickem_context(season, week, strategy))
```

The installer includes the Jinja partial directly in `weekly.html`, but that panel needs these context keys. If your weekly view does not pass them, use the merge above or link users to `/pickem`.

## Rollback

Use the path printed in `YAHOO_PICKEM_INSTALL_REPORT.txt`. Copy backed-up files from that directory over the project. Then remove the newly added files listed in the report.
