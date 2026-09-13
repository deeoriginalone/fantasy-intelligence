# Fantasy Intelligence

Fantasy Intelligence is a read-only fantasy football decision-support platform for managers who want trustworthy, timely, and explainable help throughout the season.

It combines league-aware context, roster needs, player information, freshness signals, and recommendation explanations across the major weekly management workflows.

## Core Principles

- **Trust before sophistication:** ownership, eligibility, league settings, health, and matchup facts must be supported before they drive recommendations.
- **Evidence before precision:** scores, ranks, confidence, roster fit, and FAAB guidance require disclosed sources and decision context.
- **Freshness is part of truth:** supported data is labeled with source and freshness information; stale or unavailable evidence is not presented as current.
- **Fail closed:** missing, stale, contradictory, or unsupported evidence can make a recommendation unavailable or block it entirely.
- **One league truth:** shared roster, ownership, league-settings, team-needs, and freshness contracts should remain consistent across pages.
- **Action before diagnostics:** manager-facing action and fantasy impact come before technical lineage and integrity details.
- **Read-only decision support:** recommendations are advisory only. The application does not automatically submit fantasy transactions.

## Current Capabilities

- Draft intelligence, player evaluation, roster construction, scarcity, strategy, and draft-state checks
- Draft readiness, reconciliation, publication gates, and operational readiness reporting
- Roster management with Full-PPR team-needs analysis across QB, RB, WR, TE, FLEX, K, and DEF
- Weekly lineup intelligence with START, SIT, FLEX, and MONITOR-style decision support
- Waiver and FAAB intelligence with ownership and eligibility evidence gates
- Trade analysis focused on roster fit, weakness addressed, depth, risk, and supported impact
- Pick'em support and related data-ingestion health checks
- Survivor support with explicit source gaps and unavailable states
- Freshness-aware recommendations with source, age, completeness, blocker, and recommendation-impact context
- Manager-facing explanations and secondary technical lineage details

Recommendations may be blocked when ownership, eligibility, health, matchup, league settings, or other decision-critical evidence is stale, unavailable, incomplete, or unsupported.

## Technology

- Python
- Flask
- PostgreSQL
- Sleeper API integrations where supported
- Jinja templates
- Pytest
- Read-only service and route contracts for evidence, freshness, reconciliation, and publication control

## Quick Start

Create and activate a Python environment, install the project requirements, configure PostgreSQL and the required environment variables, then start the Flask application:

```bash
cd /home/deeoriginalone/fantasy-intelligence
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The application expects a working PostgreSQL database and supported provider connectivity for live league workflows. Without those dependencies, affected features should remain unavailable or blocked rather than fabricating results.

## Configuration

Configuration is loaded through the application configuration layer and environment variables. Typical values include:

- `FLASK_SECRET_KEY`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `ADMIN_TOKEN`
- `SLEEPER_LEAGUE_ID`
- `SLEEPER_DRAFT_ID`

Keep secrets in local environment configuration. Do not commit `.env` files, tokens, credentials, or private provider data.

## Testing

Run the full test suite from the repository environment:

```bash
cd /home/deeoriginalone/fantasy-intelligence
source venv/bin/activate
python -m pytest -q
```

Focused tests should be used when changing a specific service or route. Python compilation, whitespace checks, active-route checks, and source/freshness validation are also important for decision-critical changes.

## Repository Structure

- `app.py`: Flask application and route registration
- `services/`: reusable decision, evidence, freshness, reconciliation, and intelligence services
- `templates/`: manager-facing page templates
- `static/`: presentation assets
- `tests/`: unit, contract, route, and template tests
- `draft/`, `draft_events/`: draft-state, event, readiness, and reconciliation logic
- `database/`, `migrations/`: database definitions and migration material
- `ingestion/`, `imports/`: data intake and validation helpers
- `docs/`: product requirements, data policies, strategy, maturity, and development guidance
- `scripts/`: supported maintenance and continuity tooling

Generated bundles, exports, backups, captures, archives, and package outputs are supporting artifacts rather than the canonical application source.

## Development Philosophy

Development proceeds from repository evidence and explicit contracts. A feature is not considered trustworthy merely because code exists or a unit test passes.

Changes should:

1. Identify authoritative sources and ownership boundaries.
2. Preserve shared league truth across routes.
3. Make missing and degraded evidence visible.
4. Fail closed when a recommendation cannot be supported.
5. Explain the manager-facing action, confidence, and impact.
6. Keep external transaction execution out of the product boundary.

## Known Limitations

- Live recommendation quality depends on provider availability, supported source fields, and verified freshness thresholds.
- Some recommendation inputs, including role, opportunity, duration, eligibility, or precise FAAB guidance, may be unavailable and therefore block or reduce a recommendation.
- Production readiness, recovery, operational repeatability, and database parity require environment-specific evidence.
- Historical owner behavior and outcome calibration must not be fabricated when real league history is absent.
- A blocked recommendation list does not prove that the successful publication path is fully validated.

## Documentation

- [Product Vision](docs/PRODUCT_VISION.md)
- [Data Freshness and Source Policy](docs/DATA_FRESHNESS_POLICY.md)
- [Season Management Strategy](docs/SEASON_MANAGEMENT_STRATEGY.md)
- [Season-Management Page Requirements](docs/PAGE_REQUIREMENTS.md)
- [Platform Maturity](docs/PLATFORM_MATURITY.md)
- [Project Status](PROJECT_STATUS.md)
- [Development Roadmap](DEVELOPMENT_ROADMAP.md)
- [Season Readiness](SEASON_READINESS.md)
