import csv
import io
import os

import requests

from batch_e_common import games, ready, store

DEFAULT = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
TEAM_ALIASES = {"LA": "LAR", "STL": "LAR"}


def normalize_team(team):
    code = (team or "").strip().upper()
    return TEAM_ALIASES.get(code, code)


def expected(home_elo, away_elo, home_field_advantage=55):
    return 1 / (1 + 10 ** (-((home_elo - away_elo + home_field_advantage) / 400)))


def build(rows, season, week):
    ratings = {}
    completed = []
    for row in rows:
        try:
            game_season = int(row.get("season"))
            game_week = int(row.get("week"))
            home_score = float(row.get("home_score"))
            away_score = float(row.get("away_score"))
            home_team = normalize_team(row.get("home_team"))
            away_team = normalize_team(row.get("away_team"))
        except (TypeError, ValueError):
            continue
        if home_team and away_team and (game_season, game_week) < (season, week):
            completed.append((game_season, game_week, home_team, away_team, home_score, away_score))

    for _, _, home_team, away_team, home_score, away_score in sorted(completed):
        home_elo = ratings.get(home_team, 1500.0)
        away_elo = ratings.get(away_team, 1500.0)
        actual_home = 1.0 if home_score > away_score else 0.0 if home_score < away_score else 0.5
        delta = 20 * (actual_home - expected(home_elo, away_elo))
        ratings[home_team] = home_elo + delta
        ratings[away_team] = away_elo - delta

    source_url = os.getenv("NFLVERSE_GAMES_URL", DEFAULT)
    return [
        {"team": team, "elo_rating": round(value, 2), "power_rating": round((value - 1500) / 25, 3), "source_url": source_url}
        for team, value in ratings.items()
    ]


def run(conn, season, week, dry=False):
    url = os.getenv("NFLVERSE_GAMES_URL", DEFAULT)
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    all_ratings = build(csv.DictReader(io.StringIO(response.text)), season, week)
    scheduled_teams = {team for game in games(conn, season, week) for team in (game["away_team"], game["home_team"])}
    records = [rating for rating in all_ratings if rating["team"] in scheduled_teams]
    loaded_teams = {record["team"] for record in records}
    score = len(loaded_teams) / len(scheduled_teams) if scheduled_teams else 0
    result = {"source": "ratings", "expected": len(scheduled_teams), "loaded": len(loaded_teams), "coverage": score, "missing": sorted(scheduled_teams - loaded_teams)}
    if not dry:
        if records:
            result["run_id"] = store(conn, "ratings", records, season, week, "nflverse_games")
        ready(conn, season, week, "ratings", score, None if score >= 0.999 else f"ratings coverage {len(loaded_teams)}/{len(scheduled_teams)}")
    return result
