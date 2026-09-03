"""F3-C.1 publication readiness integration tests."""

import json
import unittest
from datetime import datetime, timezone

from draft_events.readiness import (
    ReadinessEngine,
    ReadinessPolicy,
    component_blocked,
    component_ready,
    component_warning,
)
from services.publication_gate import (
    PublicationBlockedError,
    PublicationGate,
)

NOW = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)


def ready_components():
    return [
        component_ready("sleeper", "Sleeper available", observed_at=NOW),
        component_ready("draft_state", "Draft state healthy", observed_at=NOW),
        component_ready("reconciliation", "Reconciliation passed", observed_at=NOW),
        component_ready("recommendations", "Recommendations healthy", observed_at=NOW),
    ]


def report_for(components, policy=None):
    return ReadinessEngine(policy=policy, clock=lambda: NOW).evaluate(components)


class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = PublicationGate()

    def test_001_ready_allows_publication(self):
        decision = self.gate.decide(
            report_for(ready_components()), workflow="draft_recommendations"
        )
        self.assertTrue(decision.publish_allowed)
        self.assertEqual(decision.overall_status, "READY")
        self.assertEqual(decision.reason_codes, ())

    def test_002_warning_is_blocked_by_default(self):
        components = ready_components()
        components[-1] = component_warning(
            "recommendations",
            "RECOMMENDATION_DEGRADED",
            "Recommendations are degraded",
            observed_at=NOW,
        )
        decision = self.gate.decide(
            report_for(components), workflow="draft_recommendations"
        )
        self.assertFalse(decision.publish_allowed)
        self.assertEqual(decision.overall_status, "WARNING")
        self.assertIn("RECOMMENDATION_DEGRADED", decision.reason_codes)

    def test_003_blocked_reconciliation_denies_publication(self):
        components = ready_components()
        components[2] = component_blocked(
            "reconciliation",
            "RECONCILIATION_FAILED",
            "Draft drift detected",
            observed_at=NOW,
        )
        decision = self.gate.decide(
            report_for(components), workflow="draft_recommendations"
        )
        self.assertFalse(decision.publish_allowed)
        self.assertIn("RECONCILIATION_FAILED", decision.reason_codes)

    def test_004_warning_override_allows_publication(self):
        policy = ReadinessPolicy(warning_allows_publish=True)
        components = ready_components()
        components[1] = component_warning(
            "draft_state",
            "FAILED_EVENT_BACKLOG",
            "Non-critical failed event backlog",
            observed_at=NOW,
        )
        decision = self.gate.decide(
            report_for(components, policy), workflow="weekly_report"
        )
        self.assertTrue(decision.publish_allowed)
        self.assertEqual(decision.overall_status, "WARNING")

    def test_005_missing_required_component_denies_publication(self):
        decision = self.gate.decide(
            report_for(ready_components()[:-1]), workflow="draft_recommendations"
        )
        self.assertFalse(decision.publish_allowed)
        self.assertIn("REQUIRED_COMPONENT_MISSING", decision.reason_codes)

    def test_006_require_ready_returns_decision_when_allowed(self):
        decision = self.gate.require_ready(
            report_for(ready_components()), workflow="draft_recommendations"
        )
        self.assertTrue(decision.publish_allowed)

    def test_007_require_ready_raises_with_decision_when_blocked(self):
        components = ready_components()
        components[0] = component_blocked(
            "sleeper", "SLEEPER_UNAVAILABLE", "Sleeper unavailable", observed_at=NOW
        )
        with self.assertRaises(PublicationBlockedError) as caught:
            self.gate.require_ready(
                report_for(components), workflow="draft_recommendations"
            )
        self.assertFalse(caught.exception.decision.publish_allowed)
        self.assertIn("SLEEPER_UNAVAILABLE", str(caught.exception))

    def test_008_execute_calls_publisher_exactly_once_when_ready(self):
        calls = []

        def publisher(value, suffix=""):
            calls.append((value, suffix))
            return f"{value}{suffix}"

        decision, result = self.gate.execute(
            report_for(ready_components()),
            workflow="draft_recommendations",
            publisher=publisher,
            args=("player-1",),
            kwargs={"suffix": "-published"},
        )
        self.assertTrue(decision.publish_allowed)
        self.assertEqual(result, "player-1-published")
        self.assertEqual(calls, [("player-1", "-published")])

    def test_009_execute_never_calls_publisher_when_blocked(self):
        calls = []
        components = ready_components()
        components[2] = component_blocked(
            "reconciliation", "RECONCILIATION_FAILED", "Drift", observed_at=NOW
        )

        with self.assertRaises(PublicationBlockedError):
            self.gate.execute(
                report_for(components),
                workflow="draft_recommendations",
                publisher=lambda: calls.append("called"),
            )
        self.assertEqual(calls, [])

    def test_010_decision_preserves_component_statuses(self):
        decision = self.gate.decide(
            report_for(ready_components()), workflow="draft_recommendations"
        )
        self.assertEqual(decision.component_statuses["sleeper"], "READY")
        self.assertEqual(decision.component_statuses["recommendations"], "READY")

    def test_011_decision_metadata_is_preserved(self):
        decision = self.gate.decide(
            report_for(ready_components()),
            workflow="draft_recommendations",
            metadata={"draft_id": "d1", "candidate_count": 12},
        )
        self.assertEqual(decision.metadata["draft_id"], "d1")
        self.assertEqual(decision.metadata["candidate_count"], 12)

    def test_012_decision_is_json_ready(self):
        payload = self.gate.decide(
            report_for(ready_components()), workflow="draft_recommendations"
        ).to_dict()
        encoded = json.dumps(payload)
        self.assertIn('"publish_allowed": true', encoded)
        self.assertEqual(payload["workflow"], "draft_recommendations")

    def test_013_empty_workflow_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "workflow must be a non-empty string"):
            self.gate.decide(report_for(ready_components()), workflow="  ")

    def test_014_duplicate_reason_codes_are_deduplicated(self):
        components = ready_components()
        components[0] = component_blocked(
            "sleeper", "SOURCE_UNAVAILABLE", "Source unavailable", observed_at=NOW
        )
        components[2] = component_blocked(
            "reconciliation", "SOURCE_UNAVAILABLE", "Source unavailable", observed_at=NOW
        )
        decision = self.gate.decide(
            report_for(components), workflow="draft_recommendations"
        )
        self.assertEqual(decision.reason_codes.count("SOURCE_UNAVAILABLE"), 1)

    def test_015_gate_does_not_modify_readiness_report(self):
        report = report_for(ready_components())
        before = report.to_dict()
        self.gate.decide(report, workflow="draft_recommendations")
        self.assertEqual(report.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
