from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DraftPick:
    pick_no: int
    round_no: int
    roster_id: str
    player_id: str
    player_name: str = ""
    position: str = ""
    team: str = ""

    def validate(self) -> None:
        if self.pick_no < 1:
            raise ValueError("pick_no must be at least 1")
        if self.round_no < 1:
            raise ValueError("round_no must be at least 1")
        if not self.roster_id.strip():
            raise ValueError("roster_id is required")
        if not self.player_id.strip():
            raise ValueError("player_id is required")


@dataclass(frozen=True)
class Recommendation:
    player_id: str
    reason: str
    score: Optional[float] = None


@dataclass
class DraftState:
    teams: int
    rounds: int
    picks: List[DraftPick] = field(default_factory=list)
    drafted_player_ids: set[str] = field(default_factory=set)
    roster_player_ids: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def expected_picks(self) -> int:
        return self.teams * self.rounds

    @property
    def next_pick_no(self) -> int:
        return len(self.picks) + 1

    @property
    def complete(self) -> bool:
        return len(self.picks) == self.expected_picks

    def apply_pick(self, pick: DraftPick) -> None:
        pick.validate()
        if self.complete:
            raise ValueError("draft is already complete")
        if pick.pick_no != self.next_pick_no:
            raise ValueError(
                f"expected pick {self.next_pick_no}, received {pick.pick_no}"
            )
        if pick.player_id in self.drafted_player_ids:
            raise ValueError(f"player already drafted: {pick.player_id}")
        expected_round = ((pick.pick_no - 1) // self.teams) + 1
        if pick.round_no != expected_round:
            raise ValueError(
                f"pick {pick.pick_no} belongs to round {expected_round}, "
                f"received round {pick.round_no}"
            )
        self.picks.append(pick)
        self.drafted_player_ids.add(pick.player_id)
        self.roster_player_ids.setdefault(pick.roster_id, []).append(pick.player_id)
