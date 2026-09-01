# Data Dependency Matrix

Repository analyzed: fantasy-intelligence
Date: 2026-09-01

## Executive summary

This project is not a single-source data pipeline. It currently mixes:

- Manual CSV uploads from the web UI and local import scripts.
- Live API integrations (Sleeper, The Odds API, Open-Meteo, nflverse).
- Database tables that are populated from both sources and then used as downstream source-of-truth for modeling.
- Generated CSV and JSON artifacts that look like derived outputs rather than canonical inputs.

The practical result is that if manual CSV imports stop, the following categories stall first:

- Player rankings and draft-player tables.
- Weekly schedule/bye/injury/defense tables.
- Any model outputs that depend on imported ranking or projection snapshots.

The strongest live-source-of-truth path is Sleeper for league state and draft state, while the strongest refreshable market path is The Odds API + crowd/odds providers feeding `yahoo_pickem_games`.

---

## 1) Repository CSV inventory

### A. Active runtime CSVs (in use or clearly intended for active runtime)

| CSV | Path | Likely role | Source type | Manual/auto | Notes |
|---|---|---|---|---|---|
| `master_player_projections.csv` | `data/master_player_projections.csv` | Projection snapshot used in draft intelligence | Imported snapshot / curated data | Manual | Read by `imports/import_draft_intelligence.py` and `test_import.py`; core input for player projection logic |
| `injury_risk_report.csv` | `data/injury_risk_report.csv` | Derived injury-risk report | Generated / derived output | Manual or generated | Looks like an analytic export, not a canonical upstream feed |
| `injury_values.csv` | `data/injury_values.csv` | Injury-adjusted value dataset | Generated / derived output | Generated | Appears to be post-processed from projections + injury notes |
| `top150_vbd.csv` | `data/top150_vbd.csv` | VBD rankings / tier source | Imported snapshot | Manual | Used in `imports/import_draft_intelligence.py` |
| `top200_vbd_draft_board.csv` | `data/top200_vbd_draft_board.csv` | Draft board / VBD board export | Generated or curated board | Manual/generated | Likely a board export rather than a source-of-truth feed |
| `draft_board.csv` | `data/draft_board.csv` | Draft board | Local board export | Manual/generated | Used by tests and likely draft-planning workflows |
| `nfl-2026-UTC.csv` | `data/nfl-2026-UTC.csv` | NFL schedule / kickoff times | Static season snapshot | Manual | Loaded by `imports/import_weekly_intelligence.py` |
| `nfl-2026-bye-weeks.csv` | `data/nfl-2026-bye-weeks.csv` | Bye-week reference | Static season snapshot | Manual | Loaded by `imports/import_weekly_intelligence.py` |
| `nfl-injury-report.csv` | `data/nfl-injury-report.csv` | Injury report input | Static snapshot | Manual | Loaded by `imports/import_weekly_intelligence.py` |
| `defense-fp-against-2025.csv` | `data/defense-fp-against-2025.csv` | Defense matchup / fantasy points allowed | Static snapshot | Manual | Loaded by `imports/import_weekly_intelligence.py` |
| `sleepers.csv` | `data/sleepers.csv` | Sleeper roster/player export | Snapshot export | Manual/generated | Likely a local export of Sleeper data |
| `pickem_import_template.csv` | `data/pickem_import_template.csv` | Pick'em import template | Template | Manual | Import scaffold, not live data |
| `pickem_pg_import_template.csv` | `data/pickem_pg_import_template.csv` | PostgreSQL pick'em import template | Template | Manual | Postgres import scaffold |
| `reference/espn_ppr_2026_clean.csv` | `data/reference/espn_ppr_2026_clean.csv` | Reference ranking snapshot | Reference snapshot | Manual | Not obviously live runtime-critical |
| `reference/NFL26_CS_PPR300.csv` | `data/reference/NFL26_CS_PPR300.csv` | Reference ranking snapshot | Reference snapshot | Manual | Similar to ESPN / Draft rank baseline |
| `reference/FantasyPros_2026_Overall_ADP_Rankings.csv` | `data/reference/FantasyPros_2026_Overall_ADP_Rankings.csv` | Reference ADP ranking snapshot | Reference snapshot | Manual | historical reference |
| `imports/players.csv` | `imports/players.csv` | Seed player import | Manual seed | Manual | Loaded by `imports/import_players.py` |
| `uploads/test_rankings.csv` | `uploads/test_rankings.csv` | Uploaded rankings test payload | User upload | Manual | Imported through the Flask upload route |
| `uploads/fantasy_intelligence_2026_ppr_rankings.csv` | `uploads/fantasy_intelligence_2026_ppr_rankings.csv` | Real uploaded rankings file | User upload | Manual | Imported through `/imports` in `app.py` |

