"""F3-B.3 read-only live Sleeper reconciliation orchestration.

Network functions, normalization, and the local store are injected. This keeps
unit tests deterministic and prevents the module from guessing database setup.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .reconciliation import DraftReconciler, ReconciliationReport


@dataclass(frozen=True)
class LiveReconciliationIssue:
    code: str
    severity: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class LiveReconciliationReport:
    draft_id: str
    league_id: str
    draft_status: str
    source_pick_count: int
    operational_status: str
    reconciliation: ReconciliationReport | None
    issues: tuple[LiveReconciliationIssue, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.operational_status in {"PASS", "READY_WAITING_FOR_PICKS"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "league_id": self.league_id,
            "draft_status": self.draft_status,
            "source_pick_count": self.source_pick_count,
            "operational_status": self.operational_status,
            "passed": self.passed,
            "reconciliation": (
                self.reconciliation.to_dict() if self.reconciliation else None
            ),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class LiveSleeperReconciliationService:
    """Fetch, normalize, and reconcile one Sleeper draft without local writes."""

    def __init__(
        self,
        *,
        get_draft: Callable[[str], Mapping[str, Any] | None],
        get_draft_picks: Callable[[str], Iterable[Mapping[str, Any]] | None],
        normalize_pick: Callable[[Mapping[str, Any], str, str], Any],
        store: Any,
    ):
        self.get_draft = get_draft
        self.get_draft_picks = get_draft_picks
        self.normalize_pick = normalize_pick
        self.store = store

    def run(self, *, league_id: str, draft_id: str) -> LiveReconciliationReport:
        metadata = self.get_draft(draft_id)
        if not metadata:
            issue = LiveReconciliationIssue(
                code="DRAFT_METADATA_UNAVAILABLE",
                severity="CRITICAL",
                message="Sleeper draft metadata could not be retrieved",
                details={"draft_id": draft_id},
            )
            return LiveReconciliationReport(
                draft_id=draft_id,
                league_id=league_id,
                draft_status="unknown",
                source_pick_count=0,
                operational_status="BLOCKED",
                reconciliation=None,
                issues=(issue,),
            )

        metadata_draft_id = str(metadata.get("draft_id") or draft_id)
        status = str(metadata.get("status") or "unknown")
        issues: list[LiveReconciliationIssue] = []
        if metadata_draft_id != draft_id:
            issues.append(LiveReconciliationIssue(
                code="DRAFT_METADATA_ID_MISMATCH",
                severity="CRITICAL",
                message="Sleeper metadata draft ID differs from requested draft ID",
                details={"expected": draft_id, "actual": metadata_draft_id},
            ))

        raw_picks = list(self.get_draft_picks(draft_id) or [])
        if not raw_picks and status == "pre_draft" and not issues:
            reconciliation = DraftReconciler(self.store).reconcile([], draft_id)
            if reconciliation.selection_count == 0 and reconciliation.event_count == 0:
                return LiveReconciliationReport(
                    draft_id=draft_id,
                    league_id=league_id,
                    draft_status=status,
                    source_pick_count=0,
                    operational_status="READY_WAITING_FOR_PICKS",
                    reconciliation=reconciliation,
                )
            issues.append(LiveReconciliationIssue(
                code="LOCAL_STATE_PRESENT_BEFORE_SOURCE_PICKS",
                severity="CRITICAL",
                message="Local draft state exists while Sleeper reports no picks",
                details={
                    "local_event_count": reconciliation.event_count,
                    "local_selection_count": reconciliation.selection_count,
                },
            ))
            return LiveReconciliationReport(
                draft_id=draft_id,
                league_id=league_id,
                draft_status=status,
                source_pick_count=0,
                operational_status="BLOCKED",
                reconciliation=reconciliation,
                issues=tuple(issues),
            )

        normalized = []
        for index, payload in enumerate(raw_picks, start=1):
            try:
                normalized.append(self.normalize_pick(payload, league_id, draft_id))
            except Exception as exc:
                issues.append(LiveReconciliationIssue(
                    code="PICK_NORMALIZATION_FAILED",
                    severity="CRITICAL",
                    message="Sleeper pick could not be normalized",
                    details={"source_index": index, "error": str(exc)},
                ))

        if issues:
            return LiveReconciliationReport(
                draft_id=draft_id,
                league_id=league_id,
                draft_status=status,
                source_pick_count=len(raw_picks),
                operational_status="BLOCKED",
                reconciliation=None,
                issues=tuple(issues),
            )

        reconciliation = DraftReconciler(self.store).reconcile(normalized, draft_id)
        if reconciliation.passed:
            operational_status = "PASS"
        else:
            operational_status = "BLOCKED"
            issues.extend(
                LiveReconciliationIssue(
                    code=issue.code,
                    severity=_severity_for_reconciliation_code(issue.code),
                    message=issue.message,
                    details={
                        "pick_number": issue.pick_number,
                        "expected": issue.expected,
                        "actual": issue.actual,
                    },
                )
                for issue in reconciliation.issues
            )

        return LiveReconciliationReport(
            draft_id=draft_id,
            league_id=league_id,
            draft_status=status,
            source_pick_count=len(raw_picks),
            operational_status=operational_status,
            reconciliation=reconciliation,
            issues=tuple(issues),
        )


def _severity_for_reconciliation_code(code: str) -> str:
    if code in {
        "SOURCE_DUPLICATE_PICK_NUMBER",
        "SOURCE_DUPLICATE_PLAYER",
        "SOURCE_DRAFT_ID_MISMATCH",
        "SELECTION_COUNT_MISMATCH",
        "MISSING_LOCAL_SELECTION",
        "EXTRA_LOCAL_SELECTION",
        "MISSING_LOCAL_EVENT",
        "EVENT_NOT_APPLIED",
    }:
        return "CRITICAL"
    if code.startswith("FIELD_MISMATCH_"):
        return "ERROR"
    return "WARNING"
