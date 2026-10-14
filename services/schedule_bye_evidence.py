"""Source-priority and freshness contract for schedule and bye evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from services.integrity.integrity_service import schedule_bye_freshness_limits


def _timestamp(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        value = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


BYE_AUTHORITY_MODE = "SEASON_STATIC"
BYE_CONTRACT_ID = "bye.season_static.v1"
AUTOMATED_BYE_SOURCE_PREFIX = "automated:nflverse-schedules"


def season_static_bye_contract(*, source, source_recorded_at=None, retrieved_at=None, imported_at=None, now=None):
    """Single bye authority rule: season metadata is authoritative from an automated, timestamped source; no age threshold applies."""
    source = str(source or "")
    row = {"domain": "bye", "authority_mode": BYE_AUTHORITY_MODE, "contract_id": BYE_CONTRACT_ID, "source": source or "UNVERIFIED",
           "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at, "imported_at": imported_at, "age": None,
           "freshness_threshold_id": None, "fallback_used": None, "source_tier": "UNVERIFIED", "authoritative": False}
    if not source:
        return {**row, "freshness_state": "UNAVAILABLE", "completeness_state": "UNAVAILABLE", "blocker": "BYE_SOURCE_MISSING",
                "recommendation_impact": "Bye evidence has no source; it cannot support a recommendation."}
    if not source.lower().startswith(AUTOMATED_BYE_SOURCE_PREFIX):
        csv = source.lower().startswith("csv:")
        return {**row, "freshness_state": "UNAVAILABLE", "completeness_state": "COMPLETE", "blocker": "BYE_SOURCE_NOT_AUTOMATED",
                "fallback_used": "CSV_BOOTSTRAP_OR_RECOVERY" if csv else None, "source_tier": "CSV_BOOTSTRAP_OR_RECOVERY" if csv else "UNVERIFIED",
                "recommendation_impact": "Bye evidence is not from the approved automated source and cannot authorize a recommendation."}
    source_time, retrieved_time = _timestamp(source_recorded_at), _timestamp(retrieved_at)
    if source_time is None or retrieved_time is None:
        return {**row, "freshness_state": "UNAVAILABLE", "completeness_state": "INCOMPLETE", "blocker": "BYE_SOURCE_TIMESTAMP_UNVERIFIED",
                "source_tier": "AUTOMATED_SOURCE",
                "recommendation_impact": "Bye evidence lacks source or retrieval timestamps; it cannot support a recommendation."}
    evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
    return {**row, "freshness_state": "FRESH", "completeness_state": "COMPLETE", "blocker": None, "source_tier": "AUTOMATED_SOURCE",
            "age": max(0, int((evaluation_time - retrieved_time).total_seconds())), "authoritative": True,
            "recommendation_impact": "Season-static bye evidence supports the affected recommendation."}


def evidence_contract(domain, *, source, source_recorded_at=None, retrieved_at=None, imported_at=None, max_age_seconds=None, now=None):
    if domain not in {"schedule", "bye"}:
        return {
            "domain": domain, "source": str(source or "UNVERIFIED"),
            "source_recorded_at": source_recorded_at, "retrieved_at": retrieved_at,
            "imported_at": imported_at, "age": None, "freshness_state": "BLOCKED",
            "completeness_state": "UNAVAILABLE", "freshness_threshold_id": None,
            "blocker": "UNSUPPORTED_EVIDENCE_DOMAIN", "fallback_used": None,
            "recommendation_impact": "The affected recommendation is blocked because its evidence domain is unsupported.",
            "authoritative": False, "source_tier": "UNVERIFIED",
        }
    if domain == "bye":
        return season_static_bye_contract(source=source, source_recorded_at=source_recorded_at, retrieved_at=retrieved_at, imported_at=imported_at, now=now)
    threshold=schedule_bye_freshness_limits().get(domain,{})
    threshold_id=threshold.get("id")
    max_age_seconds=threshold.get("seconds") if max_age_seconds is None else max_age_seconds
    """Prefer automated data, disclose cache/CSV fallback, and fail closed without an approved threshold."""
    source = str(source or "UNVERIFIED")
    source_key = source.lower()
    if source_key.startswith("automated:"):
        tier, fallback_used = "AUTOMATED_SOURCE", None
    elif source_key.startswith("cache:"):
        tier, fallback_used = "VERIFIED_LOCAL_CACHE", "VERIFIED_LOCAL_CACHE"
    elif source_key.startswith("csv:"):
        tier, fallback_used = "CSV_BOOTSTRAP_OR_RECOVERY", "CSV_BOOTSTRAP_OR_RECOVERY"
    else:
        tier, fallback_used = "UNVERIFIED", None
    # Local import time is disclosure only; it cannot make an old CSV source fresh.
    source_time = _timestamp(source_recorded_at) or _timestamp(retrieved_at)
    if source_time is None:
        return {
            "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
            "retrieved_at": retrieved_at, "imported_at": imported_at, "age": None,
            "freshness_state": "UNAVAILABLE", "completeness_state": "INCOMPLETE", "freshness_threshold_id": threshold_id,
            "blocker": f"{domain.upper()}_SOURCE_TIMESTAMP_UNVERIFIED", "fallback_used": fallback_used,
            "recommendation_impact": f"{domain.title()} evidence is visible but cannot support the affected recommendation.",
            "authoritative": False, "source_tier": tier,
        }
    try:
        max_age_seconds = int(max_age_seconds)
    except (TypeError, ValueError):
        max_age_seconds = None
    if max_age_seconds is None or max_age_seconds <= 0:
        return {
            "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
            "retrieved_at": retrieved_at, "imported_at": imported_at, "age": None,
            "freshness_state": "UNAVAILABLE", "completeness_state": "COMPLETE",
            "freshness_threshold_id": threshold_id, "blocker": f"{domain.upper()}_FRESHNESS_THRESHOLD_UNVERIFIED", "fallback_used": fallback_used,
            "recommendation_impact": f"{domain.title()} evidence is present but cannot be used until its freshness threshold is approved.",
            "authoritative": False, "source_tier": tier,
        }
    evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
    age = max(0, int((evaluation_time - source_time).total_seconds()))
    if age <= int(max_age_seconds) * .8:
        state, blocker = "FRESH", None
    elif age <= int(max_age_seconds):
        state, blocker = "AGING", None
    else:
        state, blocker = "STALE", f"{domain.upper()}_DATA_STALE"
    return {
        "domain": domain, "source": source, "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at, "imported_at": imported_at, "age": age,
        "freshness_state": state, "completeness_state": "COMPLETE", "freshness_threshold_id": threshold_id, "blocker": blocker,
        "fallback_used": fallback_used,
        "recommendation_impact": f"{domain.title()} evidence supports the affected recommendation." if not blocker else f"{domain.title()} evidence is stale and cannot support the affected recommendation.",
        "authoritative": not bool(blocker), "source_tier": tier,
    }


EXPECTED_NFL_TEAM_COUNT = 32


def team_bye_evidence(rows, *, season, team, week, now=None, expected_team_count=EXPECTED_NFL_TEAM_COUNT):
    """Read-only season-static bye authority; no age threshold applies to season schedule metadata."""
    team = str(team or "").strip().upper()
    supported = isinstance(season, int) and not isinstance(season, bool) and season > 0
    season_rows = [dict(row) for row in (rows or []) if supported and row.get("season", season) == season]
    team_rows = [row for row in season_rows if str(row.get("team") or "").strip().upper() == team] if team else []
    coverage = {str(row.get("team") or "").strip().upper() for row in season_rows} - {""}
    base = {"domain": "bye", "authority_mode": BYE_AUTHORITY_MODE, "contract_id": BYE_CONTRACT_ID, "season": season if supported else None, "team": team or None,
            "bye_week": None, "current_week": week, "is_current_week_bye": False, "authoritative": False, "age": None,
            "freshness_threshold_id": None, "fallback_used": None}

    def result(state, blocker, completeness, impact, row=None, **extra):
        row = row or {}
        return {**base, "source": str(row.get("source") or "UNVERIFIED"), "source_recorded_at": row.get("source_recorded_at"),
                "retrieved_at": row.get("retrieved_at"), "imported_at": row.get("imported_at"), "freshness_state": state,
                "completeness_state": completeness, "blocker": blocker, "recommendation_impact": impact, **extra}

    if not supported:
        return result("BLOCKED", "BYE_SEASON_UNSUPPORTED", "UNAVAILABLE", "Bye evidence season is unsupported; it cannot support a recommendation.")
    if not team or not team_rows:
        return result("BLOCKED", "BYE_TEAM_IDENTITY_UNRESOLVED", "UNAVAILABLE", "No bye row matches this exact team; it cannot support a recommendation.")
    row = team_rows[0]
    if len({r.get("bye_week") for r in team_rows}) > 1 or None in {r.get("bye_week") for r in team_rows}:
        return result("BLOCKED", "BYE_WEEK_CONFLICT", "CONFLICTING", "Conflicting bye weeks for one team block the affected recommendation.", row)
    if len(team_rows) > 1:
        return result("BLOCKED", "BYE_DUPLICATE_ASSIGNMENT", "CONFLICTING", "Duplicate bye assignments for one team block the affected recommendation.", row)
    shared = season_static_bye_contract(source=row.get("source"), source_recorded_at=row.get("source_recorded_at"),
                                        retrieved_at=row.get("retrieved_at"), imported_at=row.get("imported_at"), now=now)
    if not shared["authoritative"]:
        return {**base, **shared, "season": base["season"], "team": team}
    if len(coverage) < expected_team_count:
        return result("UNAVAILABLE", "BYE_TEAM_COVERAGE_INCOMPLETE", "INCOMPLETE", "Bye evidence does not cover every NFL team; it cannot support a recommendation.", row)
    return {**base, **shared, "bye_week": row.get("bye_week"), "season": season, "team": team,
            "is_current_week_bye": isinstance(week, int) and row.get("bye_week") == week}


SCHEDULE_CONTEXT_CONTRACT_ID = "schedule.game_context.v1"


def team_game_context(rows, *, season, week, team, normalize=None, now=None):
    """Read-only week opponent and venue for one exact team; opponent and venue are season-static, kickoff may change."""
    norm = normalize or (lambda value: str(value or "").strip().upper() or None)
    team = norm(team)
    ctx = {"contract_id": SCHEDULE_CONTEXT_CONTRACT_ID, "season": season, "week": week, "team": team, "opponent": None, "venue": None,
           "display_matchup": None, "kickoff_pacific": None, "schedule_source": None, "schedule_source_recorded_at": None,
           "schedule_retrieved_at": None, "schedule_freshness": "UNAVAILABLE", "schedule_age_seconds": None,
           "game_context_state": "UNAVAILABLE", "blocker": None,
           "limitations": ["Opponent and venue are season-static schedule facts; kickoff time can change."]}

    def fail(state, blocker):
        return {**ctx, "game_context_state": state, "blocker": blocker}

    if not (isinstance(season, int) and not isinstance(season, bool) and isinstance(week, int) and not isinstance(week, bool) and 1 <= week <= 18):
        return fail("UNAVAILABLE", "SCHEDULE_WEEK_UNVERIFIED")
    if not team:
        return fail("BLOCKED", "SCHEDULE_TEAM_UNRESOLVED")
    games = [row for row in (rows or []) if row.get("season", season) == season and row.get("week", week) == week
             and team in {norm(row.get("home_team")), norm(row.get("away_team"))}]
    if not games:
        return fail("UNAVAILABLE", "SCHEDULE_GAME_NOT_FOUND")
    if len(games) > 1:
        return fail("BLOCKED", "SCHEDULE_GAME_CONFLICT")
    game = games[0]
    home, away = norm(game.get("home_team")), norm(game.get("away_team"))
    if not home or not away or home == away:
        return fail("BLOCKED", "SCHEDULE_TEAM_IDENTITY_MISMATCH")
    source = str(game.get("source") or "")
    ctx.update(schedule_source=source or None, schedule_source_recorded_at=game.get("source_recorded_at"), schedule_retrieved_at=game.get("retrieved_at"))
    if not source.lower().startswith(AUTOMATED_BYE_SOURCE_PREFIX):
        return fail("UNAVAILABLE", "SCHEDULE_SOURCE_NOT_AUTOMATED") | {"schedule_source": source or None}
    retrieved = _timestamp(game.get("retrieved_at"))
    if retrieved is None or _timestamp(game.get("source_recorded_at")) is None:
        return fail("UNAVAILABLE", "SCHEDULE_SOURCE_TIMESTAMP_UNVERIFIED") | {"schedule_source": source}
    venue, opponent = ("HOME", away) if team == home else ("AWAY", home)
    age = max(0, int(((_timestamp(now) or datetime.now(timezone.utc)) - retrieved).total_seconds()))
    kickoff = game.get("game_time_pacific")
    return {**ctx, "opponent": opponent, "venue": venue, "display_matchup": f"{'vs' if venue == 'HOME' else 'at'} {opponent}",
            "kickoff_pacific": str(kickoff) if kickoff else None, "schedule_freshness": "FRESH", "schedule_age_seconds": age,
            "game_context_state": "AVAILABLE", "blocker": None}
