"""F3-C.2 guarded draft recommendation publication.

This module keeps recommendation generation separate from publication. Raw
recommendations may be calculated, but they are returned to the UI only when
an authoritative PublicationGate decision permits publication.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from draft_events.readiness import ReadinessReport
from services.publication_gate import PublicationDecision, PublicationGate


@dataclass(frozen=True)
class DraftRecommendationPublication:
    workflow: str
    decision: PublicationDecision
    recommendations: tuple[Any, ...] = field(default_factory=tuple)
    suppressed_count: int = 0

    @property
    def publish_allowed(self) -> bool:
        return self.decision.publish_allowed

    @property
    def status(self) -> str:
        return self.decision.overall_status

    @property
    def blockers(self) -> tuple[str, ...]:
        return self.decision.reason_codes

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "status": self.status,
            "publish_allowed": self.publish_allowed,
            "recommendation_count": len(self.recommendations),
            "suppressed_count": self.suppressed_count,
            "blockers": list(self.blockers),
            "decision": self.decision.to_dict(),
        }


class DraftRecommendationPublicationService:
    WORKFLOW = "draft_recommendations"

    def __init__(self, gate: PublicationGate | None = None):
        self.gate = gate or PublicationGate()

    def guard(
        self,
        recommendations: Iterable[Any],
        readiness_report: ReadinessReport,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> DraftRecommendationPublication:
        rows = tuple(recommendations)
        decision = self.gate.decide(
            readiness_report,
            workflow=self.WORKFLOW,
            metadata=metadata,
        )
        if decision.publish_allowed:
            published = rows
            suppressed_count = 0
        else:
            published = ()
            suppressed_count = len(rows)
        return DraftRecommendationPublication(
            workflow=self.WORKFLOW,
            decision=decision,
            recommendations=published,
            suppressed_count=suppressed_count,
        )