### B. Historical and archival CSVs (not clearly part of active runtime)

| CSV | Path | Likely role |
|---|---|---|
| `market.csv` | `archive/Batch_D_Data_Ingestion_Pipeline/examples/market.csv` | Example market feed export |
| `ratings.csv` | `archive/Batch_D_Data_Ingestion_Pipeline/examples/ratings.csv` | Example ratings feed export |
| `pickem_pg_import_template.csv` | `backups/pickem-postgres-20260830-091746/data/pickem_pg_import_template.csv` | Backup copy of template |
| `pickem_pg_import_template.csv` | `backups/pickem-postgres-20260830-092442/data/pickem_pg_import_template.csv` | Backup copy of template |
| `pickem_pg_import_template.csv` | `yahoo_pickem_postgres_fix_v2/data/pickem_pg_import_template.csv` | Backup copy of template |
| `pickem_import_template.csv` | `yahoo_pickem_weekly_bridge_batch/data/pickem_import_template.csv` | Backup copy of template |

### C. CSVs that are clearly not live source data

These are likely templates or exports rather than canonical upstream files:

- `data/pickem_import_template.csv`
- `data/pickem_pg_import_template.csv`
- `archive/.../examples/*.csv`
- `backups/.../*.csv`

---

## 2) API integrations

| API / provider | Files | Purpose | Data consumed | Source-of-truth role |
|---|---|---|---|---|
| Sleeper API | `services/sleeper_service.py` | League, roster, draft, player, trending state | League settings, users, rosters, draft picks, player map, state | Strong live source of truth for league and draft data |
| The Odds API | `providers/the_odds_api.py`, `market_refresh.py`, `pickem_auto_feed.py` | NFL moneyline + totals market data | Moneylines, totals, bookmaker consensus | Strong live market source |
| Open-Meteo | `batch_e_weather.py` | Weather lookups for scheduled games | Temperature, precipitation, wind | Supplemental environmental data |
| nflverse games feed | `batch_e_ratings.py` | Elo / power ratings feed | Historical NFL game results | Supplemental ratings source |
| HTTP JSON crowd provider | `providers/http_json.py` | Crowd percentages for pick'em data | `away_pct`, `home_pct` from external JSON feed | Live crowd feed input |
| HTTP JSON odds provider | `providers/http_json.py` | Market odds JSON feed | `away_moneyline`, `home_moneyline`, `total` | Live odds feed input |

### API call inventory from the active code

- `services/sleeper_service.py`
  - `/league/{league_id}`
  - `/league/{league_id}/users`
  - `/league/{league_id}/rosters`
  - `/league/{league_id}/drafts`
  - `/draft/{draft_id}`
  - `/draft/{draft_id}/picks`
  - `/players/nfl`
  - `/user/{user}`
  - `/user/{user_id}/leagues/{sport}/{season}`
  - `/league/{league_id}/matchups/{week}`
  - `/league/{league_id}/transactions/{week}`
  - `/league/{league_id}/traded_picks`
  - `/league/{league_id}/winners_bracket`
  - `/league/{league_id}/losers_bracket`
  - `/state/nfl`
  - `/players/nfl/trending/{action}`

- `providers/the_odds_api.py`
  - `https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds`

- `batch_e_weather.py`
  - `https://api.open-meteo.com/v1/forecast`

- `batch_e_ratings.py`
  - `https://github.com/nflverse/nfldata/raw/master/data/games.csv`

---

## 3) Generated files and derived artifacts

These are the files in this repo that look generated or post-processed rather than upstream canonical sources.

