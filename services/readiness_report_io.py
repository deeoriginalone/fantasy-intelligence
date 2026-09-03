"""Load a serialized F3-B.4 readiness report for route-level enforcement."""

import json
from datetime import datetime
from pathlib import Path

from draft_events.readiness import (
    ComponentReadiness,
    ReadinessIssue,
    ReadinessLevel,
    ReadinessPolicy,
    ReadinessReport,
)


def load_readiness_report(path: str | Path) -> ReadinessReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    components = {}
    for name, component in payload["components"].items():
        issues = tuple(
            ReadinessIssue(
                code=issue["code"],
                message=issue["message"],
                level=ReadinessLevel.parse(issue["level"]),
                details=issue.get("details", {}),
            )
            for issue in component.get("issues", [])
        )
        components[name] = ComponentReadiness(
            name=name,
            level=ReadinessLevel.parse(component["level"]),
            summary=component["summary"],
            issues=issues,
            observed_at=(
                datetime.fromisoformat(component["observed_at"])
                if component.get("observed_at") else None
            ),
            metadata=component.get("metadata", {}),
        )
    policy_payload = payload.get("policy", {})
    policy = ReadinessPolicy(
        required_components=tuple(policy_payload.get("required_components", components)),
        warning_allows_publish=bool(policy_payload.get("warning_allows_publish", False)),
        maximum_age_seconds=policy_payload.get("maximum_age_seconds", {}),
    )
    issues = tuple(
        ReadinessIssue(
            code=issue["code"],
            message=issue["message"],
            level=ReadinessLevel.parse(issue["level"]),
            details=issue.get("details", {}),
        )
        for issue in payload.get("issues", [])
    )
    return ReadinessReport(
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        overall_level=ReadinessLevel.parse(payload["overall_status"]),
        publish_allowed=bool(payload["publish_allowed"]),
        components=components,
        issues=issues,
        policy=policy,
    )
