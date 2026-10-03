from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SOURCE = "FantasyPros consensus via DynastyProcess"
REFRESH_SECONDS = 21600
RETRY_SECONDS = 900
MAX_AGE = {"this_week": 172800, "rest_of_season": 604800}
PAGES = {"qb": "QB", "ppr-rb": "RB", "ppr-wr": "WR", "ppr-te": "TE", "k": "K", "dst": "DEF"}
FILES = ("db_playerids.csv", "fp_latest_weekly.csv", "db_fpecr_latest.csv")


def _time(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _name(value):
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def _team(value):
    value = str(value or "").upper().strip()
    return {"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}.get(value, value)


def _position(value):
    value = str(value or "").upper().strip()
    return {"PK": "K", "DST": "DEF"}.get(value, value)


def _fetch(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": "fantasy-intelligence-private-rankings/1.0"})
    response.raise_for_status()
    return response.content


def acquire(fetch=_fetch):
    release = json.loads(fetch("https://api.github.com/repos/DynastyProcess/data/commits?per_page=1"))[0]
    version = release["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", version):
        raise ValueError("Ranking release is unverified")
    artifacts = {}
    for filename in FILES:
        url = f"https://raw.githubusercontent.com/DynastyProcess/data/{version}/files/{filename}"
        raw = fetch(url)
        artifacts[filename] = {"rows": list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))), "url": url, "checksum": hashlib.sha256(raw).hexdigest()}
    return {"version": version, "artifacts": artifacts, "source": SOURCE, "use_scope": "Owner-approved private personal use; no redistribution", "license": "GPL-3.0"}


