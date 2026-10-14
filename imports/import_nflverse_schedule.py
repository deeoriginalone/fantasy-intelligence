"""Acquire and persist timestamped nflverse schedule and derived bye evidence."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from typing import Any, Mapping, Sequence
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import app
from imports.import_weekly_intelligence import ALIASES, TEAMS, abbr
from services.schedule_bye_evidence import evidence_contract


RELEASE_BASE = "https://github.com/nflverse/nflverse-data/releases/download/schedules"
GAMES_URL = f"{RELEASE_BASE}/games.csv.gz"
SOURCE_TIMESTAMP_URL = f"{RELEASE_BASE}/timestamp.txt"
LICENSE_URL = "https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md"
ATTRIBUTION = "nflverse-data; schedules maintained by Lee Sharpe's nfldata; CC BY 4.0"
AUTOMATED_SOURCE_PREFIX = "automated:nflverse-schedules"
LEGACY_BYE_SOURCE = "Gridiron Games bye-week PDF; cross-checked against nfl-2026-UTC.csv"
EASTERN = ZoneInfo("America/New_York")
PACIFIC = ZoneInfo("America/Los_Angeles")
NFL_TEAMS = frozenset(TEAMS.values())


class ScheduleEvidenceError(ValueError):
    pass


def _source_time(value: str) -> datetime:
    text = str(value or "").strip()
    try:
        wall, zone_name = text.rsplit(" ", 1)
        parsed = datetime.strptime(wall, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError) as exc:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_SOURCE_TIMESTAMP_INVALID") from exc
    if zone_name not in {"EST", "EDT"}:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_SOURCE_TIMEZONE_UNSUPPORTED")
    source_time = parsed.replace(tzinfo=EASTERN)
    if source_time.tzname() != zone_name:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_SOURCE_TIMEZONE_CONTRADICTORY")
    return source_time.astimezone(timezone.utc)


def _normalized_team(value: Any) -> str:
    team = abbr(str(value or "").strip())
    if team == "LA":
        team = "LAR"
    if team not in NFL_TEAMS:
        raise ScheduleEvidenceError(f"NFLVERSE_SCHEDULE_TEAM_UNRESOLVED:{value}")
    return team


def _game_datetime(gameday: Any, gametime: Any) -> tuple[datetime, datetime]:
    try:
        day = date.fromisoformat(str(gameday))
        kickoff = time.fromisoformat(str(gametime))
    except (TypeError, ValueError) as exc:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_KICKOFF_UNAVAILABLE") from exc
    eastern = datetime.combine(day, kickoff, tzinfo=EASTERN)
    return eastern.astimezone(timezone.utc), eastern.astimezone(PACIFIC).replace(tzinfo=None)


def build_schedule_evidence(
    rows: Sequence[Mapping[str, Any]],
    *,
    season: int,
    source_recorded_at: datetime,
    retrieved_at: datetime,
    checksum: str,
) -> dict[str, Any]:
    if source_recorded_at.tzinfo is None or retrieved_at.tzinfo is None:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_TIMESTAMPS_MUST_BE_TIMEZONE_AWARE")
    source_recorded_at = source_recorded_at.astimezone(timezone.utc)
    retrieved_at = retrieved_at.astimezone(timezone.utc)
    if source_recorded_at > retrieved_at:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_SOURCE_TIME_AFTER_RETRIEVAL")

    normalized = []
    game_ids = set()
    team_games: Counter[str] = Counter()
    team_weeks: dict[str, set[int]] = defaultdict(set)
    games_by_week: Counter[int] = Counter()
    for raw in rows:
        if str(raw.get("season")) != str(season) or raw.get("game_type") != "REG":
            continue
        try:
            week = int(raw.get("week"))
        except (TypeError, ValueError) as exc:
            raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_WEEK_INVALID") from exc
        if week not in range(1, 19):
            raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_WEEK_OUT_OF_RANGE")
        game_id = str(raw.get("game_id") or "").strip()
        if not game_id or game_id in game_ids:
            raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_GAME_ID_MISSING_OR_DUPLICATE")
        game_ids.add(game_id)
        home = _normalized_team(raw.get("home_team"))
        away = _normalized_team(raw.get("away_team"))
        if home == away or home in team_weeks and week in team_weeks[home] or away in team_weeks and week in team_weeks[away]:
            raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_TEAM_WEEK_CONFLICT")
        game_time_utc, game_time_pacific = _game_datetime(raw.get("gameday"), raw.get("gametime"))
        normalized.append({
            "game_id": game_id,
            "season": season,
            "week": week,
            "game_time_utc": game_time_utc,
            "game_time_pacific": game_time_pacific,
            "location": raw.get("location"),
            "home_team": home,
            "away_team": away,
            "result": str(raw.get("result")) if raw.get("result") not in (None, "") else None,
        })
        team_games[home] += 1
        team_games[away] += 1
        team_weeks[home].add(week)
        team_weeks[away].add(week)
        games_by_week[week] += 1

    if set(team_games) != NFL_TEAMS or any(team_games[team] != 17 for team in NFL_TEAMS):
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_TEAM_POPULATION_INCOMPLETE")
    if set(games_by_week) != set(range(1, 19)):
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_WEEK_POPULATION_INCOMPLETE")
    byes = []
    for team in sorted(NFL_TEAMS):
        missing_weeks = sorted(set(range(1, 19)) - team_weeks[team])
        if len(missing_weeks) != 1:
            raise ScheduleEvidenceError(f"NFLVERSE_SCHEDULE_BYE_DERIVATION_INCOMPLETE:{team}")
        byes.append({"team": team, "bye_week": missing_weeks[0]})

    source = f"{AUTOMATED_SOURCE_PREFIX}:games.csv.gz:sha256:{checksum}"
    schedule_contract = evidence_contract(
        "schedule", source=source, source_recorded_at=source_recorded_at,
        retrieved_at=retrieved_at, now=retrieved_at,
    )
    bye_source = f"{AUTOMATED_SOURCE_PREFIX}:derived-bye:games.csv.gz:sha256:{checksum}"
    bye_contract = evidence_contract(
        "bye", source=bye_source, source_recorded_at=source_recorded_at,
        retrieved_at=retrieved_at, now=retrieved_at,
    )
    return {
        "season": season,
        "artifact_id": "nflverse-data/releases/schedules/games.csv.gz",
        "version": "schedules",
        "checksum": checksum,
        "source": source,
        "bye_source": bye_source,
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "attribution": ATTRIBUTION,
        "license_url": LICENSE_URL,
        "rows": normalized,
        "byes": byes,
        "completeness_state": "COMPLETE",
        "team_count": len(team_games),
        "games_per_team": dict(sorted(team_games.items())),
        "games_by_week": dict(sorted(games_by_week.items())),
        "schedule_contract": schedule_contract,
        "bye_contract": bye_contract,
        "authoritative": schedule_contract["authoritative"] and bye_contract["authoritative"],
        "blockers": sorted({x for x in (schedule_contract.get("blocker"), bye_contract.get("blocker")) if x}),
        "conflict_policy": "Replace CSV bootstrap rows or rows owned by this same automated source; preserve all other source owners.",
    }


def fetch_schedule_evidence(*, season: int = 2026, now: datetime | None = None) -> dict[str, Any]:
    timestamp_body = urlopen(SOURCE_TIMESTAMP_URL, timeout=30).read().decode("utf-8-sig")
    source_recorded_at = _source_time(timestamp_body)
    payload = urlopen(GAMES_URL, timeout=60).read()
    retrieved_at = now or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_RETRIEVAL_TIME_MUST_BE_TIMEZONE_AWARE")
    checksum = hashlib.sha256(payload).hexdigest()
    try:
        decoded = gzip.decompress(payload).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(decoded)))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_ARTIFACT_INVALID") from exc
    required = {"game_id", "season", "game_type", "week", "gameday", "gametime", "home_team", "away_team", "location", "result"}
    if not rows or not required.issubset(rows[0]):
        raise ScheduleEvidenceError(f"NFLVERSE_SCHEDULE_SCHEMA_UNVERIFIED:{sorted(required - set(rows[0] if rows else {}))}")
    return build_schedule_evidence(
        rows, season=season, source_recorded_at=source_recorded_at,
        retrieved_at=retrieved_at, checksum=checksum,
    )


def _assign_match_numbers(cursor, evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    cursor.execute(
        "SELECT match_number,week,home_team,away_team,source FROM nfl_schedule WHERE season=%s",
        (evidence["season"],),
    )
    existing = cursor.fetchall()
    existing_ids = {}
    used_numbers = set()
    for match_number, week, home, away, source in existing:
        key = (int(week), _normalized_team(home), _normalized_team(away))
        if key in existing_ids:
            raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_EXISTING_GAME_IDENTITY_DUPLICATE")
        existing_ids[key] = int(match_number)
        used_numbers.add(int(match_number))
    if existing and len(existing_ids) != len(evidence["rows"]):
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_EXISTING_POPULATION_MISMATCH")
    next_number = max(used_numbers, default=0) + 1
    assigned = []
    for row in sorted(evidence["rows"], key=lambda game: (game["week"], game["game_time_utc"], game["away_team"], game["home_team"])):
        key = (row["week"], row["home_team"], row["away_team"])
        match_number = existing_ids.get(key)
        if match_number is None:
            while next_number in used_numbers:
                next_number += 1
            match_number = next_number
            used_numbers.add(match_number)
            next_number += 1
        assigned.append({**row, "match_number": match_number})
    return assigned


def publish_schedule_evidence(connection: Any, evidence: Mapping[str, Any], *, replace_known_legacy_byes: bool = False) -> dict[str, int]:
    if evidence.get("completeness_state") != "COMPLETE":
        raise ScheduleEvidenceError("NFLVERSE_SCHEDULE_PUBLICATION_INCOMPLETE")
    cursor = connection.cursor()
    try:
        schedule_rows = _assign_match_numbers(cursor, evidence)
        cursor.execute("SELECT DISTINCT source FROM bye_weeks WHERE season=%s", (evidence["season"],))
        bye_sources = {row[0] for row in cursor.fetchall()}
        allowed_bye_sources = {evidence["bye_source"]}
        if replace_known_legacy_byes:
            allowed_bye_sources.add(LEGACY_BYE_SOURCE)
        if LEGACY_BYE_SOURCE in bye_sources and not replace_known_legacy_byes:
            raise ScheduleEvidenceError("NFLVERSE_BYE_LEGACY_SOURCE_REPLACEMENT_REQUIRES_EXPLICIT_FLAG")
        disallowed = {source for source in bye_sources if source and not source.startswith("csv:") and source not in allowed_bye_sources}
        if disallowed:
            raise ScheduleEvidenceError(f"NFLVERSE_BYE_SOURCE_CONFLICT:{','.join(sorted(disallowed))}")

        source = evidence["source"]
        for row in schedule_rows:
            cursor.execute(
                """INSERT INTO nfl_schedule(season,week,match_number,game_time_utc,game_time_pacific,location,home_team,away_team,result,source,source_recorded_at,retrieved_at,imported_at)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                   ON CONFLICT(season,match_number) DO UPDATE SET week=EXCLUDED.week,game_time_utc=EXCLUDED.game_time_utc,game_time_pacific=EXCLUDED.game_time_pacific,location=EXCLUDED.location,home_team=EXCLUDED.home_team,away_team=EXCLUDED.away_team,result=EXCLUDED.result,source=EXCLUDED.source,source_recorded_at=EXCLUDED.source_recorded_at,retrieved_at=EXCLUDED.retrieved_at,imported_at=EXCLUDED.imported_at
                   WHERE nfl_schedule.source LIKE 'csv:%%' OR nfl_schedule.source LIKE 'automated:nflverse-schedules:%%'""",
                (row["season"], row["week"], row["match_number"], row["game_time_utc"], row["game_time_pacific"], row["location"], row["home_team"], row["away_team"], row["result"], source, evidence["source_recorded_at"], evidence["retrieved_at"]),
            )
            if cursor.rowcount != 1:
                raise ScheduleEvidenceError(f"NFLVERSE_SCHEDULE_SOURCE_CONFLICT:{row['match_number']}")

        bye_source = evidence["bye_source"]
        for row in evidence["byes"]:
            cursor.execute(
                """INSERT INTO bye_weeks(season,team,bye_week,source,source_recorded_at,retrieved_at,imported_at)
                   VALUES(%s,%s,%s,%s,%s,%s,NOW())
                   ON CONFLICT(season,team) DO UPDATE SET bye_week=EXCLUDED.bye_week,source=EXCLUDED.source,source_recorded_at=EXCLUDED.source_recorded_at,retrieved_at=EXCLUDED.retrieved_at,imported_at=EXCLUDED.imported_at
                   WHERE bye_weeks.source LIKE 'csv:%%' OR bye_weeks.source LIKE 'automated:nflverse-schedules:%%' OR (%s AND bye_weeks.source=%s)""",
                (evidence["season"], row["team"], row["bye_week"], bye_source, evidence["source_recorded_at"], evidence["retrieved_at"], replace_known_legacy_byes, LEGACY_BYE_SOURCE),
            )
            if cursor.rowcount != 1:
                raise ScheduleEvidenceError(f"NFLVERSE_BYE_SOURCE_CONFLICT:{row['team']}")
        connection.commit()
        return {"schedule_rows": len(schedule_rows), "bye_rows": len(evidence["byes"])}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--replace-known-legacy-byes", action="store_true")
    args = parser.parse_args()
    evidence = fetch_schedule_evidence(season=args.season)
    write_counts = None
    if args.publish:
        connection = app.get_db_connection()
        try:
            write_counts = publish_schedule_evidence(connection, evidence, replace_known_legacy_byes=args.replace_known_legacy_byes)
        finally:
            connection.close()
    print(json.dumps({key: value for key, value in evidence.items() if key not in {"rows", "byes"}} | {"game_count": len(evidence["rows"]), "bye_count": len(evidence["byes"]), "write_counts": write_counts}, default=str, sort_keys=True))


if __name__ == "__main__":
    main()