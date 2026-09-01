from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class MappingStatus(str, Enum):
    MATCHED="MATCHED"
    AMBIGUOUS="AMBIGUOUS"
    UNMATCHED="UNMATCHED"
    CONFLICT="CONFLICT"

@dataclass(frozen=True)
class PlayerIdentity:
    status: MappingStatus
    sleeper_player_id: str
    local_player_id: str | None = None
    player_name: str | None = None
    position: str | None = None
    nfl_team: str | None = None
    reason: str = ""

class PlayerMappingError(RuntimeError):
    pass

class PlayerMapper:
    def __init__(self, repository):
        self.repository=repository

    def resolve_sleeper_id(self, sleeper_player_id):
        sid=str(sleeper_player_id or "").strip()
        if not sid:
            return PlayerIdentity(MappingStatus.UNMATCHED,sid,reason="missing Sleeper player ID")
        rows=self.repository.find_by_sleeper_id(sid)
        if not rows:
            return PlayerIdentity(MappingStatus.UNMATCHED,sid,reason="no mapping row")
        local_ids={str(r[0]) for r in rows if r[0] is not None}
        names={str(r[1]) for r in rows if r[1]}
        positions={str(r[2]) for r in rows if r[2]}
        teams={str(r[3]) for r in rows if r[3]}
        if len(local_ids)>1:
            return PlayerIdentity(MappingStatus.CONFLICT,sid,reason="Sleeper ID maps to multiple local IDs")
        if not local_ids:
            return PlayerIdentity(MappingStatus.UNMATCHED,sid,player_name=next(iter(names),None),reason="mapping has no local ID")
        if len(names)>1 or len(positions)>1 or len(teams)>1:
            return PlayerIdentity(MappingStatus.CONFLICT,sid,reason="mapping attributes conflict")
        return PlayerIdentity(MappingStatus.MATCHED,sid,next(iter(local_ids)),next(iter(names),None),next(iter(positions),None),next(iter(teams),None),"exact Sleeper ID mapping")

    def require_local_id(self, sleeper_player_id):
        result=self.resolve_sleeper_id(sleeper_player_id)
        if result.status is not MappingStatus.MATCHED:
            raise PlayerMappingError(f"{result.status.value}: {result.reason}")
        return result
