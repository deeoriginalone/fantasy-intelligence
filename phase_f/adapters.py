from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol

from .models import DraftState, Recommendation


class RecommendationAdapter(Protocol):
    def recommend(self, state: DraftState) -> Recommendation | None:
        ...


class NoOpRecommendationAdapter:
    def recommend(self, state: DraftState) -> Recommendation | None:
        return None


class CallableRecommendationAdapter:
    def __init__(self, target: str):
        if ":" not in target:
            raise ValueError("adapter must use module:function format")
        module_name, function_name = target.split(":", 1)
        module = import_module(module_name)
        function = getattr(module, function_name, None)
        if not callable(function):
            raise ValueError(f"adapter target is not callable: {target}")
        self._function: Callable = function

    def recommend(self, state: DraftState) -> Recommendation | None:
        value = self._function(state)
        if value is None:
            return None
        if isinstance(value, Recommendation):
            return value
        if isinstance(value, dict):
            return Recommendation(
                player_id=str(value["player_id"]),
                reason=str(value.get("reason", "")),
                score=(None if value.get("score") is None else float(value["score"])),
            )
        raise TypeError("recommendation adapter must return dict, Recommendation, or None")
