import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from draft_events.readiness import (
    ReadinessEngine,
    component_blocked,
    component_ready,
    component_warning,
)
from services.draft_recommendation_publication import (
    DraftRecommendationPublicationService,
)
from services.readiness_report_io import load_readiness_report

NOW = datetime(2026, 9, 3, 11, 0, tzinfo=timezone.utc)


def components():
    return [
        component_ready("sleeper", "ready", observed_at=NOW),
        component_ready("draft_state", "ready", observed_at=NOW),
        component_ready("reconciliation", "ready", observed_at=NOW),
        component_ready("recommendations", "ready", observed_at=NOW),
    ]


def report(rows=None):
    return ReadinessEngine(clock=lambda: NOW).evaluate(rows or components())


class DraftRecommendationPublicationTests(unittest.TestCase):
    def setUp(self):
        self.service = DraftRecommendationPublicationService()
        self.recommendations = [
            {"player": "A", "score": 100},
            {"player": "B", "score": 95},
        ]

    def test_001_ready_publishes_all_recommendations(self):
        result = self.service.guard(self.recommendations, report())
        self.assertTrue(result.publish_allowed)
        self.assertEqual(list(result.recommendations), self.recommendations)
        self.assertEqual(result.suppressed_count, 0)

    def test_002_warning_suppresses_by_default(self):
        rows = components()
        rows[-1] = component_warning(
            "recommendations", "DEGRADED", "degraded", observed_at=NOW
        )
        result = self.service.guard(self.recommendations, report(rows))
        self.assertFalse(result.publish_allowed)
        self.assertEqual(result.recommendations, ())
        self.assertEqual(result.suppressed_count, 2)

    def test_003_blocked_reconciliation_suppresses(self):
        rows = components()
        rows[2] = component_blocked(
            "reconciliation", "RECONCILIATION_FAILED", "drift", observed_at=NOW
        )
        result = self.service.guard(self.recommendations, report(rows))
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("RECONCILIATION_FAILED", result.blockers)

    def test_004_empty_recommendations_remain_empty(self):
        result = self.service.guard([], report())
        self.assertTrue(result.publish_allowed)
        self.assertEqual(result.recommendations, ())

    def test_005_metadata_reaches_decision(self):
        result = self.service.guard(
            self.recommendations,
            report(),
            metadata={"draft_id": 7, "current_pick": 12},
        )
        self.assertEqual(result.decision.metadata["draft_id"], 7)

    def test_006_result_is_json_ready(self):
        payload = self.service.guard(self.recommendations, report()).to_dict()
        self.assertIn('"publish_allowed": true', json.dumps(payload))

    def test_007_input_list_is_not_modified(self):
        before = list(self.recommendations)
        self.service.guard(self.recommendations, report())
        self.assertEqual(self.recommendations, before)

    def test_008_readiness_json_round_trip(self):
        payload = report().to_dict()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "readiness.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_readiness_report(path)
        self.assertEqual(loaded.to_dict(), payload)


if __name__ == "__main__":
    unittest.main()
