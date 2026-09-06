import json
import logging

from flask import Blueprint, jsonify, request


LOGGER = logging.getLogger(__name__)
PROTECTED_LIVE_DRAFT_ID = "1398094331272794112"


def _is_verified_mock_draft(remote, draft_id):
    settings = remote.get("settings") or {}
    teams = settings.get("teams")
    rounds = settings.get("rounds")
    return (
        str(remote.get("draft_id") or "") == str(draft_id)
        and remote.get("league_id") is None
        and remote.get("status") in {"paused", "pre_draft"}
        and remote.get("type") == "snake"
        and isinstance(teams, int)
        and not isinstance(teams, bool)
        and teams > 0
        and isinstance(rounds, int)
        and not isinstance(rounds, bool)
        and rounds > 0
    )


def validate_identity(league_id, draft_id, remote, *, allow_mock=False):
    remote = remote or {}
    errors = []
    mock_draft = _is_verified_mock_draft(remote, draft_id)
    if str(remote.get("draft_id") or "") != str(draft_id):
        errors.append("Configured draft ID does not match Sleeper draft ID")
    if remote.get("league_id") is None and not (mock_draft and allow_mock):
        errors.append("Sleeper draft metadata is ambiguous without a league ID")
    elif remote.get("league_id") is not None and str(remote.get("league_id")) != str(league_id):
        errors.append("Configured league ID does not match Sleeper draft league ID")
    return {
        "valid": not errors,
        "errors": errors,
        "mock_draft": mock_draft,
        "draft_id": remote.get("draft_id"),
        "league_id": remote.get("league_id"),
        "season": remote.get("season"),
        "status": remote.get("status"),
    }


def _relation_exists(cur, relation_name):
    cur.execute("SELECT to_regclass(%s)", (relation_name,))
    row = cur.fetchone()
    return bool(row and row[0])


def ensure_schema(cur):
    """Create hardening-owned objects without assuming application tables exist."""
    statements = [
        """CREATE TABLE IF NOT EXISTS draft_sessions (
            draft_id varchar(50) PRIMARY KEY,
            league_id varchar(50) NOT NULL,
            season varchar(10),
            status varchar(25),
            authoritative boolean NOT NULL DEFAULT false,
            last_validated_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )""",
        """CREATE UNIQUE INDEX IF NOT EXISTS draft_sessions_one_authoritative_uidx
            ON draft_sessions ((authoritative)) WHERE authoritative=true""",
        """CREATE TABLE IF NOT EXISTS draft_sync_audit (
            id bigserial PRIMARY KEY,
            draft_id varchar(50) NOT NULL,
            league_id varchar(50) NOT NULL,
            status varchar(25) NOT NULL,
            received_count integer NOT NULL DEFAULT 0,
            stored_count integer NOT NULL DEFAULT 0,
            matched_count integer NOT NULL DEFAULT 0,
            quarantined_count integer NOT NULL DEFAULT 0,
            details jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS draft_player_quarantine (
            id bigserial PRIMARY KEY,
            draft_id varchar(50) NOT NULL,
            pick_no integer,
            player_id varchar(50),
            sleeper_name text,
            normalized_name text,
            reason text NOT NULL,
            payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            status varchar(25) NOT NULL DEFAULT 'OPEN',
            created_at timestamptz NOT NULL DEFAULT now(),
            resolved_at timestamptz
        )""",
        """CREATE UNIQUE INDEX IF NOT EXISTS draft_player_quarantine_open_uidx
            ON draft_player_quarantine(draft_id,pick_no)
            WHERE status='OPEN' AND pick_no IS NOT NULL""",
        """CREATE TABLE IF NOT EXISTS draft_mutation_history (
            id bigserial PRIMARY KEY,
            draft_id varchar(50) NOT NULL,
            action varchar(50) NOT NULL,
            player_name text,
            team_name text,
            source varchar(25) NOT NULL,
            before_state jsonb,
            after_state jsonb,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )""",
    ]
    for statement in statements:
        cur.execute(statement)

    # These indexes depend on application-owned tables. Create them only when
    # those tables already exist, so first-run hardening cannot fail early.
    if _relation_exists(cur, "sleeper_draft_picks"):
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS sleeper_draft_player_uidx
               ON sleeper_draft_picks(draft_id,player_id)
               WHERE player_id IS NOT NULL AND btrim(player_id) <> ''"""
        )
    if _relation_exists(cur, "my_roster"):
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS my_roster_player_name_uidx
               ON my_roster(player_name)
               WHERE player_name IS NOT NULL AND btrim(player_name) <> ''"""
        )


