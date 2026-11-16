"""Schedule-owned lineup lock state from the automated nflverse schedule evidence.

Lock state never depends on FantasyPros/DynastyProcess publication, provider projections, or
opportunity evidence. Kickoff evidence must come from the automated nflverse schedule import and
pass the repository schedule freshness threshold; otherwise the player is LOCK_UNVERIFIED. An
automated kickoff that fails only the freshness contract is kept as display-only context (with its
age and limitation) and never authorizes a lock, an unlock, or a lineup move. BYE rests on the
season-static bye contract and the week's schedule rows agreeing that the team has no game.
"""
from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from services.schedule_bye_evidence import AUTOMATED_BYE_SOURCE_PREFIX, evidence_contract
from services.team_codes import canonical_team

LOCK_CONTRACT_ID = "lineup.game_lock.v1"
SCHEDULE_SOURCE_PREFIX = AUTOMATED_BYE_SOURCE_PREFIX
LOCK_LABELS = {"OPEN": "Open", "LOCKED": "Locked", "LOCK_UNVERIFIED": "Unverified", "BYE": "Bye", "NOT_APPLICABLE": "Not applicable"}
VERIFIED_LOCK_STATES = frozenset({"OPEN", "LOCKED", "BYE"})
USABLE_FRESHNESS = {"FRESH", "AGING"}
# Only an automated kickoff that fails the freshness contract may be shown as historical context.
CONTEXT_FRESHNESS_BLOCKERS = frozenset({"SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED", "SCHEDULE_DATA_STALE"})
LOCK_RULE = "Sleeper locks each player at his own game's kickoff."
FRESHNESS_REASONS = {
    "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED": "No schedule freshness threshold is approved, so the kickoff time cannot be verified as current.",
    "SCHEDULE_DATA_STALE": "The schedule evidence is older than its approved freshness limit; the kickoff may have changed.",
    "SCHEDULE_SOURCE_TIMESTAMP_UNVERIFIED": "The schedule evidence has no source timestamp.",
}


