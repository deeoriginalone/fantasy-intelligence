"""Flask Blueprint for Yahoo Pick'em intelligence."""
from __future__ import annotations
import json
import os
from pathlib import Path
from flask import Blueprint, current_app, jsonify, render_template, request
from yahoo_pickem import PickemGame, PickemSettings, build_week, summarize_week
from pickem_store import PickemStore

pickem_bp = Blueprint("pickem", __name__)
MODEL_VERSION = "pickem-v1.0.0"


def _db_path() -> str:
    configured = current_app.config.get("PICKEM_DATABASE_PATH")
    if configured:
        return configured
    return str(Path(current_app.root_path) / "data" / "fantasy_intelligence.db")


def _store() -> PickemStore:
    store = PickemStore(_db_path())
    store.migrate()
    return store


def _settings() -> PickemSettings:
    strategy = request.args.get("strategy", "balanced")
    return PickemSettings(strategy=strategy)


def _game_from_row(row: dict) -> PickemGame:
    allowed = PickemGame.__dataclass_fields__.keys()
    return PickemGame(**{key: row[key] for key in allowed if key in row})


def build_pickem_context(season: int, week: int, strategy: str = "balanced") -> dict:
    store = _store()
    rows = store.list_games(season, week)
    games = [_game_from_row(row) for row in rows]
    settings = PickemSettings(strategy=strategy)
    recommendations = build_week(games, settings)
    store.save_predictions(recommendations, MODEL_VERSION, strategy)
    return {
        "pickem_recommendations": recommendations,
        "pickem_summary": summarize_week(recommendations),
        "pickem_strategy": strategy,
        "pickem_season": season,
        "pickem_week": week,
        "pickem_model_version": MODEL_VERSION,
    }


@pickem_bp.get("/pickem")
def pickem_page():
    season = request.args.get("season", type=int) or current_app.config.get("NFL_SEASON", 2026)
    week = request.args.get("week", type=int) or current_app.config.get("NFL_WEEK", 1)
    strategy = request.args.get("strategy", "balanced")
    return render_template("pickem.html", **build_pickem_context(season, week, strategy))


@pickem_bp.get("/api/pickem")
def pickem_api():
    season = request.args.get("season", type=int) or current_app.config.get("NFL_SEASON", 2026)
    week = request.args.get("week", type=int) or current_app.config.get("NFL_WEEK", 1)
    strategy = request.args.get("strategy", "balanced")
    return jsonify(build_pickem_context(season, week, strategy))


@pickem_bp.post("/api/pickem/games")
def upsert_pickem_game():
    payload = request.get_json(silent=True) or {}
    try:
        game = PickemGame(**payload)
        game.validate()
        _store().upsert_game(payload)
    except (TypeError, KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "game_id": game.game_id}), 201


@pickem_bp.get("/api/pickem/health")
def pickem_health():
    return jsonify({"ok": True, "model_version": MODEL_VERSION, "database": _db_path()})
