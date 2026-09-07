import psycopg2
import pytest

from draft_state_hardening import (
	_capture_derived_state,
	_derived_state_counts,
	detect_draft_transition,
	ensure_schema,
	reset_draft_session,
	session_status,
	validate_identity,
)


class ResetCursor:
	def __init__(self, counts=(0, 0, 0), session=None):
		self.counts = list(counts)
		self.session = session
		self.statements = []
		self.rowcount = 0
		self.pending = None

	def execute(self, statement, params=()):
		self.statements.append((statement, params))
		if statement.startswith("SELECT to_regclass"):
			relation = params[0] if params else ""
			self.pending = (relation,)
			return
		if statement.startswith("UPDATE draft_board"):
			self.rowcount = 2
		elif statement.startswith("DELETE FROM league_rosters"):
			self.rowcount = 2
		elif statement.startswith("DELETE FROM my_roster"):
			self.rowcount = 1

	def fetchone(self):
		if self.pending is not None:
			pending, self.pending = self.pending, None
			return (pending[0] if pending else None,)
		if self.session is not None:
			session, self.session = self.session, None
			return session
		return (self.counts.pop(0),)


def test_reset_clears_only_derived_tables_and_preserves_history_tables():
	cur = ResetCursor()

	result = reset_draft_session(cur, old_draft_id="draft-a", new_draft_id="draft-b")

	assert result["validation"] == {
		"draft_board": 0,
		"league_rosters": 0,
		"my_roster": 0,
	}
	statements = " ".join(statement for statement, _ in cur.statements)
	assert "draft_events" not in statements
	assert "draft_selections" not in statements
	assert "draft_sync_audit" not in statements
	assert "draft_reconciliation_runs" not in statements


def test_reset_validation_failure_fails_closed():
	cur = ResetCursor(counts=(1, 0, 0))

	with pytest.raises(RuntimeError, match="reset validation failed"):
		reset_draft_session(cur, old_draft_id="draft-a", new_draft_id="draft-b")


def test_session_status_fails_closed_on_authoritative_identity_mismatch():
	cur = ResetCursor(session=("draft-a", "league", "2026", "paused"))

	state = session_status(
		cur,
		league_id="league",
		configured_draft_id="draft-b",
		remote={"draft_id": "draft-b", "league_id": "league"},
	)

	assert state["valid"] is False
	assert state["transition"] is True
	assert "Authoritative draft session does not match configured draft ID" in state["errors"]


def test_draft_transition_detects_changed_authoritative_id():
	assert detect_draft_transition("draft-a", "draft-b") is True
	assert detect_draft_transition("draft-a", "draft-a") is False
	assert detect_draft_transition(None, "draft-a") is False


def test_derived_state_counts_default_to_zero_when_tables_are_missing():
	class MissingDerivedTablesCursor:
		def execute(self, statement, params=()):
			if "FROM draft_board" in statement or "FROM league_rosters" in statement or "FROM my_roster" in statement:
				raise psycopg2.errors.UndefinedTable("relation does not exist")
			self.statement = statement
		def fetchone(self):
			return (0,)

	result = _derived_state_counts(MissingDerivedTablesCursor())
	assert result == {"draft_board": 0, "league_rosters": 0, "my_roster": 0}


def test_ensure_schema_bootstraps_health_and_calibration_tables_for_fresh_db():
	class RecordingCursor:
		def __init__(self):
			self.executed = []
		def execute(self, statement, params=()):
			self.executed.append(" ".join(statement.split()).lower())
		def fetchone(self):
			return (None,)

	cur = RecordingCursor()
	ensure_schema(cur)

	assert any("create table if not exists draft_decision_outcomes" in statement for statement in cur.executed)
	assert any("create table if not exists draft_reconciliation_runs" in statement for statement in cur.executed)
	assert any("create table if not exists draft_board" in statement for statement in cur.executed)
	assert any("create table if not exists league_rosters" in statement for statement in cur.executed)
	assert any("create table if not exists my_roster" in statement for statement in cur.executed)
	assert any("create table if not exists league_teams" in statement for statement in cur.executed)
	assert any("create table if not exists players" in statement for statement in cur.executed)
	assert any("create unique index if not exists sleeper_api_snapshots_uidx" in statement for statement in cur.executed)


def test_capture_derived_state_defaults_to_empty_when_tables_are_missing():
	class MissingDerivedTablesCursor:
		def execute(self, statement, params=()):
			if "SELECT to_regclass" in statement:
				self.pending = (None,)
				return
			if any(name in statement for name in ("FROM draft_board", "FROM league_rosters", "FROM my_roster")):
				raise psycopg2.errors.UndefinedTable("relation does not exist")
		def fetchone(self):
			if getattr(self, 'pending', None) is not None:
				pending, self.pending = self.pending, None
				return pending
			return (None,)
		def fetchall(self):
			return []

	result = _capture_derived_state(MissingDerivedTablesCursor())
	assert result == {"draft_board": [], "league_rosters": [], "my_roster": []}


def test_reset_draft_session_ignores_missing_derived_tables_on_first_run():
	class MissingTableCursor:
		def __init__(self):
			self.rowcount = 0
			self.pending = None
		def execute(self, statement, params=()):
			if "SELECT to_regclass" in statement:
				self.pending = (None,)
				return
			if "draft_board" in statement or "league_rosters" in statement or "my_roster" in statement:
				raise psycopg2.errors.UndefinedTable("relation does not exist")
		def fetchone(self):
			if self.pending is not None:
				pending, self.pending = self.pending, None
				return pending
			return (0,)

	cur = MissingTableCursor()
	result = reset_draft_session(cur, old_draft_id="old", new_draft_id="new")
	assert result["validation"] == {"draft_board": 0, "league_rosters": 0, "my_roster": 0}
	assert result["rows_cleared"] == {"draft_board": 0, "league_rosters": 0, "my_roster": 0}


def test_standalone_mock_metadata_uses_configured_league_when_allowed():
	remote = {
		'draft_id': 'd',
		'league_id': None,
		'status': 'pre_draft',
		'type': 'snake',
		'metadata': {'league_id': 'l'},
		'settings': {'teams': 10, 'rounds': 15},
	}
	result = validate_identity('l', 'd', remote, allow_mock=True)
	assert result['valid'] is True
	assert result['league_id'] == 'l'


def test_identity_valid(): assert validate_identity('l','d',{'league_id':'l','draft_id':'d'})['valid']
def test_pre_draft_mock_identity_requires_explicit_mock_mode():
	remote = {
		'league_id': None,
		'draft_id': 'd',
		'status': 'pre_draft',
		'type': 'snake',
		'settings': {'teams': 10, 'rounds': 15},
	}
	assert not validate_identity('l', 'd', remote)['valid']
	assert validate_identity(
		'l',
		'd',
		remote,
		allow_mock=True,
	)['valid']
def test_draft_mismatch(): assert not validate_identity('l','d',{'league_id':'l','draft_id':'x'})['valid']
def test_league_mismatch(): assert not validate_identity('l','d',{'league_id':'x','draft_id':'d'})['valid']
