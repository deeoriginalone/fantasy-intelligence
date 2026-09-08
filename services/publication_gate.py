"""F3-C.1 publication readiness enforcement.

This module converts an authoritative F3-B.4 ReadinessReport into an immutable
publication decision. It does not generate, mutate, or publish recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping, TypeVar

from draft_events.readiness import ReadinessReport

T = TypeVar("T")


@dataclass(frozen=True)
class PublicationDecision:
    workflow: str
    overall_status: str
    publish_allowed: bool
    decided_at: datetime
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    component_statuses: Mapping[str, str] = field(default_factory=dict)
    readiness_generated_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "overall_status": self.overall_status,
            "publish_allowed": self.publish_allowed,
            "decided_at": self.decided_at.isoformat(),
            "reason_codes": list(self.reason_codes),
            "component_statuses": dict(self.component_statuses),
            "readiness_generated_at": (
                self.readiness_generated_at.isoformat()
                if self.readiness_generated_at else None
            ),
            "metadata": dict(self.metadata),
        }


class PublicationBlockedError(RuntimeError):
    def __init__(self, decision: PublicationDecision):
        self.decision = decision
        reasons = ", ".join(decision.reason_codes) or decision.overall_status
        super().__init__(
            f"Publication blocked for workflow {decision.workflow!r}: {reasons}"
        )


class PublicationGate:
    """Fail-closed publication control backed by a ReadinessReport."""

    def decide(
        self,
        readiness_report: ReadinessReport,
        *,
        workflow: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> PublicationDecision:
        if not workflow or not workflow.strip():
            raise ValueError("workflow must be a non-empty string")

        component_statuses = {
            name: component.level.name
            for name, component in sorted(readiness_report.components.items())
        }
        reason_codes = tuple(dict.fromkeys(
            issue.code for issue in readiness_report.issues
        ))
        if not readiness_report.publish_allowed and not reason_codes:
            reason_codes = (f"READINESS_{readiness_report.overall_status}",)

        return PublicationDecision(
            workflow=workflow.strip(),
            overall_status=readiness_report.overall_status,
            publish_allowed=bool(readiness_report.publish_allowed),
            decided_at=readiness_report.generated_at,
            reason_codes=reason_codes,
            component_statuses=component_statuses,
            readiness_generated_at=readiness_report.generated_at,
            metadata=metadata or {},
        )

    def can_publish(self, readiness_report: ReadinessReport, *, workflow: str) -> bool:
        return self.decide(readiness_report, workflow=workflow).publish_allowed

    def require_ready(
        self,
        readiness_report: ReadinessReport,
        *,
        workflow: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> PublicationDecision:
        decision = self.decide(
            readiness_report,
            workflow=workflow,
            metadata=metadata,
        )
        if not decision.publish_allowed:
            raise PublicationBlockedError(decision)
        return decision

    def execute(
        self,
        readiness_report: ReadinessReport,
        *,
        workflow: str,
        publisher: Callable[..., T],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> tuple[PublicationDecision, T]:
        """Run a publisher only after readiness authorizes publication."""
        decision = self.require_ready(
            readiness_report,
            workflow=workflow,
            metadata=metadata,
        )
        result = publisher(*args, **dict(kwargs or {}))
        return decision, result
