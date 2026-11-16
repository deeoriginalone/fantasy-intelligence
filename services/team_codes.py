"""Explicit NFL team-code mapping between Sleeper, nflverse, FantasyPros, and JerryGM.

Repository canonical codes follow Sleeper (``LAR``, ``JAX``, ``WAS``). nflverse and JerryGM
spell the Rams ``LA``; FantasyPros spells Jacksonville ``JAC``. Unknown codes never resolve.
"""
from __future__ import annotations

from typing import Any

CANONICAL_TEAMS = frozenset({
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
})
ALIASES_TO_CANONICAL = {
    "LA": "LAR", "STL": "LAR", "JAC": "JAX", "WSH": "WAS", "OAK": "LV", "LVR": "LV", "SD": "LAC", "KAN": "KC",
    "GNB": "GB", "NWE": "NE", "NEP": "NE", "NOR": "NO", "NOS": "NO", "SFO": "SF", "TAM": "TB",
}
CANONICAL_TO_NFLVERSE = {"LAR": "LA"}


def canonical_team(value: Any) -> str | None:
    """Return the repository (Sleeper) team code, or None when the code is not a current NFL team."""
    code = str(value or "").strip().upper()
    code = ALIASES_TO_CANONICAL.get(code, code)
    return code if code in CANONICAL_TEAMS else None


def nflverse_team(value: Any) -> str | None:
    """Return the nflverse spelling used by nflverse releases and the JerryGM API."""
    code = canonical_team(value)
    return CANONICAL_TO_NFLVERSE.get(code, code) if code else None


def jerrygm_defense_id(value: Any) -> str | None:
    """JerryGM's documented team-defense identity (``ids.gsis`` = ``DST-<nflverse code>``)."""
    code = nflverse_team(value)
    return f"DST-{code}" if code else None
