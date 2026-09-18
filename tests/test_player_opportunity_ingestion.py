import csv
import gzip
import json

import pytest

import imports.import_nflverse_opportunity as opportunity_import
from imports.import_nflverse_opportunity import build_evidence
from services.player_opportunity_calculation import calculate_player_opportunity
from services.player_opportunity_publication import publish_player_opportunity

NOW = "2026-09-17T12:00:00+00:00"
FRESH_ENV = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "86400"}


def stat_row(player_id, team, opponent, week=3, targets=0, carries=0, season=2026):
    return {"player_id": player_id, "team": team, "opponent_team": opponent, "season": str(season), "week": str(week), "targets": str(targets), "carries": str(carries)}


def rows():
    return [
        stat_row("p1", "KC", "DEN", targets=8, carries=0),
        stat_row("p2", "KC", "DEN", targets=2, carries=15),
        stat_row("p3", "DEN", "KC", targets=5, carries=5),
        stat_row("p4", "DEN", "KC", targets=5, carries=5),
    ]


def write_fixture(tmp_path, gzip_it=False):
    path = tmp_path / ("weekly.csv.gz" if gzip_it else "weekly.csv")
    fieldnames = ["player_id", "team", "opponent_team", "season", "week", "targets", "carries"]
    text_rows = rows()
    if gzip_it:
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(text_rows)
    else:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(text_rows)
    return path


def evidence_from_rows(**overrides):
    kwargs = {"season": 2026, "retrieved_at": NOW, "now": NOW, "threshold_environment": FRESH_ENV,
              "source": "automated:nflverse", "version": "stats_player_week_2026", "checksum": "abc123", "source_recorded_at": NOW}
    kwargs.update(overrides)
    return calculate_player_opportunity(rows(), **kwargs)


class FakeCursor:
    def __init__(self, fail_on_row=None):
        self.statements = []
        self.fail_on_row = fail_on_row
        self._insert_count = 0

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if sql.strip().startswith("INSERT"):
            self._insert_count += 1
            if self.fail_on_row is not None and self._insert_count == self.fail_on_row:
                raise RuntimeError("SIMULATED_TRANSACTION_FAILURE")

    def close(self):
        pass


class FakeConnection:
    def __init__(self, fail_on_row=None):
        self.cursor_instance = FakeCursor(fail_on_row=fail_on_row)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


# 1. successful automated retrieval feeds calculation
def test_local_fixture_retrieval_feeds_calculation(tmp_path):
    path = write_fixture(tmp_path)
    evidence = build_evidence(path, season=2026)
    by_id = {row["player_id"]: row for row in evidence["rows"]}
    assert by_id["p1"]["target_share"] == 0.8
    assert evidence["provenance"]["source"] == f"fixture:{path.name}"
    assert evidence["provenance"]["checksum"]


def test_missing_required_columns_raises_before_calculation(tmp_path):
    path = tmp_path / "bad.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["player_id", "team"])
        writer.writeheader()
        writer.writerow({"player_id": "p1", "team": "KC"})
    with pytest.raises(ValueError, match="NFLVERSE_OPPORTUNITY_SCHEMA_UNVERIFIED"):
        build_evidence(path, season=2026)


def test_verified_nflverse_url_emits_automated_authority_and_preserves_location(monkeypatch):
    source_url = opportunity_import.NFLVERSE_RELEASE_URL.format(season=2026)

    monkeypatch.setattr(opportunity_import, "load_weekly_stats", lambda path: (rows(), "sha256:test"))
    monkeypatch.setattr(opportunity_import, "urlopen", lambda *args, **kwargs: type("Response", (), {"read": lambda self: b"2026-09-18T00:00:00Z"})())
    evidence = build_evidence(source_url, season=2026, threshold_environment=FRESH_ENV)
    assert evidence["provenance"]["source"] == "automated:nflverse"
    assert evidence["provenance"]["source_authority"] == "automated:nflverse"
    assert evidence["provenance"]["source_location"] == source_url


def test_arbitrary_remote_url_does_not_claim_automated_authority(monkeypatch):
    monkeypatch.setattr(opportunity_import, "load_weekly_stats", lambda path: (rows(), "sha256:test"))
    evidence = build_evidence("https://example.invalid/weekly.csv.gz", season=2026, threshold_environment=FRESH_ENV)
    assert evidence["provenance"]["source"] != "automated:nflverse"
    assert evidence["provenance"]["source_authority"] == "UNVERIFIED"


def test_local_fixture_does_not_claim_automated_authority(tmp_path):
    path = write_fixture(tmp_path)
    evidence = build_evidence(path, season=2026, threshold_environment=FRESH_ENV)
    assert evidence["provenance"]["source_authority"] == "UNVERIFIED"


