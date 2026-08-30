"""Yahoo Pick'em intelligence engine for Fantasy Intelligence.

No network calls are made here. The engine consumes normalized game records from
JSON, database rows, or a future permitted data-provider adapter.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import exp, pow
from typing import Iterable, Optional


@dataclass(frozen=True)
class PickemSettings:
    market_weight: float = 0.55
    elo_weight: float = 0.25
    situation_weight: float = 0.20
    home_field_elo: float = 37.5
    situation_scale: float = 6.5
    strategy: str = "balanced"

    def validate(self) -> None:
        if abs(self.market_weight + self.elo_weight + self.situation_weight - 1.0) > 0.0001:
            raise ValueError("Pick'em model weights must total 1.0")
        if self.situation_scale <= 0:
            raise ValueError("situation_scale must be greater than zero")
        if self.strategy not in {"protect-lead", "balanced", "gain-ground"}:
            raise ValueError("Unknown Pick'em strategy")


@dataclass(frozen=True)
class PickemGame:
    game_id: str
    season: int
    week: int
    kickoff: str
    away_team: str
    home_team: str
    yahoo_away_pct: float
    yahoo_home_pct: float
    market_home_probability: float
    away_elo: float = 1500.0
    home_elo: float = 1500.0
    away_situation_points: float = 0.0
    home_situation_points: float = 0.0
    projected_total: Optional[float] = None
    source_updated_at: Optional[str] = None

    def validate(self) -> None:
        if not self.game_id or not self.away_team or not self.home_team:
            raise ValueError("game_id and both teams are required")
        if self.away_team == self.home_team:
            raise ValueError("away and home teams must differ")
        if abs(self.yahoo_away_pct + self.yahoo_home_pct - 1.0) > 0.02:
            raise ValueError("Yahoo percentages must total approximately 1.0")
        for name, value in (
            ("yahoo_away_pct", self.yahoo_away_pct),
            ("yahoo_home_pct", self.yahoo_home_pct),
            ("market_home_probability", self.market_home_probability),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _strategy_weights(settings: PickemSettings) -> tuple[float, float, float]:
    if settings.strategy == "protect-lead":
        return 0.70, 0.20, 0.10
    if settings.strategy == "gain-ground":
        return 0.45, 0.25, 0.30
    return settings.market_weight, settings.elo_weight, settings.situation_weight


def calculate_game(game: PickemGame, settings: PickemSettings = PickemSettings()) -> dict:
    settings.validate()
    game.validate()
    elo_home = 1 / (1 + pow(10, -(game.home_elo - game.away_elo + settings.home_field_elo) / 400))
    situational_home = 1 / (1 + exp(-(game.home_situation_points - game.away_situation_points) / settings.situation_scale))
    market_w, elo_w, situation_w = _strategy_weights(settings)
    home_probability = _clamp(
        game.market_home_probability * market_w
        + elo_home * elo_w
        + situational_home * situation_w
    )
    home_selected = home_probability >= 0.5
    model_pick = game.home_team if home_selected else game.away_team
    pick_probability = home_probability if home_selected else 1 - home_probability
    crowd_home = game.yahoo_home_pct >= game.yahoo_away_pct
    crowd_pick = game.home_team if crowd_home else game.away_team
    crowd_percentage = game.yahoo_home_pct if home_selected else game.yahoo_away_pct
    crowd_side_probability = home_probability if crowd_home else 1 - home_probability
    max_crowd = max(game.yahoo_home_pct, game.yahoo_away_pct)
    differs = model_pick != crowd_pick

    if max_crowd >= 0.70 and crowd_side_probability < 0.60:
        signal = "PUBLIC TRAP"
    elif pick_probability >= 0.85:
        signal = "ELITE PICK"
    elif pick_probability >= 0.72 and differs:
        signal = "STRONG VALUE"
    elif crowd_percentage <= 0.35 and pick_probability >= 0.50:
        signal = "UPSET VALUE"
    elif pick_probability >= 0.72:
        signal = "STRONG PICK"
    else:
        signal = "COIN FLIP"

    return {
        **asdict(game),
        "elo_home_probability": elo_home,
        "situation_home_probability": situational_home,
        "model_home_probability": home_probability,
        "model_pick": model_pick,
        "pick_probability": pick_probability,
        "crowd_pick": crowd_pick,
        "crowd_percentage": crowd_percentage,
        "contrarian_edge": pick_probability - crowd_percentage,
        "signal": signal,
    }


def build_week(games: Iterable[PickemGame], settings: PickemSettings = PickemSettings()) -> list[dict]:
    seen: set[str] = set()
    calculated: list[dict] = []
    for game in games:
        if game.game_id in seen:
            raise ValueError(f"Duplicate game_id: {game.game_id}")
        seen.add(game.game_id)
        calculated.append(calculate_game(game, settings))
    ordered = sorted(calculated, key=lambda row: (row["pick_probability"], row["game_id"]))
    points = {row["game_id"]: index + 1 for index, row in enumerate(ordered)}
    for row in calculated:
        row["confidence_points"] = points[row["game_id"]]
        row["expected_confidence_value"] = row["pick_probability"] * row["confidence_points"]
    return sorted(calculated, key=lambda row: row["confidence_points"], reverse=True)


def summarize_week(recommendations: list[dict]) -> dict:
    if not recommendations:
        return {"lock": None, "best_value": None, "best_upset": None, "public_trap": None, "expected_correct": 0.0}
    by_conf = sorted(recommendations, key=lambda x: x["pick_probability"], reverse=True)
    by_edge = sorted(recommendations, key=lambda x: x["contrarian_edge"], reverse=True)
    return {
        "lock": by_conf[0],
        "best_value": by_edge[0],
        "best_upset": next((x for x in by_edge if x["crowd_percentage"] <= 0.35), None),
        "public_trap": next((x for x in recommendations if x["signal"] == "PUBLIC TRAP"), None),
        "expected_correct": sum(x["pick_probability"] for x in recommendations),
    }


POSITION_CAPS = {"QB": 0.08, "RB": 0.10, "WR": 0.08, "TE": 0.08, "DST": 0.15, "K": 0.12}


def fantasy_game_script_adjustment(position: str, team_win_probability: float, projected_total: Optional[float] = None) -> dict:
    position = position.upper()
    if position not in POSITION_CAPS:
        raise ValueError(f"Unsupported position: {position}")
    total_effect = _clamp(((projected_total or 42) - 42) / 100, -0.04, 0.05)
    if position == "DST":
        adjustment = (team_win_probability - 0.5) * 0.30
        reason = "Win probability supports sack and turnover opportunity" if team_win_probability >= 0.6 else "Game script reduces defensive upside"
    elif position == "RB":
        adjustment = (team_win_probability - 0.5) * 0.16
        reason = "Positive game script supports rushing volume" if team_win_probability >= 0.6 else "Trailing risk may reduce rushing volume"
    elif position in {"QB", "WR", "TE"}:
        adjustment = (0.5 - team_win_probability) * 0.08 + total_effect
        reason = "Potential trailing script supports pass volume" if team_win_probability < 0.45 else "Scoring environment drives the adjustment"
    else:
        adjustment = total_effect
        reason = "Projected scoring environment drives kicker adjustment"
    cap = POSITION_CAPS[position]
    return {"adjustment": _clamp(adjustment, -cap, cap), "cap": cap, "reason": reason}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
