import pytest

from draft_state_hardening import (
	detect_draft_transition,
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

	def execute(self, statement, params=()):
		self.statements.append((statement, params))
		if statement.startswith("UPDATE draft_board"):
			self.rowcount = 2
		elif statement.startswith("DELETE FROM league_rosters"):
			self.rowcount = 2
		elif statement.startswith("DELETE FROM my_roster"):
			self.rowcount = 1

	def fetchone(self):
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
