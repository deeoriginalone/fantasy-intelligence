from copy import deepcopy

import pytest

from draft_state_hardening import rotate_draft_environment


class RotationCursor:
    def __init__(self, database):
        self.database = database
        self.statements = []
        self.rowcount = 0
        self.pending = None

    def execute(self, statement, params=()):
        self.statements.append((statement, params))
        normalized = " ".join(statement.split()).lower()
        self.rowcount = 0
        if "select to_regclass" in normalized:
            self.pending = ("present",)
        elif "select pg_advisory_xact_lock" in normalized:
            self.pending = None
        elif "from draft_sessions" in normalized:
            self.pending = self.database.authoritative
        elif normalized.startswith("select count(*) from draft_board"):
            self.pending = (1 if self.database.force_nonempty_after_clear else len(self.database.board),)
        elif normalized.startswith("select count(*) from league_rosters"):
            self.pending = (1 if self.database.force_nonempty_after_clear else len(self.database.rosters),)
        elif normalized.startswith("select count(*) from my_roster"):
            self.pending = (1 if self.database.force_nonempty_after_clear else len(self.database.my_roster),)
        elif normalized.startswith("select player_name, starred"):
            self.pending = None
        elif normalized.startswith("select team_name, player_name"):
            self.pending = None
        elif normalized.startswith("select player_name, position"):
            self.pending = None
        elif normalized.startswith("update draft_board"):
            self.database.board = []
            self.rowcount = 2
        elif normalized.startswith("delete from league_rosters"):
            self.database.rosters = []
            self.rowcount = 2
        elif normalized.startswith("delete from my_roster"):
            self.database.my_roster = []
            self.rowcount = 1
        elif normalized.startswith("update draft_sessions"):
            self.database.authoritative = None
        elif normalized.startswith("insert into draft_sessions"):
            destination = str(params[0])
            self.database.authoritative = (destination, params[1], params[2], params[3])
        elif normalized.startswith("insert into draft_sync_audit"):
            self.database.rotation_audits.append(params)
        elif normalized.startswith("insert into draft_mutation_history"):
            self.database.rotation_history.append(params)

    def fetchone(self):
        pending, self.pending = self.pending, None
        return pending

    def fetchall(self):
        for statement, _ in reversed(self.statements):
            normalized = " ".join(statement.split()).lower()
            if normalized.startswith("select player_name, starred"):
                return list(self.database.board)
            if normalized.startswith("select team_name, player_name"):
                return list(self.database.rosters)
            if normalized.startswith("select player_name, position"):
                return list(self.database.my_roster)
        return []

    def close(self):
        pass


class RotationConnection:
    def __init__(self, database):
        self.database = database
        self.snapshot = deepcopy(database.snapshot())
        self.cursor_instance = RotationCursor(database)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        self.database.restore(self.snapshot)

    def close(self):
        pass


class RotationDatabase:
    def __init__(self, authoritative=("mock-a", "league", "2026", "pre_draft")):
        self.authoritative = authoritative
        self.board = [("Player A", False, True)]
        self.rosters = [("Team A", "Player A", "WR", None)]
        self.my_roster = [("Player A", "WR", "WR1", None)]
        self.rotation_audits = []
        self.rotation_history = []
        self.force_nonempty_after_clear = False
        self.connections = []

    def snapshot(self):
        return {
            "authoritative": self.authoritative,
            "board": self.board,
            "rosters": self.rosters,
            "my_roster": self.my_roster,
            "rotation_audits": self.rotation_audits,
            "rotation_history": self.rotation_history,
        }

    def restore(self, snapshot):
        self.authoritative = snapshot["authoritative"]
        self.board = snapshot["board"]
        self.rosters = snapshot["rosters"]
        self.my_roster = snapshot["my_roster"]
        self.rotation_audits = snapshot["rotation_audits"]
        self.rotation_history = snapshot["rotation_history"]

    def connect(self):
        connection = RotationConnection(self)
        self.connections.append(connection)
        return connection


def mock_remote(draft_id):
    return {
        "draft_id": draft_id,
        "league_id": None,
        "status": "pre_draft",
        "season": "2026",
        "type": "snake",
        "settings": {"teams": 10, "rounds": 15},
    }


def live_remote(draft_id):
    return {
        "draft_id": draft_id,
        "league_id": "league",
        "status": "pre_draft",
        "season": "2026",
        "type": "snake",
        "settings": {"teams": 10, "rounds": 15},
    }


def rotate(database, remote, old_draft_id, new_draft_id, mode):
    synchronized = []
    result = rotate_draft_environment(
        database.connect,
        lambda draft_id: remote,
        lambda draft_id: [{"pick_no": 1}],
        old_draft_id,
        new_draft_id,
        "league",
        mode,
        synchronize=lambda: synchronized.append(new_draft_id) or {"stored": 1},
        protected_live_draft_id="live-draft",
    )
    return result, synchronized


def test_matching_live_rotation_succeeds_and_syncs_destination():
    database = RotationDatabase()

    result, synchronized = rotate(
        database,
        live_remote("live-draft"),
        "mock-a",
        "live-draft",
        "LIVE",
    )

    assert result["new_draft_id"] == "live-draft"
    assert synchronized == ["live-draft"]
    assert database.authoritative[0] == "live-draft"
    assert database.board == []
    assert database.rosters == []
    assert database.my_roster == []
    assert len(database.rotation_audits) == 1
    assert len(database.rotation_history) == 1


