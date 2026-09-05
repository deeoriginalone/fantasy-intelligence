"""F3-B.3.1 production-store parity validation.

The PostgreSQL store is loaded only from the explicit environment variable
F3_POSTGRES_STORE_FACTORY using module:symbol syntax. Tests never guess the
repository's connection factory or credentials.
"""

import importlib
import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from draft_events.models import DraftEvent
from draft_events.reconciliation import DraftReconciler
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore, PostgresDraftEventStoreContract

FACTORY_ENV = "F3_POSTGRES_STORE_FACTORY"
BATCH_SIZE = int(os.environ.get("F3_PARITY_BATCH_SIZE", "1000"))
REPLAY_PASSES = int(os.environ.get("F3_PARITY_REPLAY_PASSES", "10"))
ROSTER_COUNT = 12


def load_symbol(spec):
    if ":" not in spec:
        raise ValueError(f"{FACTORY_ENV} must use module:symbol syntax")
    module_name, symbol_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), symbol_name)


def build_postgres_store():
    spec = os.environ.get(FACTORY_ENV)
    if not spec:
        raise unittest.SkipTest(
            f"{FACTORY_ENV} is not set; PostgreSQL parity cannot run without an explicit store factory"
        )
    factory = load_symbol(spec)
    store = factory()
    missing = [
        method for method in PostgresDraftEventStoreContract.required_methods
        if not callable(getattr(store, method, None))
    ]
    if missing:
        raise AssertionError(f"PostgreSQL store is missing required methods: {missing}")
    return store


