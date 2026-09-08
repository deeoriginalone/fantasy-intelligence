"""F3-B.2 large-batch reconciliation tests."""

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from draft_events.models import DraftEvent
from draft_events.reconciliation import DraftReconciler
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore

BATCH_SIZE = 1000
ROSTER_COUNT = 12


def make_event(index: int, draft_id: str = "f3b2-draft") -> DraftEvent:
    pick = index + 1
    return DraftEvent(
        event_id=f"f3b2:{draft_id}:{pick}",
        league_id="f3b2-league",
        draft_id=draft_id,
        pick_number=pick,
        round=(index // ROSTER_COUNT) + 1,
        round_pick=(index % ROSTER_COUNT) + 1,
        roster_id=f"roster-{(index % ROSTER_COUNT) + 1}",
        owner_id=None,
        player_id=f"player-{pick}",
        event_type="selection",
        occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(seconds=index),
        source="f3-b2-generated-source",
        raw_payload={"fixture": True, "pick_number": pick},
    )


def make_batch(size=BATCH_SIZE, draft_id="f3b2-draft"):
    return [make_event(i, draft_id=draft_id) for i in range(size)]


def issue_codes(report):
    return {issue.code for issue in report.issues}


class LargeBatchReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.draft_id = "f3b2-draft"
        self.source = make_batch(draft_id=self.draft_id)
        self.store = InMemoryDraftEventStore()
        self.processor = DraftEventProcessor(self.store)
        self.reconciler = DraftReconciler(self.store)

    def ingest(self, events):
        results = [self.processor.process(event) for event in events]
        self.assertFalse([result for result in results if result.status == "FAILED"])
        return results

    def test_001_exact_1000_pick_match_passes(self):
        self.ingest(self.source)
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.source_count, BATCH_SIZE)
        self.assertEqual(report.event_count, BATCH_SIZE)
        self.assertEqual(report.selection_count, BATCH_SIZE)
        self.assertEqual(report.issues, ())

    def test_002_missing_local_pick_is_reported(self):
        missing_index = 499
        self.ingest(self.source[:missing_index] + self.source[missing_index + 1:])
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertFalse(report.passed)
        self.assertIn(500, report.missing_selection_pick_numbers)
        self.assertIn("MISSING_LOCAL_SELECTION", issue_codes(report))
        self.assertIn("SELECTION_COUNT_MISMATCH", issue_codes(report))

    def test_003_extra_local_pick_is_reported(self):
        self.ingest(self.source)
        extra = make_event(BATCH_SIZE, draft_id=self.draft_id)
        self.ingest([extra])
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertFalse(report.passed)
        self.assertIn(BATCH_SIZE + 1, report.extra_selection_pick_numbers)
        self.assertIn("EXTRA_LOCAL_SELECTION", issue_codes(report))

    def test_004_player_mismatch_is_reported(self):
        local = list(self.source)
        local[249] = replace(local[249], player_id="local-wrong-player")
        self.ingest(local)
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertFalse(report.passed)
        self.assertIn("FIELD_MISMATCH_PLAYER_ID", issue_codes(report))

    def test_005_roster_mismatch_is_reported(self):
        local = list(self.source)
        local[99] = replace(local[99], roster_id="wrong-roster")
        self.ingest(local)
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertIn("FIELD_MISMATCH_ROSTER_ID", issue_codes(report))

    def test_006_event_id_mismatch_is_reported(self):
        local = list(self.source)
        local[749] = replace(local[749], event_id="local-alternate-event")
        self.ingest(local)
        report = self.reconciler.reconcile(self.source, self.draft_id)
        codes = issue_codes(report)
        self.assertIn("FIELD_MISMATCH_EVENT_ID", codes)
        self.assertIn("MISSING_LOCAL_EVENT", codes)

    def test_007_non_applied_event_is_reported(self):
        self.ingest(self.source)
        target = self.source[399]
        self.store.mark(target.event_id, "FAILED", "injected state drift")
        report = self.reconciler.reconcile(self.source, self.draft_id)
        self.assertIn("EVENT_NOT_APPLIED", issue_codes(report))

    def test_008_duplicate_source_pick_is_reported(self):
        self.ingest(self.source)
        duplicate = replace(
            self.source[0],
            event_id="source-duplicate-pick",
            player_id="source-duplicate-player",
        )
        report = self.reconciler.reconcile(self.source + [duplicate], self.draft_id)
        self.assertIn(1, report.source_duplicate_pick_numbers)
        self.assertIn("SOURCE_DUPLICATE_PICK_NUMBER", issue_codes(report))

    def test_009_duplicate_source_player_is_reported(self):
        self.ingest(self.source)
        duplicate = replace(
            self.source[1],
            event_id="source-duplicate-player-event",
            pick_number=BATCH_SIZE + 1,
            round=84,
            round_pick=5,
            player_id=self.source[0].player_id,
        )
        report = self.reconciler.reconcile(self.source + [duplicate], self.draft_id)
        self.assertIn(self.source[0].player_id, report.source_duplicate_player_ids)
        self.assertIn("SOURCE_DUPLICATE_PLAYER", issue_codes(report))

    def test_010_foreign_draft_source_event_is_reported(self):
        self.ingest(self.source)
        foreign = make_event(0, draft_id="different-draft")
        report = self.reconciler.reconcile(self.source + [foreign], self.draft_id)
        self.assertIn("SOURCE_DRAFT_ID_MISMATCH", issue_codes(report))

    def test_011_report_serializes_to_json_ready_dictionary(self):
        self.ingest(self.source)
        payload = self.reconciler.reconcile(self.source, self.draft_id).to_dict()
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["source_count"], BATCH_SIZE)
        self.assertEqual(payload["issues"], [])


if __name__ == "__main__":
    unittest.main()
