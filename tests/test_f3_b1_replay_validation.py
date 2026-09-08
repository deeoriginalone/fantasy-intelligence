"""F3-B.1 large-batch replay validation.

These tests exercise the existing DraftEventProcessor and
InMemoryDraftEventStore contracts. They do not modify production code or
require live Sleeper data or PostgreSQL.
"""

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from draft_events.models import DraftEvent
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore


DEFAULT_BATCH_SIZE = 1000
REPLAY_PASSES = 10
ROSTER_COUNT = 12


def make_event(index: int, *, draft_id: str = "f3b1-large-draft") -> DraftEvent:
    """Create one deterministic, schema-valid selection event.

    ``index`` is zero-based. Persisted pick numbers are one-based.
    Player IDs and event IDs remain unique inside a draft.
    """
    pick_number = index + 1
    round_number = (index // ROSTER_COUNT) + 1
    round_pick = (index % ROSTER_COUNT) + 1
    roster_number = (index % ROSTER_COUNT) + 1
    occurred_at = datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(seconds=index)

    return DraftEvent(
        event_id=f"f3b1:{draft_id}:{pick_number}",
        league_id="f3b1-large-league",
        draft_id=draft_id,
        pick_number=pick_number,
        round=round_number,
        round_pick=round_pick,
        roster_id=f"roster-{roster_number}",
        owner_id=None,
        player_id=f"player-{pick_number}",
        event_type="selection",
        occurred_at=occurred_at,
        source="f3-b1-generated-fixture",
        raw_payload={
            "fixture": True,
            "scenario": "large-batch-replay",
            "pick_number": pick_number,
        },
    )


def make_batch(size: int = DEFAULT_BATCH_SIZE, *, draft_id: str = "f3b1-large-draft"):
    return [make_event(i, draft_id=draft_id) for i in range(size)]


def snapshot(store: InMemoryDraftEventStore, draft_id: str):
    """Return a stable representation used to detect state drift."""
    ordered = store.ordered_state(draft_id)
    return tuple(
        (
            event.event_id,
            event.pick_number,
            event.round,
            event.round_pick,
            event.roster_id,
            event.owner_id,
            event.player_id,
            event.source,
            repr(event.raw_payload),
        )
        for event in ordered
    )


def process_batch(processor: DraftEventProcessor, events):
    results = [processor.process(event) for event in events]
    return {
        "processed": len(results),
        "applied": sum(1 for result in results if result.applied),
        "duplicates": sum(1 for result in results if result.duplicate),
        "failed": sum(1 for result in results if result.status == "FAILED"),
        "results": results,
    }


class LargeBatchReplayValidationTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryDraftEventStore()
        self.processor = DraftEventProcessor(self.store)
        self.draft_id = "f3b1-large-draft"
        self.batch = make_batch(draft_id=self.draft_id)

    def assert_store_counts(self, expected):
        self.assertEqual(len(self.store.events), expected)
        self.assertEqual(len(self.store.selections), expected)
        self.assertEqual(len(self.store.ordered_state(self.draft_id)), expected)

    def test_001_baseline_large_batch_import(self):
        metrics = process_batch(self.processor, self.batch)

        self.assertEqual(metrics["processed"], DEFAULT_BATCH_SIZE)
        self.assertEqual(metrics["applied"], DEFAULT_BATCH_SIZE)
        self.assertEqual(metrics["duplicates"], 0)
        self.assertEqual(metrics["failed"], 0)
        self.assert_store_counts(DEFAULT_BATCH_SIZE)
        self.assertEqual(
            [event.pick_number for event in self.store.ordered_state(self.draft_id)],
            list(range(1, DEFAULT_BATCH_SIZE + 1)),
        )

    def test_002_identical_replay_is_idempotent(self):
        first = process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        second = process_batch(self.processor, self.batch)
        after = snapshot(self.store, self.draft_id)

        self.assertEqual(first["applied"], DEFAULT_BATCH_SIZE)
        self.assertEqual(second["applied"], 0)
        self.assertEqual(second["duplicates"], DEFAULT_BATCH_SIZE)
        self.assertEqual(second["failed"], 0)
        self.assertEqual(before, after)
        self.assert_store_counts(DEFAULT_BATCH_SIZE)

    def test_003_ten_replays_do_not_change_state(self):
        process_batch(self.processor, self.batch)
        baseline = snapshot(self.store, self.draft_id)

        for replay_number in range(1, REPLAY_PASSES + 1):
            with self.subTest(replay_number=replay_number):
                metrics = process_batch(self.processor, self.batch)
                self.assertEqual(metrics["applied"], 0)
                self.assertEqual(metrics["duplicates"], DEFAULT_BATCH_SIZE)
                self.assertEqual(metrics["failed"], 0)
                self.assertEqual(snapshot(self.store, self.draft_id), baseline)
                self.assert_store_counts(DEFAULT_BATCH_SIZE)

    def test_004_partial_prefix_then_complete_batch_adds_only_missing_events(self):
        prefix_size = DEFAULT_BATCH_SIZE // 4
        prefix = self.batch[:prefix_size]

        first = process_batch(self.processor, prefix)
        prefix_snapshot = snapshot(self.store, self.draft_id)
        second = process_batch(self.processor, self.batch)

        self.assertEqual(first["applied"], prefix_size)
        self.assertEqual(second["duplicates"], prefix_size)
        self.assertEqual(second["applied"], DEFAULT_BATCH_SIZE - prefix_size)
        self.assertEqual(second["failed"], 0)
        self.assertEqual(snapshot(self.store, self.draft_id)[:prefix_size], prefix_snapshot)
        self.assert_store_counts(DEFAULT_BATCH_SIZE)

    def test_005_reverse_order_import_reconstructs_pick_order(self):
        metrics = process_batch(self.processor, reversed(self.batch))

        self.assertEqual(metrics["applied"], DEFAULT_BATCH_SIZE)
        self.assertEqual(metrics["failed"], 0)
        self.assertEqual(
            [event.pick_number for event in self.store.ordered_state(self.draft_id)],
            list(range(1, DEFAULT_BATCH_SIZE + 1)),
        )

    def test_006_conflicting_event_id_for_existing_pick_fails_without_state_drift(self):
        process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        conflict = replace(
            make_event(0, draft_id=self.draft_id),
            event_id="f3b1:conflict:event-id",
            player_id="f3b1:conflict:player",
        )

        result = self.processor.process(conflict)

        self.assertEqual(result.status, "FAILED")
        self.assertIn("duplicate pick_number", result.message)
        self.assertEqual(snapshot(self.store, self.draft_id), before)
        self.assertEqual(len(self.store.selections), DEFAULT_BATCH_SIZE)
        self.assertEqual(
            len(self.store.ordered_state(self.draft_id)),
            DEFAULT_BATCH_SIZE,
        )
        self.assertEqual(len(self.store.events), DEFAULT_BATCH_SIZE + 1)
        self.assertEqual(self.store.get_event(conflict.event_id)["status"], "FAILED")

    def test_007_conflicting_player_for_new_pick_fails_without_selection_drift(self):
        process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        conflict = replace(
            make_event(DEFAULT_BATCH_SIZE, draft_id=self.draft_id),
            player_id=self.batch[0].player_id,
        )

        result = self.processor.process(conflict)

        self.assertEqual(result.status, "FAILED")
        self.assertIn("player already selected", result.message)
        self.assertEqual(snapshot(self.store, self.draft_id), before)
        self.assertEqual(len(self.store.selections), DEFAULT_BATCH_SIZE)
        self.assertEqual(len(self.store.events), DEFAULT_BATCH_SIZE + 1)
        self.assertEqual(self.store.get_event(conflict.event_id)["status"], "FAILED")

    def test_008_mid_batch_callback_failure_rolls_back_failed_selection_then_replays(self):
        failure_pick = DEFAULT_BATCH_SIZE // 2
        gate = {"fail": True}

        def roster_update(event):
            if gate["fail"] and event.pick_number == failure_pick:
                raise RuntimeError("f3-b1 injected callback failure")

        processor = DraftEventProcessor(self.store, roster_update=roster_update)
        first = process_batch(processor, self.batch)

        self.assertEqual(first["applied"], DEFAULT_BATCH_SIZE - 1)
        self.assertEqual(first["failed"], 1)
        self.assertEqual(len(self.store.selections), DEFAULT_BATCH_SIZE - 1)
        self.assertEqual(self.store.get_event(f"f3b1:{self.draft_id}:{failure_pick}")["status"], "FAILED")

        gate["fail"] = False
        replay_results = processor.replay_failed()

        self.assertEqual(len(replay_results), 1)
        self.assertTrue(replay_results[0].applied)
        self.assertEqual(replay_results[0].status, "APPLIED")
        self.assert_store_counts(DEFAULT_BATCH_SIZE)


if __name__ == "__main__":
    unittest.main()
