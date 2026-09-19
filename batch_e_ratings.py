import csv
import hashlib
import io
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
from typing import Any, Mapping

import requests

from batch_e_common import canonical_schedule_games, ready, store
from imports.import_weekly_intelligence import TEAMS, abbr

DEFAULT = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
MODEL_NAME = "nflverse-historical-elo"
MODEL_VERSION = "nflverse-historical-elo-v2.0.0"
INITIAL_RATING = 1500.0
HOME_FIELD_ADVANTAGE = 55.0
K_FACTOR = 20.0
COMPLETED_GAME_RULE = "completed scores with game season/week before target"
CANONICAL_TEAMS = frozenset(TEAMS.values())
REPLAY_CLASSIFICATIONS = (
    "INCLUDED_COMPLETED_GAME",
    "EXCLUDED_FUTURE_GAME",
    "EXCLUDED_UNPLAYED_GAME",
    "EXCLUDED_UNSUPPORTED_SEASON",
    "EXCLUDED_UNSUPPORTED_STATUS",
    "EXCLUDED_MISSING_IDENTITY",
    "EXCLUDED_MISSING_SCORE",
    "BLOCKING_MALFORMED_COMPLETED_GAME",
)


def normalize_team(team):
    return abbr(team)


def _identity_detail(raw_team):
    raw = str(raw_team or "").strip().upper()
    normalized = normalize_team(raw_team)
    if not raw:
        return raw, normalized, "MISSING_IDENTITY", "empty source identity"
    if normalized in CANONICAL_TEAMS:
        if raw == normalized:
            return raw, normalized, "CURRENT_CANONICAL_TEAM", "canonical abbreviation"
        return raw, normalized, "VERIFIED_HISTORICAL_FRANCHISE_ALIAS", f"canonical alias {raw}->{normalized}"
    if len(raw) > 5 or not raw.isalnum():
        return raw, normalized, "NON_NFL_OR_MALFORMED", "invalid team identity shape"
    return raw, normalized, "UNSUPPORTED", "no verified canonical mapping"


def expected(home_elo, away_elo, home_field_advantage=HOME_FIELD_ADVANTAGE):
    return 1 / (1 + 10 ** (-((home_elo - away_elo + home_field_advantage) / 400)))


