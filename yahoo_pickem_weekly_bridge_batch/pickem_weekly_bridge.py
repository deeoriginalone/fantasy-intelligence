"""Bridge Pick'em SQLite recommendations into Flask Weekly Intelligence context."""
from __future__ import annotations
from pathlib import Path
from pickem_store import PickemStore
from yahoo_pickem import PickemGame, PickemSettings, build_week, summarize_week

MODEL_VERSION = "pickem-v1.0.1"


def default_pickem_db(project_root=None):
    root = Path(project_root or Path(__file__).resolve().parent)
    return str(root / "data" / "fantasy_intelligence.db")


def build_weekly_pickem_context(week, season=2026, strategy="balanced", database_path=None):
    store = PickemStore(database_path or default_pickem_db())
    store.migrate()
    rows = store.list_games(int(season), int(week))
    allowed = PickemGame.__dataclass_fields__.keys()
    games = [PickemGame(**{k: row[k] for k in allowed if k in row}) for row in rows]
    recommendations = build_week(games, PickemSettings(strategy=strategy))
    if recommendations:
        store.save_predictions(recommendations, MODEL_VERSION, strategy)
    return {
        "pickem_recommendations": recommendations,
        "pickem_summary": summarize_week(recommendations),
        "pickem_strategy": strategy,
        "pickem_week": int(week),
        "pickem_season": int(season),
        "pickem_model_version": MODEL_VERSION,
    }
