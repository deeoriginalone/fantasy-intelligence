from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from auth import admin_required


def create_sandbox_blueprint(get_db_connection):
    bp = Blueprint("season_sandbox", __name__)

    def ensure_tables(cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS application_state (
                state_key VARCHAR(100) PRIMARY KEY,
                state_value JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id SERIAL PRIMARY KEY,
                data_mode VARCHAR(20) NOT NULL,
                sandbox_draft_id INTEGER,
                recommendation_type VARCHAR(40) NOT NULL,
                subject VARCHAR(255),
                action VARCHAR(255),
                score NUMERIC(10,2),
                confidence VARCHAR(20),
                details JSONB NOT NULL DEFAULT '{}'::jsonb,
                status VARCHAR(25) NOT NULL DEFAULT 'proposed',
                created_at TIMESTAMP DEFAULT NOW(),
                resolved_at TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS recommendation_history_context_idx
            ON recommendation_history (
                data_mode,
                sandbox_draft_id,
                recommendation_type,
                created_at DESC
            )
            """
        )

    def get_persisted_state(cur):
        ensure_tables(cur)
        cur.execute(
            """
            SELECT state_value
            FROM application_state
            WHERE state_key = 'active_sandbox'
            """
        )
        row = cur.fetchone()
        return row[0] if row else None

    def persist_state(cur, state):
        cur.execute(
            """
            INSERT INTO application_state (state_key, state_value, updated_at)
            VALUES ('active_sandbox', %s::jsonb, NOW())
            ON CONFLICT (state_key)
            DO UPDATE SET
                state_value = EXCLUDED.state_value,
                updated_at = NOW()
            """,
            (__import__("json").dumps(state),),
        )

    def clear_state(cur):
        cur.execute(
            "DELETE FROM application_state WHERE state_key = 'active_sandbox'"
        )

    def list_completed_slot_five(cur):
        cur.execute(
            """
            SELECT
                id,
                draft_name,
                strategy,
                teams,
                rounds,
                draft_position,
                status,
                overall_grade,
                roster_score,
                current_pick,
                created_at
            FROM mock_drafts
            WHERE teams = 10
              AND draft_position = 5
              AND status = 'complete'
            ORDER BY
                CASE
                    WHEN draft_name LIKE 'Draft #%'
                    THEN 0
                    ELSE 1
                END,
                created_at DESC
            LIMIT 50
            """
        )
        columns = [
            "id", "draft_name", "strategy", "teams", "rounds",
            "draft_position", "status", "overall_grade", "roster_score",
            "current_pick", "created_at",
        ]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_mock_summary(cur, draft_id):
        cur.execute(
            """
            SELECT
                id,
                draft_name,
                strategy,
                teams,
                rounds,
                draft_position,
                status,
                overall_grade,
                roster_score,
                current_pick,
                created_at
            FROM mock_drafts
            WHERE id = %s
            """,
            (draft_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        columns = [
            "id", "draft_name", "strategy", "teams", "rounds",
            "draft_position", "status", "overall_grade", "roster_score",
            "current_pick", "created_at",
        ]
        result = dict(zip(columns, row))
        cur.execute(
            """
            SELECT COUNT(*)
            FROM mock_picks
            WHERE draft_id = %s
              AND draft_slot = %s
            """,
            (draft_id, result["draft_position"]),
        )
        result["roster_players"] = cur.fetchone()[0]
        return result

    def get_sandbox_roster(cur, draft_id):
        cur.execute(
            """
            SELECT
                mp.round_num,
                mp.pick_no,
                mp.player_name,
                UPPER(mp.position),
                mp.nfl_team,
                mp.overall_rank,
                mp.draft_score,
                p.projected_points,
                p.tier,
                p.adp,
                p.bye_week,
                p.injury_status
            FROM mock_picks mp
            JOIN mock_drafts md
              ON md.id = mp.draft_id
            LEFT JOIN players p
              ON p.player_name = mp.player_name
            WHERE mp.draft_id = %s
              AND mp.draft_slot = md.draft_position
            ORDER BY mp.pick_no
            """,
            (draft_id,),
        )
        columns = [
            "round", "pick_no", "player", "position", "nfl_team", "rank",
            "draft_score", "projection", "tier", "adp", "bye_week",
            "injury_status",
        ]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def current_context():
        mode = session.get("data_mode")
        draft_id = session.get("sandbox_draft_id")
        if mode == "MOCK" and draft_id:
            return {"mode": "MOCK", "sandbox_draft_id": int(draft_id)}

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            state = get_persisted_state(cur)
            conn.commit()
        finally:
            cur.close()
            conn.close()

        if state and state.get("mode") == "MOCK" and state.get("draft_id"):
            session["data_mode"] = "MOCK"
            session["sandbox_draft_id"] = int(state["draft_id"])
            return {
                "mode": "MOCK",
                "sandbox_draft_id": int(state["draft_id"]),
            }
        return {"mode": "LIVE", "sandbox_draft_id": None}

    @bp.app_context_processor
    def inject_data_mode():
        try:
            return {"data_context": current_context()}
        except Exception as exc:
            current_app.logger.warning("Unable to load data mode: %s", exc)
            return {"data_context": {"mode": "LIVE", "sandbox_draft_id": None}}

    @bp.route("/sandbox")
    def sandbox_home():
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            ensure_tables(cur)
            drafts = list_completed_slot_five(cur)
            context = current_context()
            active = None
            roster = []
            if context["mode"] == "MOCK":
                active = get_mock_summary(cur, context["sandbox_draft_id"])
                roster = get_sandbox_roster(cur, context["sandbox_draft_id"])
            conn.commit()
        finally:
            cur.close()
            conn.close()
        return render_template(
            "season_sandbox.html",
            title="Season Sandbox",
            drafts=drafts,
            active=active,
            roster=roster,
            context=context,
        )

    @bp.route("/sandbox/activate/<int:draft_id>", methods=["POST"])
    @admin_required
    def activate_sandbox(draft_id):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            ensure_tables(cur)
            summary = get_mock_summary(cur, draft_id)
            if not summary or summary["status"] != "complete":
                return "Completed mock draft not found", 404
            state = {
                "mode": "MOCK",
                "draft_id": draft_id,
                "description": summary["draft_name"],
            }
            persist_state(cur, state)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
        session["data_mode"] = "MOCK"
        session["sandbox_draft_id"] = draft_id
        return redirect(url_for("season_sandbox.sandbox_home"))

    @bp.route("/sandbox/live", methods=["POST"])
    @admin_required
    def exit_sandbox():
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            ensure_tables(cur)
            clear_state(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
        session.pop("data_mode", None)
        session.pop("sandbox_draft_id", None)
        return redirect(url_for("season_sandbox.sandbox_home"))

    # Export helpers on the blueprint so future modules can reuse them.
    bp.get_current_context = current_context
    bp.get_sandbox_roster = get_sandbox_roster
    bp.ensure_tables = ensure_tables
    return bp