def evaluate(snapshot, nfl_state, now=None, *, sleeper_catalog=None):
    now = now or datetime.now(timezone.utc)
    result = {key: snapshot.get(key) for key in ("last_attempt", "last_successful_refresh", "refresh_error", "version")}
    result.update(source=SOURCE, horizons={})
    artifacts = snapshot.get("artifacts") or {}
    identities = (artifacts.get("db_playerids.csv") or {}).get("rows") or []
    provider_counts = Counter(row.get("fantasypros_id") for row in identities)
    sleeper_counts = Counter(row.get("sleeper_id") for row in identities)
    mapping = {row["fantasypros_id"]: row for row in identities if row.get("fantasypros_id") not in (None, "", "NA") and row.get("sleeper_id") not in (None, "", "NA") and provider_counts[row["fantasypros_id"]] == 1 and sleeper_counts[row["sleeper_id"]] == 1}
    provider_rows = {}
    for row in identities:
        provider_rows.setdefault(row.get("fantasypros_id"), []).append(row)
    name_position_index = {}
    contextual_index = {}
    for sleeper_id, record in (sleeper_catalog or {}).items():
        name = record.get("full_name") or " ".join(str(record.get(key) or "") for key in ("first_name", "last_name"))
        normalized_name = _name(name)
        if normalized_name:
            name_position_index.setdefault((normalized_name, _position(record.get("position"))), []).append((sleeper_id, record))
            team = _team(record.get("team"))
            if team not in {"", "NA", "FA"}:
                contextual_index.setdefault((normalized_name, _position(record.get("position")), team), []).append((sleeper_id, record))
    try:
        season, week = int(nfl_state["season"]), int(nfl_state["week"])
        start = _time(nfl_state["season_start_date"]).date()
        week_start = start + timedelta(days=7 * (week - 1))
        active = nfl_state.get("season_type") == "regular" and start.year == season and 1 <= week <= 18
    except (KeyError, TypeError, ValueError):
        active = False
    team_games = {}
    if active:
        for row in (artifacts.get(FILES[1]) or {}).get("rows") or []:
            try:
                if row.get("page") not in PAGES:
                    continue
                age = (now - _time(row["scrape_date"])).total_seconds()
                kickoff = datetime.fromtimestamp(float(row["player_game_kickoff_ts"]), timezone.utc)
                team = _team(row.get("team"))
                if 0 <= age <= MAX_AGE["this_week"] and team not in {"", "FA", "NA"} and week_start <= kickoff.date() < week_start + timedelta(days=7) and row.get("fantasypros_id") not in (None, "", "NA"):
                    team_games.setdefault(team, {}).setdefault(kickoff, set()).add(row["fantasypros_id"])
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                continue
    for horizon, filename in (("this_week", FILES[1]), ("rest_of_season", FILES[2])):
        artifact = artifacts.get(filename) or {}
        parsed, rejected, diagnostics = [], Counter(), []
        supported_rows = 0
        for row in artifact.get("rows") or []:
            path = str(row.get("fp_page") or "")
            page = row.get("page") if horizon == "this_week" else path.removeprefix("/nfl/rankings/ros-").removesuffix(".php") if path.startswith("/nfl/rankings/ros-") else None
            if page not in PAGES:
                continue
            supported_rows += 1
            provider_id = row.get("fantasypros_id") if horizon == "this_week" else row.get("id")
            game_evidence = None
            try:
                published = _time(row["scrape_date"])
                age = (now - published).total_seconds()
                if not active or not start <= published.date() <= start + timedelta(days=126):
                    raise ValueError("Season or NFL week is unverified")
                if age < 0 or age > MAX_AGE[horizon]:
                    raise ValueError("Source is stale or future-dated")
                if horizon == "this_week":
                    if row.get("player_game_kickoff_ts") in (None, "", "NA"):
                        published_identity = mapping.get(provider_id)
                        current = (sleeper_catalog or {}).get((published_identity or {}).get("sleeper_id")) or {}
                        current_team = _team(current.get("team"))
                        games = team_games.get(current_team, {})
                        if published_identity and current and current_team in {"", "FA", "NA"}:
                            raise ValueError("KICKOFF_CURRENT_TEAM_NOT_SUPPLIED")
                        if not published_identity or _position(published_identity.get("position")) != PAGES[page] or _position(current.get("position")) != PAGES[page] or current.get("status") != "Active" or len(games) != 1:
                            raise ValueError("KICKOFF_UNAVAILABLE")
                        kickoff, supporting_ids = next(iter(games.items()))
                        if len(supporting_ids) < 2:
                            raise ValueError("KICKOFF_UNAVAILABLE")
                        game_evidence = {"method": "PUBLISHED_ID_CURRENT_SLEEPER_TEAM_CORROBORATED_KICKOFF", "sleeper_team": current_team, "publisher_team": row.get("team"), "supporting_source_player_count": len(supporting_ids), "kickoff": kickoff.isoformat()}
                    else:
                        kickoff = datetime.fromtimestamp(float(row["player_game_kickoff_ts"]), timezone.utc)
                    if not week_start <= kickoff.date() < week_start + timedelta(days=7):
                        raise ValueError("Ranking belongs to another NFL week")
                    if kickoff <= now:
                        raise ValueError("Game already started")
                identity = mapping.get(provider_id)
                identity_method = "PUBLISHED_PROVIDER_CROSSWALK"
                if page == "dst":
                    team = str(row.get("team") or "").upper().strip()
                    team = {"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}.get(team, team)
                    record = (sleeper_catalog or {}).get(team)
                    if not record or record.get("position") not in {"DEF", "DST"} or record.get("team") != team:
                        raise ValueError("TEAM_DEFENSE_IDENTITY_UNVERIFIED")
                    identity = {"sleeper_id": team, "position": "DEF"}
                    identity_method = "EXACT_SLEEPER_TEAM_ID"
                elif not identity:
                    matches = provider_rows.get(provider_id, [])
                    source_name = row.get("player_name") or row.get("player")
                    contextual = contextual_index.get((_name(source_name), PAGES[page], _team(row.get("team"))), [])
                    if (not matches or (len(matches) == 1 and matches[0].get("sleeper_id") in (None, "", "NA"))) and len(contextual) == 1:
                        sleeper_id, record = contextual[0]
                        identity = {"sleeper_id": sleeper_id, "position": record.get("position")}
                        identity_method = "OWNER_APPROVED_UNIQUE_NAME_POSITION_TEAM"
                    elif len(contextual) > 1 and not matches:
                        raise ValueError("CONTEXTUAL_IDENTITY_AMBIGUOUS")
                    elif not matches:
                        raise ValueError("PROVIDER_ID_ABSENT_FROM_CROSSWALK")
                    elif len(matches) > 1:
                        raise ValueError("DUPLICATE_PROVIDER_ID")
                    elif matches[0].get("sleeper_id") in (None, "", "NA"):
                        raise ValueError("SLEEPER_ID_MISSING")
                    else:
                        raise ValueError("DUPLICATE_SLEEPER_ID")
                position = _position(identity.get("position"))
                if position != PAGES[page]:
                    raise ValueError("POSITION_CONFLICT")
                rank = float(row["ecr"])
                if not math.isfinite(rank) or rank <= 0:
                    raise ValueError("Consensus rank is invalid")
                parsed.append({"player_id": identity["sleeper_id"], "provider_id": provider_id, "identity_method": identity_method, "identity_evidence": {"source_name": row.get("player_name") or row.get("player"), "source_position": PAGES[page], "source_team": row.get("team"), "sleeper_team": (sleeper_catalog or {}).get(identity["sleeper_id"], {}).get("team")}, "game_evidence": game_evidence, "position": PAGES[page], "ecr": rank, "source_date": row["scrape_date"], "source_age_seconds": int(age), "horizon": horizon, "scoring": "PPR", "season": season, "week": week if horizon == "this_week" else None})
            except (KeyError, TypeError, ValueError, OverflowError, OSError) as error:
                rejected[str(error)] += 1
                matches = provider_rows.get(provider_id, [])
                sleeper_id = matches[0].get("sleeper_id") if len(matches) == 1 else None
                sleeper_record = (sleeper_catalog or {}).get(sleeper_id) or {}
                classification = "CONFIRMED_STARTED_GAME" if str(error) == "Game already started" else "CONFIRMED_STALE_OR_FUTURE_SOURCE" if str(error) == "Source is stale or future-dated" else "CONFIRMED_INVALID_RANK" if str(error) == "Consensus rank is invalid" else "PENDING_VERIFICATION"
                diagnostics.append({"provider_id": provider_id, "player": row.get("player_name") or row.get("player"), "page": page, "team": row.get("team"), "reason": str(error), "classification": classification, "raw_ecr": row.get("ecr"), "raw_kickoff": row.get("player_game_kickoff_ts"), "source_date": row.get("scrape_date"), "crosswalk_matches": [{"sleeper_id": match.get("sleeper_id"), "position": match.get("position")} for match in matches], "sleeper_check": {key: sleeper_record.get(key) for key in ("team", "status", "injury_status")} if sleeper_record else None})
                if str(error) in {"PROVIDER_ID_ABSENT_FROM_CROSSWALK", "SLEEPER_ID_MISSING"}:
                    name = str(row.get("player_name") or row.get("player") or "")
                    normalized_name = "".join(character for character in name.casefold() if character.isalnum())
                    diagnostics[-1]["investigation_candidates"] = [{"player_id": candidate_id, "team": record.get("team"), "status": record.get("status"), "injury_status": record.get("injury_status"), "method": "NAME_POSITION_RESEARCH_ONLY"} for candidate_id, record in name_position_index.get((normalized_name, PAGES[page]), [])]
        counts = Counter(row["player_id"] for row in parsed)
        ranks = {row["player_id"]: row for row in parsed if counts[row["player_id"]] == 1}
        for row in parsed:
            if counts[row["player_id"]] > 1:
                rejected["DUPLICATE_RANK_PLAYER_ID"] += 1
                diagnostics.append({"player_id": row["player_id"], "reason": "DUPLICATE_RANK_PLAYER_ID", "classification": "PENDING_VERIFICATION", "raw_ecr": row["ecr"], "source_date": row["source_date"]})
        reconciliation = {"input_rows": len(artifact.get("rows") or []), "supported_scope_rows": supported_rows, "published_rows": len(ranks), "review_records": len(diagnostics), "reconciled": supported_rows == len(ranks) + len(diagnostics)}
        result["horizons"][horizon] = {"state": "AVAILABLE" if ranks else "UNAVAILABLE", "ranks": ranks, "rejections": dict(rejected), "diagnostics": diagnostics, "reconciliation": reconciliation, "max_age_seconds": MAX_AGE[horizon], "source_url": artifact.get("url"), "checksum": artifact.get("checksum")}
    return result


def refresh(path, *, fetch=_fetch, now=None, force=False, scope=None):
    now = now or datetime.now(timezone.utc)
    path = Path(path)
    try:
        snapshot = json.loads(path.read_text())
        if not isinstance(snapshot, dict):
            snapshot = {}
    except (OSError, ValueError):
        snapshot = {}
    try:
        interval = RETRY_SECONDS if snapshot.get("refresh_error") else REFRESH_SECONDS
        age = (now - _time(snapshot.get("last_attempt"))).total_seconds()
        due = age < 0 or age >= interval
    except (TypeError, ValueError):
        due = True
    if scope is not None and snapshot.get("scope") != scope:
        due = True
    if not force and not due:
        return snapshot
    try:
        snapshot = {**acquire(fetch), "last_successful_refresh": now.isoformat(), "refresh_error": None}
    except Exception as error:
        snapshot["refresh_error"] = f"Ranking refresh failed: {type(error).__name__}"
    snapshot["last_attempt"] = now.isoformat()
    if scope is not None:
        snapshot["scope"] = scope
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        json.dump(snapshot, temporary)
        temp_name = temporary.name
    os.replace(temp_name, path)
    return snapshot


def read_rankings(path, nfl_state, *, now=None, sleeper_catalog=None):
    now = now or datetime.now(timezone.utc)
    try:
        scope = ":".join(str(nfl_state.get(key)) for key in ("season", "season_type", "week"))
        return evaluate(refresh(path, now=now, scope=scope), nfl_state, now, sleeper_catalog=sleeper_catalog)
    except (OSError, ValueError, TypeError, AttributeError):
        return evaluate({"refresh_error": "Ranking cache unavailable"}, nfl_state, now)