from contextlib import contextmanager
from copy import deepcopy

class InMemoryDraftEventStore:
    """Executable reference store. Production should implement this contract with PostgreSQL."""
    def __init__(self):
        self.events = {}
        self.selections = {}

    @contextmanager
    def transaction(self):
        snapshot = (deepcopy(self.events), deepcopy(self.selections))
        try:
            yield self
        except Exception:
            self.events, self.selections = snapshot
            raise

    def get_event(self, event_id): return self.events.get(event_id)
    def save_received(self, event):
        self.events[event.event_id] = {'event': event, 'status':'RECEIVED', 'error':None}
    def mark(self, event_id, status, error=None):
        self.events[event_id]['status'] = status; self.events[event_id]['error'] = error
    def selection_by_pick(self, draft_id, pick_number):
        return self.selections.get((draft_id, pick_number))
    def selection_by_player(self, draft_id, player_id):
        return next((v for (d,_),v in self.selections.items() if d==draft_id and v.player_id==player_id), None)
    def apply_selection(self, event): self.selections[(event.draft_id,event.pick_number)] = event
    def failed_events(self):
        return [v['event'] for v in self.events.values() if v['status']=='FAILED']
    def ordered_state(self, draft_id):
        return [v for (d,_),v in sorted(self.selections.items(), key=lambda x:x[0][1]) if d==draft_id]

class PostgresDraftEventStoreContract:
    """Required production methods; wire to the repository's existing DB helper."""
    required_methods = (
        'transaction','get_event','save_received','mark','selection_by_pick',
        'selection_by_player','apply_selection','failed_events','ordered_state'
    )
