from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class CrowdRecord:
    season: int; week: int; away_team: str; home_team: str
    yahoo_away_pct: float; yahoo_home_pct: float; source: str

@dataclass(frozen=True)
class OddsRecord:
    season: int; week: int; away_team: str; home_team: str
    away_moneyline: int; home_moneyline: int
    projected_total: float | None; source: str

class CrowdProvider(Protocol):
    name: str
    def fetch(self, season: int, week: int) -> list[CrowdRecord]: ...

class OddsProvider(Protocol):
    name: str
    def fetch(self, season: int, week: int) -> list[OddsRecord]: ...
