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
- Opening Waivers refreshes a missing cache, a cache older than six hours, or a changed NFL season/type/week. No always-running app, manager upload, or system timer is required. Failed attempts retry after 15 minutes of subsequent use.
- Every visit evaluates source dates, independently of retrieval time: weekly ranks have a 48-hour maximum age; ROS ranks have a seven-day maximum age. These are explicit operational limits for the upstream publication cadence, not promises of forecast accuracy.
- A successful download never changes `scrape_date`. A failed refresh retains the last successful snapshot and exposes the failure, but source-age/week gates still withhold outdated ranks and affected advice.
- Weekly scope is corroborated with current Sleeper NFL state and source kickoff dates; started games are excluded. ROS requires explicit ROS positional-page labels. Draft, dynasty, non-PPR skill-position pages, and historical points are not silent substitutes.
- Each supported row is reconciled to a published rank or a diagnostic record. Exact player crosswalks normalize `PK` to `K`; team defenses use exact supported Sleeper team IDs. Pending mapping/game verification is distinct from confirmed stale/started-game/invalid-rank evidence.
- The atomic cache lives in the Flask instance directory as `dynastyprocess-rankings.json`. Last attempt, last successful retrieval, source dates, source URLs, commit version, checksums, and failure status remain available separately.

Exact thresholds should be maintained in one implementation-owned registry and validated by tests. This document should link to that registry after it exists.
