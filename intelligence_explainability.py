"""Deterministic, serializable explanations for Fantasy Intelligence decisions."""
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

@dataclass(frozen=True)
class Component:
    name: str
    value: float
    weight: float
    contribution: float
    source_timestamp: Optional[str] = None


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def build_explanation(*, pick: str, probability: float, components: Iterable[Dict[str, Any]],
                      crowd_percentage: Optional[float] = None,
                      warnings: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    if not pick:
        raise ValueError("pick is required")
    probability = float(probability)
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1")

    normalized: List[Component] = []
    for raw in components:
        value = float(raw["value"])
        weight = float(raw["weight"])
        normalized.append(Component(
            name=str(raw["name"]), value=value, weight=weight,
            contribution=value * weight,
            source_timestamp=raw.get("source_timestamp"),
        ))
    weight_sum = sum(c.weight for c in normalized)
    if normalized and abs(weight_sum - 1.0) > 1e-6:
        raise ValueError("component weights must total 1.0")

    edge = None if crowd_percentage is None else probability - float(crowd_percentage)
    reason = f"{pick} is projected at {_pct(probability)}."
    if edge is not None:
        reason += f" Model-to-crowd edge: {edge * 100:+.1f} points."

    return {
        "pick": pick,
        "probability": probability,
        "crowd_percentage": crowd_percentage,
        "contrarian_edge": edge,
        "components": [asdict(c) for c in normalized],
        "reason": reason,
        "warnings": sorted(set(warnings or [])),
    }
