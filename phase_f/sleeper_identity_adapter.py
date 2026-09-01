from __future__ import annotations
from .models import DraftPick
from .player_mapper import MappingStatus, PlayerMappingError

class SleeperDraftEventAdapter:
    def __init__(self, identity_resolver):
        self.identity_resolver=identity_resolver

    def translate(self,event):
        identity=self.identity_resolver.resolve_sleeper_id(event.get("player_id"))
        if identity.status is not MappingStatus.MATCHED:
            raise PlayerMappingError(f"{identity.status.value}: {identity.reason}")
        return DraftPick(
            pick_no=int(event["pick_no"]),
            round_no=int(event["round"]),
            roster_id=str(event["roster_id"]),
            player_id=str(identity.local_player_id),
            player_name=identity.player_name or str(event.get("metadata",{}).get("first_name","") + " " + event.get("metadata",{}).get("last_name","")).strip(),
            position=identity.position or str(event.get("metadata",{}).get("position", "")),
            team=identity.nfl_team or str(event.get("metadata",{}).get("team", "")),
        )
