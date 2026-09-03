"""F3-B.4 centralized readiness gate tests."""

import json
import unittest
from datetime import datetime, timedelta, timezone

from draft_events.readiness import (
    ComponentReadiness,
    ReadinessEngine,
    ReadinessLevel,
    ReadinessPolicy,
    component_blocked,
    component_ready,
    component_warning,
)

NOW = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
REQUIRED = ("sleeper", "draft_state", "reconciliation", "recommendations")


def all_ready(observed_at=NOW):
    return [
        component_ready("sleeper", "Sleeper available", observed_at=observed_at),
        component_ready("draft_state", "Draft state healthy", observed_at=observed_at),
        component_ready("reconciliation", "Reconciliation passed", observed_at=observed_at),
        component_ready("recommendations", "Recommendations healthy", observed_at=observed_at),
    ]


class ReadinessGateTests(unittest.TestCase):
    def engine(self, policy=None):
        return ReadinessEngine(policy=policy, clock=lambda: NOW)

    def test_001_everything_healthy_is_ready_and_publishable(self):
        report = self.engine().evaluate(all_ready())
        self.assertEqual(report.overall_status, "READY")
        self.assertTrue(report.publish_allowed)

    def test_002_warning_blocks_publication_by_default(self):
        components = all_ready()
        components[-1] = component_warning(
            "recommendations", "RECOMMENDATION_DEGRADED", "Recommendations are degraded", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "WARNING")
        self.assertFalse(report.publish_allowed)

    def test_003_warning_can_publish_only_when_policy_explicitly_allows_it(self):
        policy = ReadinessPolicy(warning_allows_publish=True)
        components = all_ready()
        components[1] = component_warning(
            "draft_state", "FAILED_EVENT_BACKLOG", "Non-critical failed-event backlog", observed_at=NOW
        )
        report = self.engine(policy).evaluate(components)
        self.assertEqual(report.overall_status, "WARNING")
        self.assertTrue(report.publish_allowed)

    def test_004_reconciliation_failure_blocks(self):
        components = all_ready()
        components[2] = component_blocked(
            "reconciliation", "RECONCILIATION_FAILED", "Draft state drift detected", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "BLOCKED")
        self.assertFalse(report.publish_allowed)

    def test_005_sleeper_unavailable_blocks(self):
        components = all_ready()
        components[0] = component_blocked(
            "sleeper", "SLEEPER_UNAVAILABLE", "Sleeper metadata unavailable", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "BLOCKED")

    def test_006_recommendation_engine_unavailable_blocks(self):
        components = all_ready()
        components[3] = component_blocked(
            "recommendations", "RECOMMENDATIONS_UNAVAILABLE", "Recommendation engine unavailable", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "BLOCKED")

    def test_007_multiple_warnings_remain_warning(self):
        components = all_ready()
        components[0] = component_warning("sleeper", "SLOW_SOURCE", "Sleeper response slow", observed_at=NOW)
        components[3] = component_warning(
            "recommendations", "LOW_CANDIDATE_COUNT", "Candidate count is low", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "WARNING")
        self.assertEqual(len(report.issues), 2)

    def test_008_warning_plus_blocker_is_blocked(self):
        components = all_ready()
        components[0] = component_warning("sleeper", "SLOW_SOURCE", "Sleeper response slow", observed_at=NOW)
        components[2] = component_blocked(
            "reconciliation", "RECONCILIATION_FAILED", "Drift detected", observed_at=NOW
        )
        report = self.engine().evaluate(components)
        self.assertEqual(report.overall_status, "BLOCKED")

    def test_009_missing_required_component_blocks(self):
        report = self.engine().evaluate(all_ready()[:-1])
        self.assertEqual(report.overall_status, "BLOCKED")
        self.assertEqual(report.component("recommendations").level, ReadinessLevel.BLOCKED)
        self.assertIn("REQUIRED_COMPONENT_MISSING", {issue.code for issue in report.issues})

    def test_010_duplicate_component_is_rejected(self):
        components = all_ready() + [component_ready("sleeper", "duplicate", observed_at=NOW)]
        with self.assertRaisesRegex(ValueError, "Duplicate readiness component"):
            self.engine().evaluate(components)

    def test_011_stale_component_blocks(self):
        policy = ReadinessPolicy(maximum_age_seconds={"sleeper": 60})
        components = all_ready()
        components[0] = component_ready(
            "sleeper", "Old Sleeper result", observed_at=NOW - timedelta(seconds=61)
        )
        report = self.engine(policy).evaluate(components)
        self.assertEqual(report.overall_status, "BLOCKED")
        self.assertIn("COMPONENT_STALE", {issue.code for issue in report.issues})

    def test_012_fresh_component_passes(self):
        policy = ReadinessPolicy(maximum_age_seconds={"sleeper": 60})
        components = all_ready()
        components[0] = component_ready(
            "sleeper", "Fresh Sleeper result", observed_at=NOW - timedelta(seconds=60)
        )
        report = self.engine(policy).evaluate(components)
        self.assertEqual(report.overall_status, "READY")

    def test_013_missing_freshness_timestamp_blocks_when_policy_requires_age(self):
        policy = ReadinessPolicy(maximum_age_seconds={"sleeper": 60})
        components = all_ready()
        components[0] = component_ready("sleeper", "No timestamp")
        report = self.engine(policy).evaluate(components)
        self.assertIn("COMPONENT_TIMESTAMP_MISSING", {issue.code for issue in report.issues})
        self.assertEqual(report.overall_status, "BLOCKED")

    def test_014_future_timestamp_warns(self):
        policy = ReadinessPolicy(maximum_age_seconds={"sleeper": 60})
        components = all_ready()
        components[0] = component_ready(
            "sleeper", "Future timestamp", observed_at=NOW + timedelta(seconds=5)
        )
        report = self.engine(policy).evaluate(components)
        self.assertEqual(report.overall_status, "WARNING")
        self.assertIn("COMPONENT_TIMESTAMP_IN_FUTURE", {issue.code for issue in report.issues})

    def test_015_json_serialization_contains_authoritative_decision(self):
        payload = self.engine().evaluate(all_ready()).to_dict()
        encoded = json.dumps(payload)
        self.assertIn('"overall_status": "READY"', encoded)
        self.assertTrue(payload["publish_allowed"])
        self.assertEqual(sorted(payload["components"]), sorted(REQUIRED))

    def test_016_engine_is_read_only_for_input_components(self):
        components = all_ready()
        before = tuple(components)
        self.engine().evaluate(components)
        self.assertEqual(tuple(components), before)


if __name__ == "__main__":
    unittest.main()
