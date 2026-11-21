# Data Freshness and Source Policy

## Fantasy Intelligence 2.0 Application

Freshness exists to protect personal fantasy decisions. Show supported evidence quickly, disclose age and limitations, and use proportional validation. Missing, stale, unresolved, or contradictory evidence remains `UNAVAILABLE`, `BLOCKED`, or `INSUFFICIENT_EVIDENCE`; it must never become fabricated certainty.

Freshness policy does not authorize ranking, confidence, FAAB, probability, or transaction behavior by itself. Recovery snapshots must preserve freshness metadata and validation evidence.

## Status

This document defines the required freshness contract. Exact domain thresholds must be set from implementation and operational evidence. No unverified threshold is declared here.

## Source priority

1. Sleeper live data where the required fact is supported.
2. Verified local persistence or cache with source timestamp and age.
3. Supported enrichment source with disclosed provenance.
4. CSV or manual import only for a one-time bootstrap, controlled recovery, or test fixture.
5. Explicitly unavailable.

A cached value must not silently override newer live truth.

## CSV and manual-data rule

Routine weekly decisions must not require a manager-maintained CSV or manual upload. CSV-backed inputs must identify their source and import time, carry an explicit freshness state, and become `UNAVAILABLE` or `BLOCKED` when they cannot be refreshed by a supported automated process. A CSV is never a silent fallback for live data.

## Required freshness fields

Every decision-critical payload should expose:

- Domain
- Source
- Source record time when available
- Retrieved-at time
- Age
- Freshness threshold identifier
- Freshness state
- Completeness state
- Blocker reason
- Fallback used
- Recommendation impact

## Required freshness states

- **FRESH:** Within the verified domain threshold.
- **AGING:** Near the threshold and should be refreshed.
- **STALE:** Beyond the threshold and not safe for authoritative use.
- **UNAVAILABLE:** No supported value exists.
- **BLOCKED:** Required evidence is missing or invalid and the associated recommendation must not be produced.

## Domain requirements

### League settings
- Preferred source: Sleeper where supported.
- Impact: Roster slots, scoring context, FLEX eligibility, and team-needs calculations.

### Rosters and ownership
- Preferred source: Current Sleeper league rosters.
- Impact: Waiver availability, trade context, roster identity, and team needs.
- Safety rule: Unverified ownership blocks waiver recommendations.

### Draft state and start time
- Preferred source: Sleeper draft and league data where supported.
- Impact: Dashboard state and date/time presentation.

### Matchups
- Preferred source: Sleeper where supported, plus disclosed enrichment where required.
- Impact: Lineup context and opponent difficulty.

### Health and availability
- Source: Must be explicitly documented by the implementation.
- Impact: START, SIT, FLEX, MONITOR, waiver, and trade confidence.
- Safety rule: Unknown health may not be displayed as healthy.

### Projections and opportunity metrics
- Source: Must be disclosed and licensed or otherwise permitted.
- Impact: Weekly Score, baseline, waiver value, and trade impact.
- Safety rule: No invented projection or opportunity value.

## Failure behavior

- A failed live refresh must not make an old cache appear current.
- Stale or unavailable inputs must reduce confidence or block the affected recommendation.
- The page must present a useful manager-facing explanation and the last verified time when available.

## Multi-source and Yahoo policy

Each field must have a source owner, allowed secondary sources, conflict policy, freshness requirement, identity contract, missing-data behavior, and recommendation effect. A secondary source may fill a documented gap, corroborate a fact, or add source-specific context; it may not silently replace the owning source. Agreement improves confidence only through a defined and tested contract. Disagreement is not averaged away.

The owner reports approved Yahoo API access and a Yahoo Survivor league. Yahoo is a planned read-only source candidate, not verified capability. Survivor endpoints, fields, scopes, authentication, identifiers, rate limits, licensing, league access, and source timestamps are **UNKNOWN PENDING API VERIFICATION**. League-specific Yahoo facts should prefer Yahoo when supported, while local state remains disclosed cache/recovery/derived state only. Conflicts and unsupported or incomplete responses become `UNAVAILABLE`, `DEGRADED`, or `BLOCKED` as appropriate.

