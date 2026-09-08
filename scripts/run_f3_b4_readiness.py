#!/usr/bin/env python3
"""Evaluate readiness from an explicit JSON component file."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from draft_events.readiness import (
    ComponentReadiness,
    ReadinessEngine,
    ReadinessIssue,
    ReadinessLevel,
    ReadinessPolicy,
)


def parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


def load_component(payload):
    issues = tuple(
        ReadinessIssue(
            code=issue["code"],
            message=issue["message"],
            level=ReadinessLevel.parse(issue["level"]),
            details=issue.get("details", {}),
        )
        for issue in payload.get("issues", [])
    )
    return ComponentReadiness(
        name=payload["name"],
        level=ReadinessLevel.parse(payload["level"]),
        summary=payload["summary"],
        issues=issues,
        observed_at=parse_datetime(payload.get("observed_at")),
        metadata=payload.get("metadata", {}),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON file containing policy and components")
    parser.add_argument("--output-dir", default="audit/f3_b4/readiness")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    policy_payload = payload.get("policy", {})
    policy = ReadinessPolicy(
        required_components=tuple(policy_payload.get(
            "required_components",
            ("sleeper", "draft_state", "reconciliation", "recommendations"),
        )),
        warning_allows_publish=bool(policy_payload.get("warning_allows_publish", False)),
        maximum_age_seconds=policy_payload.get("maximum_age_seconds", {}),
    )
    report = ReadinessEngine(policy=policy).evaluate(
        load_component(component) for component in payload["components"]
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_payload = report.to_dict()
    (output_dir / "readiness.json").write_text(
        json.dumps(report_payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (output_dir / "READINESS.md").write_text(
        "# F3-B.4 Readiness Report\n\n"
        f"- Overall status: **{report.overall_status}**\n"
        f"- Publication allowed: **{report.publish_allowed}**\n"
        f"- Generated at: `{report.generated_at.isoformat()}`\n\n"
        "## Components\n\n"
        + "\n".join(
            f"- **{name}**: {component.level.name} - {component.summary}"
            for name, component in sorted(report.components.items())
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report_payload, indent=2, default=str))
    return 0 if report.publish_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