def make_event(index, draft_id):
    pick = index + 1
    return DraftEvent(
        event_id=f"f3b31:{draft_id}:{pick}",
        league_id=f"league-{draft_id}",
        draft_id=draft_id,
        pick_number=pick,
        round=(index // ROSTER_COUNT) + 1,
        round_pick=(index % ROSTER_COUNT) + 1,
        roster_id=f"roster-{(index % ROSTER_COUNT) + 1}",
        owner_id=None,
        player_id=f"f3b31-player-{pick}",
        event_type="selection",
        occurred_at=datetime(2026, 9, 3, tzinfo=timezone.utc) + timedelta(seconds=index),
        source="f3-b3-1-parity",
        raw_payload={"fixture": True, "pick_number": pick},
    )


def make_batch(draft_id, size=BATCH_SIZE):
    return [make_event(index, draft_id) for index in range(size)]


def process_batch(processor, events):
    results = [processor.process(event) for event in events]
    return {
        "applied": sum(1 for result in results if result.applied),
        "duplicates": sum(1 for result in results if result.duplicate),
        "failed": sum(1 for result in results if result.status == "FAILED"),
    }


def snapshot(store, draft_id):
    return tuple(
        (
            event.event_id,
            event.pick_number,
            event.round,
            event.round_pick,
            event.roster_id,
            event.owner_id,
            event.player_id,
            event.event_type,
        )
        for event in store.ordered_state(draft_id)
    )


def assert_event_metadata(test_case, actual, expected):
    test_case.assertEqual(actual.event_id, expected.event_id)
    test_case.assertEqual(actual.league_id, expected.league_id)
    test_case.assertEqual(actual.draft_id, expected.draft_id)
    test_case.assertEqual(actual.pick_number, expected.pick_number)
    test_case.assertEqual(actual.round, expected.round)
    test_case.assertEqual(actual.round_pick, expected.round_pick)
    test_case.assertEqual(actual.roster_id, expected.roster_id)
    test_case.assertEqual(actual.owner_id, expected.owner_id)
    test_case.assertEqual(actual.player_id, expected.player_id)
    test_case.assertEqual(actual.event_type, expected.event_type)
    test_case.assertEqual(actual.occurred_at, expected.occurred_at)
    test_case.assertEqual(actual.source, expected.source)
    test_case.assertEqual(actual.raw_payload, expected.raw_payload)


def cleanup_store(store, draft_id):
    """Use an explicit test cleanup hook; never guess SQL or delete methods."""
    cleanup = getattr(store, "cleanup_test_draft", None)
    if not callable(cleanup):
        raise unittest.SkipTest(
            "PostgreSQL store must expose cleanup_test_draft(draft_id) for isolated parity tests"
        )
    cleanup(draft_id)


class StoreContractMixin:
    store_kind = None

    def create_store(self):
        raise NotImplementedError

    def setUp(self):
        self.draft_id = f"f3b31-{self.store_kind}-{self._testMethodName}"
        self.store = self.create_store()
        if self.store_kind == "postgres":
            cleanup_store(self.store, self.draft_id)
        self.processor = DraftEventProcessor(self.store)
        self.batch = make_batch(self.draft_id)

    def tearDown(self):
        if getattr(self, "store_kind", None) == "postgres" and hasattr(self, "store"):
            cleanup_store(self.store, self.draft_id)

    def test_001_contract_methods_exist(self):
        missing = [
            method for method in PostgresDraftEventStoreContract.required_methods
            if not callable(getattr(self.store, method, None))
        ]
        self.assertEqual(missing, [])

    def test_002_baseline_large_batch_import(self):
        metrics = process_batch(self.processor, self.batch)
        self.assertEqual(metrics, {"applied": BATCH_SIZE, "duplicates": 0, "failed": 0})
        ordered = self.store.ordered_state(self.draft_id)
        self.assertEqual(len(ordered), BATCH_SIZE)
        assert_event_metadata(self, ordered[0], self.batch[0])

    def test_003_identical_replay_is_idempotent(self):
        process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        metrics = process_batch(self.processor, self.batch)
        self.assertEqual(metrics, {"applied": 0, "duplicates": BATCH_SIZE, "failed": 0})
        self.assertEqual(snapshot(self.store, self.draft_id), before)

    def test_004_repeated_replay_is_stable(self):
        process_batch(self.processor, self.batch)
        baseline = snapshot(self.store, self.draft_id)
        for replay_number in range(REPLAY_PASSES):
            with self.subTest(replay_number=replay_number + 1):
                metrics = process_batch(self.processor, self.batch)
                self.assertEqual(metrics["duplicates"], BATCH_SIZE)
                self.assertEqual(metrics["failed"], 0)
                self.assertEqual(snapshot(self.store, self.draft_id), baseline)

    def test_005_partial_replay_adds_only_missing(self):
        prefix = BATCH_SIZE // 4
        first = process_batch(self.processor, self.batch[:prefix])
        second = process_batch(self.processor, self.batch)
        self.assertEqual(first["applied"], prefix)
        self.assertEqual(second["duplicates"], prefix)
        self.assertEqual(second["applied"], BATCH_SIZE - prefix)
        self.assertEqual(len(self.store.ordered_state(self.draft_id)), BATCH_SIZE)

    def test_006_duplicate_pick_is_failed_and_selection_is_stable(self):
        process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        conflict = replace(
            self.batch[0],
            event_id=f"f3b31:{self.draft_id}:conflicting-event",
            player_id="f3b31-conflicting-player",
        )
        result = self.processor.process(conflict)
        self.assertEqual(result.status, "FAILED")
        self.assertIn("duplicate pick_number", result.message)
        self.assertEqual(snapshot(self.store, self.draft_id), before)

    def test_007_duplicate_player_is_failed_and_selection_is_stable(self):
        process_batch(self.processor, self.batch)
        before = snapshot(self.store, self.draft_id)
        conflict = replace(
            make_event(BATCH_SIZE, self.draft_id),
            player_id=self.batch[0].player_id,
        )
        result = self.processor.process(conflict)
        self.assertEqual(result.status, "FAILED")
        self.assertIn("player already selected", result.message)
        self.assertEqual(snapshot(self.store, self.draft_id), before)

    def test_008_reconciliation_exact_match(self):
        process_batch(self.processor, self.batch)
        report = DraftReconciler(self.store).reconcile(self.batch, self.draft_id)
        self.assertTrue(report.passed, report.to_dict())

    def test_009_reconciliation_detects_missing_local_pick(self):
        process_batch(self.processor, self.batch[:-1])
        report = DraftReconciler(self.store).reconcile(self.batch, self.draft_id)
        codes = {issue.code for issue in report.issues}
        self.assertIn("MISSING_LOCAL_SELECTION", codes)
        self.assertIn("SELECTION_COUNT_MISMATCH", codes)


class InMemoryParityReferenceTests(StoreContractMixin, unittest.TestCase):
    store_kind = "memory"

    def create_store(self):
        return InMemoryDraftEventStore()


class PostgreSQLParityTests(StoreContractMixin, unittest.TestCase):
    store_kind = "postgres"

    def create_store(self):
        return build_postgres_store()


if __name__ == "__main__":
    unittest.main()