| Generated / derived artifact | Path | Why it looks generated |
|---|---|---|
| `project_audit.json` | `project_audit.json` | Audit export generated by repository auditing scripts |
| `PICKEM_INPUT_CENTER_REPORT.txt` | `PICKEM_INPUT_CENTER_REPORT.txt` | Human-readable generated report |
| `PICKEM_POSTGRES_FIX_REPORT.txt` | `PICKEM_POSTGRES_FIX_REPORT.txt` | Installation/fix report |
| `SLEEPER_CONSOLIDATION_REPORT.json` | `SLEEPER_CONSOLIDATION_REPORT.json` | Consolidation summary generated by a script |
| `YAHOO_PICKEM_INSTALL_REPORT.txt` | `YAHOO_PICKEM_INSTALL_REPORT.txt` | Install report |
| `data/injury_risk_report.csv` | `data/injury_risk_report.csv` | Analytical scorecard derived from injury data |
| `data/injury_values.csv` | `data/injury_values.csv` | Derived value sheet from projection + injury analysis |
| `data/draft_board.csv` | `data/draft_board.csv` | Local board snapshot, not an upstream feed |
| `data/top200_vbd_draft_board.csv` | `data/top200_vbd_draft_board.csv` | VBD-based projected board export |
| `audit/data_dependencies/*.txt` | `audit/data_dependencies/*.txt` | Generated dependency discovery artifacts |
| `reports/*.md` | `reports/*` | Reporting output, not canonical feeds |
| `docs/...` | `docs/*.md` | Project documentation generated from repo state |

### Strongest “appears generated” CSVs

These are the CSVs with the strongest signal of being derived outputs:

- `data/injury_risk_report.csv`
- `data/injury_values.csv`
- `data/draft_board.csv`
- `data/top200_vbd_draft_board.csv`
- `data/sleepers.csv` (likely an export from Sleeper, not an original source)

---

## 4) Source-of-truth classification

| Dependency | Source-of-truth status | Evidence |
|---|---|---|
| Sleeper league state | Strong source of truth | `services/sleeper_service.py` and template text in `templates/league_overview.html` call Sleeper the source of truth for settings, managers, roster slots and draft order |
| Sleeper draft state | Strong source of truth | Draft board, picks, draft metadata are pulled from `/draft/{draft_id}` and `/draft/{draft_id}/picks` |
| NFL schedule / kickoff | Mixed: static file + DB table | `imports/import_weekly_intelligence.py` populates `nfl_schedule` from `data/nfl-2026-UTC.csv`; no live API client is the main schedule source here |
| Player rankings | Not a single canonical source | This repo accepts manual uploads via `/imports` and uses CSV snapshots; no external API integration is present for ranking refresh |
| Market odds | Strong live source of truth for market feeds | `providers/the_odds_api.py` and `pickem_auto_feed.py` update `yahoo_pickem_games` with live lines |
| Crowd data | Live feed source | `providers/http_json.py` pulls from configured crowd endpoints |
| Weather | Supplemental source | `batch_e_weather.py` pulls externally but not a canonical game-source feed |
| Injury status | Mixed: file snapshot + live Sleeper API | `batch_e_injuries.py` hits Sleeper player injuries, while `data/nfl-injury-report.csv` is a local snapshot |
| Defense matchup data | Static snapshot | `data/defense-fp-against-2025.csv` is loaded into `defense_matchups` |

### Important caveat

There is no single, fully verified canonical source of truth for all player ranking/projection data in the active runtime. The code accepts CSV snapshots and user uploads, and this is the main governance gap.

---

## 5) Manual dependencies

These are the parts of the pipeline that depend on human file upload or manual local-seeding actions.

