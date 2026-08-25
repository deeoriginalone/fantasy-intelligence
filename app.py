from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os

import psycopg2

from services.import_rankings import import_rankings


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5433,
        database="fantasy_intelligence",
        user="fantasy",
        password="fantasy",
    )


def get_league():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT league_name, team_name, teams, scoring_type
        FROM league_info
        LIMIT 1
        """
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def build_roster_slots(roster):
    slots = {
        "QB": None,
        "RB1": None,
        "RB2": None,
        "WR1": None,
        "WR2": None,
        "TE": None,
        "FLEX": None,
    }
    bench = []

    for player in roster:
        position = player[2]

        if position == "QB" and slots["QB"] is None:
            slots["QB"] = player
        elif position == "RB" and slots["RB1"] is None:
            slots["RB1"] = player
        elif position == "RB" and slots["RB2"] is None:
            slots["RB2"] = player
        elif position == "WR" and slots["WR1"] is None:
            slots["WR1"] = player
        elif position == "WR" and slots["WR2"] is None:
            slots["WR2"] = player
        elif position == "TE" and slots["TE"] is None:
            slots["TE"] = player
        elif position in {"RB", "WR", "TE"} and slots["FLEX"] is None:
            slots["FLEX"] = player
        else:
            bench.append(player)

    return slots, bench


def fetch_available_players(cur):
    cur.execute(
        """
        SELECT p.ranking, p.player_name, p.position, p.nfl_team
        FROM players p
        WHERE NOT EXISTS (
            SELECT 1
            FROM league_rosters lr
            WHERE lr.player_name = p.player_name
        )
          AND NOT EXISTS (
            SELECT 1
            FROM draft_board db
            WHERE db.player_name = p.player_name
              AND db.drafted = true
        )
        ORDER BY p.ranking
        """
    )
    return cur.fetchall()


@app.route("/")
def dashboard():
    league = get_league()

    if league is None:
        return render_template(
            "dashboard.html",
            title="Fantasy Intelligence Dashboard",
            league_name="Fantasy Intelligence",
            team_name="Not configured",
            teams="Not configured",
            scoring_type="Not configured",
        )

    return render_template(
        "dashboard.html",
        title="Fantasy Intelligence Dashboard",
        league_name=league[0],
        team_name=league[1],
        teams=league[2],
        scoring_type=league[3],
    )


@app.route("/predraft")
def predraft():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ranking, player_name, position, nfl_team
        FROM players
        ORDER BY ranking
        LIMIT 25
        """
    )
    players = cur.fetchall()

    counts = {}
    tops = {}

    for position in ["QB", "RB", "WR", "TE"]:
        cur.execute(
            "SELECT COUNT(*) FROM players WHERE position = %s",
            (position,),
        )
        counts[position] = cur.fetchone()[0]

        cur.execute(
            """
            SELECT ranking, player_name
            FROM players
            WHERE position = %s
            ORDER BY ranking
            LIMIT 10
            """,
            (position,),
        )
        tops[position] = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "predraft.html",
        title="Predraft Intelligence Lab",
        players=players,
        qb_count=counts["QB"],
        rb_count=counts["RB"],
        wr_count=counts["WR"],
        te_count=counts["TE"],
        top_qbs=tops["QB"],
        top_rbs=tops["RB"],
        top_wrs=tops["WR"],
        top_tes=tops["TE"],
        best_pick=players[0][1] if players else None,
    )


@app.route("/imports", methods=["GET", "POST"])
def imports():
    if request.method == "POST":
        uploaded_file = request.files.get("file")

        if uploaded_file is None or not uploaded_file.filename:
            return "No file selected", 400

        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        uploaded_file.save(filepath)
        import_rankings(filepath)

        return f"Imported: {filename}"

    return render_template("imports.html", title="Imports")


@app.route("/agents")
def agents():
    return render_template("agents.html", title="Agents")


@app.route("/draftcenter")
def draftcenter():
    return render_template("draftcenter.html", title="Draft Center")


