#!/usr/bin/env python3
"""Create an auditable publication decision from a readiness-report JSON file."""

import argparse
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
from services.publication_gate import PublicationGate


def parse_readiness(payload):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--output-dir", default="audit/f3_c1/publication")
    args = parser.parse_args()

    readiness = parse_readiness(
        json.loads(Path(args.readiness).read_text(encoding="utf-8"))
    )
    decision = PublicationGate().decide(readiness, workflow=args.workflow)
    payload = decision.to_dict()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "publication_decision.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (output_dir / "PUBLICATION_DECISION.md").write_text(
        "# F3-C.1 Publication Decision\n\n"
        f"- Workflow: `{decision.workflow}`\n"
        f"- Readiness: **{decision.overall_status}**\n"
        f"- Publication allowed: **{decision.publish_allowed}**\n"
        f"- Decided at: `{decision.decided_at.isoformat()}`\n\n"
        "## Reasons\n\n"
        + ("None\n" if not decision.reason_codes else "\n".join(
            f"- `{code}`" for code in decision.reason_codes
        ) + "\n"),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, default=str))
    return 0 if decision.publish_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