| Manual dependency | Trigger | Consumers | What breaks if not refreshed |
|---|---|---|---|
| Uploaded ranking CSVs | `/imports` route in `app.py` and `services/import_rankings.py` | `players` table | Draft ranking inputs stop updating |
| `imports/players.csv` | `imports/import_players.py` | `players` table | Seed player table is not refreshed |
| `data/nfl-2026-UTC.csv` | `imports/import_weekly_intelligence.py` | `nfl_schedule` | Current-week schedule and game identity stop updating |
| `data/nfl-2026-bye-weeks.csv` | `imports/import_weekly_intelligence.py` | `bye_weeks` | Bye-week lookups stop updating |
| `data/nfl-injury-report.csv` | `imports/import_weekly_intelligence.py` | `injury_reports` | Injury tables stop updating |
| `data/defense-fp-against-2025.csv` | `imports/import_weekly_intelligence.py` | `defense_matchups` | Defensive matchup values stop updating |
| `data/master_player_projections.csv` | `imports/import_draft_intelligence.py` and `test_import.py` | draft intelligence / player projection inputs | Projections and draft readiness stop updating |
| `data/top150_vbd.csv` | `imports/import_draft_intelligence.py` | tiering and VBD-based draft analysis | Tier and VBD enrichment stop updating |
| `data/draft_board.csv` | board workflows and tests | local board snapshot | Draft-board tracking is stale |
| `data/top200_vbd_draft_board.csv` | analytic board output | draft planning board | Board modeling is stale |
| `uploads/*.csv` | manual user upload | `players` table via ranking import | Any user-imported model inputs stop flowing into the app |

---

## 6) Automated dependencies

These are the parts of the pipeline that are refreshed automatically without manual CSV import.

| Automated dependency | Files | Source | Output |
|---|---|---|---|
| Sleeper sync | `services/sleeper_service.py`, `sleeper_hub.py`, `sleeper_intelligence.py` | Sleeper API | League, draft, roster, player and trending data |
| Market refresh | `market_refresh.py`, `providers/the_odds_api.py` | The Odds API | `yahoo_pickem_games` moneylines and probabilities |
| Pick'em auto feed | `pickem_auto_feed.py`, `providers/http_json.py` | Crowd + odds JSON feeds | `yahoo_pickem_games` crowd/odds update |
| Weather refresh | `batch_e_weather.py` | Open-Meteo | Weather records for scheduled games |
| Ratings refresh | `batch_e_ratings.py` | nflverse games feed | Elo/power rating records |
| Injury refresh | `batch_e_injuries.py` | Sleeper NFL players API | Injury status enrichment |
| Post-processed DB tables | `pickem_pg_store.py`, `weekly_intelligence.py`, `pickem_pg_context.py` | DB state | Derived pick'em and weekly intelligence outputs |

---

## 7) What stops updating if manual CSV imports stop?

This is the practical failure list.

### High-impact stop conditions

1. Ranking and draft data
   - `uploads/*.csv` stop updating the `players` table through `services/import_rankings.py`.
   - `data/master_player_projections.csv` and `data/top150_vbd.csv` stop updating projection and tier logic.
   - Result: draft intelligence, readiness scoring, and recommendation engine inputs become stale.

2. Weekly scheduling and team metadata
   - `data/nfl-2026-UTC.csv`, `data/nfl-2026-bye-weeks.csv`, `data/nfl-injury-report.csv`, and `data/defense-fp-against-2025.csv` stop refreshing.
   - Result: `nfl_schedule`, `bye_weeks`, `injury_reports`, and `defense_matchups` stop updating.

3. Board and analysis exports
   - `data/draft_board.csv`, `data/top200_vbd_draft_board.csv`, and `data/injury_values.csv` stop being refreshed.
   - Result: personal board and model analysis outputs drift behind the live season.

### Lower-impact stop conditions

- Reference snapshots under `data/reference/*.csv` will not refresh, but they are not obviously part of the live runtime path.
- Template CSVs under `data/` and `archive/` do not affect live intelligence once the live tables are already populated.

---

## 8) Which CSVs can be replaced by APIs?

