#!/usr/bin/env python3
from pathlib import Path
import shutil
from datetime import datetime
import py_compile

root = Path.cwd()
stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
ratings_path = root / "batch_e_ratings.py"
weather_path = root / "batch_e_weather.py"

for path in (ratings_path, weather_path):
    if not path.exists():
        raise SystemExit(f"{path.name} not found in current directory")
    backup = path.with_name(f"{path.name}.before_lar_fix_{stamp}")
    shutil.copy2(path, backup)
    print(f"backup: {backup.name}")

ratings_path.write_text('import csv\nimport io\nimport os\n\nimport requests\n\nfrom batch_e_common import games, ready, store\n\nDEFAULT = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"\nTEAM_ALIASES = {"LA": "LAR", "STL": "LAR"}\n\n\ndef normalize_team(team):\n    code = (team or "").strip().upper()\n    return TEAM_ALIASES.get(code, code)\n\n\ndef expected(home_elo, away_elo, home_field_advantage=55):\n    return 1 / (1 + 10 ** (-((home_elo - away_elo + home_field_advantage) / 400)))\n\n\ndef build(rows, season, week):\n    ratings = {}\n    completed = []\n    for row in rows:\n        try:\n            game_season = int(row.get("season"))\n            game_week = int(row.get("week"))\n            home_score = float(row.get("home_score"))\n            away_score = float(row.get("away_score"))\n            home_team = normalize_team(row.get("home_team"))\n            away_team = normalize_team(row.get("away_team"))\n        except (TypeError, ValueError):\n            continue\n        if home_team and away_team and (game_season, game_week) < (season, week):\n            completed.append((game_season, game_week, home_team, away_team, home_score, away_score))\n\n    for _, _, home_team, away_team, home_score, away_score in sorted(completed):\n        home_elo = ratings.get(home_team, 1500.0)\n        away_elo = ratings.get(away_team, 1500.0)\n        actual_home = 1.0 if home_score > away_score else 0.0 if home_score < away_score else 0.5\n        delta = 20 * (actual_home - expected(home_elo, away_elo))\n        ratings[home_team] = home_elo + delta\n        ratings[away_team] = away_elo - delta\n\n    source_url = os.getenv("NFLVERSE_GAMES_URL", DEFAULT)\n    return [\n        {"team": team, "elo_rating": round(value, 2), "power_rating": round((value - 1500) / 25, 3), "source_url": source_url}\n        for team, value in ratings.items()\n    ]\n\n\ndef run(conn, season, week, dry=False):\n    url = os.getenv("NFLVERSE_GAMES_URL", DEFAULT)\n    response = requests.get(url, timeout=90)\n    response.raise_for_status()\n    all_ratings = build(csv.DictReader(io.StringIO(response.text)), season, week)\n    scheduled_teams = {team for game in games(conn, season, week) for team in (game["away_team"], game["home_team"])}\n    records = [rating for rating in all_ratings if rating["team"] in scheduled_teams]\n    loaded_teams = {record["team"] for record in records}\n    score = len(loaded_teams) / len(scheduled_teams) if scheduled_teams else 0\n    result = {"source": "ratings", "expected": len(scheduled_teams), "loaded": len(loaded_teams), "coverage": score, "missing": sorted(scheduled_teams - loaded_teams)}\n    if not dry:\n        if records:\n            result["run_id"] = store(conn, "ratings", records, season, week, "nflverse_games")\n        ready(conn, season, week, "ratings", score, None if score >= 0.999 else f"ratings coverage {len(loaded_teams)}/{len(scheduled_teams)}")\n    return result\n', encoding="utf-8")

weather_text = weather_path.read_text(encoding="utf-8")
if "'LAR':" not in weather_text and '"LAR":' not in weather_text:
    marker = "'LA':(33.9535,-118.3392),"
    if marker not in weather_text:
        raise SystemExit("Could not find LA coordinate entry in batch_e_weather.py")
    weather_text = weather_text.replace(marker, marker + "'LAR':(33.9535,-118.3392),", 1)
    weather_path.write_text(weather_text, encoding="utf-8")

py_compile.compile(str(ratings_path), doraise=True)
py_compile.compile(str(weather_path), doraise=True)
print("PASS: ratings and weather files repaired")
