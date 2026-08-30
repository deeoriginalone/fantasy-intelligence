"""SQLite persistence for Pick'em inputs, predictions, outcomes, and survivor history."""
from __future__ import annotations
import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("migrations") / "003_yahoo_pickem.sql"


class PickemStore:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def migrate(self) -> None:
        with closing(self.connect()) as connection:
            connection.executescript(SCHEMA_PATH.read_text())
            connection.commit()

    def upsert_game(self, payload: dict) -> None:
        sql = """
        INSERT INTO yahoo_pickem_games (
          game_id, season, week, kickoff, away_team, home_team,
          yahoo_away_pct, yahoo_home_pct, market_home_probability,
          away_elo, home_elo, away_situation_points, home_situation_points,
          projected_total, source_updated_at, raw_payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET
          kickoff=excluded.kickoff, yahoo_away_pct=excluded.yahoo_away_pct,
          yahoo_home_pct=excluded.yahoo_home_pct,
          market_home_probability=excluded.market_home_probability,
          away_elo=excluded.away_elo, home_elo=excluded.home_elo,
          away_situation_points=excluded.away_situation_points,
          home_situation_points=excluded.home_situation_points,
          projected_total=excluded.projected_total,
          source_updated_at=excluded.source_updated_at,
          raw_payload=excluded.raw_payload,
          updated_at=CURRENT_TIMESTAMP
        """
        values = (
            payload["game_id"], payload["season"], payload["week"], payload["kickoff"],
            payload["away_team"], payload["home_team"], payload["yahoo_away_pct"],
            payload["yahoo_home_pct"], payload["market_home_probability"],
            payload.get("away_elo", 1500), payload.get("home_elo", 1500),
            payload.get("away_situation_points", 0), payload.get("home_situation_points", 0),
            payload.get("projected_total"), payload.get("source_updated_at"), json.dumps(payload),
        )
        with closing(self.connect()) as connection:
            connection.execute(sql, values)
            connection.commit()

    def list_games(self, season: int, week: int) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM yahoo_pickem_games WHERE season=? AND week=? ORDER BY kickoff", (season, week)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_predictions(self, recommendations: list[dict], model_version: str, strategy: str) -> None:
        sql = """
        INSERT INTO yahoo_pickem_predictions (
          game_id, model_version, strategy, model_pick, model_probability,
          crowd_pick, crowd_percentage, contrarian_edge, signal,
          confidence_points, expected_confidence_value, component_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id, model_version, strategy) DO UPDATE SET
          model_pick=excluded.model_pick, model_probability=excluded.model_probability,
          crowd_pick=excluded.crowd_pick, crowd_percentage=excluded.crowd_percentage,
          contrarian_edge=excluded.contrarian_edge, signal=excluded.signal,
          confidence_points=excluded.confidence_points,
          expected_confidence_value=excluded.expected_confidence_value,
          component_json=excluded.component_json, generated_at=CURRENT_TIMESTAMP
        """
        with closing(self.connect()) as connection:
            for row in recommendations:
                connection.execute(sql, (
                    row["game_id"], model_version, strategy, row["model_pick"], row["pick_probability"],
                    row["crowd_pick"], row["crowd_percentage"], row["contrarian_edge"], row["signal"],
                    row["confidence_points"], row["expected_confidence_value"], json.dumps(row),
                ))
            connection.commit()