## Threshold registry

### Pending Provider-ID Investigation, October 3, 2026

- Final pending-record recheck: both current WR-filtered Sleeper responses (with and without `active=true`) supply no team for KhaDarel Hodge, Xavier Smith, or Lil'Jordan Humphrey. Hodge is Questionable; Smith and Humphrey are Active without listed injuries. This supersedes earlier LAR/DEN observations, but does not prove player unavailability. Ben Sauls also remains a pending identity case without an agreed NFL team.
- A missing weekly kickoff can be corroborated only with a unique published player-ID link, current Active Sleeper team/position, and at least two distinct provider player records in the fresh weekly artifact agreeing on one current-week team kickoff. Ambiguous/stale games, missing current team, and started games fail closed. The original publisher FA/team field is retained beside the explicit game-evidence method; local CSV schedules without retrieval metadata are not used to authorize ranks.

- Subsequent owner approval permits a contextual exception only when normalized full name, canonical position, and current NFL team agree uniquely between the ranking source and Sleeper. Method: `OWNER_APPROVED_UNIQUE_NAME_POSITION_TEAM`; not a source-published crosswalk. Name/position alone, FA/missing team, duplicate candidates, and conflicting published IDs do not qualify. These matches are reevaluated against current Sleeper data on each read and retain provider ID, Sleeper ID, team evidence, source version, and checksum.
- Under this explicitly approved rule, the pinned-source audit recovered 15 weekly and 12 ROS links, producing 514 weekly and 445 ROS ranks on October 3, 2026. Missing kickoff rows and nonqualifying identities remain pending rather than being inferred healthy, unavailable, or resolved.

- Missing ranking-provider links are not injury exclusions. The prior live audit confirmed Active/no-listed-injury kickers whose published crosswalk lacks FantasyPros IDs, and a differing FantasyPros ID for Roman Wilson. Name/position leads remain research-only.
- Checked the latest DynastyProcess player-ID release metadata: October 2, 2026. The cached ranking/crosswalk evidence remains the reproducible starting point; a new retrieval must not be described as a corrected identity unless the mapping actually changes.
- Targeted FantasyPros profile checks produced HTTP 403 for Tyler Loop and an unusable advertising redirect for Roman Wilson. No access restriction was bypassed and no stable-ID link was recovered from those responses.
- The candidate ffverse `playerids` release endpoint returned HTTP 404. The app's existing nflverse player-metadata endpoint returned HTTP 200, but its header exposes GSIS/ESPN IDs and no FantasyPros ID; it cannot prove these missing provider links.
- No additional identity mappings were published in this investigation. Resolution requires a supported updated crosswalk or explicitly reviewed stable-ID evidence; pending players must remain visible in the ranking-data review queue, not be declared unavailable or ranked from a guessed name join.

### Private Waiver Consensus

- Implementation owner: `services/dynastyprocess_rankings.py`. FantasyPros PPR consensus is obtained from commit-pinned DynastyProcess artifacts for the owner's private app, without redistribution.
- Opening My Team refreshes the shared cache when it is missing, older than six hours, or scoped to a different NFL season/type/week. Waivers reads the same cache, refreshes it only when it is missing, and offers a manual refresh. No always-running app, manager upload, or system timer is required. Failed attempts retry after 15 minutes of subsequent use.
- Every visit evaluates source dates, independently of retrieval time: weekly ranks have a 48-hour maximum age; ROS ranks have a seven-day maximum age. These are explicit operational limits for the upstream publication cadence, not promises of forecast accuracy.
- A successful download never changes `scrape_date`. A failed refresh retains the last successful snapshot and exposes the failure, but source-age/week gates still withhold outdated ranks and affected advice.
- Weekly scope is corroborated with current Sleeper NFL state and source kickoff dates; started games are excluded. ROS requires explicit ROS positional-page labels. Draft, dynasty, non-PPR skill-position pages, and historical points are not silent substitutes.
- Each supported row is reconciled to a published rank or a diagnostic record. Exact player crosswalks normalize `PK` to `K`; team defenses use exact supported Sleeper team IDs. Pending mapping/game verification is distinct from confirmed stale/started-game/invalid-rank evidence.
- The atomic cache lives in the Flask instance directory as `dynastyprocess-rankings.json`. Last attempt, last successful retrieval, source dates, source URLs, commit version, checksums, and failure status remain available separately.