# 2/3/4/5. target/carry/touch evidence, source/retrieval metadata, checksum/version, threshold/freshness persisted
def test_publish_persists_metrics_and_full_provenance():
    evidence = evidence_from_rows()
    conn = FakeConnection()
    count = publish_player_opportunity(conn, evidence)
    assert count == 4
    insert_statements = [params for sql, params in conn.cursor_instance.statements if sql.strip().startswith("INSERT")]
    by_player = {params[2]: params for params in insert_statements}
    p1 = by_player["p1"]
    # season, week, player_id, team, targets, carries, target_share, carry_share, touch_share, ...
    assert p1[0] == 2026 and p1[2] == "p1" and p1[3] == "KC"
    assert p1[6] == 0.8  # target_share
    assert p1[13] == "automated:nflverse"  # source
    assert p1[14] == "automated"  # source_authority
    assert p1[16] == NOW  # retrieved_at
    assert p1[18] == "stats_player_week_2026"  # version
    assert p1[19] == "abc123"  # checksum
    assert p1[20] == "opportunity.evidence.v1"  # freshness_threshold_id
    assert p1[21] == "FRESH"  # freshness_state
    assert conn.committed is True


# 6/7. rerun is deterministic and does not duplicate rows
def test_rerun_same_artifact_is_deterministic_and_replaces_not_duplicates():
    evidence = evidence_from_rows()
    conn = FakeConnection()
    first = publish_player_opportunity(conn, evidence)
    second = publish_player_opportunity(conn, evidence)
    assert first == second == 4
    deletes = [sql for sql, _ in conn.cursor_instance.statements if sql.strip().startswith("DELETE")]
    assert len(deletes) == 2
    inserts = [sql for sql, _ in conn.cursor_instance.statements if sql.strip().startswith("INSERT")]
    assert "ON CONFLICT (season, week, player_id) DO UPDATE" in inserts[0]


# 8/9/10. replacement is atomic and scoped only to the weeks present in this batch
def test_replacement_is_scoped_to_season_and_specific_weeks_only():
    evidence = evidence_from_rows()
    conn = FakeConnection()
    publish_player_opportunity(conn, evidence)
    delete_sql, delete_params = conn.cursor_instance.statements[0]
    assert "DELETE FROM player_opportunity_evidence" in delete_sql
    assert "week = ANY(%s)" in delete_sql
    assert "source LIKE 'automated:nflverse%%'" in delete_sql
    assert delete_params == (2026, [3])