def _record_sync_audit(db, draft_id, league_id, status, details, result=None, quarantined=0):
    result = result or {}
    conn = db()
    cur = conn.cursor()
    try:
        ensure_schema(cur)
        cur.execute(
            """
            INSERT INTO draft_sync_audit(
                draft_id,league_id,status,received_count,stored_count,
                matched_count,quarantined_count,details
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            """,
            (
                str(draft_id),
                str(league_id),
                status,
                int(result.get("received", 0) or 0),
                int(result.get("stored", 0) or 0),
                int(result.get("matched_to_rankings", 0) or 0),
                int(quarantined or 0),
                json.dumps(details, default=str),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def detect_draft_transition(old_draft_id, new_draft_id):
    old_id = str(old_draft_id) if old_draft_id is not None else None
    new_id = str(new_draft_id) if new_draft_id is not None else None
    return old_id is not None and new_id is not None and old_id != new_id


def _log_session_event(event, *, old_draft_id, new_draft_id, rows_cleared=None, validation=None):
    LOGGER.info(
        event,
        extra={
            "draft_session_event": event,
            "old_draft_id": old_draft_id,
            "new_draft_id": new_draft_id,
            "rows_cleared": rows_cleared or {},
            "validation": validation or {},
        },
    )


def _derived_state_counts(cur):
    counts = {}
    for name, sql in (
        ("draft_board", "SELECT count(*) FROM draft_board WHERE drafted=true"),
        ("league_rosters", "SELECT count(*) FROM league_rosters"),
        ("my_roster", "SELECT count(*) FROM my_roster"),
    ):
        cur.execute(sql)
        counts[name] = int(cur.fetchone()[0] or 0)
    return counts


def _acquire_session_lock(cur):
    cur.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        ("fantasy-intelligence:draft-environment",),
    )


def _authoritative_session(cur, *, for_update=False):
    cur.execute(
        """SELECT draft_id, league_id, season, status
           FROM draft_sessions WHERE authoritative=true
           ORDER BY updated_at DESC LIMIT 1"""
        + (" FOR UPDATE" if for_update else "")
    )
    return cur.fetchone()


def current_rotation_mode(cur, draft_id):
    cur.execute(
        """SELECT details->>'mode'
           FROM draft_sync_audit
           WHERE draft_id=%s AND status='ROTATION_COMPLETED'
           ORDER BY id DESC LIMIT 1""",
        (str(draft_id),),
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def _capture_derived_state(cur):
    cur.execute(
        """SELECT player_name, starred, drafted
           FROM draft_board WHERE drafted=true ORDER BY player_name"""
    )
    board = cur.fetchall()
    cur.execute(
        """SELECT team_name, player_name, position, drafted_at
           FROM league_rosters ORDER BY id"""
    )
    rosters = cur.fetchall()
    cur.execute(
        """SELECT player_name, position, slot, drafted_at
           FROM my_roster ORDER BY id"""
    )
    my_roster = cur.fetchall()
    return {
        "draft_board": [list(row) for row in board],
        "league_rosters": [list(row) for row in rosters],
        "my_roster": [list(row) for row in my_roster],
    }


def _record_rotation_history(cur, *, old_draft_id, new_draft_id, mode, before_state):
    cur.execute(
        """INSERT INTO draft_mutation_history(
               draft_id, action, source, before_state, after_state, metadata
           ) VALUES(%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",
        (
            str(old_draft_id or new_draft_id),
            "DRAFT_ENVIRONMENT_ROTATION",
            "draft_environment",
            json.dumps(before_state, default=str),
            json.dumps({"draft_board": [], "league_rosters": [], "my_roster": []}),
            json.dumps({"old_draft_id": old_draft_id, "new_draft_id": new_draft_id, "mode": mode}),
        ),
    )


def _validate_empty_derived_state(counts):
    return all(counts.get(name) == 0 for name in ("draft_board", "league_rosters", "my_roster"))


def reset_draft_session(cur, *, old_draft_id, new_draft_id):
    _log_session_event(
        "DRAFT_SESSION_RESET_STARTED",
        old_draft_id=old_draft_id,
        new_draft_id=new_draft_id,
    )
    cur.execute("UPDATE draft_board SET drafted=false WHERE drafted=true")
    board_cleared = cur.rowcount
    cur.execute("DELETE FROM league_rosters")
    roster_cleared = cur.rowcount
    cur.execute("DELETE FROM my_roster")
    my_roster_cleared = cur.rowcount
    rows_cleared = {
        "draft_board": board_cleared,
        "league_rosters": roster_cleared,
        "my_roster": my_roster_cleared,
    }
    validation = _derived_state_counts(cur)
    if not _validate_empty_derived_state(validation):
        _log_session_event(
            "DRAFT_SESSION_RESET_FAILED",
            old_draft_id=old_draft_id,
            new_draft_id=new_draft_id,
            rows_cleared=rows_cleared,
            validation=validation,
        )
        raise RuntimeError("Draft session reset validation failed")
    _log_session_event(
        "DRAFT_SESSION_RESET_COMPLETED",
        old_draft_id=old_draft_id,
        new_draft_id=new_draft_id,
        rows_cleared=rows_cleared,
        validation=validation,
    )
    return {"rows_cleared": rows_cleared, "validation": validation}


def session_status(cur, *, league_id, configured_draft_id, remote, allow_mock=False):
    identity = validate_identity(
        league_id,
        configured_draft_id,
        remote,
        allow_mock=allow_mock,
    )
    stored = _authoritative_session(cur)
    old_draft_id = stored[0] if stored else None
    transition = detect_draft_transition(old_draft_id, configured_draft_id)
    identity_matches_session = stored is None or str(old_draft_id) == str(configured_draft_id)
    valid = identity["valid"] and identity_matches_session
    errors = list(identity["errors"])
    if not identity_matches_session:
        errors.append("Authoritative draft session does not match configured draft ID")
    return {
        "valid": valid,
        "errors": errors,
        "old_draft_id": old_draft_id,
        "new_draft_id": str(configured_draft_id),
        "transition": transition,
        "authoritative_session": stored,
        "identity": identity,
    }


def rotate_draft_environment(
    db,
    get_draft,
    get_draft_picks,
    old_draft_id,
    new_draft_id,
    league_id,
    mode,
    *,
    synchronize=None,
    synchronize_factory=None,
    refresh_health=None,
    protected_live_draft_id=None,
):
    mode = str(mode or "").upper()
    if mode not in {"LIVE", "MOCK"}:
        raise ValueError("mode must be LIVE or MOCK")

    remote = get_draft(str(new_draft_id)) or {}
    identity = validate_identity(
        league_id,
        str(new_draft_id),
        remote,
        allow_mock=mode == "MOCK",
    )
    if not identity["valid"]:
        raise RuntimeError("; ".join(identity["errors"]))
    if mode == "LIVE" and identity["mock_draft"]:
        raise RuntimeError("mock draft cannot authorize LIVE rotation")
    if mode == "MOCK" and not identity["mock_draft"]:
        raise RuntimeError("MOCK rotation requires verified mock metadata")
    if mode == "MOCK" and protected_live_draft_id is not None and str(new_draft_id) == str(protected_live_draft_id):
        raise RuntimeError("protected live draft cannot be rotated in MOCK mode")

    conn = db()
    cur = conn.cursor()
    try:
        ensure_schema(cur)
        _acquire_session_lock(cur)
        current = _authoritative_session(cur, for_update=True)
        current_id = str(current[0]) if current else None
        if old_draft_id is not None and current_id != str(old_draft_id):
            raise RuntimeError("authoritative draft changed during rotation")
        before_state = _capture_derived_state(cur)
        reset_result = reset_draft_session(
            cur,
            old_draft_id=current_id,
            new_draft_id=str(new_draft_id),
        )
        cur.execute(
            "UPDATE draft_sessions SET authoritative=false WHERE authoritative=true"
        )
        cur.execute(
            """INSERT INTO draft_sessions(
                   draft_id, league_id, season, status, authoritative, last_validated_at
               ) VALUES(%s,%s,%s,%s,true,now())
               ON CONFLICT(draft_id) DO UPDATE SET
                   league_id=excluded.league_id,
                   season=excluded.season,
                   status=excluded.status,
                   authoritative=true,
                   last_validated_at=now(),
                   updated_at=now()""",
            (str(new_draft_id), str(league_id), identity["season"], identity["status"]),
        )
        cur.execute(
            """INSERT INTO draft_sync_audit(
                   draft_id, league_id, status, received_count, stored_count,
                   matched_count, quarantined_count, details
               ) VALUES(%s,%s,%s,0,0,0,0,%s::jsonb)""",
            (
                str(new_draft_id),
                str(league_id),
                "ROTATION_COMPLETED",
                json.dumps({
                    "old_draft_id": current_id,
                    "new_draft_id": str(new_draft_id),
                    "mode": mode,
                    "before_counts": {
                        key: len(value) for key, value in before_state.items()
                    },
                    "after_counts": reset_result["validation"],
                }),
            ),
        )
        _record_rotation_history(
            cur,
            old_draft_id=current_id,
            new_draft_id=str(new_draft_id),
            mode=mode,
            before_state=before_state,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    result = {
        "old_draft_id": current_id,
        "new_draft_id": str(new_draft_id),
        "mode": mode,
        "identity": identity,
        "reset": reset_result,
    }
    try:
        result["remote_pick_count"] = len(get_draft_picks(str(new_draft_id)) or [])
        if synchronize is not None:
            result["synchronization"] = synchronize()
        if refresh_health is not None:
            result["health"] = refresh_health()
    except Exception as exc:
        _record_sync_audit(
            db,
            str(new_draft_id),
            league_id,
            "ROTATION_FAILED",
            {
                "old_draft_id": current_id,
                "new_draft_id": str(new_draft_id),
                "mode": mode,
                "error": str(exc),
            },
        )
        raise
    return result


def build_hardened_sync(
    original,
    db,
    get_draft,
    get_picks,
    league_id,
    draft_id,
    *,
    allow_mock=False,
):
    def run():
        remote = get_draft(draft_id) or {}
        identity = validate_identity(
            league_id,
            draft_id,
            remote,
            allow_mock=allow_mock,
        )
        if not identity["valid"]:
            raise RuntimeError("; ".join(identity["errors"]))

        conn = db()
        cur = conn.cursor()
        try:
            ensure_schema(cur)
            _acquire_session_lock(cur)
            current_status = session_status(
                cur,
                league_id=league_id,
                configured_draft_id=draft_id,
                remote=remote,
                allow_mock=allow_mock,
            )
            if not current_status["identity"]["valid"] or (
                not current_status["valid"] and not current_status["transition"]
            ):
                raise RuntimeError("; ".join(current_status["errors"]))
            if current_status["transition"]:
                _log_session_event(
                    "DRAFT_SESSION_TRANSITION",
                    old_draft_id=current_status["old_draft_id"],
                    new_draft_id=draft_id,
                )
                reset_draft_session(
                    cur,
                    old_draft_id=current_status["old_draft_id"],
                    new_draft_id=draft_id,
                )
            cur.execute(
                "UPDATE draft_sessions SET authoritative=false "
                "WHERE authoritative=true AND draft_id<>%s",
                (str(draft_id),),
            )
            cur.execute(
                """
                INSERT INTO draft_sessions(
                    draft_id,league_id,season,status,authoritative,last_validated_at
                )
                VALUES(%s,%s,%s,%s,true,now())
                ON CONFLICT(draft_id) DO UPDATE SET
                    league_id=excluded.league_id,
                    season=excluded.season,
                    status=excluded.status,
                    authoritative=true,
                    last_validated_at=now(),
                    updated_at=now()
                """,
                (
                    str(draft_id),
                    str(league_id),
                    identity["season"],
                    identity["status"],
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

        try:
            result = original()
        except Exception as exc:
            _record_sync_audit(
                db,
                draft_id,
                league_id,
                "FAILED",
                {"identity": identity, "error": str(exc)},
            )
            raise

        picks = get_picks(draft_id) or []
        quarantined = 0
        conn = db()
        cur = conn.cursor()
        try:
            ensure_schema(cur)
            for pick in picks:
                player_id = str(pick.get("player_id") or "")
                cur.execute(
                    """
                    SELECT local_player_name,matched,sleeper_name,normalized_name
                    FROM sleeper_player_map
                    WHERE sleeper_player_id=%s
                    """,
                    (player_id,),
                )
                row = cur.fetchone()
                if row and row[0] and row[1]:
                    cur.execute(
                        """
                        UPDATE draft_player_quarantine
                        SET status='RESOLVED', resolved_at=now()
                        WHERE draft_id=%s AND pick_no=%s AND status='OPEN'
                        """,
                        (str(draft_id), pick.get("pick_no")),
                    )
                    continue
                metadata = pick.get("metadata") or {}
                name = " ".join(
                    value
                    for value in [metadata.get("first_name"), metadata.get("last_name")]
                    if value
                ).strip() or (row[2] if row else player_id)
                cur.execute(
                    """
                    INSERT INTO draft_player_quarantine(
                        draft_id,pick_no,player_id,sleeper_name,normalized_name,
                        reason,payload
                    )
                    VALUES(%s,%s,%s,%s,%s,'No verified local player match',%s::jsonb)
                    ON CONFLICT (draft_id,pick_no)
                    WHERE status='OPEN' AND pick_no IS NOT NULL
                    DO UPDATE SET
                        player_id=excluded.player_id,
                        sleeper_name=excluded.sleeper_name,
                        normalized_name=excluded.normalized_name,
                        payload=excluded.payload
                    """,
                    (
                        str(draft_id),
                        pick.get("pick_no"),
                        player_id,
                        name,
                        row[3] if row else None,
                        json.dumps(pick, default=str),
                    ),
                )
                quarantined += 1
            conn.commit()
        except Exception as exc:
            conn.rollback()
            _record_sync_audit(
                db,
                draft_id,
                league_id,
                "FAILED",
                {"identity": identity, "error": str(exc), "phase": "quarantine"},
                result=result,
                quarantined=quarantined,
            )
            raise
        finally:
            cur.close()
            conn.close()

        _record_sync_audit(
            db,
            draft_id,
            league_id,
            "SUCCESS",
            identity,
            result=result,
            quarantined=quarantined,
        )
        output = dict(result)
        output.update(identity_valid=True, quarantined=quarantined)
        return output

    return run


def create_blueprint(
    db,
    get_draft,
    get_draft_picks,
    league_id,
    draft_id,
    *,
    synchronize=None,
    synchronize_factory=None,
    refresh_health=None,
    protected_live_draft_id=PROTECTED_LIVE_DRAFT_ID,
):
    from auth import admin_required, csrf_required

    bp = Blueprint("draft_state_hardening", __name__, url_prefix="/draft-hardening")

    @bp.get("/status")
    def status():
        identity = validate_identity(
            league_id,
            draft_id,
            get_draft(draft_id) or {},
        )
        conn = db()
        cur = conn.cursor()
        try:
            required = (
                "draft_sessions",
                "draft_sync_audit",
                "draft_player_quarantine",
                "draft_mutation_history",
            )
            schema = {name: _relation_exists(cur, name) for name in required}
            session = None
            open_quarantine = None
            if schema["draft_sessions"]:
                cur.execute(
                    """
                    SELECT draft_id,league_id,season,status,authoritative,last_validated_at
                    FROM draft_sessions
                    WHERE authoritative=true
                    """
                )
                session = cur.fetchone()
            if schema["draft_player_quarantine"]:
                cur.execute(
                    """
                    SELECT count(*) FROM draft_player_quarantine
                    WHERE draft_id=%s AND status='OPEN'
                    """,
                    (str(draft_id),),
                )
                open_quarantine = cur.fetchone()[0]
        finally:
            cur.close()
            conn.close()
        return jsonify(
            identity=identity,
            schema_ready=all(schema.values()),
            schema=schema,
            authoritative_session=session,
            open_quarantine=open_quarantine,
        )

    @bp.get("/session-status")
    def session_status_route():
        conn = db()
        cur = conn.cursor()
        try:
            ensure_schema(cur)
            state = session_status(
                cur,
                league_id=league_id,
                configured_draft_id=draft_id,
                remote=get_draft(draft_id) or {},
                allow_mock=current_rotation_mode(cur, draft_id) == "MOCK",
            )
            state["derived_state"] = _derived_state_counts(cur)
            return jsonify(state)
        finally:
            cur.close()
            conn.close()

    @bp.post("/reset-session")
    @admin_required
    def reset_session_route():
        conn = db()
        cur = conn.cursor()
        try:
            ensure_schema(cur)
            stored = _authoritative_session(cur)
            old_draft_id = stored[0] if stored else None
            remote = get_draft(draft_id) or {}
            identity = validate_identity(league_id, draft_id, remote)
            if not identity["valid"]:
                return jsonify(valid=False, errors=identity["errors"]), 409
            result = reset_draft_session(
                cur,
                old_draft_id=old_draft_id,
                new_draft_id=draft_id,
            )
            cur.execute(
                "UPDATE draft_sessions SET authoritative=false WHERE authoritative=true AND draft_id<>%s",
                (str(draft_id),),
            )
            cur.execute(
                """INSERT INTO draft_sessions(
                       draft_id,league_id,season,status,authoritative,last_validated_at
                   ) VALUES(%s,%s,%s,%s,true,now())
                   ON CONFLICT(draft_id) DO UPDATE SET
                       league_id=excluded.league_id, season=excluded.season,
                       status=excluded.status, authoritative=true,
                       last_validated_at=now(), updated_at=now()""",
                (str(draft_id), str(league_id), identity["season"], identity["status"]),
            )
            conn.commit()
            return jsonify(
                valid=True,
                old_draft_id=old_draft_id,
                new_draft_id=str(draft_id),
                **result,
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    @bp.post("/rotate")
    @admin_required
    @csrf_required
    def rotate_route():
        body = request.get_json(silent=True) or request.form
        destination = str(body.get("draft_id") or "").strip()
        mode = str(body.get("mode") or "").strip().upper()
        if not destination or not mode:
            return jsonify(error="draft_id and mode are required"), 400
        if destination != str(draft_id):
            return jsonify(
                error="destination must match the configured draft ID; restart after configuration change",
                configured_draft_id=str(draft_id),
            ), 409
        try:
            result = rotate_draft_environment(
                db,
                get_draft,
                get_draft_picks,
                old_draft_id=(
                    request.headers.get("X-Old-Draft-ID")
                    or body.get("old_draft_id")
                ),
                new_draft_id=destination,
                league_id=league_id,
                mode=mode,
                synchronize=(
                    synchronize_factory(destination, mode == "MOCK")
                    if synchronize_factory is not None
                    else synchronize
                ),
                refresh_health=refresh_health,
                protected_live_draft_id=(
                    protected_live_draft_id
                ),
            )
            return jsonify(result)
        except (RuntimeError, ValueError) as exc:
            return jsonify(error=str(exc)), 409

    return bp
