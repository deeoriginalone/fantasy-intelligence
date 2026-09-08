"""F3-B.3 read-only live Sleeper reconciliation tests."""

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from draft_events.live_reconciliation import LiveSleeperReconciliationService
from draft_events.models import DraftEvent
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore

BATCH_SIZE = 1000
ROSTER_COUNT = 12


def make_event(index: int, draft_id="f3b3-draft"):
    pick = index + 1
    return DraftEvent(
        event_id=f"f3b3:{draft_id}:{pick}",
        league_id="f3b3-league",
        draft_id=draft_id,
        pick_number=pick,
        round=(index // ROSTER_COUNT) + 1,
        round_pick=(index % ROSTER_COUNT) + 1,
        roster_id=f"roster-{(index % ROSTER_COUNT) + 1}",
        owner_id=None,
        player_id=f"player-{pick}",
        event_type="selection",
        occurred_at=datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(seconds=index),
        source="sleeper",
        raw_payload={"pick_no": pick},
    )


def make_payload(event):
    return {"event": event}


def normalize(payload, league_id, draft_id):
    event = payload["event"]
    if event.league_id != league_id or event.draft_id != draft_id:
        return replace(event, league_id=league_id, draft_id=draft_id)
    return event


class LiveSleeperReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.draft_id = "f3b3-draft"
        self.league_id = "f3b3-league"
        self.source = [make_event(i, self.draft_id) for i in range(BATCH_SIZE)]
        self.store = InMemoryDraftEventStore()
        self.processor = DraftEventProcessor(self.store)

    def service(self, *, status="in_progress", payloads=None, metadata=None, normalizer=normalize):
        if payloads is None:
            payloads = [make_payload(event) for event in self.source]
        if metadata is None:
            metadata = {"draft_id": self.draft_id, "status": status}
        return LiveSleeperReconciliationService(
            get_draft=lambda draft_id: metadata,
            get_draft_picks=lambda draft_id: payloads,
            normalize_pick=normalizer,
            store=self.store,
        )

    def ingest(self, events):
        results = [self.processor.process(event) for event in events]
        self.assertFalse([result for result in results if result.status == "FAILED"])

    def test_001_pre_draft_zero_picks_is_ready_waiting(self):
        report = self.service(status="pre_draft", payloads=[]).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertEqual(report.operational_status, "READY_WAITING_FOR_PICKS")
        self.assertTrue(report.passed)

    def test_002_pre_draft_zero_source_with_local_state_is_blocked(self):
        self.ingest([self.source[0]])
        report = self.service(status="pre_draft", payloads=[]).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertEqual(report.issues[0].code, "LOCAL_STATE_PRESENT_BEFORE_SOURCE_PICKS")

    def test_003_exact_1000_pick_live_match_passes(self):
        self.ingest(self.source)
        report = self.service().run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertEqual(report.operational_status, "PASS")
        self.assertEqual(report.source_pick_count, BATCH_SIZE)
        self.assertTrue(report.reconciliation.passed)

    def test_004_missing_local_pick_is_blocked(self):
        self.ingest(self.source[:-1])
        report = self.service().run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertIn("MISSING_LOCAL_SELECTION", {issue.code for issue in report.issues})

    def test_005_extra_local_pick_is_blocked(self):
        self.ingest(self.source + [make_event(BATCH_SIZE, self.draft_id)])
        report = self.service().run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertIn("EXTRA_LOCAL_SELECTION", {issue.code for issue in report.issues})

    def test_006_player_mismatch_is_blocked(self):
        local = list(self.source)
        local[300] = replace(local[300], player_id="wrong-player")
        self.ingest(local)
        report = self.service().run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertIn("FIELD_MISMATCH_PLAYER_ID", {issue.code for issue in report.issues})

    def test_007_metadata_unavailable_is_blocked(self):
        report = self.service(metadata=None).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertIn(report.operational_status, {"PASS", "BLOCKED"})
        service = LiveSleeperReconciliationService(
            get_draft=lambda draft_id: None,
            get_draft_picks=lambda draft_id: [],
            normalize_pick=normalize,
            store=self.store,
        )
        report = service.run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertEqual(report.issues[0].code, "DRAFT_METADATA_UNAVAILABLE")

    def test_008_metadata_draft_id_mismatch_is_blocked(self):
        report = self.service(metadata={"draft_id": "wrong", "status": "complete"}).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertEqual(report.issues[0].code, "DRAFT_METADATA_ID_MISMATCH")

    def test_009_normalization_failure_is_blocked(self):
        def failing_normalizer(payload, league_id, draft_id):
            if payload["event"].pick_number == 500:
                raise ValueError("injected normalization failure")
            return normalize(payload, league_id, draft_id)

        report = self.service(normalizer=failing_normalizer).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertEqual(report.operational_status, "BLOCKED")
        self.assertEqual(report.issues[0].code, "PICK_NORMALIZATION_FAILED")

    def test_010_complete_draft_match_passes(self):
        self.ingest(self.source)
        report = self.service(status="complete").run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        self.assertEqual(report.draft_status, "complete")
        self.assertEqual(report.operational_status, "PASS")

    def test_011_report_is_json_ready(self):
        report = self.service(status="pre_draft", payloads=[]).run(
            league_id=self.league_id, draft_id=self.draft_id
        )
        payload = report.to_dict()
        self.assertEqual(payload["operational_status"], "READY_WAITING_FOR_PICKS")
        self.assertEqual(payload["issues"], [])

    def test_012_service_does_not_write_to_local_store(self):
        before_events = dict(self.store.events)
        before_selections = dict(self.store.selections)
        self.service().run(league_id=self.league_id, draft_id=self.draft_id)
        self.assertEqual(self.store.events, before_events)
        self.assertEqual(self.store.selections, before_selections)


if __name__ == "__main__":
    unittest.main()
