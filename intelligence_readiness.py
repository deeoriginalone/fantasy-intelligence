"""Readiness scoring and publication gates for weekly intelligence."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_WEIGHTS = {
    "schedule": 0.15,
    "market": 0.30,
    "ratings": 0.20,
    "injuries": 0.15,
    "weather": 0.15,
    "validation": 0.05,
}

@dataclass(frozen=True)
class ReadinessResult:
    score: int
    status: str
    publishable: bool
    blockers: List[str]
    warnings: List[str]
    components: Dict[str, float]
    evaluated_at: str


def calculate_readiness(components: Dict[str, Any], *, blockers: Optional[Iterable[str]] = None,
                        warnings: Optional[Iterable[str]] = None,
                        weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    weights = dict(weights or DEFAULT_WEIGHTS)
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError("readiness weights must total 1.0")
    normalized = {}
    for name in weights:
        value = float(components.get(name, 0.0))
        normalized[name] = max(0.0, min(1.0, value))
    score = round(100 * sum(normalized[k] * weights[k] for k in weights))
    blocker_list = sorted(set(blockers or []))
    warning_list = sorted(set(warnings or []))
    status = "READY" if score >= 90 else "CAUTION" if score >= 75 else "INCOMPLETE"
    publishable = score >= 75 and not blocker_list
    result = ReadinessResult(
        score=score, status=status, publishable=publishable,
        blockers=blocker_list, warnings=warning_list, components=normalized,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )
    return asdict(result)


def validate_weekly_inputs(games: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    blockers, warnings = [], []
    seen = set()
    for index, game in enumerate(games, start=1):
        identity = (game.get("season"), game.get("week"), game.get("away_team"), game.get("home_team"))
        if identity in seen:
            blockers.append(f"duplicate game at row {index}: {identity}")
        seen.add(identity)
        if game.get("market_probability_home") is None:
            blockers.append(f"missing market probability at row {index}")
        else:
            p = float(game["market_probability_home"])
            if not 0 <= p <= 1:
                blockers.append(f"invalid market probability at row {index}")
        ya, yh = game.get("yahoo_percentage_away"), game.get("yahoo_percentage_home")
        if ya is None or yh is None:
            warnings.append(f"missing Yahoo percentages at row {index}")
        elif abs(float(ya) + float(yh) - 1.0) > 0.02:
            blockers.append(f"Yahoo percentages do not sum to approximately 100% at row {index}")
    if not seen:
        blockers.append("no games loaded")
    return {"blockers": sorted(set(blockers)), "warnings": sorted(set(warnings))}
