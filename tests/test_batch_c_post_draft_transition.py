"""Batch C transition tests without loading production config or secrets."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_transition_module():
    flask = types.ModuleType("flask")
    class Blueprint:
        def __init__(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            return lambda fn: fn
        def post(self, *args, **kwargs):
            return lambda fn: fn
    flask.Blueprint = Blueprint
    flask.jsonify = lambda value: value
    auth = types.ModuleType("auth")
    auth.admin_required = lambda fn: fn
    auth.csrf_required = lambda fn: fn
    original_flask = sys.modules.get("flask")
    original_auth = sys.modules.get("auth")
    sys.modules["flask"] = flask
    sys.modules["auth"] = auth
    try:
        spec = importlib.util.spec_from_file_location(
            "post_draft_transition_under_test",
            ROOT / "post_draft_transition.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if original_flask is None:
            sys.modules.pop("flask", None)
        else:
            sys.modules["flask"] = original_flask
        if original_auth is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = original_auth


transition = _load_transition_module()
evaluate_transition = transition.evaluate_transition
finalize_transition = transition.finalize_transition


class Cursor:
    def __init__(self, one):
        self.one = list(one)
        self.executed = []
    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
    def fetchone(self):
        return self.one.pop(0) if self.one else None


def ready_cursor(state_row=None):
    rows = [("d", "l", "in_progress", True)]
    rows += [(10,), (10,), (10,), (0,), (0,), (0,), (0,), (0,), (2,)]
    rows.append((state_row,) if state_row is not None else None)
    return Cursor(rows)


def remote(status="complete"):
    return {"draft_id": "d", "league_id": "l", "status": status}


def test_ready_when_identity_counts_and_invariants_pass():
    result = evaluate_transition(ready_cursor(), "l", "d", remote())
    assert result["ready"] is True
    assert result["counts"]["pending_outcomes"] == 2


def test_remote_draft_must_be_complete():
    result = evaluate_transition(ready_cursor(), "l", "d", remote("in_progress"))
    assert result["ready"] is False
    assert "Remote draft is not complete" in result["errors"]


def test_count_mismatch_blocks_transition():
    rows = [("d", "l", "in_progress", True)]
    rows += [(10,), (9,), (10,), (0,), (0,), (0,), (0,), (0,), (0,)]
    result = evaluate_transition(Cursor(rows), "l", "d", remote())
    assert result["ready"] is False
    assert "Sleeper and draft-board pick counts differ" in result["errors"]


def test_finalize_is_idempotent_when_state_is_active():
    state = {"state": "SEASON_ACTIVE", "draft_id": "d"}
    cur = ready_cursor(state)
    result = finalize_transition(cur, "l", "d", remote())
    assert result["changed"] is False
    assert not any("DELETE FROM drafted_players" in sql for sql, _ in cur.executed)


def test_finalize_materializes_and_transitions():
    cur = ready_cursor()
    result = finalize_transition(cur, "l", "d", remote())
    assert result["changed"] is True
    sql = " ".join(value[0] for value in cur.executed)
    assert "DELETE FROM drafted_players" in sql
    assert "UPDATE available_players" in sql
    assert "UPDATE draft_sessions SET status='complete'" in sql
    assert "VALUES('current_week'" in sql
