from __future__ import annotations

from flask import Blueprint, current_app, render_template, request, session
from weekly_intelligence import enrich_players, current_week, upcoming_byes
from services.weekly_lineup_intelligence import build_lineup_intelligence, optimize_lineup
from services.trade_intelligence import build_trade_intelligence
from services.trade_target_center import build_trade_target_center
from services.decision_ranking import build_action, build_decision_ranking
from services.matchup_intelligence import build_matchup_intelligence
from services.ux_evidence import shared_league_facts
from services.team_needs import league_settings_contract, team_needs_contract

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
                player=row_to_player(tuple(row) + (None, None))
                raw_status=raw.get("injury_status") or raw.get("status")
                if raw_status:
                    player["injury_status"]=raw_status
                    player["injury_source"]="sleeper_players"
                result.append(player)
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
                "shared_facts": shared_league_facts({}, source="Season Sandbox", blocker="LIVE_LEAGUE_FACTS_NOT_APPLICABLE"),
            }
        roster, league = live_roster(cur)
        roster = enrich_players(cur, roster, current_week(cur))
        return context, roster, {
            "team_name": "DiE-HaRd-9eRs-FaN",
            "league_name": league.get("name") or "Fantasy Intelligence Champions League",
            "strategy": "LIVE",
            "draft_name": None,
            "shared_facts": shared_league_facts(league),
        }

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
        if context["mode"] == "LIVE":
            league_id=current_app.config.get("SLEEPER_LEAGUE_ID","")
            catalog=get_all_players() or {}; all_rosters=get_rosters(league_id) or []
            owned=set()
            for league_roster in all_rosters:
                for pid in league_roster.get("players") or []:
                    raw=catalog.get(str(pid),{}) or {}
                    full=raw.get("full_name") or " ".join(x for x in (raw.get("first_name"),raw.get("last_name")) if x)
                    if full: owned.add(normalize_player_name(full))
            return [p for p in rows if normalize_player_name(p["player"]) not in owned][:limit]
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
            league_payload = get_league(current_app.config.get("SLEEPER_LEAGUE_ID", "")) or {} if context["mode"] == "LIVE" else {}
            league_settings = league_settings_contract(league_payload, source="Sleeper API" if context["mode"] == "LIVE" else "Season Sandbox", blocker=None if context["mode"] == "LIVE" else "LIVE_LEAGUE_SETTINGS_NOT_APPLICABLE")
            team_needs = team_needs_contract(roster, league_settings)
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

        return render_template("team.html", weekly_starter_score=weekly_starter_score, title="My Team", context=context, roster=roster, meta=meta, starters=starters, bench=bench, total=total, vacancies=vacancies, counts=counts, grades=grades, needs=needs, overall=overall, roster_score=score, league_settings=league_settings, team_needs=team_needs)

    @bp.route("/lineup")
    def lineup_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            lineup_intelligence = build_lineup_intelligence(roster)
        finally:
            cur.close(); conn.close()
        return render_template("lineup.html", title="Weekly Lineup Intelligence", context=context, meta=meta, lineup_intelligence=lineup_intelligence)

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
            teams=[]; target_roster=[]; partner={}
            target_slot=request.args.get("team",type=int)
            if context["mode"] == "MOCK":
                teams=[t for t in other_mock_teams(cur,context["draft_id"]) if t["name"] != "My Mock Team"]
                partner=next((t for t in teams if t["slot"]==target_slot),{})
                if target_slot:target_roster=mock_roster(cur,context["draft_id"],target_slot);target_roster=enrich_players(cur,target_roster,current_week(cur))
            else:
                league_id=current_app.config.get("SLEEPER_LEAGUE_ID","")
                users=get_users(league_id) or [];sleep_rosters=get_rosters(league_id) or [];catalog=get_all_players() or {}
                users_by_id={str(u.get("user_id")):u for u in users};owner_ids={str(u.get("user_id")) for u in users if u.get("is_owner") is True}
                for item in sleep_rosters:
                    rid=int(item.get("roster_id") or 0);oid=str(item.get("owner_id") or "")
                    if oid in owner_ids:continue
                    user=users_by_id.get(oid,{}) or {};metadata=user.get("metadata") or {};name=metadata.get("team_name") or user.get("display_name") or f"Roster {rid}"
                    teams.append({"slot":rid,"name":name})
                    if target_slot==rid:
                        partner={"slot":rid,"name":name};raw=[]
                        for pid in item.get("players") or []:
                            data=catalog.get(str(pid),{}) or {};full=data.get("full_name") or " ".join(x for x in (data.get("first_name"),data.get("last_name")) if x)
                            if not full:continue
                            cur.execute("SELECT player_name,UPPER(position),nfl_team,ranking,projected_points,tier,adp,bye_week,injury_status FROM players WHERE REGEXP_REPLACE(LOWER(player_name),'[^a-z0-9]','','g')=%s LIMIT 1",(normalize_player_name(full),))
                            row=cur.fetchone()
                            raw.append(row_to_player(tuple(row)+(None,None)) if row else {"player":full,"position":str(data.get("position") or "NA").upper().replace("DST","DEF"),"nfl_team":data.get("team") or "FA","rank":None,"projection":None,"tier":None,"adp":None,"bye_week":None,"injury_status":"Unknown","pick_no":None,"round":None})
                        target_roster=enrich_players(cur,raw,current_week(cur))
            trade_intelligence=build_trade_intelligence(roster,target_roster,partner)
            trade_target_center=build_trade_target_center(trade_intelligence)
        finally:
            cur.close();conn.close()
        return render_template("trades.html",title="Trade Target Center",context=context,meta=meta,teams=teams,target_slot=target_slot,trade_intelligence=trade_intelligence,trade_target_center=trade_target_center)

    @bp.route("/gm")
    def gm_page():
        conn = get_db_connection(); cur = conn.cursor()
        try:
            context, roster, meta = current_roster(cur)
            starters, bench, total, vacancies = optimize_lineup(roster)
            counts, grades, needs, overall, score = roster_analysis(roster, vacancies)
            pool = waiver_pool(cur, context, roster, limit=20)
            waivers = faab_recommendations(pool, counts)[:5]
            lineup_intelligence = build_lineup_intelligence(roster)
            matchup_intelligence = build_matchup_intelligence(roster, lineup_intelligence.get("starters"))
            extra_actions = []
            for vacancy in vacancies:
                extra_actions.append(build_action(action_id=f"roster:vacancy:{vacancy}", category="lineup", title=f"Fill {vacancy}", action=f"Fill vacant {vacancy} starter slot", reason="A vacant starter slot has a zero-point baseline until filled.", urgency="CRITICAL", confidence={"label":"HIGH","score":100}, risk_reduction=100, source="roster_analysis", metadata={"slot":vacancy}))
            for index, need in enumerate(needs[:5], 1):
                extra_actions.append(build_action(action_id=f"team-health:{index}", category="waiver", title="Address roster need", action=need, reason=need, urgency="HIGH", confidence={"label":"MEDIUM","score":70}, risk_reduction=50, source="roster_analysis"))
            for index, candidate in enumerate(waivers[:3], 1):
                extra_actions.append(build_action(action_id=f"waiver-watch:{index}:{candidate['player']}", category="waiver", title=f"Review {candidate['player']}", action=f"Review {candidate['player']} at ${candidate['faab']} FAAB", reason=f"Priority score {candidate['priority_score']:.1f}; roster need {candidate['need']}.", urgency="HIGH" if candidate.get("need") else "MEDIUM", confidence={"label":"MEDIUM","score":70}, risk_reduction=min(100,float(candidate.get("need") or 0)*25), source="waiver_watch", metadata={"faab":candidate.get("faab")}))
            incomplete = [p for p in roster if p.get("evidence_gaps")]
            if incomplete:
                extra_actions.append(build_action(action_id="data-integrity:weekly-evidence", category="matchup", title="Resolve weekly evidence", action=f"Resolve weekly evidence for {len(incomplete)} roster player(s)", reason="Schedule, bye, health, or matchup evidence is incomplete.", urgency="CRITICAL", confidence={"label":"LOW","score":0}, evidence_complete=False, blockers=sorted({gap for p in incomplete for gap in p.get("evidence_gaps",[])}), source="weekly_intelligence"))
            for index, player in enumerate(matchup_intelligence.get("favorable_matchups",[])[:3],1):
                extra_actions.append(build_action(action_id=f"matchup:{index}:{player['player']}", category="matchup", title=f"Exploit {player['player']} matchup", action=f"Prioritize {player['player']} against {player.get('opponent') or 'TBD'}", reason=f"Supplied matchup modifier is {player['matchup_modifier']:+.1%}.", urgency="MEDIUM", confidence=player.get("confidence"), expected_points_gain=max(0.0,player["weekly_score"]-player["weekly_baseline"]), evidence_complete=not player.get("evidence_gaps"), blockers=player.get("evidence_gaps") or (), source="matchup_intelligence", metadata={"position":player.get("position"),"matchup_rank":player.get("matchup_rank")}))
            decision_ranking = build_decision_ranking(lineup_intelligence=lineup_intelligence, extra_actions=extra_actions, limit=12)
        finally:
            cur.close(); conn.close()
        return render_template("gm.html", title="Weekly Command Center", context=context, meta=meta, overall=overall, roster_score=score, total=total, vacancies=vacancies, waivers=waivers, roster=roster, lineup_intelligence=lineup_intelligence, decision_ranking=decision_ranking, matchup_intelligence=matchup_intelligence)

    return bp