def utc_datetime(value: Any) -> datetime | None:
    """Parse a timestamp as an aware UTC datetime; naive values are treated as UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _display_zone() -> ZoneInfo:
    name = (os.environ.get("TIME_ZONE") or "").strip() or "America/Los_Angeles"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("America/Los_Angeles")


def kickoff_display(kickoff: datetime) -> str:
    """Deterministic local kickoff text in the configured application time zone, e.g. 'Sun Nov 15 1:05 PM PST'."""
    local = kickoff.astimezone(_display_zone())
    hour = local.hour % 12 or 12
    return f"{local:%a} {local:%b} {local.day} {hour}:{local:%M} {'AM' if local.hour < 12 else 'PM'} {local.tzname()}"


def age_label(seconds: int) -> str:
    if seconds >= 86400:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"
    if seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    minutes = max(1, seconds // 60)
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _date_display(value: datetime) -> str:
    local = value.astimezone(_display_zone())
    return f"{local:%b} {local.day}, {local.year}"


def _display_context(kickoff: datetime, now: datetime, recorded: datetime | None, retrieved: datetime | None, blocker: str) -> dict[str, Any] | None:
    """Display-only kickoff context from an automated row that failed the freshness contract; never lock authority."""
    reference = recorded or retrieved
    if reference is None:
        return None
    age = max(0, int((now - reference).total_seconds()))
    passed = kickoff <= now
    why = "schedule freshness is not approved" if blocker == "SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED" else "the schedule is past its approved freshness limit"
    return {
        "state": "HISTORICAL_CONTEXT", "decision_authority": False, "kickoff_utc": _iso(kickoff), "kickoff_display": kickoff_display(kickoff),
        "kickoff_passed": passed, "label": "Appears past kickoff" if passed else "Appears not yet started",
        "schedule_recorded_at": _iso(recorded), "schedule_retrieved_at": _iso(retrieved), "age_seconds": age, "age_label": age_label(age),
        "limitation": (f"Stored schedule recorded {_date_display(reference)} ({age_label(age)} old); {why}, so this kickoff is display-only context "
                       "and cannot lock, unlock, or move a player."),
    }


def _valid_week(season: Any, week: Any) -> bool:
    return (isinstance(season, int) and not isinstance(season, bool) and season > 0
            and isinstance(week, int) and not isinstance(week, bool) and 1 <= week <= 18)


def _row_matches(row: Mapping[str, Any], season: int, week: int) -> bool:
    try:
        return int(row.get("season", season)) == season and int(row.get("week", week)) == week
    except (TypeError, ValueError):
        return False


def build_game_lock(team: Any, *, schedule_rows: Sequence[Mapping[str, Any]] | None, season: Any, week: Any, now: Any = None,
                    is_bye: bool = False, bye_authoritative: bool | None = None, mode: str = "LIVE", max_age_seconds: Any = None) -> dict[str, Any]:
    """Return one team's game and lock contract: OPEN, LOCKED, BYE, LOCK_UNVERIFIED, or NOT_APPLICABLE (sandbox).

    Top-level kickoff fields are populated only for verified OPEN/LOCKED states. ``bye_authoritative`` is the
    season-static bye contract's verdict when the caller has one; ``False`` keeps a claimed bye unverified.
    """
    now = utc_datetime(now) or datetime.now(timezone.utc)
    code = canonical_team(team)
    lock = {
        "contract_id": LOCK_CONTRACT_ID, "state": "LOCK_UNVERIFIED", "label": LOCK_LABELS["LOCK_UNVERIFIED"], "season": season, "week": week,
        "team": code or (str(team).strip().upper() or None if team else None), "opponent": None, "venue": None,
        "kickoff_utc": None, "kickoff_display": None, "kickoff_timezone": "UTC", "kickoff_passed": None, "no_game": False,
        "schedule_source": None, "source_recorded_at": None, "retrieved_at": None, "freshness_state": "UNAVAILABLE",
        "freshness_threshold_id": None, "age_seconds": None, "evaluated_at": _iso(now), "blocker": None, "reason": None,
        "decision_authority": False, "display_context": None, "authority": "SCHEDULE_OWNED", "lock_rule": LOCK_RULE,
    }

    def unverified(blocker: str, reason: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {**lock, "state": "LOCK_UNVERIFIED", "label": LOCK_LABELS["LOCK_UNVERIFIED"], "decision_authority": False,
                "display_context": context, "blocker": blocker, "reason": reason}

    if str(mode or "").upper() == "MOCK":
        return {**lock, "state": "NOT_APPLICABLE", "label": LOCK_LABELS["NOT_APPLICABLE"], "freshness_state": "NOT_APPLICABLE",
                "reason": "Season Sandbox has no live NFL kickoff, so lineup lock state does not apply."}
    if not _valid_week(season, week):
        return unverified("SCHEDULE_WEEK_UNVERIFIED", "The NFL season or week is unverified, so a kickoff cannot be matched.")
    if code is None:
        return unverified("SCHEDULE_TEAM_UNRESOLVED", "The player's NFL team is missing or unrecognized.")
    week_rows = [row for row in (schedule_rows or []) if isinstance(row, Mapping) and _row_matches(row, season, week)]
    if not week_rows:
        return unverified("SCHEDULE_UNAVAILABLE", "No schedule evidence is loaded for this NFL week.")
    games = [row for row in week_rows if code in {canonical_team(row.get("home_team")), canonical_team(row.get("away_team"))}]
    if len(games) > 1:
        return unverified("SCHEDULE_GAME_CONFLICT", "More than one game lists this team this week.")
    if not games:
        if not is_bye:
            return unverified("SCHEDULE_GAME_NOT_FOUND", "No game for this team was found in this week's schedule.")
        if bye_authoritative is False:
            return unverified("BYE_EVIDENCE_UNVERIFIED", "The bye is not from the approved automated, timestamped bye source, so it cannot be confirmed.")
        return {**lock, "state": "BYE", "label": LOCK_LABELS["BYE"], "no_game": True, "freshness_state": "NOT_APPLICABLE", "decision_authority": True,
                "reason": "Bye week: his team has no game this week, so no kickoff lock applies and he cannot score."}
    if is_bye:
        return unverified("SCHEDULE_BYE_CONFLICT", "Bye evidence and this week's schedule disagree for this team.")
    game = games[0]
    home, away = canonical_team(game.get("home_team")), canonical_team(game.get("away_team"))
    if not home or not away or home == away:
        return unverified("SCHEDULE_TEAM_IDENTITY_MISMATCH", "The scheduled game does not have two distinct recognized teams.")
    venue, opponent = ("HOME", away) if code == home else ("AWAY", home)
    source = str(game.get("source") or "")
    source_time, retrieved_time = utc_datetime(game.get("source_recorded_at")), utc_datetime(game.get("retrieved_at"))
    kickoff = utc_datetime(game.get("game_time_utc"))
    lock.update(opponent=opponent, venue=venue, schedule_source=source or None, source_recorded_at=_iso(source_time), retrieved_at=_iso(retrieved_time))
    if not source.lower().startswith(SCHEDULE_SOURCE_PREFIX):
        return unverified("SCHEDULE_SOURCE_NOT_AUTOMATED", "Kickoff evidence is not from the automated nflverse schedule source.")
    if kickoff is None:
        return unverified("SCHEDULE_KICKOFF_UNAVAILABLE", "The scheduled kickoff time is missing or unreadable.")
    freshness = evidence_contract("schedule", source=source, source_recorded_at=game.get("source_recorded_at"),
                                  retrieved_at=game.get("retrieved_at"), now=now, max_age_seconds=max_age_seconds)
    lock.update(freshness_state=freshness.get("freshness_state") or "UNAVAILABLE", freshness_threshold_id=freshness.get("freshness_threshold_id"),
                age_seconds=freshness.get("age"))
    if lock["freshness_state"] not in USABLE_FRESHNESS:
        blocker = freshness.get("blocker") or f"SCHEDULE_FRESHNESS_{lock['freshness_state']}"
        context = _display_context(kickoff, now, source_time, retrieved_time, blocker) if blocker in CONTEXT_FRESHNESS_BLOCKERS else None
        return unverified(blocker, FRESHNESS_REASONS.get(blocker, "Kickoff freshness cannot be verified."), context)
    lock.update(kickoff_utc=_iso(kickoff), kickoff_display=kickoff_display(kickoff), kickoff_passed=kickoff <= now, decision_authority=True)
    if kickoff <= now:
        return {**lock, "state": "LOCKED", "label": LOCK_LABELS["LOCKED"],
                "reason": f"Kickoff {lock['kickoff_display']} has passed; Sleeper locks the player at kickoff."}
    return {**lock, "state": "OPEN", "label": LOCK_LABELS["OPEN"], "reason": f"Kickoff {lock['kickoff_display']}; the player can still be moved."}


def _player_key(row: Mapping[str, Any]) -> str:
    return str(row.get("source_player_id") or row.get("local_player_id") or "").strip()


def _team_of(row: Mapping[str, Any]) -> Any:
    position = str(row.get("position") or "").upper().replace("DST", "DEF")
    return row.get("nfl_team") or (_player_key(row) if position == "DEF" else None)


def _bye_authority(row: Mapping[str, Any]) -> bool | None:
    """Season-static bye contract verdict attached by weekly enrichment, or None when the row carries none."""
    evidence = row.get("weekly_evidence")
    contract = evidence.get("bye") if isinstance(evidence, Mapping) else None
    return bool(contract.get("authoritative")) if isinstance(contract, Mapping) and contract else None


def build_roster_game_locks(roster: Sequence[Mapping[str, Any]] | None, *, schedule_rows: Sequence[Mapping[str, Any]] | None, season: Any, week: Any,
                            now: Any = None, mode: str = "LIVE", max_age_seconds: Any = None) -> dict[str, Any]:
    """Lock contract for every identified roster player, keyed by Sleeper player ID."""
    now = utc_datetime(now) or datetime.now(timezone.utc)
    players = {}
    for row in roster or []:
        key = _player_key(row) if isinstance(row, Mapping) else ""
        if not key:
            continue
        players[key] = build_game_lock(_team_of(row), schedule_rows=schedule_rows, season=season, week=week, now=now, is_bye=bool(row.get("is_bye")),
                                       bye_authoritative=_bye_authority(row), mode=mode, max_age_seconds=max_age_seconds)
    counts = Counter(lock["state"] for lock in players.values())
    verified = sum(counts[state] for state in VERIFIED_LOCK_STATES)
    rows = [row for row in (schedule_rows or []) if isinstance(row, Mapping)]
    if str(mode or "").upper() == "MOCK":
        state = "NOT_APPLICABLE"
    elif players and verified == len(players):
        state = "AVAILABLE"
    elif verified:
        state = "PARTIAL"
    else:
        state = "UNAVAILABLE"
    retrieved = sorted({lock["retrieved_at"] for lock in players.values() if lock.get("retrieved_at")})
    return {
        "contract_id": LOCK_CONTRACT_ID, "state": state, "season": season, "week": week, "evaluated_at": _iso(now),
        "game_count": len(rows), "schedule_sources": sorted({str(row.get("source")) for row in rows if row.get("source")}),
        "schedule_retrieved_at": retrieved, "counts": dict(sorted(counts.items())),
        "blockers": sorted({lock["blocker"] for lock in players.values() if lock.get("blocker")}),
        "players": players, "authority": "SCHEDULE_OWNED", "lock_rule": LOCK_RULE,
        "independent_of": ["FantasyPros/DynastyProcess consensus", "provider projections", "opportunity evidence"],
    }


def unverified_lock(reason_code: str, reason: str, *, season: Any = None, week: Any = None) -> dict[str, Any]:
    """Fail-closed lock used when no schedule-owned lock contract was supplied for a player."""
    lock = build_game_lock(None, schedule_rows=None, season=season, week=week)
    return {**lock, "blocker": reason_code, "reason": reason}


def not_applicable_lock(*, season: Any = None, week: Any = None) -> dict[str, Any]:
    return build_game_lock(None, schedule_rows=None, season=season, week=week, mode="MOCK")
