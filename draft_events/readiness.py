"""F3-B.4 centralized, read-only readiness gates.

The engine consumes explicit component results and returns one authoritative
READY, WARNING, or BLOCKED decision. It performs no network, database, or
publication writes.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Iterable, Mapping


class ReadinessLevel(IntEnum):
    READY = 0
    WARNING = 1
    BLOCKED = 2

    @classmethod
    def parse(cls, value: "ReadinessLevel | str") -> "ReadinessLevel":
        if isinstance(value, cls):
            return value
        try:
            return cls[str(value).strip().upper()]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Unsupported readiness level: {value!r}") from exc


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    message: str
    level: ReadinessLevel
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "level": self.level.name,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ComponentReadiness:
    name: str
    level: ReadinessLevel
    summary: str
    issues: tuple[ReadinessIssue, ...] = field(default_factory=tuple)
    observed_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return self.level == ReadinessLevel.READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level.name,
            "ready": self.ready,
            "summary": self.summary,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "metadata": dict(self.metadata),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class ReadinessPolicy:
    required_components: tuple[str, ...] = (
        "sleeper",
        "draft_state",
        "reconciliation",
        "recommendations",
    )
    warning_allows_publish: bool = False
    maximum_age_seconds: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessReport:
    generated_at: datetime
    overall_level: ReadinessLevel
    publish_allowed: bool
    components: Mapping[str, ComponentReadiness]
    issues: tuple[ReadinessIssue, ...]
    policy: ReadinessPolicy

    @property
    def overall_status(self) -> str:
        return self.overall_level.name

    def component(self, name: str) -> ComponentReadiness | None:
        return self.components.get(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "overall_status": self.overall_status,
            "publish_allowed": self.publish_allowed,
            "components": {
                name: component.to_dict()
                for name, component in sorted(self.components.items())
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "policy": {
                "required_components": list(self.policy.required_components),
                "warning_allows_publish": self.policy.warning_allows_publish,
                "maximum_age_seconds": dict(self.policy.maximum_age_seconds),
            },
        }


class ReadinessEngine:
    def __init__(self, policy: ReadinessPolicy | None = None, clock=None):
        self.policy = policy or ReadinessPolicy()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(self, components: Iterable[ComponentReadiness]) -> ReadinessReport:
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("Readiness clock must return a timezone-aware datetime")

        by_name: dict[str, ComponentReadiness] = {}
        aggregate_issues: list[ReadinessIssue] = []

        for component in components:
            if component.name in by_name:
                raise ValueError(f"Duplicate readiness component: {component.name}")
            normalized = self._apply_freshness(component, now)
            by_name[component.name] = normalized
            aggregate_issues.extend(normalized.issues)

        for required in self.policy.required_components:
            if required not in by_name:
                issue = ReadinessIssue(
                    code="REQUIRED_COMPONENT_MISSING",
                    message=f"Required readiness component is missing: {required}",
                    level=ReadinessLevel.BLOCKED,
                    details={"component": required},
                )
                by_name[required] = ComponentReadiness(
                    name=required,
                    level=ReadinessLevel.BLOCKED,
                    summary="Required component did not report readiness",
                    issues=(issue,),
                    observed_at=now,
                )
                aggregate_issues.append(issue)

        overall = max(
            (component.level for component in by_name.values()),
            default=ReadinessLevel.BLOCKED,
        )
        publish_allowed = overall == ReadinessLevel.READY or (
            overall == ReadinessLevel.WARNING and self.policy.warning_allows_publish
        )

        return ReadinessReport(
            generated_at=now,
            overall_level=overall,
            publish_allowed=publish_allowed,
            components=by_name,
            issues=tuple(aggregate_issues),
            policy=self.policy,
        )

    def _apply_freshness(self, component: ComponentReadiness, now: datetime) -> ComponentReadiness:
        maximum_age = self.policy.maximum_age_seconds.get(component.name)
        if maximum_age is None:
            return component
        if component.observed_at is None:
            issue = ReadinessIssue(
                code="COMPONENT_TIMESTAMP_MISSING",
                message=f"Freshness cannot be verified for {component.name}",
                level=ReadinessLevel.BLOCKED,
                details={"component": component.name, "maximum_age_seconds": maximum_age},
            )
            return _escalate_component(component, issue)
        observed_at = component.observed_at
        if observed_at.tzinfo is None:
            issue = ReadinessIssue(
                code="COMPONENT_TIMESTAMP_NAIVE",
                message=f"Freshness timestamp is not timezone-aware for {component.name}",
                level=ReadinessLevel.BLOCKED,
                details={"component": component.name},
            )
            return _escalate_component(component, issue)
        age_seconds = (now - observed_at).total_seconds()
        if age_seconds < 0:
            issue = ReadinessIssue(
                code="COMPONENT_TIMESTAMP_IN_FUTURE",
                message=f"Freshness timestamp is in the future for {component.name}",
                level=ReadinessLevel.WARNING,
                details={"component": component.name, "age_seconds": age_seconds},
            )
            return _escalate_component(component, issue)
        if age_seconds > maximum_age:
            issue = ReadinessIssue(
                code="COMPONENT_STALE",
                message=f"Readiness component is stale: {component.name}",
                level=ReadinessLevel.BLOCKED,
                details={
                    "component": component.name,
                    "age_seconds": age_seconds,
                    "maximum_age_seconds": maximum_age,
                },
            )
            return _escalate_component(component, issue)
        return component


def _escalate_component(component: ComponentReadiness, issue: ReadinessIssue) -> ComponentReadiness:
    return ComponentReadiness(
        name=component.name,
        level=max(component.level, issue.level),
        summary=component.summary,
        issues=component.issues + (issue,),
        observed_at=component.observed_at,
        metadata=component.metadata,
    )


def component_ready(name: str, summary: str, *, observed_at=None, metadata=None):
    return ComponentReadiness(
        name=name,
        level=ReadinessLevel.READY,
        summary=summary,
        observed_at=observed_at,
        metadata=metadata or {},
    )


def component_warning(name: str, code: str, message: str, *, observed_at=None, metadata=None):
    issue = ReadinessIssue(code, message, ReadinessLevel.WARNING)
    return ComponentReadiness(
        name=name,
        level=ReadinessLevel.WARNING,
        summary=message,
        issues=(issue,),
        observed_at=observed_at,
        metadata=metadata or {},
    )


def component_blocked(name: str, code: str, message: str, *, observed_at=None, metadata=None):
    issue = ReadinessIssue(code, message, ReadinessLevel.BLOCKED)
    return ComponentReadiness(
        name=name,
        level=ReadinessLevel.BLOCKED,
        summary=message,
        issues=(issue,),
        observed_at=observed_at,
        metadata=metadata or {},
    )


def sleeper_component(live_report, *, observed_at=None):
    status = live_report.operational_status
    metadata = {
        "draft_id": live_report.draft_id,
        "draft_status": live_report.draft_status,
        "source_pick_count": live_report.source_pick_count,
    }
    if status in {"PASS", "READY_WAITING_FOR_PICKS"}:
        return component_ready("sleeper", status, observed_at=observed_at, metadata=metadata)
    return component_blocked(
        "sleeper",
        "LIVE_RECONCILIATION_BLOCKED",
        "Live Sleeper reconciliation is blocked",
        observed_at=observed_at,
        metadata=metadata,
    )


def reconciliation_component(report, *, observed_at=None):
    metadata = {
        "draft_id": report.draft_id,
        "source_count": report.source_count,
        "event_count": report.event_count,
        "selection_count": report.selection_count,
    }
    if report.passed:
        return component_ready(
            "reconciliation", "Draft state reconciled", observed_at=observed_at, metadata=metadata
        )
    return component_blocked(
        "reconciliation",
        "RECONCILIATION_FAILED",
        "Draft-state reconciliation has unresolved issues",
        observed_at=observed_at,
        metadata=metadata,
    )
