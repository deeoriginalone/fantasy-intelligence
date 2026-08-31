"""Validated draft-completion to season-active transition.

The transition is fail-closed, idempotent, and uses one caller-owned database
transaction. It relies only on schema verified in Batch C discovery.
"""
from __future__ import annotations

import json
from flask import Blueprint, jsonify
from auth import admin_required, csrf_required

COMPLETE_STATUSES = {"complete", "completed"}
STATE_KEY = "season_transition"


def _scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def evaluate_transition(cur, league_id, draft_id, remote_draft):
    remote_draft = remote_draft or {}
    errors = []
    if str(remote_draft.get("draft_id") or "") != str(draft_id):
        errors.append("Remote draft ID mismatch")
    if str(remote_draft.get("league_id") or "") != str(league_id):
        errors.append("Remote league ID mismatch")
    remote_status = str(remote_draft.get("status") or "").lower()
    if remote_status not in COMPLETE_STATUSES:
        errors.append("Remote draft is not complete")

    cur.execute(
        "SELECT draft_id,league_id,status,authoritative FROM draft_sessions "
        "WHERE draft_id=%s",
        (str(draft_id),),
    )
    session = cur.fetchone()
    if not session:
        errors.append("Draft session is missing")
    else:
        if str(session[1]) != str(league_id):
            errors.append("Draft session league ID mismatch")
        if not bool(session[3]):
            errors.append("Draft session is not authoritative")

    sleeper_picks = _scalar(
        cur,
        "SELECT count(*) FROM sleeper_draft_picks WHERE draft_id=%s",
        (str(draft_id),),
    )
    board_picks = _scalar(cur, "SELECT count(*) FROM draft_board WHERE drafted=true")
    roster_players = _scalar(cur, "SELECT count(*) FROM league_rosters")
    open_quarantine = _scalar(
        cur,
        "SELECT count(*) FROM draft_player_quarantine "
        "WHERE draft_id=%s AND status='OPEN'",
        (str(draft_id),),
    )
    multiple_owners = _scalar(
        cur,
        "SELECT count(*) FROM (SELECT player_name FROM league_rosters "
        "GROUP BY player_name HAVING count(DISTINCT team_name)>1) x",
    )
    roster_not_drafted = _scalar(
        cur,
        "SELECT count(*) FROM league_rosters r WHERE NOT EXISTS "
        "(SELECT 1 FROM draft_board d WHERE d.player_name=r.player_name "
        "AND d.drafted=true)",
    )
    drafted_without_owner = _scalar(
        cur,
        "SELECT count(*) FROM draft_board d WHERE d.drafted=true AND NOT EXISTS "
        "(SELECT 1 FROM league_rosters r WHERE r.player_name=d.player_name)",
    )
    my_roster_orphans = _scalar(
        cur,
        "SELECT count(*) FROM my_roster m WHERE NOT EXISTS "
        "(SELECT 1 FROM league_rosters r WHERE r.player_name=m.player_name)",
    )
    pending_outcomes = _scalar(
        cur,
        "SELECT count(*) FROM draft_decision_outcomes "
        "WHERE draft_id=%s AND actual_available IS NULL",
        (str(draft_id),),
    )

    if sleeper_picks == 0:
        errors.append("No synchronized draft picks")
    if sleeper_picks != board_picks:
        errors.append("Sleeper and draft-board pick counts differ")
    if sleeper_picks != roster_players:
        errors.append("Sleeper and league-roster pick counts differ")
    if open_quarantine:
        errors.append("Open player quarantine records remain")
    if multiple_owners:
        errors.append("Players have multiple owners")
    if roster_not_drafted:
        errors.append("Roster players are not marked drafted")
    if drafted_without_owner:
        errors.append("Drafted players have no owner")
    if my_roster_orphans:
        errors.append("My roster contains orphan players")

    return {
        "ready": not errors,
        "errors": errors,
        "remote_status": remote_status,
        "session": session,
        "counts": {
            "sleeper_picks": sleeper_picks,
            "draft_board": board_picks,
            "league_rosters": roster_players,
            "open_quarantine": open_quarantine,
            "multiple_owners": multiple_owners,
            "roster_not_drafted": roster_not_drafted,
            "drafted_without_owner": drafted_without_owner,
            "my_roster_orphans": my_roster_orphans,
            "pending_outcomes": pending_outcomes,
        },
    }


