from __future__ import annotations

from flask import Blueprint, current_app, render_template, request, session
from weekly_intelligence import enrich_players, current_week, upcoming_byes

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
STARTER_SLOTS = ("QB", "RB1", "RB2", "WR1", "WR2", "TE", "FLEX", "K", "DEF")


def create_owner_operations_blueprint(
    get_db_connection,
    get_league,
    get_users,
    get_rosters,
    get_all_players,
    normalize_player_name,
):
    bp = Blueprint("owner_ops", __name__)

    def data_context(cur):
        cur.execute(
            """
            SELECT state_value
            FROM application_state
            WHERE state_key = 'active_sandbox'
            """
        )
        row = cur.fetchone()
        state = row[0] if row else None
        if state and state.get("mode") == "MOCK" and state.get("draft_id"):
            return {"mode": "MOCK", "draft_id": int(state["draft_id"])}
        return {"mode": "LIVE", "draft_id": None}

    def row_to_player(row):
        return {
            "player": row[0],
            "position": (row[1] or "NA").upper().replace("DST", "DEF"),
            "nfl_team": row[2] or "FA",
            "rank": row[3],
            "projection": float(row[4] or 0),
            "tier": row[5],
            "adp": float(row[6]) if row[6] is not None else None,
            "bye_week": row[7],
            "injury_status": row[8] or "Healthy / Not listed",
            "pick_no": row[9] if len(row) > 9 else None,
            "round": row[10] if len(row) > 10 else None,
        }

    def mock_roster(cur, draft_id, draft_slot=None):
        if draft_slot is None:
            cur.execute("SELECT draft_position FROM mock_drafts WHERE id = %s", (draft_id,))
            found = cur.fetchone()
            draft_slot = found[0] if found else 5
        cur.execute(
            """
            SELECT
                mp.player_name,
                UPPER(mp.position),
                mp.nfl_team,
                mp.overall_rank,
                p.projected_points,
                p.tier,
                p.adp,
                p.bye_week,
                p.injury_status,
                mp.pick_no,
                mp.round_num
            FROM mock_picks mp
            LEFT JOIN players p ON p.player_name = mp.player_name
            WHERE mp.draft_id = %s
              AND mp.draft_slot = %s
            ORDER BY mp.pick_no
            """,
            (draft_id, draft_slot),
        )
        return [row_to_player(row) for row in cur.fetchall()]

    def live_roster(cur):
        league = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or {}
        users = get_users(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or []
        rosters = get_rosters(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or []
        all_players = get_all_players() or {}
        owner_ids = {
            str(user.get("user_id"))
            for user in users
            if user.get("is_owner") is True
        }
        owner_roster = next(
            (r for r in rosters if str(r.get("owner_id") or "") in owner_ids),
            None,
        )
        if not owner_roster:
            return [], league
        player_ids = [str(pid) for pid in (owner_roster.get("players") or [])]
        local_names = []
        for pid in player_ids:
            raw = all_players.get(pid) or {}
            name = raw.get("full_name") or " ".join(
                part for part in (raw.get("first_name"), raw.get("last_name")) if part
            )
            if name:
                local_names.append((name, raw.get("position"), raw.get("team")))
        result = []
        for name, position, team in local_names:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE REGEXP_REPLACE(LOWER(player_name), '[^a-z0-9]', '', 'g') = %s
                LIMIT 1
                """,
                (normalize_player_name(name),),
            )
            row = cur.fetchone()
            if row:
                result.append(row_to_player(tuple(row) + (None, None)))
            else:
                result.append({
                    "player": name,
                    "position": (position or "NA").upper().replace("DST", "DEF"),
                    "nfl_team": team or "FA",
                    "rank": None,
                    "projection": 0.0,
                    "tier": None,
                    "adp": None,
                    "bye_week": None,
                    "injury_status": "Unknown",
                    "pick_no": None,
                    "round": None,
                })
        return result, league

    def current_roster(cur):
        context = data_context(cur)
        if context["mode"] == "MOCK":
            cur.execute(
                "SELECT draft_name, strategy, draft_position FROM mock_drafts WHERE id = %s",
                (context["draft_id"],),
            )
            row = cur.fetchone()
            roster = mock_roster(cur, context["draft_id"], row[2] if row else 5)
            roster = enrich_players(cur, roster, current_week(cur))
            return context, roster, {
                "team_name": "My Mock Team",
                "league_name": "Season Sandbox",
                "strategy": row[1] if row else "WR_HEAVY",
                "draft_name": row[0] if row else f"Mock #{context['draft_id']}",
            }
        roster, league = live_roster(cur)
        roster = enrich_players(cur, roster, current_week(cur))
        return context, roster, {
            "team_name": "DiE-HaRd-9eRs-FaN",
            "league_name": league.get("name") or "Fantasy Intelligence Champions League",
            "strategy": "LIVE",
            "draft_name": None,
        }

    def optimize_lineup(roster):
        available = sorted(roster, key=lambda p: (-p.get("weekly_score", 0), p.get("rank") or 9999))
        used = set()
        starters = []

        def take(slot, allowed):
            candidate = next(
                (p for p in available if p["player"] not in used and p["position"] in allowed),
                None,
            )
            if candidate:
                used.add(candidate["player"])
                starters.append({**candidate, "slot": slot, "vacant": False})
            else:
                starters.append({
                    "slot": slot, "player": "Vacant", "position": "/".join(allowed),
                    "nfl_team": "--", "rank": None, "projection": 0.0,
                    "tier": None, "adp": None, "bye_week": None,
                    "injury_status": "Needs roster move", "vacant": True,
                })

        take("QB", ("QB",))
        take("RB1", ("RB",))
        take("RB2", ("RB",))
        take("WR1", ("WR",))
        take("WR2", ("WR",))
        take("TE", ("TE",))
        take("FLEX", ("RB", "WR", "TE"))
        take("K", ("K",))
        take("DEF", ("DEF",))
        bench = [p for p in available if p["player"] not in used]
        total = round(sum(p["projection"] for p in starters), 1)
        vacancies = [p["slot"] for p in starters if p["vacant"]]
        return starters, bench, total, vacancies

    def roster_analysis(roster, vacancies):
        counts = {pos: sum(1 for p in roster if p["position"] == pos) for pos in POSITIONS}
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        needs = []
        grades = {}
        for pos in POSITIONS:
            count = counts[pos]
            target = targets[pos]
            ratio = count / target if target else 1
            grades[pos] = "A" if ratio >= 1 else "B" if ratio >= .75 else "C" if ratio >= .5 else "F"
            if count < target:
                needs.append(f"Add {pos} depth: {count} rostered, target {target}.")
        for slot in vacancies:
            message = f"Fill vacant {slot} starter slot before Week 1."
            if message not in needs:
                needs.insert(0, message)
        injured = [p for p in roster if str(p["injury_status"]).lower() not in {"healthy / not listed", "healthy", "none", ""}]
        if injured:
            needs.append(f"Monitor {len(injured)} player(s) with an injury designation.")
        score = sum(min(counts[p] / targets[p], 1) for p in POSITIONS) / len(POSITIONS) * 100
        overall = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"
        return counts, grades, needs, overall, round(score)

    def waiver_pool(cur, context, roster, limit=40):
        roster_names = {p["player"] for p in roster}
        if context["mode"] == "MOCK":
            cur.execute(
                """
                SELECT p.player_name, UPPER(p.position), p.nfl_team, p.ranking,
                       p.projected_points, p.tier, p.adp, p.bye_week, p.injury_status
                FROM players p
                WHERE UPPER(p.position) IN ('QB','RB','WR','TE','K','DEF')
                  AND NOT EXISTS (
                      SELECT 1 FROM mock_picks mp
                      WHERE mp.draft_id = %s AND mp.player_name = p.player_name
                  )
                ORDER BY p.ranking NULLS LAST
                LIMIT %s
                """,
                (context["draft_id"], limit),
            )
        else:
            cur.execute(
                """
                SELECT player_name, UPPER(position), nfl_team, ranking,
                       projected_points, tier, adp, bye_week, injury_status
                FROM players
                WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF')
                ORDER BY ranking NULLS LAST
                LIMIT %s
                """,
                (limit * 3,),
            )
        rows = [row_to_player(tuple(row) + (None, None)) for row in cur.fetchall()]
        return [p for p in rows if p["player"] not in roster_names][:limit]

    def faab_recommendations(pool, counts):
        targets = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
        recs = []
        for player in pool:
            need = max(0, targets.get(player["position"], 1) - counts.get(player["position"], 0))
            rank_value = max(0, 110 - (player["rank"] or 110))
            tier_value = max(0, 7 - (player["tier"] or 7)) * 5
            score = rank_value + tier_value + need * 20
            bid = max(0, min(35, round(score / 6)))
            if player["position"] in {"K", "DEF"}:
                bid = min(bid, 3)
            recs.append({**player, "priority_score": round(score, 1), "faab": bid, "bid_low": max(0, bid - 3), "bid_high": min(40, bid + 4), "need": need})
        return sorted(recs, key=lambda p: (-p["priority_score"], p["rank"] or 9999))

    def other_mock_teams(cur, draft_id):
        cur.execute(
            """
            SELECT DISTINCT draft_slot, team_name
            FROM mock_picks
            WHERE draft_id = %s
            ORDER BY draft_slot
            """,
            (draft_id,),
        )
        return [{"slot": row[0], "name": row[1]} for row in cur.fetchall()]

    @bp.route("/team")
    def team_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
        finally:
            cur.close(); conn.close()
        weekly_defaults = {
            "weekly_baseline": 0.0, "matchup_modifier": 0.0,
            "injury_multiplier": 1.0, "weekly_score": 0.0,
            "is_bye": False, "bye_week": None, "opponent": None,
            "home_away": None, "game_time_pacific": None,
            "matchup_rank": None, "injury_status": "Unknown", "vacant": False,
        }
        for player in [*starters, *bench]:
            for key, value in weekly_defaults.items(): player.setdefault(key, value)
        weekly_starter_score = sum(float(player.get("weekly_score") or 0) for player in starters)

        return render_template("team.html", weekly_starter_score=weekly_starter_score, title="My Team", context=context, roster=roster, meta=meta, starters=starters, bench=bench, total=total, vacancies=vacancies, counts=counts, grades=grades, needs=needs, overall=overall, roster_score=score)

    @bp.route("/lineup")
    def lineup_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
        finally:
            cur.close(); conn.close()
        return render_template("lineup.html", title="Lineup Optimizer", context=context, meta=meta, starters=starters, bench=bench, total=total, vacancies=vacancies)

    @bp.route("/waivers")
    def waivers_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool = waiver_pool(cur, context, roster)
            recommendations = faab_recommendations(pool, counts)[:25]
        finally:
            cur.close(); conn.close()
        return render_template("waivers.html", title="Waiver and FAAB Center", context=context, meta=meta, recommendations=recommendations, needs=needs, vacancies=vacancies, faab_budget=100)

    @bp.route("/trades")
    def trades_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            teams = []
            target_roster = []
            target_slot = request.args.get("team", type=int)
            if context["mode"] == "MOCK":
                teams = other_mock_teams(cur, context["draft_id"])
                teams = [t for t in teams if t["name"] != "My Mock Team"]
                if target_slot:
                    target_roster = mock_roster(cur, context["draft_id"], target_slot)
            trade_ideas = []
            my_bench = sorted(roster, key=lambda p: (p["projection"], -(p["rank"] or 9999)))[:6]
            targets = sorted(target_roster, key=lambda p: (-p["projection"], p["rank"] or 9999))[:8]
            for target in targets:
                offer = min(my_bench, key=lambda p: abs(p["projection"] - target["projection"]), default=None)
                if offer:
                    delta = round(target["projection"] - offer["projection"], 1)
                    verdict = "LEAN ACCEPT" if delta >= 10 else "FAIR" if delta >= -10 else "DECLINE"
                    trade_ideas.append({"target": target, "offer": offer, "delta": delta, "verdict": verdict})
        finally:
            cur.close(); conn.close()
        return render_template("trades.html", title="Trade Center", context=context, meta=meta, roster=roster, teams=teams, target_slot=target_slot, target_roster=target_roster, trade_ideas=trade_ideas)

    @bp.route("/gm")
    def gm_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool = waiver_pool(cur, context, roster, limit=20)
            waivers = faab_recommendations(pool, counts)[:5]
            actions = []
            for vacancy in vacancies:
                actions.append({"priority": "URGENT", "action": f"Fill vacant {vacancy} slot", "source": "Roster"})
            for need in needs[:5]:
                actions.append({"priority": "HIGH", "action": need, "source": "Team Health"})
            if waivers:
                top = waivers[0]
                actions.append({"priority": "HIGH", "action": f"Review {top['player']} at ${top['faab']} FAAB", "source": "Waivers"})
            actions.append({"priority": "MEDIUM", "action": "Review optimized lineup before Week 1 lock", "source": "Lineup"})
        finally:
            cur.close(); conn.close()
        return render_template("gm.html", title="GM Center", context=context, meta=meta, overall=overall, roster_score=score, total=total, vacancies=vacancies, actions=actions, waivers=waivers)

    return bp
