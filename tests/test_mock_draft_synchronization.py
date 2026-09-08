import pytest

from draft_state_hardening import build_hardened_sync


class Cursor:
    def __init__(self, statements):
        self.statements = statements

    def execute(self, statement, params=None):
        self.statements.append((statement, params))

    def fetchone(self):
        return None

    def close(self):
        pass


class Connection:
    def __init__(self):
        self.statements = []
        self.cursor_instance = Cursor(self.statements)
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


def test_verified_mock_draft_reaches_synchronization_persistence():
    draft_id = "mock-draft-1"
    remote = {
        "draft_id": draft_id,
        "league_id": None,
        "status": "paused",
        "season": 2026,
        "type": "snake",
        "settings": {"teams": 10, "rounds": 14},
    }
    connections = []

    def database():
        connection = Connection()
        connections.append(connection)
        return connection

    run = build_hardened_sync(
        lambda: {"stored": 0},
        database,
        lambda value: remote,
        lambda value: [],
        "configured-league",
        draft_id,
        allow_mock=True,
    )

    result = run()

    assert result["identity_valid"] is True
    assert result["stored"] == 0
    assert connections
    assert any(
        "INSERT INTO draft_sessions" in statement
        for connection in connections
        for statement, _ in connection.statements
    )


def test_incomplete_mock_metadata_remains_fail_closed():
    remote = {
        "draft_id": "mock-draft-1",
        "league_id": None,
        "status": "paused",
        "season": 2026,
        "type": "snake",
    }

    run = build_hardened_sync(
        lambda: {"stored": 0},
        lambda: pytest.fail("persistence must not be reached"),
        lambda value: remote,
        lambda value: [],
        "configured-league",
        "mock-draft-1",
    )

    with pytest.raises(RuntimeError, match="ambiguous without a league ID"):
        run()


def test_live_league_identity_synchronizes_with_matching_league_and_draft():
    calls = []
    remote = {
        "draft_id": "live-draft-1",
        "league_id": "live-league-1",
        "status": "pre_draft",
        "season": 2026,
        "type": "snake",
        "settings": {"teams": 10, "rounds": 15},
    }

    run = build_hardened_sync(
        lambda: calls.append("original") or {"stored": 0},
        lambda: Connection(),
        lambda value: remote,
        lambda value: [],
        "live-league-1",
        "live-draft-1",
    )

    assert run()["identity_valid"] is True
    assert calls == ["original"]


def test_invalid_mock_identity_preserves_session_and_skips_original_sync():
    calls = []

    run = build_hardened_sync(
        lambda: calls.append("original"),
        lambda: pytest.fail("database must not be opened before validation"),
        lambda value: {
            "draft_id": "mock-draft-1",
            "league_id": None,
            "status": "pre_draft",
            "type": "snake",
            "settings": {"teams": 10, "rounds": 15},
        },
        lambda value: pytest.fail("draft picks must not be fetched after validation"),
        "live-league-1",
        "mock-draft-1",
    )

    with pytest.raises(RuntimeError, match="ambiguous without a league ID"):
        run()

    assert calls == []