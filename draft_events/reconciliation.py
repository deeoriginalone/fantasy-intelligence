"""F3-B.2 normalized draft-state reconciliation.

The reconciler compares normalized source DraftEvent objects with the local
DraftEventStore contract. It is intentionally independent of Sleeper network
access: callers obtain and normalize source picks before invoking reconcile().
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    message: str
    pick_number: int | None = None
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationReport:
    draft_id: str
    source_count: int
    event_count: int
    selection_count: int
    expected_pick_numbers: tuple[int, ...]
    source_duplicate_pick_numbers: tuple[int, ...]
    source_duplicate_player_ids: tuple[str, ...]
    missing_selection_pick_numbers: tuple[int, ...]
    extra_selection_pick_numbers: tuple[int, ...]
    issues: tuple[ReconciliationIssue, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.issues

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "status": self.status,
            "passed": self.passed,
            "source_count": self.source_count,
            "event_count": self.event_count,
            "selection_count": self.selection_count,
            "expected_pick_numbers": list(self.expected_pick_numbers),
            "source_duplicate_pick_numbers": list(self.source_duplicate_pick_numbers),
            "source_duplicate_player_ids": list(self.source_duplicate_player_ids),
            "missing_selection_pick_numbers": list(self.missing_selection_pick_numbers),
            "extra_selection_pick_numbers": list(self.extra_selection_pick_numbers),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class DraftReconciler:
    """Compare normalized source events with a local draft-event store."""

    def __init__(self, store):
        self.store = store

    def reconcile(self, source_events: Iterable[Any], draft_id: str) -> ReconciliationReport:
        source = list(source_events)
        local = list(self.store.ordered_state(draft_id))
        issues: list[ReconciliationIssue] = []

        source_for_draft = [event for event in source if event.draft_id == draft_id]
        foreign = [event for event in source if event.draft_id != draft_id]
        for event in foreign:
            issues.append(ReconciliationIssue(
                code="SOURCE_DRAFT_ID_MISMATCH",
                message="Source event belongs to a different draft",
                pick_number=getattr(event, "pick_number", None),
                expected=draft_id,
                actual=event.draft_id,
            ))

        source_pick_counts = Counter(event.pick_number for event in source_for_draft)
        source_player_counts = Counter(event.player_id for event in source_for_draft)
        duplicate_picks = tuple(sorted(pick for pick, count in source_pick_counts.items() if count > 1))
        duplicate_players = tuple(sorted(player for player, count in source_player_counts.items() if count > 1))

        for pick in duplicate_picks:
            issues.append(ReconciliationIssue(
                code="SOURCE_DUPLICATE_PICK_NUMBER",
                message="Source contains the same pick number more than once",
                pick_number=pick,
                expected=1,
                actual=source_pick_counts[pick],
            ))
        for player_id in duplicate_players:
            issues.append(ReconciliationIssue(
                code="SOURCE_DUPLICATE_PLAYER",
                message="Source contains the same player more than once",
                expected=1,
                actual={"player_id": player_id, "count": source_player_counts[player_id]},
            ))

        source_by_pick = {}
        for event in source_for_draft:
            source_by_pick.setdefault(event.pick_number, event)
        local_by_pick = {event.pick_number: event for event in local}

        source_picks = set(source_by_pick)
        local_picks = set(local_by_pick)
        missing = tuple(sorted(source_picks - local_picks))
        extra = tuple(sorted(local_picks - source_picks))
        expected_pick_numbers = tuple(sorted(source_picks))

        if len(source_for_draft) != len(local):
            issues.append(ReconciliationIssue(
                code="SELECTION_COUNT_MISMATCH",
                message="Source and local selection counts differ",
                expected=len(source_for_draft),
                actual=len(local),
            ))

        for pick in missing:
            issues.append(ReconciliationIssue(
                code="MISSING_LOCAL_SELECTION",
                message="Source pick is missing from local selections",
                pick_number=pick,
                expected=source_by_pick[pick].event_id,
                actual=None,
            ))
        for pick in extra:
            issues.append(ReconciliationIssue(
                code="EXTRA_LOCAL_SELECTION",
                message="Local selection does not exist in source",
                pick_number=pick,
                expected=None,
                actual=local_by_pick[pick].event_id,
            ))

        comparable_fields = (
            "event_id", "league_id", "draft_id", "pick_number", "round",
            "round_pick", "roster_id", "owner_id", "player_id", "event_type",
        )
        for pick in sorted(source_picks & local_picks):
            expected_event = source_by_pick[pick]
            actual_event = local_by_pick[pick]
            for field_name in comparable_fields:
                expected_value = getattr(expected_event, field_name)
                actual_value = getattr(actual_event, field_name)
                if expected_value != actual_value:
                    issues.append(ReconciliationIssue(
                        code=f"FIELD_MISMATCH_{field_name.upper()}",
                        message=f"Local selection field differs from source: {field_name}",
                        pick_number=pick,
                        expected=expected_value,
                        actual=actual_value,
                    ))

            stored_event = self.store.get_event(expected_event.event_id)
            if stored_event is None:
                issues.append(ReconciliationIssue(
                    code="MISSING_LOCAL_EVENT",
                    message="Source event ID is absent from the local event store",
                    pick_number=pick,
                    expected=expected_event.event_id,
                    actual=None,
                ))
            elif stored_event.get("status") != "APPLIED":
                issues.append(ReconciliationIssue(
                    code="EVENT_NOT_APPLIED",
                    message="Local event exists but is not APPLIED",
                    pick_number=pick,
                    expected="APPLIED",
                    actual=stored_event.get("status"),
                ))

        event_count = sum(
            1 for record in self.store.events.values()
            if record["event"].draft_id == draft_id
        ) if hasattr(self.store, "events") else len(source_for_draft) - sum(
            1 for event in source_for_draft if self.store.get_event(event.event_id) is None
        )

        return ReconciliationReport(
            draft_id=draft_id,
            source_count=len(source_for_draft),
            event_count=event_count,
            selection_count=len(local),
            expected_pick_numbers=expected_pick_numbers,
            source_duplicate_pick_numbers=duplicate_picks,
            source_duplicate_player_ids=duplicate_players,
            missing_selection_pick_numbers=missing,
            extra_selection_pick_numbers=extra,
            issues=tuple(issues),
        )
