from .models import ProcessingResult, ValidationError

class DraftEventProcessor:
    def __init__(self, store, player_exists=lambda _: True, owner_exists=lambda r,o: True,
                 roster_update=lambda e: None, draft_board_update=lambda e: None):
        self.store=store; self.player_exists=player_exists; self.owner_exists=owner_exists
        self.roster_update=roster_update; self.draft_board_update=draft_board_update

    def process(self, event):
        existing=self.store.get_event(event.event_id)
        if existing and existing['status']=='APPLIED':
            return ProcessingResult(event.event_id,'APPLIED','idempotent no-op',True,False)
        try:
            with self.store.transaction():
                if not existing: self.store.save_received(event)
                event.validate()
                if not self.player_exists(event.player_id): raise ValidationError('unknown player_id')
                if not self.owner_exists(event.roster_id,event.owner_id): raise ValidationError('unknown roster_id or owner_id')
                pick=self.store.selection_by_pick(event.draft_id,event.pick_number)
                if pick and pick.event_id != event.event_id: raise ValidationError('duplicate pick_number')
                player=self.store.selection_by_player(event.draft_id,event.player_id)
                if player and player.event_id != event.event_id: raise ValidationError('player already selected')
                self.store.mark(event.event_id,'VALIDATED')
                self.store.apply_selection(event)
                self.roster_update(event)
                self.draft_board_update(event)
                self.store.mark(event.event_id,'APPLIED')
            return ProcessingResult(event.event_id,'APPLIED','selection applied',False,True)
        except Exception as exc:
            if not self.store.get_event(event.event_id): self.store.save_received(event)
            self.store.mark(event.event_id,'FAILED',str(exc))
            return ProcessingResult(event.event_id,'FAILED',str(exc),False,False)

    def replay_failed(self):
        return [self.process(e) for e in list(self.store.failed_events())]
