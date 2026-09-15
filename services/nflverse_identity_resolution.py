"""Deterministic nflverse player identity resolution."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def resolve_player_identity(record: Mapping[str, Any], identities: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Resolve by nflverse player id first, then exact normalized name."""
    by_id: dict[str, Mapping[str, Any]] = {}
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    values = identities.values() if isinstance(identities, Mapping) else identities
    for identity in values:
        player_id = str(identity.get("gsis_id") or identity.get("player_id") or "").strip()
        name = _normalize(identity.get("full_name") or identity.get("player_name") or identity.get("name"))
        if player_id:
            by_id[player_id] = identity
        if name:
            by_name.setdefault(name, []).append(identity)
    player_id = str(record.get("gsis_id") or record.get("player_id") or "").strip()
    candidate = by_id.get(player_id) if player_id else None
    if candidate is None:
        matches = by_name.get(_normalize(record.get("full_name") or record.get("player_name") or record.get("name")), [])
        if len(matches) > 1:
            return {"resolved": False, "reason": "AMBIGUOUS_IDENTITY", "player_id": player_id or None}
        candidate = matches[0] if matches else None
    if candidate is None:
        return {"resolved": False, "reason": "UNRESOLVED_IDENTITY", "player_id": player_id or None}
    return {"resolved": True, "reason": None, "player_id": str(candidate.get("gsis_id") or candidate.get("player_id") or player_id), "identity": dict(candidate)}


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())