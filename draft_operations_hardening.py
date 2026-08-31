import json

from flask import Blueprint, jsonify, redirect, render_template, url_for


def state(cur, player_name):
    cur.execute(
        "SELECT drafted, starred FROM draft_board WHERE player_name=%s",
        (player_name,),
    )
    board = cur.fetchone()
    cur.execute(
        "SELECT id, team_name, position FROM league_rosters "
        "WHERE player_name=%s ORDER BY id",
        (player_name,),
    )
    league = cur.fetchall()
    cur.execute(
        "SELECT id, position, slot FROM my_roster "
        "WHERE player_name=%s ORDER BY id",
        (player_name,),
    )
    mine = cur.fetchall()
    return {"board": board, "league": league, "mine": mine}


def audit(
    cur,
    draft_id,
    action,
    player_name,
    team_name,
    source,
    before_state,
    after_state,
    metadata=None,
):
    cur.execute(
        """
        INSERT INTO draft_mutation_history(
            draft_id, action, player_name, team_name, source,
            before_state, after_state, metadata
        )
        VALUES(%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
        """,
        (
            str(draft_id),
            action,
            player_name,
            team_name,
            source,
            json.dumps(before_state, default=str),
            json.dumps(after_state, default=str),
            json.dumps(metadata or {}, default=str),
        ),
    )


def invariants(cur):
    cur.execute(
        """
        SELECT player_name, array_agg(DISTINCT team_name)
        FROM league_rosters
        GROUP BY player_name
        HAVING count(DISTINCT team_name) > 1
        """
    )
    multiple_owners = cur.fetchall()
    cur.execute(
        """
        SELECT lr.player_name
        FROM league_rosters lr
        LEFT JOIN draft_board d ON d.player_name = lr.player_name
        WHERE coalesce(d.drafted, false) = false
        """
    )
    roster_not_drafted = cur.fetchall()
    cur.execute(
        """
        SELECT d.player_name
        FROM draft_board d
        WHERE d.drafted = true
          AND NOT EXISTS(
              SELECT 1 FROM league_rosters r
              WHERE r.player_name = d.player_name
          )
        """
    )
    drafted_without_owner = cur.fetchall()
    cur.execute(
        """
        SELECT m.player_name
        FROM my_roster m
        WHERE NOT EXISTS(
            SELECT 1 FROM league_rosters r
            WHERE r.player_name = m.player_name
        )
        """
    )
    my_roster_orphans = cur.fetchall()
    return {
        "multiple_owners": multiple_owners,
        "roster_not_drafted": roster_not_drafted,
        "drafted_without_owner": drafted_without_owner,
        "my_roster_orphans": my_roster_orphans,
        "valid": not (
            multiple_owners
            or roster_not_drafted
            or drafted_without_owner
            or my_roster_orphans
        ),
    }