### League Transaction History (FAAB market evidence)

- Owners: `services/sleeper_snapshots.py` stores and reads, and `services/waiver_market_evidence.py` (`waiver.faab_market.v1`) evaluates, Sleeper `GET /v1/league/{league_id}/transactions/{week}` responses kept in `sleeper_api_snapshots` (one row per league, season, and week; `fetched_at` is that week's request time). Every refresh is recorded in `sleeper_sync_runs` with scope `transaction_history` and status `success`, `partial`, or `failed`.
- Refresh: only the explicit command `python refresh_sleeper_transactions.py` fetches and stores weeks; viewing Waivers never fetches or stores transactions. Run it after each weekly waiver run.
- Completeness, not age: a completed week does not expire. A stored week counts only when later-week Sleeper transactions already existed when it was retrieved (CLOSED: one week later; FINAL: two or more). The current open week never counts, and a week stored while still open counts only after it is refetched. Coverage is COMPLETE when every week from the league start week to the week before the current one is verified and the latest refresh succeeded; PARTIAL when some weeks are unverified or the latest refresh did not succeed; UNAVAILABLE when no week is verified; and CONTRADICTORY when stored weeks are invalid or conflict.
- No numeric staleness threshold exists for transaction history, and none is implied.

### Waiver Role and Opportunity Evidence (W6)

- Owners: `services/player_opportunity_reader.py` reads `player_opportunity_evidence` (targets, carries, and Full-PPR points from nflverse `stats_player_week`, published by `services/player_opportunity_publication.py`); `services/snap_share_reader.py` reads `snap_share_evidence` (offensive snap share from nflverse `snap_counts`, published by `services/snap_share_publication.py`); `services/waiver_role_evidence.py` evaluates both for `/waivers`.
- Thresholds (defined in `services/integrity/integrity_service.py`): `opportunity.evidence.v1` from `OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS`, with no code default (unset or invalid blocks role evidence); `snap_share.evidence.v1` from `SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS`, with the owner-approved 86400-second implementation default when unset (an invalid value blocks). Both are 86400 seconds (24 hours) in the live environment.
- Age and timestamps: age is measured from `retrieved_at`, the time the refresh retrieved the nflverse release, and judged at read time: FRESH up to 80% of the limit, AGING up to the limit, then STALE; a persisted state is never upgraded. `source_recorded_at` is the upstream nflverse release timestamp (`timestamp.txt`), kept for lineage and not used for age.
- Completeness: the completed-week boundary is the latest week whose every game has a result in the automated nflverse schedule (`nfl_schedule`). A source is verified through the latest week for which every team that played has stored rows; it is COMPLETE when that reaches the completed-week boundary, and otherwise PARTIAL or INCOMPLETE.
- Current versus historical: a source is CURRENT only when it is COMPLETE and FRESH or AGING. When neither source is current, a player's stored games are HISTORICAL ONLY and no current role or trend is claimed; when only one is current, only its metrics are used and the other is named as not current.
- Refresh: `refresh_opportunity_evidence.py` retrieves nflverse data and publishes completed weeks. Since `754ed0c` it runs automatically: `scheduler/opportunity-evidence-refresh.service` (`Type=oneshot`, repository working directory, `venv/bin/python refresh_opportunity_evidence.py`, 15-minute timeout; installed as a user unit in `~/.config/systemd/user/`) is triggered by `scheduler/opportunity-evidence-refresh.timer` at 00:30, 06:30, 12:30, and 18:30 America/Los_Angeles with `Persistent=true`, so a run missed while the machine was off fires at the next start. The runs fall 30 minutes after each schedule refresh, four inside every 24-hour window. The command remains available by hand (`python refresh_opportunity_evidence.py [--season YEAR] [--dry-run]`; `--dry-run` writes nothing). Viewing Waivers never fetches or stores this evidence and never starts a refresh.
- Run result: each run prints one JSON result that reports `stats_player_week` and `snap_counts` separately: what was acquired (artifact, checksum, `source_recorded_at`, and `retrieved_at`), whether the provider artifact changed, the stored state before the run, and the stored state after it as `/waivers` evaluates it. Status (exit code): `success` (0) every source published and current; `no_source_update` (0) the same, with every provider artifact unchanged; `no_completed_week` (0) no week of the season is complete, so nothing is fetched or written; `partial` (2) a source failed or is not current after the run; `failed` (1) nothing was published, including when the automated schedule or the database is unavailable. systemd records exit 1 and 2 as failed runs, and the JSON stays in the user journal.
- Timestamps on every run: `source_recorded_at` stays the provider's release time. `retrieved_at` advances only when a source is reacquired, validated, and published; re-downloading identical content advances it because the source was actually reacquired, and the run reports that content as unchanged (`no_source_update`). A failed acquisition or publication changes nothing, and timer execution alone never renews freshness.
- Partial runs: a source that publishes keeps its new rows when the other source fails, and the failed source keeps its previous rows and retrieval time; /waivers then uses only the current source's metrics, or shows the stored games as HISTORICAL ONLY under the rules above. After a week completes and before both providers publish it, runs report `partial` and the affected source is not current until the next successful run.
- Schedule dependency: the completed-week boundary comes from the stored automated schedule, which `scheduler/nflverse-schedule-refresh.timer` refreshes separately (00:00, 06:00, 12:00, and 18:00 America/Los_Angeles). The opportunity refresh does not make a stale schedule authoritative, and W6 does not add a schedule-freshness gate of its own to that boundary, so if the schedule refresh stalls, the opportunity refresh and /waivers lag together.
- Failed refresh: each source replaces its weeks in one transaction and rolls back on failure, so a failed source keeps its previously stored rows and their original `retrieved_at`, and a failed refresh never makes old evidence current. Evidence for a week after the completed-week boundary is rejected.

### NFL Schedule and Kickoff Evidence

- Threshold ID: `schedule.evidence.v1`, read from `SCHEDULE_EVIDENCE_MAX_AGE_SECONDS` by `services/integrity/integrity_service.py`. Approved maximum age: 86400 seconds (24 hours), set in the local environment only, never as a code default.
- Source: the automated nflverse `schedules` release (`games.csv.gz`), written only by `imports/import_nflverse_schedule.py --publish`. Age is measured from the upstream `timestamp.txt` value stored as `source_recorded_at`, not from `retrieved_at` or `imported_at`.
- Required refresh cadence: every six hours during the NFL season (`scheduler/nflverse-schedule-refresh.timer`).
- Decision impact: FRESH evidence may authorize OPEN, LOCKED, and BYE lock states. AGING evidence remains usable and visible under the existing contract. STALE, missing, contradictory, or unsupported evidence makes the player LOCK_UNVERIFIED, and an unverified player is never moved into or out of the lineup.
- A failed refresh writes nothing: it never advances `source_recorded_at` and never makes old evidence fresh. A republish rejects bye rows owned by any source other than CSV bootstrap, an earlier automated nflverse derived-bye artifact, or the explicitly overridden legacy source, and rejects a stored game whose home/away pair moved to a different week (`NFLVERSE_SCHEDULE_GAME_WEEK_MOVED`) instead of duplicating it.
- Operational basis (November 16, 2026): 3,656 successful upstream schedule releases from September 1 to November 16 with a 20-minute median gap and an 18.6-hour maximum gap (no gap above 24 hours); a six-hour import cadence simulated against that history and every kickoff kept evidence under 24 hours old; controlled Week 11 lock-state validation passed from pre-kickoff through Monday Night Football; two consecutive live publications succeeded.

Exact thresholds should be maintained in one implementation-owned registry and validated by tests. This document should link to that registry after it exists.