def _timestamp(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _freshness(retrieved_at, threshold_seconds, now):
    retrieved = _timestamp(retrieved_at)
    evaluation_time = _timestamp(now) or datetime.now(timezone.utc)
    age = max(0, int((evaluation_time - retrieved).total_seconds()))
    if age <= threshold_seconds * 0.8:
        return "FRESH"
    if age <= threshold_seconds:
        return "AGING"
    return "STALE"


def _source_timestamp(response):
    raw = response.headers.get("Last-Modified")
    if not raw:
        return None, None
    try:
        parsed = parsedate_to_datetime(raw).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None, raw
    return parsed, raw


def _row_game_time(row):
    for key in ("game_time", "game_datetime", "scheduled_at", "gameday"):
        value = row.get(key)
        if value in (None, ""):
            continue
        if key == "gameday" and row.get("gametime"):
            value = f"{value}T{row['gametime']}"
        parsed = _timestamp(value)
        if parsed:
            return parsed
    return None


def _row_status(row):
    for key in ("status", "game_status", "result_status"):
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip().lower()
    return None


def _score(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _classify_row(row, season, week, cutoff):
    try:
        game_season = int(row.get("season") or row.get("game_season"))
        game_week = int(row.get("week") or row.get("game_week"))
    except (TypeError, ValueError):
        return "EXCLUDED_UNSUPPORTED_SEASON", None
    if game_season > season or (game_season == season and game_week >= week):
        return "EXCLUDED_FUTURE_GAME", None
    if game_season < 1999 or game_season > season:
        return "EXCLUDED_UNSUPPORTED_SEASON", None
    status = _row_status(row)
    if status in {"canceled", "cancelled", "postponed", "suspended"}:
        return "EXCLUDED_UNSUPPORTED_STATUS", None
    supported_statuses = {"final", "completed", "complete", "scheduled", "pre", "pregame", "unplayed", "not started"}
    if status is not None and status not in supported_statuses:
        return "EXCLUDED_UNSUPPORTED_STATUS", None
    game_time = _row_game_time(row)
    home_score = _score(row.get("home_score"))
    away_score = _score(row.get("away_score"))
    explicit_completed = status in {"final", "completed", "complete"}
    if home_score is None or away_score is None:
        return ("BLOCKING_MALFORMED_COMPLETED_GAME" if explicit_completed else "EXCLUDED_UNPLAYED_GAME"), None
    if game_time is None or (cutoff and game_time >= cutoff):
        return ("BLOCKING_MALFORMED_COMPLETED_GAME" if explicit_completed else "EXCLUDED_UNPLAYED_GAME"), None
    raw_home, normalized_home, home_class, home_rule = _identity_detail(row.get("home_team"))
    raw_away, normalized_away, away_class, away_rule = _identity_detail(row.get("away_team"))
    if not raw_home or not raw_away:
        return "BLOCKING_MALFORMED_COMPLETED_GAME" if explicit_completed else "EXCLUDED_MISSING_IDENTITY", None
    if normalized_home not in CANONICAL_TEAMS or normalized_away not in CANONICAL_TEAMS or normalized_home == normalized_away:
        return "BLOCKING_MALFORMED_COMPLETED_GAME", {
            "game_id": row.get("game_id") or row.get("id") or "UNKNOWN_GAME",
            "home_team": raw_home,
            "away_team": raw_away,
            "normalized_home_team": normalized_home,
            "normalized_away_team": normalized_away,
            "classification": home_class if normalized_home not in CANONICAL_TEAMS else away_class,
            "normalization_rule": home_rule if normalized_home not in CANONICAL_TEAMS else away_rule,
        }
    return "INCLUDED_COMPLETED_GAME", {
        "season": game_season,
        "week": game_week,
        "game_time": game_time,
        "home_team": normalized_home,
        "away_team": normalized_away,
        "home_score": home_score,
        "away_score": away_score,
        "game_id": row.get("game_id") or row.get("id") or "UNKNOWN_GAME",
        "raw_home_team": raw_home,
        "raw_away_team": raw_away,
    }


def reconstruct_ratings(rows, season, week, cutoff=None):
    ratings = {}
    unresolved = []
    invalid = []
    identity_lineage = []
    classifications = {name: 0 for name in REPLAY_CLASSIFICATIONS}
    completed_keys = {}
    for row in rows:
        classification, game = _classify_row(row, season, week, cutoff)
        classifications[classification] += 1
        if classification != "INCLUDED_COMPLETED_GAME":
            if classification == "BLOCKING_MALFORMED_COMPLETED_GAME":
                invalid.append(game or {"game_id": row.get("game_id") or row.get("id") or "UNKNOWN_GAME", "home_team": row.get("home_team"), "away_team": row.get("away_team"), "classification": classification})
                if game:
                    unresolved.append(game)
            continue
        for raw, canonical in ((game["raw_home_team"], game["home_team"]), (game["raw_away_team"], game["away_team"])):
            if raw != canonical:
                identity_lineage.append({"raw_identity": raw, "canonical_identity": canonical, "classification": "VERIFIED_HISTORICAL_FRANCHISE_ALIAS", "normalization_rule": f"canonical alias {raw}->{canonical}"})
        key = (game["season"], game["week"], game["home_team"], game["away_team"])
        prior = completed_keys.get(key)
        if prior and prior != (game["home_score"], game["away_score"]):
            invalid.append({"game_id": game["game_id"], "home_team": game["home_team"], "away_team": game["away_team"], "classification": "BLOCKING_MALFORMED_COMPLETED_GAME", "normalization_rule": "contradictory completed-game duplicate"})
            classifications["INCLUDED_COMPLETED_GAME"] -= 1
            classifications["BLOCKING_MALFORMED_COMPLETED_GAME"] += 1
            continue
        completed_keys[key] = (game["home_score"], game["away_score"])
        home_elo = ratings.get(game["home_team"], INITIAL_RATING)
        away_elo = ratings.get(game["away_team"], INITIAL_RATING)
        actual_home = 1.0 if game["home_score"] > game["away_score"] else 0.0 if game["home_score"] < game["away_score"] else 0.5
        delta = K_FACTOR * (actual_home - expected(home_elo, away_elo, HOME_FIELD_ADVANTAGE))
        ratings[game["home_team"]] = home_elo + delta
        ratings[game["away_team"]] = away_elo - delta
    return ratings, unresolved, invalid, identity_lineage, classifications


def build(rows, season, week):
    ratings, _, _, _, _ = reconstruct_ratings(rows, season, week)
    return [
        {"team": team, "elo_rating": round(value, 2), "power_rating": round((value - INITIAL_RATING) / 25, 3), "source_url": DEFAULT}
        for team, value in sorted(ratings.items())
    ]


def _blocked(*, season, week, source_identifier, source_url, retrieved_at, source_recorded_at, generated_at, freshness_threshold_id, source_checksum, blockers, expected_team_count=0, resolved_team_count=0, expected_game_count=0, usable_game_count=0, unresolved_identities=None, duplicate_identities=None, historical_rows_unresolved=None, scheduled_teams_unresolved=None, scheduled_teams_missing_rating=None, replay_classification_counts=None, lineage=None):
    return {
        "available": False,
        "season": season,
        "week": week,
        "model_name": MODEL_NAME,
        "model_version": None,
        "source_type": "MODEL_ONLY",
        "authority_state": "INFORMATIONAL_ONLY",
        "decision_effect": "NONE",
        "initial_rating": INITIAL_RATING,
        "source_identifier": source_identifier,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "source_recorded_at": source_recorded_at,
        "generated_at": generated_at,
        "source_checksum": source_checksum,
        "freshness_threshold_id": freshness_threshold_id,
        "freshness_state": "UNAVAILABLE",
        "completeness_state": "INCOMPLETE",
        "expected_team_count": expected_team_count,
        "resolved_team_count": resolved_team_count,
        "expected_game_count": expected_game_count,
        "usable_game_count": usable_game_count,
        "team_ratings": {},
        "validated_games": [],
        "unresolved_identities": unresolved_identities or [],
        "duplicate_identities": duplicate_identities or [],
        "historical_rows_unresolved": historical_rows_unresolved or [],
        "scheduled_teams_unresolved": scheduled_teams_unresolved or [],
        "scheduled_teams_missing_rating": scheduled_teams_missing_rating or [],
        "replay_classification_counts": replay_classification_counts or {name: 0 for name in REPLAY_CLASSIFICATIONS},
        "blocker_reasons": blockers,
        "lineage": lineage or {},
    }


def build_evidence_batch(*, season, week, scheduled_games, historical_rows, source_identifier, source_url, retrieved_at, generated_at, model_version=MODEL_VERSION, freshness_threshold_id=None, freshness_threshold_seconds=None, source_checksum=None, source_recorded_at=None, source_recorded_raw=None, now=None):
    retrieved_value = _timestamp(retrieved_at)
    source_recorded_value = _timestamp(source_recorded_at)
    generated_value = _timestamp(generated_at)
    blockers = []
    if not source_identifier:
        blockers.append("ELO_SOURCE_IDENTIFIER_UNAVAILABLE")
    if not source_url:
        blockers.append("ELO_SOURCE_URL_UNAVAILABLE")
    if retrieved_value is None:
        blockers.append("ELO_RETRIEVED_TIMESTAMP_UNAVAILABLE")
    if generated_value is None:
        blockers.append("ELO_GENERATED_TIMESTAMP_UNAVAILABLE")
    if not model_version:
        blockers.append("ELO_MODEL_VERSION_UNAVAILABLE")
    if not source_checksum:
        blockers.append("ELO_SOURCE_CHECKSUM_UNAVAILABLE")
    try:
        threshold_seconds = int(freshness_threshold_seconds)
    except (TypeError, ValueError):
        threshold_seconds = 0
    if not freshness_threshold_id or threshold_seconds <= 0:
        blockers.append("ELO_FRESHNESS_THRESHOLD_UNAVAILABLE")
    if not isinstance(scheduled_games, list) or not scheduled_games:
        blockers.append("ELO_SCHEDULE_EVIDENCE_UNAVAILABLE")
        scheduled_games = []

    normalized_games = []
    scheduled_unresolved = []
    duplicate_identities = []
    seen_games = set()
    seen_teams = set()
    for game in scheduled_games:
        home_team = normalize_team(game.get("home_team")) if isinstance(game, Mapping) else ""
        away_team = normalize_team(game.get("away_team")) if isinstance(game, Mapping) else ""
        game_id = str(game.get("game_id") or "").strip() if isinstance(game, Mapping) else ""
        if home_team not in CANONICAL_TEAMS or away_team not in CANONICAL_TEAMS or home_team == away_team or not game_id:
            scheduled_unresolved.extend([team for team in (home_team, away_team) if team not in CANONICAL_TEAMS or not team])
            continue
        identity = (game_id, home_team, away_team)
        if identity in seen_games:
            duplicate_identities.append(game_id)
        seen_games.add(identity)
        for team in (home_team, away_team):
            if team in seen_teams:
                duplicate_identities.append(team)
            seen_teams.add(team)
        normalized_games.append({"game_id": game_id, "home_team": home_team, "away_team": away_team})

    cutoffs = [_timestamp(game.get("scheduled_at")) for game in scheduled_games if isinstance(game, Mapping)]
    cutoffs = [value for value in cutoffs if value is not None]
    cutoff = min(cutoffs) if cutoffs else None
    if cutoff is None:
        blockers.append("ELO_SCHEDULE_CUTOFF_UNAVAILABLE")
    ratings, historical_unresolved, invalid_history, identity_lineage, replay_counts = reconstruct_ratings(historical_rows, season, week, cutoff)
    expected_teams = {team for game in normalized_games for team in (game["home_team"], game["away_team"])}
    historical_scheduled_blockers = [row for row in historical_unresolved if row.get("normalized_home_team") in expected_teams or row.get("normalized_away_team") in expected_teams]
    invalid_scheduled_blockers = [row for row in invalid_history if row.get("normalized_home_team") in expected_teams or row.get("normalized_away_team") in expected_teams or row.get("home_team") in expected_teams or row.get("away_team") in expected_teams]
    if invalid_scheduled_blockers:
        blockers.append("ELO_HISTORICAL_RECONSTRUCTION_INCOMPLETE")
    if scheduled_unresolved:
        blockers.append("ELO_CANONICAL_IDENTITY_UNRESOLVED")
    if historical_scheduled_blockers:
        blockers.append("ELO_HISTORICAL_RECONSTRUCTION_INCOMPLETE")
    if duplicate_identities:
        blockers.append("ELO_DUPLICATE_IDENTITY")
    resolved_teams = expected_teams.intersection(ratings)
    usable_games = [game for game in normalized_games if game["home_team"] in ratings and game["away_team"] in ratings]
    expected_game_count = len(normalized_games)
    missing_ratings = sorted(expected_teams - resolved_teams)
    if missing_ratings:
        blockers.append("ELO_SCHEDULE_TEAM_RATING_MISSING")
    if len(usable_games) != expected_game_count:
        blockers.append("ELO_SCHEDULE_GAME_COVERAGE_INCOMPLETE")
    freshness_state = "UNAVAILABLE"
    if not blockers:
        freshness_state = _freshness(retrieved_at, threshold_seconds, now)
        if freshness_state == "STALE":
            blockers.append("ELO_SOURCE_DATA_STALE")
    lineage = {
        "owner": "batch_e_ratings",
        "completed_game_rule": COMPLETED_GAME_RULE,
        "home_field_advantage": HOME_FIELD_ADVANTAGE,
        "k_factor": K_FACTOR,
        "canonical_team_owner": "imports.import_weekly_intelligence.abbr",
        "initial_rating_is_model_parameter": True,
    }
    structural_blockers = [blocker for blocker in blockers if blocker != "ELO_FRESHNESS_THRESHOLD_UNAVAILABLE"]
    if structural_blockers:
        result = _blocked(season=season, week=week, source_identifier=source_identifier, source_url=source_url, retrieved_at=retrieved_value, source_recorded_at=source_recorded_value, generated_at=generated_value, freshness_threshold_id=freshness_threshold_id, source_checksum=source_checksum, blockers=sorted(set(blockers)), expected_team_count=len(expected_teams), resolved_team_count=len(resolved_teams), expected_game_count=expected_game_count, usable_game_count=len(usable_games), unresolved_identities=scheduled_unresolved, duplicate_identities=sorted(set(duplicate_identities)), historical_rows_unresolved=historical_unresolved + invalid_history, scheduled_teams_unresolved=scheduled_unresolved, scheduled_teams_missing_rating=missing_ratings, replay_classification_counts=replay_counts, lineage={**lineage, "completed_game_cutoff": cutoff, "historical_rows_unresolved": historical_unresolved + invalid_history, "historical_identity_lineage": identity_lineage, "source_recorded_raw": source_recorded_raw})
        result["freshness_state"] = freshness_state
        result["model_version"] = model_version if model_version else None
        return result
    validated_games = [
        {
            "game_id": game["game_id"],
            "home_team": game["home_team"],
            "away_team": game["away_team"],
            "home_rating": float(ratings[game["home_team"]]),
            "away_rating": float(ratings[game["away_team"]]),
        }
        for game in sorted(normalized_games, key=lambda item: item["game_id"])
    ]
    return {
        "available": not blockers,
        "season": season,
        "week": week,
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "source_type": "MODEL_ONLY",
        "authority_state": "INFORMATIONAL_ONLY",
        "decision_effect": "NONE",
        "initial_rating": INITIAL_RATING,
        "source_identifier": source_identifier,
        "source_url": source_url,
        "retrieved_at": retrieved_value,
        "source_recorded_at": source_recorded_value,
        "generated_at": generated_value,
        "source_checksum": source_checksum,
        "freshness_threshold_id": freshness_threshold_id,
        "freshness_state": freshness_state,
        "completeness_state": "COMPLETE",
        "expected_team_count": len(expected_teams),
        "resolved_team_count": len(resolved_teams),
        "expected_game_count": expected_game_count,
        "usable_game_count": len(usable_games),
        "team_ratings": {team: ratings[team] for team in sorted(expected_teams)},
        "validated_games": validated_games,
        "unresolved_identities": [],
        "duplicate_identities": [],
        "historical_rows_unresolved": historical_unresolved + invalid_history,
        "scheduled_teams_unresolved": [],
        "scheduled_teams_missing_rating": [],
        "blocker_reasons": sorted(set(blockers)),
        "replay_classification_counts": replay_counts,
        "lineage": {**lineage, "completed_game_cutoff": cutoff, "historical_identity_lineage": identity_lineage, "source_recorded_raw": source_recorded_raw},
    }

def run(conn, season, week, dry=False, freshness_threshold_id=None, freshness_threshold_seconds=None):
    url = os.getenv("NFLVERSE_GAMES_URL", DEFAULT)
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    retrieved_at = datetime.now(timezone.utc)
    source_recorded_at, source_recorded_raw = _source_timestamp(response)
    scheduled_games = canonical_schedule_games(conn, season, week)
    evidence_batch = build_evidence_batch(
        season=season,
        week=week,
        scheduled_games=scheduled_games,
        historical_rows=list(csv.DictReader(io.StringIO(response.text))),
        source_identifier="nflverse_games",
        source_url=url,
        retrieved_at=retrieved_at,
        generated_at=datetime.now(timezone.utc),
        model_version=MODEL_VERSION,
        freshness_threshold_id=freshness_threshold_id,
        freshness_threshold_seconds=freshness_threshold_seconds,
        source_checksum=hashlib.sha256(response.content).hexdigest(),
        source_recorded_at=source_recorded_at,
        source_recorded_raw=source_recorded_raw,
    )
    scheduled_teams = {team for game in scheduled_games for team in (game["away_team"], game["home_team"])}
    records = [{"team": team, "elo_rating": rating, "power_rating": round((rating - INITIAL_RATING) / 25, 3), "source_url": url} for team, rating in evidence_batch["team_ratings"].items()]
    loaded_teams = set(evidence_batch["team_ratings"])
    score = len(loaded_teams) / len(scheduled_teams) if scheduled_teams else 0
    result = {"source": "ratings", "expected": len(scheduled_teams), "loaded": len(loaded_teams), "coverage": score, "missing": sorted(scheduled_teams - loaded_teams), "evidence_batch": evidence_batch}
    if not dry:
        if records:
            result["run_id"] = store(conn, "ratings", records, season, week, "nflverse_games")
        ready(conn, season, week, "ratings", score, None if evidence_batch["available"] else ";".join(evidence_batch["blocker_reasons"]))
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--freshness-threshold-id")
    parser.add_argument("--freshness-threshold-seconds", type=int)
    args = parser.parse_args()
    from batch_e_common import connect

    conn = connect()
    try:
        result = run(conn, args.season, args.week, args.dry_run, args.freshness_threshold_id, args.freshness_threshold_seconds)
    finally:
        conn.close()
    print(result)


if __name__ == "__main__":
    main()
