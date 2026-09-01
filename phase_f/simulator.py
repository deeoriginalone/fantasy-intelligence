from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .adapters import NoOpRecommendationAdapter, RecommendationAdapter
from .models import DraftPick, DraftState, Recommendation


@dataclass
class SimulationResult:
    state: DraftState
    recommendations: List[Recommendation | None] = field(default_factory=list)


class DraftSimulator:
    def __init__(
        self,
        teams: int,
        rounds: int,
        recommendation_adapter: RecommendationAdapter | None = None,
    ):
        if teams < 2:
            raise ValueError("teams must be at least 2")
        if rounds < 1:
            raise ValueError("rounds must be at least 1")
        self.state = DraftState(teams=teams, rounds=rounds)
        self.adapter = recommendation_adapter or NoOpRecommendationAdapter()

    def replay(self, picks: Iterable[DraftPick]) -> SimulationResult:
        recommendations: List[Recommendation | None] = []
        for pick in picks:
            self.state.apply_pick(pick)
            recommendations.append(self.adapter.recommend(self.state))
        return SimulationResult(self.state, recommendations)
