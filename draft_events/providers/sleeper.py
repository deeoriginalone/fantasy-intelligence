from datetime import datetime, timezone
from ..models import DraftEvent, ValidationError

def _timestamp(value):
    if value is None: return datetime.now(timezone.utc)
    value=float(value)
    if value > 10_000_000_000: value /= 1000
    return datetime.fromtimestamp(value, timezone.utc)

def from_sleeper_pick(payload, league_id, draft_id):
    """Translate a Sleeper pick payload without coupling core processing to Sleeper."""
    metadata=payload.get('metadata') or {}
    player_id=payload.get('player_id') or metadata.get('player_id')
    pick=payload.get('pick_no')
    rnd=payload.get('round')
    round_pick=payload.get('draft_slot')
    roster=payload.get('roster_id')
    event_id=str(payload.get('event_id') or f"sleeper:{draft_id}:{pick}")
    return DraftEvent(
        event_id=event_id, league_id=str(league_id), draft_id=str(draft_id),
        pick_number=int(pick), round=int(rnd), round_pick=int(round_pick),
        roster_id=str(roster) if roster is not None else None,
        owner_id=str(payload.get('picked_by')) if payload.get('picked_by') is not None else None,
        player_id=str(player_id or ''), event_type='selection',
        occurred_at=_timestamp(payload.get('created')), source='sleeper', raw_payload=dict(payload)
    )
