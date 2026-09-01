from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class ValidationError(ValueError):
    pass

@dataclass(frozen=True)
class DraftEvent:
    event_id: str
    league_id: str
    draft_id: str
    pick_number: int
    round: int
    round_pick: int
    player_id: str
    event_type: str
    occurred_at: datetime
    source: str
    roster_id: Optional[str] = None
    owner_id: Optional[str] = None
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        required = {
            'event_id': self.event_id, 'league_id': self.league_id,
            'draft_id': self.draft_id, 'player_id': self.player_id,
            'source': self.source
        }
        missing = [k for k, v in required.items() if not str(v).strip()]
        if missing: raise ValidationError('missing required fields: ' + ', '.join(missing))
        if self.event_type != 'selection': raise ValidationError('unsupported event_type')
        if self.pick_number < 1 or self.round < 1 or self.round_pick < 1:
            raise ValidationError('pick_number, round, and round_pick must be positive')
        if not (self.roster_id or self.owner_id):
            raise ValidationError('roster_id or owner_id is required')
        if self.occurred_at.tzinfo is None:
            raise ValidationError('occurred_at must be timezone-aware')

@dataclass(frozen=True)
class ProcessingResult:
    event_id: str
    status: str
    message: str
    duplicate: bool = False
    applied: bool = False