| CSV | Replaceable by API? | Best replacement | Notes |
|---|---|---|---|
| `data/nfl-2026-UTC.csv` | Yes | NFL schedule API / nflverse feed / Sleeper schedule state | This is a season schedule snapshot and is a natural API-target replacement |
| `data/nfl-2026-bye-weeks.csv` | Yes | Schedule-derived byes or league API | Usually derived from schedule metadata |
| `data/nfl-injury-report.csv` | Yes | Sleeper players API or other live injury feed | `batch_e_injuries.py` already does this |
| `data/defense-fp-against-2025.csv` | Partially | nflverse / stats API / custom analytics feed | It is a derived fantasy-defense view; API replacement is possible but not direct |
| `data/master_player_projections.csv` | Yes, but not yet implemented | FantasyPros / ESPN / other projection feed | Strong candidate for real API or scraper automation |
| `data/top150_vbd.csv` | Partially | Model-generated internal output or stat feed | This is more of a derived internal artifact than an upstream source |
| `data/sleepers.csv` | Yes | Sleeper API | This is likely a snapshot export of a live API endpoint |
| `data/draft_board.csv` | No | Local state / DB export | This is a user or app board, not an API source |
| `data/top200_vbd_draft_board.csv` | No or only internal generation | Internal modeling engine output | This is downstream analysis, not upstream data |
| `data/injury_values.csv` | No | Internal derived model output | This is post-processed output |
| `data/pickem_import_template.csv` | No | Template generation | Not runtime data |
| `data/reference/*.csv` | Sometimes | External ranking snapshots or API feeds | These are references, not active data sources |

---

## 9) Which CSVs appear to be generated outputs?

These are the files with the strongest evidence of being generated or derived outputs rather than canonical upstream datasets:

| CSV | Assessment |
|---|---|
| `data/injury_risk_report.csv` | Strongly generated |
| `data/injury_values.csv` | Strongly generated |
| `data/draft_board.csv` | Likely generated or manually curated board export |
| `data/top200_vbd_draft_board.csv` | Strongly generated |
| `data/sleepers.csv` | Likely generated export from Sleeper |
| `data/pickem_import_template.csv` | Template, not data |
| `data/pickem_pg_import_template.csv` | Template, not data |

These are more likely upstream or snapshot datasets than generated outputs:

- `data/master_player_projections.csv`
- `data/top150_vbd.csv`
- `data/nfl-2026-UTC.csv`
- `data/nfl-2026-bye-weeks.csv`
- `data/nfl-injury-report.csv`
- `data/defense-fp-against-2025.csv`
- `data/reference/*.csv`

---

## 10) Dependency matrix summary

| Category | Summary |
|---|---|
| CSV files in repo | 29 total repository CSVs; active runtime subset is around 18-20 values; backup/archival duplicates add more historical files |
| API integrations | At least 4 active API families: Sleeper, The Odds API, Open-Meteo, nflverse |
| Generated files | Several CSVs and reports are clearly derived outputs, especially injury and board snapshots |
| Source of truth | Sleeper is the strongest live source-of-truth for roster and draft state; market/odds feeds are strong live sources for pick'em feeds |
| Manual dependency risk | High if user-uploaded rankings or imported CSV snapshots are stopped |
| Automated dependency risk | Low for market/weather/ratings/injury refresh if APIs are available |
| Most fragile input chain | Uploaded rankings + projection snapshots + schedule snapshots |

---

## 11) Key project files behind the matrix

- `app.py` — Flask routes and manual import flow
- `services/import_rankings.py` — generic CSV upload import into `players`
- `imports/import_players.py` — seed import for player data
- `imports/import_weekly_intelligence.py` — schedule / bye / injury / matchup ingestion
- `imports/import_draft_intelligence.py` — projection + VBD enrichment
- `services/sleeper_service.py` — live Sleeper API integration
- `providers/the_odds_api.py` — live odds market integration
- `providers/http_json.py` — crowd + odds JSON consumer
- `batch_e_weather.py` — Open-Meteo weather integration
- `batch_e_ratings.py` — nflverse Elo ratings integration
- `batch_e_injuries.py` — Sleeper injury API integration
- `market_refresh.py` — market refresh pipeline
- `pickem_auto_feed.py` — pick'em feed refresh pipeline

---

## Bottom line

The repo is best described as a hybrid dependency graph:

- Competing source types: local CSV snapshots, live API feeds, and DB-derived outputs.
- The biggest manual dependency risk is the ranking/projection layer.
- The biggest automated dependency path is the Sleeper + market/odds pipeline.
- The most obvious generated CSVs are injury and board files, not the canonical upstream datasets.

If manual file imports are stopped, the model loses ranking/projection continuity first, and the season-schedule/injury tables also start to drift unless API-based refreshes replace those imports.
