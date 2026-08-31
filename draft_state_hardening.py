import json

from flask import Blueprint, jsonify


def validate_identity(league_id, draft_id, remote):
    remote = remote or {}
    errors = []
    if str(remote.get("draft_id") or "") != str(draft_id):
        errors.append("Configured draft ID does not match Sleeper draft ID")
    if str(remote.get("league_id") or "") != str(league_id):
        errors.append("Configured league ID does not match Sleeper draft league ID")
    return {
        "valid": not errors,
        "errors": errors,
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


def build_hardened_sync(original, db, get_draft, get_picks, league_id, draft_id):
    def run():
        remote = get_draft(draft_id) or {}
        identity = validate_identity(league_id, draft_id, remote)
        if not identity["valid"]:
            raise RuntimeError("; ".join(identity["errors"]))

        conn = db()
        cur = conn.cursor()
        try:
            ensure_schema(cur)
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


def create_blueprint(db, get_draft, league_id, draft_id):
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

    return bp