def track(req, db, available, draft_id):
    error = message = None
    if req.method == "POST":
        team_name = (req.form.get("team_name") or "").strip()
        player_name = (req.form.get("player_name") or "").strip()
        if not team_name or not player_name:
            error = "Select both a team and a player."
        else:
            conn = db()
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT position FROM players WHERE player_name=%s",
                    (player_name,),
                )
                player = cur.fetchone()
                cur.execute(
                    "SELECT 1 FROM league_teams WHERE team_name=%s",
                    (team_name,),
                )
                team = cur.fetchone()
                cur.execute(
                    "SELECT team_name FROM league_rosters "
                    "WHERE player_name=%s FOR UPDATE",
                    (player_name,),
                )
                owner = cur.fetchone()
                if not player:
                    error = "The selected player was not found."
                elif not team:
                    error = "The selected team was not found."
                elif owner:
                    error = f"{player_name} has already been drafted by {owner[0]}."
                else:
                    before = state(cur, player_name)
                    position = player[0]
                    cur.execute(
                        "INSERT INTO league_rosters(team_name,player_name,position) "
                        "VALUES(%s,%s,%s)",
                        (team_name, player_name, position),
                    )
                    cur.execute(
                        """
                        INSERT INTO draft_board(player_name,starred,drafted)
                        VALUES(%s,false,true)
                        ON CONFLICT(player_name) DO UPDATE SET drafted=true
                        """,
                        (player_name,),
                    )
                    if team_name == "My Team":
                        cur.execute(
                            """
                            INSERT INTO my_roster(player_name,position)
                            SELECT %s,%s
                            WHERE NOT EXISTS(
                                SELECT 1 FROM my_roster WHERE player_name=%s
                            )
                            """,
                            (player_name, position, player_name),
                        )
                    after = state(cur, player_name)
                    validation = invariants(cur)
                    if not validation["valid"]:
                        raise RuntimeError(
                            "Invariant violation " + json.dumps(validation, default=str)
                        )
                    audit(
                        cur,
                        draft_id,
                        "MANUAL_PICK",
                        player_name,
                        team_name,
                        "trackdraft",
                        before,
                        after,
                        {"position": position},
                    )
                    conn.commit()
                    message = f"Recorded {player_name} to {team_name}."
            except Exception as exc:
                conn.rollback()
                error = str(exc)
            finally:
                cur.close()
                conn.close()

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT team_name FROM league_teams ORDER BY id")
        teams = [row[0] for row in cur.fetchall()]
        available_players = available(cur)
        cur.execute(
            """
            SELECT id,team_name,player_name,position,drafted_at
            FROM league_rosters
            ORDER BY drafted_at DESC,id DESC
            LIMIT 20
            """
        )
        recent = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template(
        "trackdraft.html",
        title="Draft Tracker",
        teams=teams,
        available_players=available_players,
        recent_picks=recent,
        message=message,
        error=error,
    )


def undo(req, db, draft_id):
    pick_id = (req.form.get("pick_id") or "").strip()
    if not pick_id.isdigit():
        return redirect(url_for("track_draft"))
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT team_name,player_name,position FROM league_rosters "
            "WHERE id=%s FOR UPDATE",
            (int(pick_id),),
        )
        row = cur.fetchone()
        if row:
            team_name, player_name, position = row
            before = state(cur, player_name)
            cur.execute("DELETE FROM league_rosters WHERE id=%s", (int(pick_id),))
            cur.execute(
                "SELECT 1 FROM league_rosters WHERE player_name=%s",
                (player_name,),
            )
            owned = cur.fetchone() is not None
            cur.execute(
                "UPDATE draft_board SET drafted=%s WHERE player_name=%s",
                (owned, player_name),
            )
            if not owned:
                cur.execute(
                    "DELETE FROM my_roster WHERE player_name=%s",
                    (player_name,),
                )
            after = state(cur, player_name)
            validation = invariants(cur)
            if not validation["valid"]:
                raise RuntimeError(
                    "Invariant violation " + json.dumps(validation, default=str)
                )
            audit(
                cur,
                draft_id,
                "UNDO_PICK",
                player_name,
                team_name,
                "trackdraft_undo",
                before,
                after,
                {"pick_id": int(pick_id), "position": position},
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("track_draft"))


def blueprint(db, draft_id):
    bp = Blueprint("draft_operations", __name__, url_prefix="/draft-operations")

    @bp.get("/health")
    def health():
        conn = db()
        cur = conn.cursor()
        try:
            validation = invariants(cur)
            cur.execute(
                "SELECT count(*) FROM draft_mutation_history WHERE draft_id=%s",
                (str(draft_id),),
            )
            mutation_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT action,player_name,team_name,source,created_at
                FROM draft_mutation_history
                WHERE draft_id=%s
                ORDER BY id DESC
                LIMIT 10
                """,
                (str(draft_id),),
            )
            recent_mutations = cur.fetchall()
        finally:
            cur.close()
            conn.close()
        return jsonify(
            draft_id=str(draft_id),
            invariants=validation,
            mutation_count=mutation_count,
            recent_mutations=recent_mutations,
        )

    return bp
