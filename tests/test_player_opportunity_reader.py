import pytest

from services.player_opportunity_reader import read_player_opportunity, read_player_what_changed


NOW = "2026-09-17T12:00:00+00:00"
COLUMNS = (
    "season", "week", "player_id", "team", "targets", "carries",
    "target_share", "carry_share", "touch_share", "snap_share",
    "route_participation", "red_zone_share", "role_classification", "source",
    "source_authority", "source_recorded_at", "retrieved_at", "artifact_id",
    "version", "checksum", "freshness_threshold_id", "freshness_state",
    "completeness_state", "lineage", "publication_state",
)


def row(week, *, target_share=0.2, carry_share=0.1, touch_share=0.15, **updates):
    values = {
        "season": 2026, "week": week, "player_id": "p1", "team": "KC",
        "targets": 4, "carries": 2, "target_share": target_share,
        "carry_share": carry_share, "touch_share": touch_share,
        "snap_share": None, "route_participation": None, "red_zone_share": None,
        "role_classification": None, "source": "automated:nflverse",
        "source_authority": "automated", "source_recorded_at": NOW,
        "retrieved_at": NOW, "artifact_id": "stats_player_week_2026",
        "version": "2026.09.17", "checksum": "sha256:test",
        "freshness_threshold_id": "opportunity.evidence.v1", "freshness_state": "FRESH",
        "completeness_state": "COMPLETE", "lineage": {"reconciliation": {"reconciled": True}},
        "publication_state": "PUBLISHED",
    }
    values.update(updates)
    return tuple(values[name] for name in COLUMNS)


class ReaderCursor:
    description = [(name,) for name in COLUMNS]

    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.statements = []
        self.closed = False

    def execute(self, query, params):
        self.statements.append((query, params))
        if self.error:
            raise self.error

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ReaderConnection:
    def __init__(self, rows=None, error=None):
        self.reader_cursor = ReaderCursor(rows=rows, error=error)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.reader_cursor

    def close(self):
        self.closed = True


def test_reader_returns_deterministic_scoped_rows_and_parameterized_query():
    connection = ReaderConnection([row(2, target_share=0.3), row(1)])
    result = read_player_opportunity(connection, player_id="p1", season=2026, week_start=1, week_end=2)
    query, params = connection.reader_cursor.statements[0]
    assert result["state"] == "AVAILABLE"
    assert result["supported_weeks"] == [1, 2]
    assert [item["week"] for item in result["rows"]] == [1, 2]
    assert params == ("p1", 2026, 1, 2)
    assert "p1" not in query and "%s" in query
    assert not connection.committed and not connection.rolled_back


def test_reader_supports_exact_week_filtering():
    connection = ReaderConnection([row(2)])
    result = read_player_opportunity(connection, player_id="p1", season=2026, week=2)
    query, params = connection.reader_cursor.statements[0]
    assert result["state"] == "AVAILABLE"
    assert result["supported_weeks"] == [2]
    assert params == ("p1", 2026, 2)
    assert "week = %s" in query


def test_reader_preserves_zero_and_null_and_role_metrics_unavailable():
    result = read_player_opportunity(db_connection=ReaderConnection([row(1, target_share=0, carry_share=None)]), player_id="p1", season=2026)
    assert result["rows"][0]["target_share"] == 0.0
    assert result["rows"][0]["carry_share"] is None
    assert result["rows"][0]["snap_share"] is None
    assert result["rows"][0]["role_classification"] is None


def test_reader_fails_closed_for_empty_failed_and_invalid_scope_reads():
    empty = read_player_opportunity(ReaderConnection(), player_id="p1", season=2026)
    failed = read_player_opportunity(ReaderConnection(error=RuntimeError()), player_id="p1", season=2026)
    invalid = read_player_opportunity(ReaderConnection(), player_id="", season=2026)
    assert empty["state"] == "UNAVAILABLE"
    assert empty["blockers"] == ["OPPORTUNITY_READER_NO_ROWS"]
    assert failed["state"] == "BLOCKED"
    assert failed["blockers"] == ["OPPORTUNITY_READER_QUERY_FAILED"]
    assert invalid["state"] == "BLOCKED"
    assert invalid["blockers"] == ["OPPORTUNITY_PLAYER_IDENTITY_INVALID"]


def test_reader_fails_closed_for_duplicate_mismatch_and_contract_rows():
    duplicate = read_player_opportunity(ReaderConnection([row(1), row(1)]), player_id="p1", season=2026)
    mismatch = read_player_opportunity(ReaderConnection([row(1, player_id="other")]), player_id="p1", season=2026)
    stale = read_player_opportunity(ReaderConnection([row(1, freshness_state="STALE")]), player_id="p1", season=2026)
    unreconciled = read_player_opportunity(ReaderConnection([row(1, lineage={"reconciliation": {"reconciled": False}})]), player_id="p1", season=2026)
    assert duplicate["state"] == "BLOCKED" and "OPPORTUNITY_DUPLICATE_PLAYER_WEEK" in duplicate["blockers"]
    assert mismatch["state"] == "BLOCKED" and "OPPORTUNITY_PLAYER_IDENTITY_MISMATCH" in mismatch["blockers"]
    assert stale["state"] == "BLOCKED" and "OPPORTUNITY_EVIDENCE_NOT_CURRENT" in stale["blockers"]
    assert unreconciled["state"] == "BLOCKED" and "OPPORTUNITY_RECONCILIATION_UNVERIFIED" in unreconciled["blockers"]


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("source", None, "OPPORTUNITY_SOURCE_UNSUPPORTED"),
        ("source_authority", "UNVERIFIED", "OPPORTUNITY_SOURCE_AUTHORITY_UNSUPPORTED"),
        ("source_recorded_at", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:source_recorded_at"),
        ("retrieved_at", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:retrieved_at"),
        ("artifact_id", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:artifact_id"),
        ("version", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:version"),
        ("checksum", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:checksum"),
        ("freshness_threshold_id", None, "OPPORTUNITY_PUBLISHED_FIELD_UNAVAILABLE:freshness_threshold_id"),
        ("freshness_state", "UNKNOWN", "OPPORTUNITY_EVIDENCE_NOT_CURRENT"),
        ("completeness_state", "INCOMPLETE", "OPPORTUNITY_INCOMPLETE"),
        ("publication_state", "DRAFT", "OPPORTUNITY_PUBLICATION_STATE_INVALID"),
    ],
)
def test_reader_rejects_invalid_publication_contract_fields(field, value, blocker):
    result = read_player_opportunity(ReaderConnection([row(1, **{field: value})]), player_id="p1", season=2026)
    assert result["state"] == "BLOCKED"
    assert blocker in result["blockers"]


def test_adapter_delegates_comparison_and_preserves_reader_blockers():
    available = read_player_what_changed(ReaderConnection([row(1), row(2, target_share=0.3)]), player_id="p1", season=2026)
    blocked = read_player_what_changed(ReaderConnection(error=RuntimeError()), player_id="p1", season=2026)
    assert available["state"] == "AVAILABLE"
    assert available["decision_effect"] == "INFORMATIONAL_ONLY"
    assert available["current_week"] == 2
    assert blocked["state"] == "BLOCKED"
    assert "OPPORTUNITY_READER_QUERY_FAILED" in blocked["blockers"]
    assert not any(label in str(available).upper() for label in ("BUY LOW", "SELL HIGH", "BREAKOUT", "REGRESSION", "START", "SIT", "ADD", "DROP"))