def test_one_week_refresh_does_not_scope_delete_to_other_weeks():
    week5_rows = [stat_row("p5", "KC", "DEN", week=5, targets=4, carries=0), stat_row("p6", "KC", "DEN", week=5, targets=1, carries=10)]
    evidence = calculate_player_opportunity(week5_rows, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    conn = FakeConnection()
    publish_player_opportunity(conn, evidence)
    delete_sql, delete_params = conn.cursor_instance.statements[0]
    assert delete_params == (2026, [5])


# 9. missing threshold publishes zero rows
def test_missing_threshold_publishes_zero_rows():
    evidence = evidence_from_rows(threshold_environment={"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": ""})
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_THRESHOLD_UNVERIFIED"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 10. missing retrieved_at publishes zero rows
def test_missing_retrieved_at_publishes_zero_rows():
    evidence = evidence_from_rows(retrieved_at=None)
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_RETRIEVED_AT_UNAVAILABLE"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 11. stale evidence publishes zero rows
def test_stale_evidence_publishes_zero_rows():
    evidence = evidence_from_rows(retrieved_at="2020-01-01T00:00:00+00:00")
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_DATA_STALE"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 12. missing checksum publishes zero rows
def test_missing_checksum_publishes_zero_rows():
    evidence = evidence_from_rows(checksum=None)
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_CHECKSUM_UNAVAILABLE"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 13. unresolved required identities publish zero rows (all rows unresolved)
def test_all_unresolved_identities_publish_zero_rows():
    incomplete = [{"team": "KC", "opponent_team": "DEN", "season": "2026", "week": "3", "targets": "3", "carries": "0"}]
    evidence = calculate_player_opportunity(incomplete, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_NO_RESOLVED_ROWS"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 2. reconciled complete batch publishes
def test_reconciled_complete_batch_publishes():
    evidence = evidence_from_rows()
    assert evidence["reconciliation"]["reconciled"] is True
    conn = FakeConnection()
    assert publish_player_opportunity(conn, evidence) == 4


# 3. unexplained dropped row (accounting does not reconcile) blocks publication
def test_unreconciled_accounting_blocks_publication():
    evidence = dict(evidence_from_rows())
    tampered = dict(evidence["reconciliation"])
    tampered["published_row_count"] = tampered["published_row_count"] - 1  # simulate a silently dropped row
    tampered["reconciled"] = (tampered["published_row_count"] + tampered["excluded_row_count"]) == tampered["input_row_count"]
    evidence["reconciliation"] = tampered
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_ACCOUNTING_UNRECONCILED"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 4. duplicate player-week blocks the whole batch
def test_duplicate_player_week_blocks_publication():
    duplicated = rows() + [stat_row("p1", "KC", "DEN", targets=1, carries=0)]
    evidence = calculate_player_opportunity(duplicated, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_DUPLICATE_PLAYER_WEEK"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 5. contradictory team identity blocks the whole batch
def test_contradictory_team_identity_blocks_publication():
    contradictory = rows() + [stat_row("p1", "DEN", "KC", targets=1, carries=0)]
    evidence = calculate_player_opportunity(contradictory, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_CONTRADICTORY_TEAM_IDENTITY"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 6/13. unresolved identity alone (no duplicates/contradictions) does not block the rest of the batch
def test_unresolved_identity_alone_does_not_block_resolved_rows():
    partially_unresolved = rows() + [{"team": "KC", "opponent_team": "DEN", "season": 2026, "week": 3, "targets": 3, "carries": 0}]
    evidence = calculate_player_opportunity(partially_unresolved, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    assert evidence["reconciliation"]["unresolved_identity_count"] == 1
    conn = FakeConnection()
    assert publish_player_opportunity(conn, evidence) == 4


# 11. AGING is permitted for publication per the existing opportunity authority contract
def test_aging_evidence_is_publishable():
    threshold_env = {"OPPORTUNITY_EVIDENCE_MAX_AGE_SECONDS": "100"}
    evidence = calculate_player_opportunity(rows(), season=2026, retrieved_at="2026-09-17T11:58:30+00:00", now=NOW, threshold_environment=threshold_env, source="automated:nflverse", checksum="abc123")
    assert evidence["freshness_state"] == "AGING"
    conn = FakeConnection()
    assert publish_player_opportunity(conn, evidence) == 4


# 14. calculation or transaction failure rolls back the whole batch
def test_transaction_failure_rolls_back_whole_batch():
    evidence = evidence_from_rows()
    conn = FakeConnection(fail_on_row=2)
    with pytest.raises(RuntimeError, match="SIMULATED_TRANSACTION_FAILURE"):
        publish_player_opportunity(conn, evidence)
    assert conn.committed is False
    assert conn.rolled_back is True


# 15. CSV or non-automated source cannot claim automated authority
def test_csv_source_cannot_publish():
    evidence = evidence_from_rows(source="csv:manual-upload.csv")
    conn = FakeConnection()
    with pytest.raises(ValueError, match="OPPORTUNITY_PUBLICATION_SOURCE_NOT_AUTOMATED"):
        publish_player_opportunity(conn, evidence)
    assert conn.cursor_instance.statements == []


# 16. unsupported metrics remain NULL/unavailable
def test_unsupported_metrics_persist_as_null():
    evidence = evidence_from_rows()
    conn = FakeConnection()
    publish_player_opportunity(conn, evidence)
    insert_params = [params for sql, params in conn.cursor_instance.statements if sql.strip().startswith("INSERT")]
    for params in insert_params:
        assert params[9] is None  # snap_share
        assert params[10] is None  # route_participation
        assert params[11] is None  # red_zone_share
        assert params[12] is None  # role_classification


# 17. zero denominators remain unavailable, not numeric zero
def test_zero_team_totals_remain_unavailable_not_zero():
    no_touches = [stat_row("p1", "KC", "DEN", targets=0, carries=0)]
    evidence = calculate_player_opportunity(no_touches, season=2026, retrieved_at=NOW, now=NOW, threshold_environment=FRESH_ENV, source="automated:nflverse", checksum="abc123")
    row = evidence["rows"][0]
    assert row["target_share"] is None
    assert row["carry_share"] is None
    assert row["touch_share"] is None
    assert row["authoritative"] is False


# 18. existing valid publication remains intact after a failed refresh
def test_failed_refresh_does_not_touch_prior_publish_in_same_connection_lifetime():
    good_evidence = evidence_from_rows()
    conn = FakeConnection()
    publish_player_opportunity(conn, good_evidence)
    assert conn.committed is True
    stale_refresh = evidence_from_rows(retrieved_at="2020-01-01T00:00:00+00:00")
    with pytest.raises(ValueError, match="OPPORTUNITY_DATA_STALE"):
        publish_player_opportunity(conn, stale_refresh)
    # The failed refresh never reached the database: no new DELETE/INSERT statements appended.
    statements_after_failed_refresh = len(conn.cursor_instance.statements)
    assert statements_after_failed_refresh == 5  # 1 delete + 4 inserts from the first, successful publish only
