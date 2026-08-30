from __future__ import annotations
from datetime import datetime

TEAM_ALIASES = {
    "ARI":"ARI","ATL":"ATL","BAL":"BAL","BUF":"BUF","CAR":"CAR","CHI":"CHI","CIN":"CIN","CLE":"CLE",
    "DAL":"DAL","DEN":"DEN","DET":"DET","GB":"GB","GNB":"GB","HOU":"HOU","IND":"IND","JAX":"JAX","JAC":"JAX",
    "KC":"KC","KAN":"KC","LAC":"LAC","LAR":"LAR","LV":"LV","LVR":"LV","MIA":"MIA","MIN":"MIN","NE":"NE",
    "NEP":"NE","NO":"NO","NOS":"NO","NYG":"NYG","NYJ":"NYJ","PHI":"PHI","PIT":"PIT","SF":"SF","SFO":"SF",
    "SEA":"SEA","TB":"TB","TAM":"TB","TEN":"TEN","WAS":"WAS","WSH":"WAS"
}

def normalize_team(value):
    if not value: return None
    return TEAM_ALIASES.get(str(value).upper().strip(), str(value).upper().strip())

def current_week(cur, season=2026):
    cur.execute("SELECT state_value FROM application_state WHERE state_key='current_week'")
    row=cur.fetchone()
    if row and row[0] and row[0].get("week"):
        return int(row[0]["week"])
    return 1

def set_current_week(cur, week, season=2026):
    import json
    cur.execute("""INSERT INTO application_state(state_key,state_value,updated_at)
                   VALUES('current_week',%s::jsonb,NOW())
                   ON CONFLICT(state_key) DO UPDATE SET state_value=EXCLUDED.state_value,updated_at=NOW()""",
                (json.dumps({"season":season,"week":int(week)}),))

def matchup_modifier(rank):
    if rank is None: return 0.0
    # Rank 1 = toughest, rank 32 = easiest; capped at +/-15%.
    return round(max(-0.15, min(0.15, (float(rank)-16.5)/103.3333)), 4)

def injury_multiplier(status):
    text=(status or "").lower()
    if any(x in text for x in ("out","ir","reserve-ret")): return 0.0
    if "doubtful" in text: return 0.25
    if "questionable" in text: return 0.85
    if "probable" in text: return 0.97
    return 1.0

def enrich_players(cur, players, week, season=2026):
    enriched=[]
    for original in players:
        p=dict(original)
        team=normalize_team(p.get("nfl_team"))
        position=(p.get("position") or "").upper().replace("DST","DEF")
        p["nfl_team"]=team or p.get("nfl_team")
        p["position"]=position
        cur.execute("SELECT bye_week FROM bye_weeks WHERE season=%s AND team=%s",(season,team))
        row=cur.fetchone(); bye=row[0] if row else None
        p["bye_week"]=bye
        p["is_bye"]=bool(bye==week)
        cur.execute("""SELECT CASE WHEN home_team=%s THEN away_team ELSE home_team END,
                              CASE WHEN home_team=%s THEN 'HOME' ELSE 'AWAY' END,
                              game_time_pacific
                       FROM nfl_schedule
                       WHERE season=%s AND week=%s AND (home_team=%s OR away_team=%s)
                       LIMIT 1""",(team,team,season,week,team,team))
        sched=cur.fetchone()
        p["opponent"]=sched[0] if sched else None
        p["home_away"]=sched[1] if sched else None
        p["game_time_pacific"]=sched[2] if sched else None
        cur.execute("""SELECT injury,status FROM injury_reports
                       WHERE season=%s AND REGEXP_REPLACE(LOWER(player_name),'[^a-z0-9]','','g')=
                             REGEXP_REPLACE(LOWER(%s),'[^a-z0-9]','','g')
                       ORDER BY report_date DESC LIMIT 1""",(season,p.get("player")))
        inj=cur.fetchone()
        if inj:
            p["injury"]=inj[0]; p["injury_status"]=inj[1] or p.get("injury_status")
        else: p["injury"]=None
        matchup_pos="DEF" if position=="DEF" else position
        cur.execute("""SELECT defense_rank,fp_per_game_allowed FROM defense_matchups
                       WHERE season=%s AND position=%s AND defense_team=%s""",
                    (season-1,matchup_pos,p.get("opponent")))
        m=cur.fetchone(); rank=m[0] if m else None
        p["matchup_rank"]=rank; p["fp_allowed"]=float(m[1]) if m else None
        p["matchup_modifier"]=matchup_modifier(rank)
        season_projection=float(p.get("projection") or 0)
        p["weekly_baseline"]=round(season_projection/17.0,2)
        mult=injury_multiplier(p.get("injury_status"))
        p["injury_multiplier"]=mult
        p["weekly_score"]=0.0 if p["is_bye"] else round(p["weekly_baseline"]*(1+p["matchup_modifier"])*mult,2)
        enriched.append(p)
    return enriched

def upcoming_byes(cur, players, current, horizon=3, season=2026):
    rows=[]
    for p in players:
        team=normalize_team(p.get("nfl_team"))
        cur.execute("SELECT bye_week FROM bye_weeks WHERE season=%s AND team=%s",(season,team))
        r=cur.fetchone()
        if r and current <= r[0] <= current+horizon:
            rows.append({"player":p.get("player"),"position":p.get("position"),"team":team,"bye_week":r[0]})
    return sorted(rows,key=lambda x:(x["bye_week"],x["position"],x["player"]))
