import unittest
from draft_events.repository_integration import RepositoryCallbacks
from draft_events.sleeper_ingestion import SleeperDraftIngestionService
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore

class IntegrationTests(unittest.TestCase):
    def test_repository_callbacks(self):
        calls=[]
        c=RepositoryCallbacks(lambda p:p=="p1",lambda r,o:r=="r1",lambda e:calls.append("roster"),lambda e:calls.append("board"))
        self.assertTrue(c.player_exists("p1"))
        self.assertTrue(c.owner_exists("r1",None))
        c.update_roster(object()); c.update_draft_board(object())
        self.assertEqual(calls,["roster","board"])

    def test_sleeper_ingestion(self):
        store=InMemoryDraftEventStore()
        svc=SleeperDraftIngestionService(DraftEventProcessor(store))
        payload={"event_id":"s1","pick_no":1,"round":1,"draft_slot":1,"roster_id":1,"player_id":"p1","created":1788200000000}
        result=svc.process_pick(payload,"l1","d1")
        self.assertEqual(result.status,"APPLIED")
        self.assertEqual(store.ordered_state("d1")[0].source,"sleeper")

    def test_sleeper_batch_is_idempotent(self):
        store=InMemoryDraftEventStore()
        svc=SleeperDraftIngestionService(DraftEventProcessor(store))
        payload={"event_id":"s1","pick_no":1,"round":1,"draft_slot":1,"roster_id":1,"player_id":"p1","created":1788200000000}
        first=svc.process_picks([payload],"l1","d1")[0]
        second=svc.process_picks([payload],"l1","d1")[0]
        self.assertTrue(first.applied)
        self.assertTrue(second.duplicate)