@app.route("/draftboard")
def draftboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            p.ranking,
            p.player_name,
            p.position,
            p.nfl_team,
            COALESCE(d.starred, false),
            (
                COALESCE(d.drafted, false)
                OR EXISTS (
                    SELECT 1
                    FROM league_rosters lr
                    WHERE lr.player_name = p.player_name
                )
            ) AS drafted
        FROM players p
        LEFT JOIN draft_board d
            ON p.player_name = d.player_name
        ORDER BY p.ranking
        LIMIT 50
        """
    )
    players = cur.fetchall()

    cur.execute(
        """
        SELECT id, player_name, position, COALESCE(slot, '')
        FROM my_roster
        WHERE player_name IS NOT NULL
          AND BTRIM(player_name) <> ''
        ORDER BY drafted_at, id
        """
    )
    roster = cur.fetchall()

    cur.close()
    conn.close()

    roster_names = {player[1] for player in roster}
    available_players = [
        player
        for player in players
        if not player[5] and player[1] not in roster_names
    ]

    best_available = available_players[0] if available_players else None
    position_leaders = {
        position: next(
            (player for player in available_players if player[2] == position),
            None,
        )
        for position in ["QB", "RB", "WR", "TE"]
    }
    draft_targets = [player for player in available_players if player[4]]
    drafted_count = sum(1 for player in players if player[5])
    roster_slots, bench = build_roster_slots(roster)

    needed_positions = []
    for slot, roster_player in roster_slots.items():
        if roster_player is not None or slot == "FLEX":
            continue
        position = slot.rstrip("12")
        if position not in needed_positions:
            needed_positions.append(position)

    team_recommendation = next(
        (player for player in available_players if player[2] in needed_positions),
        best_available,
    )

    return render_template(
        "draftboard.html",
        title="My Draft Board",
        players=players,
        available_players=available_players,
        best_available=best_available,
        position_leaders=position_leaders,
        draft_targets=draft_targets,
        drafted_count=drafted_count,
        roster=roster,
        roster_slots=roster_slots,
        bench=bench,
        team_recommendation=team_recommendation,
    )


@app.route("/draftboard/toggle-star", methods=["POST"])
def toggle_star():
    player_name = request.form.get("player_name", "").strip()
    if not player_name:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, true, false)
        ON CONFLICT (player_name)
        DO UPDATE SET starred = NOT draft_board.starred
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/toggle-drafted", methods=["POST"])
def toggle_drafted():
    player_name = request.form.get("player_name", "").strip()
    if not player_name:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, false, true)
        ON CONFLICT (player_name)
        DO UPDATE SET drafted = NOT draft_board.drafted
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/add-to-team", methods=["POST"])
def add_to_team():
    player_name = request.form.get("player_name", "").strip()
    position = request.form.get("position", "").strip().upper()

    if not player_name or not position:
        return redirect(url_for("draftboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO my_roster (player_name, position)
        SELECT %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM my_roster WHERE player_name = %s
        )
        """,
        (player_name, position, player_name),
    )
    cur.execute(
        """
        INSERT INTO draft_board (player_name, starred, drafted)
        VALUES (%s, false, true)
        ON CONFLICT (player_name)
        DO UPDATE SET drafted = true
        """,
        (player_name,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("draftboard"))


@app.route("/draftboard/remove-from-team", methods=["POST"])
def remove_from_team():
    roster_id = request.form.get("roster_id", "").strip()
    if roster_id.isdigit():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM my_roster WHERE id = %s", (int(roster_id),))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("draftboard"))


@app.route("/position/<position>")
def position_rankings(position):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ranking, player_name, nfl_team
        FROM players
        WHERE position = %s
        ORDER BY ranking
        """,
        (position.upper(),),
    )
    players = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        "position.html",
        title=f"{position.upper()} Rankings",
        players=players,
    )


@app.route("/league")
def league_manager():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, team_name FROM league_teams ORDER BY id")
    teams = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("league.html", title="League Manager", teams=teams)


@app.route("/league/add-team", methods=["POST"])
def add_league_team():
    team_name = request.form.get("team_name", "").strip()
    if team_name:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO league_teams (team_name) VALUES (%s) ON CONFLICT DO NOTHING",
            (team_name,),
        )
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("league_manager"))


@app.route("/league/delete-team", methods=["POST"])
def delete_league_team():
    team_id = request.form.get("team_id", "").strip()
    if team_id.isdigit():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM league_teams WHERE id = %s", (int(team_id),))
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("league_manager"))


@app.route("/rosters")
def league_rosters():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, team_name FROM league_teams ORDER BY id")
    teams = cur.fetchall()
    cur.execute(
        """
        SELECT id, team_name, player_name, position, drafted_at
        FROM league_rosters
        ORDER BY drafted_at, id
        """
    )
    roster_rows = cur.fetchall()
    cur.close()
    conn.close()

    rosters_by_team = []
    for team_id, team_name in teams:
        rosters_by_team.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "players": [row for row in roster_rows if row[1] == team_name],
            }
        )

    return render_template(
        "rosters.html",
        title="League Rosters",
        rosters_by_team=rosters_by_team,
    )


@app.route("/trackdraft", methods=["GET", "POST"])
def track_draft():
    error = None
    message = None

    if request.method == "POST":
        team_name = request.form.get("team_name", "").strip()
        player_name = request.form.get("player_name", "").strip()

        if not team_name or not player_name:
            error = "Select both a team and a player."
        else:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT position
                FROM players
                WHERE player_name = %s
                LIMIT 1
                """,
                (player_name,),
            )
            player_row = cur.fetchone()

            cur.execute(
                "SELECT 1 FROM league_teams WHERE team_name = %s",
                (team_name,),
            )
            team_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT 1 FROM league_rosters WHERE player_name = %s",
                (player_name,),
            )
            already_drafted = cur.fetchone() is not None

            if player_row is None:
                error = "The selected player was not found."
            elif not team_exists:
                error = "The selected team was not found."
            elif already_drafted:
                error = f"{player_name} has already been drafted."
            else:
                position = player_row[0]
                cur.execute(
                    """
                    INSERT INTO league_rosters (team_name, player_name, position)
                    VALUES (%s, %s, %s)
                    """,
                    (team_name, player_name, position),
                )
                cur.execute(
                    """
                    INSERT INTO draft_board (player_name, starred, drafted)
                    VALUES (%s, false, true)
                    ON CONFLICT (player_name)
                    DO UPDATE SET drafted = true
                    """,
                    (player_name,),
                )

                if team_name == "My Team":
                    cur.execute(
                        """
                        INSERT INTO my_roster (player_name, position)
                        SELECT %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM my_roster WHERE player_name = %s
                        )
                        """,
                        (player_name, position, player_name),
                    )

                conn.commit()
                message = f"Recorded {player_name} to {team_name}."

            cur.close()
            conn.close()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT team_name FROM league_teams ORDER BY id")
    teams = [row[0] for row in cur.fetchall()]
    available_players = fetch_available_players(cur)
    cur.execute(
        """
        SELECT id, team_name, player_name, position, drafted_at
        FROM league_rosters
        ORDER BY drafted_at DESC, id DESC
        LIMIT 20
        """
    )
    recent_picks = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "trackdraft.html",
        title="Draft Tracker",
        teams=teams,
        available_players=available_players,
        recent_picks=recent_picks,
        message=message,
        error=error,
    )


@app.route("/trackdraft/undo", methods=["POST"])
def undo_draft_pick():
    pick_id = request.form.get("pick_id", "").strip()

    if not pick_id.isdigit():
        return redirect(url_for("track_draft"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT team_name, player_name FROM league_rosters WHERE id = %s",
        (int(pick_id),),
    )
    pick = cur.fetchone()

    if pick is not None:
        team_name, player_name = pick
        cur.execute("DELETE FROM league_rosters WHERE id = %s", (int(pick_id),))
        cur.execute(
            "UPDATE draft_board SET drafted = false WHERE player_name = %s",
            (player_name,),
        )
        if team_name == "My Team":
            cur.execute(
                "DELETE FROM my_roster WHERE player_name = %s",
                (player_name,),
            )
        conn.commit()

    cur.close()
    conn.close()
    return redirect(url_for("track_draft"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
