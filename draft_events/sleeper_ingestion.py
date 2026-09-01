from .providers.sleeper import from_sleeper_pick

class SleeperDraftIngestionService:
    def __init__(self, processor):
        self.processor = processor

    def process_pick(self, payload, league_id, draft_id):
        event = from_sleeper_pick(payload, league_id, draft_id)
        return self.processor.process(event)

    def process_picks(self, payloads, league_id, draft_id):
        return [self.process_pick(p, league_id, draft_id) for p in payloads]