def test_rotation_reports_degraded_success_when_health_refresh_fails():
    database = RotationDatabase()

    def failing_health():
        raise RuntimeError('relation "draft_decision_outcomes" does not exist')

    result = rotate_draft_environment(
        database.connect,
        lambda draft_id: live_remote(draft_id),
        lambda draft_id: [{"pick_no": 1}],
        "mock-a",
        "live-draft",
        "league",
        "LIVE",
        refresh_health=failing_health,
        protected_live_draft_id="protected-live-draft",
    )

    assert result["degraded"] is True
    assert any(w["step"] == "health" for w in result["warnings"])
    assert "health" not in result or result.get("health") is None
    # Authority must remain committed even though health refresh failed.
    assert database.authoritative[0] == "live-draft"
    assert any(
        params[2] == "ROTATION_HEALTH_DEGRADED"
        for params in database.rotation_audits
    )


def test_rotation_reports_degraded_success_when_synchronize_fails():
    database = RotationDatabase()

    def failing_sync():
        raise RuntimeError("sync unavailable")

    result = rotate_draft_environment(
        database.connect,
        lambda draft_id: live_remote(draft_id),
        lambda draft_id: [{"pick_no": 1}],
        "mock-a",
        "live-draft",
        "league",
        "LIVE",
        synchronize=failing_sync,
        protected_live_draft_id="protected-live-draft",
    )

    assert result["degraded"] is True
    assert any(w["step"] == "synchronization" for w in result["warnings"])
    assert database.authoritative[0] == "live-draft"


def test_mock_a_to_mock_b_rotation_preserves_history_and_clears_active_state():
    database = RotationDatabase()
    database.rotation_history.append(("historical-event",))

    result, _ = rotate(
        database,
        mock_remote("mock-b"),
        "mock-a",
        "mock-b",
        "MOCK",
    )

    assert result["new_draft_id"] == "mock-b"
    assert database.authoritative[0] == "mock-b"
    assert database.board == []
    assert database.rosters == []
    assert database.my_roster == []
    assert database.rotation_history[0] == ("historical-event",)


def test_explicit_mock_rotation_can_leave_live_session_without_deleting_history():
    database = RotationDatabase(authoritative=("live-draft", "league", "2026", "pre_draft"))
    database.rotation_history.append(("real-draft-history",))

    result, _ = rotate(database, mock_remote("mock-b"), "live-draft", "mock-b", "MOCK")

    assert result["new_draft_id"] == "mock-b"
    assert database.authoritative[0] == "mock-b"
    assert database.board == []
    assert database.rotation_history[0] == ("real-draft-history",)


def test_mock_mode_cannot_target_protected_live_draft():
    database = RotationDatabase(authoritative=("mock-a", "league", "2026", "pre_draft"))

    with pytest.raises(RuntimeError, match="protected live draft"):
        rotate(database, mock_remote("live-draft"), "mock-a", "live-draft", "MOCK")

    assert database.authoritative[0] == "mock-a"
    assert database.board


def test_invalid_destination_fails_before_database_mutation_or_sync():
    database = RotationDatabase()
    synchronized = []

    with pytest.raises(RuntimeError, match="ambiguous without a league ID"):
        rotate_draft_environment(
            database.connect,
            lambda draft_id: mock_remote("different-draft"),
            lambda draft_id: pytest.fail("picks must not be fetched"),
            "mock-a",
            "mock-b",
            "league",
            "LIVE",
            synchronize=lambda: synchronized.append(True),
        )

    assert synchronized == []
    assert not database.connections
    assert database.authoritative[0] == "mock-a"
    assert database.board


def test_live_draft_id_mismatch_fails_before_database_mutation():
    database = RotationDatabase()

    with pytest.raises(RuntimeError, match="Configured draft ID does not match"):
        rotate_draft_environment(
            database.connect,
            lambda draft_id: live_remote("different-draft"),
            lambda draft_id: pytest.fail("picks must not be fetched"),
            "mock-a",
            "live-draft",
            "league",
            "LIVE",
        )

    assert not database.connections
    assert database.authoritative[0] == "mock-a"


def test_live_league_mismatch_fails_before_database_mutation():
    database = RotationDatabase()

    with pytest.raises(RuntimeError, match="Configured league ID does not match"):
        rotate_draft_environment(
            database.connect,
            lambda draft_id: {
                **live_remote("live-draft"),
                "league_id": "different-league",
            },
            lambda draft_id: pytest.fail("picks must not be fetched"),
            "mock-a",
            "live-draft",
            "league",
            "LIVE",
        )

    assert not database.connections
    assert database.authoritative[0] == "mock-a"


def test_reset_failure_rolls_back_authority_and_derived_state():
    database = RotationDatabase()
    database.force_nonempty_after_clear = True

    with pytest.raises(RuntimeError, match="reset validation failed"):
        rotate(database, mock_remote("mock-b"), "mock-a", "mock-b", "MOCK")

    assert database.authoritative[0] == "mock-a"
    assert database.board
    assert database.rosters
    assert database.my_roster
    assert database.rotation_audits == []
    assert database.rotation_history == []
    assert database.connections[0].rollbacks == 1


def test_advisory_lock_serializes_rotation_transaction():
    database = RotationDatabase()

    rotate(database, mock_remote("mock-b"), "mock-a", "mock-b", "MOCK")

    statements = database.connections[0].cursor_instance.statements
    assert any("pg_advisory_xact_lock" in statement for statement, _ in statements)
