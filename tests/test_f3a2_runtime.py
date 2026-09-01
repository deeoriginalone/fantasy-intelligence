import unittest
from unittest.mock import patch
from draft_events.runtime import process_runtime_picks
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore
from draft_events.sleeper_ingestion import SleeperDraftIngestionService

class RuntimeTests(unittest.TestCase):
    @patch("draft_events.runtime.build_runtime_ingestion")
    def test_runtime_summary(self, build):
        store=InMemoryDraftEventStore()
        build.return_value=SleeperDraftIngestionService(DraftEventProcessor(store))
        payload={"event_id":"s1","pick_no":1,"round":1,"draft_slot":1,"roster_id":1,"player_id":"p1","created":1788200000000}
        result=process_runtime_picks(lambda:None,[payload],"l1","d1",[{"roster_id":1}])
        self.assertEqual(result["applied"],1)
        second=process_runtime_picks(lambda:None,[payload],"l1","d1",[{"roster_id":1}])
        self.assertEqual(second["duplicates"],1)

    def test_existing_writes_are_noops_in_runtime_contract(self):
        from draft_events.repository_integration import RepositoryCallbacks
        callbacks=RepositoryCallbacks(lambda p:True,lambda r,o:True,lambda e:None,lambda e:None)
        self.assertIsNone(callbacks.update_roster(object()))
        self.assertIsNone(callbacks.update_draft_board(object()))