def finalize_transition(cur, league_id, draft_id, remote_draft, season=2026):
    check = evaluate_transition(cur, league_id, draft_id, remote_draft)
    if not check["ready"]:
        raise RuntimeError("; ".join(check["errors"]))

    cur.execute(
        "SELECT state_value FROM application_state WHERE state_key=%s FOR UPDATE",
        (STATE_KEY,),
    )
    row = cur.fetchone()
    existing = row[0] if row else None
    if existing and existing.get("draft_id") == str(draft_id) and existing.get("state") == "SEASON_ACTIVE":
        return {"changed": False, "state": existing, "validation": check}

    cur.execute("DELETE FROM drafted_players")
    cur.execute(
        "INSERT INTO drafted_players(player_name) "
        "SELECT player_name FROM league_rosters ORDER BY player_name"
    )
    cur.execute(
        "UPDATE available_players SET availability_status='AVAILABLE', "
        "drafted_by_owner=NULL,drafted_pick=NULL,last_updated=NOW()"
    )
    cur.execute(
        "UPDATE available_players ap SET availability_status='DRAFTED', "
        "drafted_by_owner=lr.team_name,drafted_pick=sp.pick_no,last_updated=NOW() "
        "FROM league_rosters lr LEFT JOIN sleeper_draft_picks sp "
        "ON sp.draft_id=%s AND sp.player_name=lr.player_name "
        "WHERE ap.player_name=lr.player_name",
        (str(draft_id),),
    )
    cur.execute(
        "UPDATE draft_sessions SET status='complete',authoritative=false," 
        "last_validated_at=NOW(),updated_at=NOW() WHERE draft_id=%s",
        (str(draft_id),),
    )
    state = {
        "state": "SEASON_ACTIVE",
        "league_id": str(league_id),
        "draft_id": str(draft_id),
        "season": int(season),
        "week": 1,
        "validation": check["counts"],
    }
    cur.execute(
        "INSERT INTO application_state(state_key,state_value,updated_at) "
        "VALUES(%s,%s::jsonb,NOW()) ON CONFLICT(state_key) DO UPDATE SET "
        "state_value=EXCLUDED.state_value,updated_at=NOW()",
        (STATE_KEY, json.dumps(state)),
    )
    cur.execute(
        "INSERT INTO application_state(state_key,state_value,updated_at) "
        "VALUES('current_week',%s::jsonb,NOW()) ON CONFLICT(state_key) DO UPDATE SET "
        "state_value=EXCLUDED.state_value,updated_at=NOW()",
        (json.dumps({"season": int(season), "week": 1}),),
    )
    return {"changed": True, "state": state, "validation": check}


def create_post_draft_blueprint(db, get_draft, league_id, draft_id, season=2026):
    bp = Blueprint("post_draft_transition", __name__, url_prefix="/post-draft")

    @bp.get("/readiness")
    def readiness():
        conn = db(); cur = conn.cursor()
        try:
            return jsonify(evaluate_transition(cur, league_id, draft_id, get_draft(draft_id) or {}))
        finally:
            cur.close(); conn.close()

    @bp.post("/finalize")
    @admin_required
    @csrf_required
    def finalize():
        conn = db(); cur = conn.cursor()
        try:
            result = finalize_transition(cur, league_id, draft_id, get_draft(draft_id) or {}, season)
            conn.commit()
            return jsonify(result)
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close(); conn.close()

    return bp
