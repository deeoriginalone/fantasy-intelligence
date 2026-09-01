from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping

@dataclass(frozen=True)
class NormalizedRecommendation:
    player_id: str
    reason: str
    score: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> "NormalizedRecommendation":
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("adapter must return a mapping or NormalizedRecommendation")
        player_id = str(value.get("player_id", "")).strip()
        if not player_id:
            raise ValueError("recommendation requires player_id")
        score = value.get("score")
        return cls(player_id, str(value.get("reason", "")), None if score is None else float(score), dict(value.get("metadata") or {}))
