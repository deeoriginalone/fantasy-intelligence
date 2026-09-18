from __future__ import annotations
from datetime import datetime
from services.schedule_bye_evidence import evidence_contract as schedule_bye_evidence_contract
from services.ux_evidence import weekly_evidence_contract
from services.lineup_evidence import build_lineup_evidence, build_matchup_evidence, build_projection_evidence
from services.ux_evidence import weekly_evidence_contract
from services.authoritative_week import acquire_authoritative_week
from services.sleeper_service import get_nfl_state

TEAM_ALIASES = {
    "ARI":"ARI","ATL":"ATL","BAL":"BAL","BUF":"BUF","CAR":"CAR","CHI":"CHI","CIN":"CIN","CLE":"CLE",
    "DAL":"DAL","DEN":"DEN","DET":"DET","GB":"GB","GNB":"GB","HOU":"HOU","IND":"IND","JAX":"JAX","JAC":"JAX",
    "KC":"KC","KAN":"KC","LAC":"LAC","LAR":"LAR","LV":"LV","LVR":"LV","MIA":"MIA","MIN":"MIN","NE":"NE",
    "NEP":"NE","NO":"NO","NOS":"NO","NYG":"NYG","NYJ":"NYJ","PHI":"PHI","PIT":"PIT","SF":"SF","SFO":"SF",
    "SEA":"SEA","TB":"TB","TAM":"TB","TEN":"TEN","WAS":"WAS","WSH":"WAS"
}

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LAC": "Los Angeles Chargers", "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

def normalize_team(value):
    if not value: return None
    return TEAM_ALIASES.get(str(value).upper().strip(), str(value).upper().strip())

def current_week(cur, season=2026, sleeper_state_reader=get_nfl_state):
    context = acquire_authoritative_week(cur, sleeper_state_reader, season=season)
    return context["week"] if context["authoritative"] else None

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

def enrich_players(cur, players, week, season=2026, allow_local_weekly_data=True, allow_local_health_fallback=True, require_automated_weekly_evidence=False):
    enriched=[]
    for original in players:
        p=dict(original)
        team=normalize_team(p.get("nfl_team"))
        position=(p.get("position") or "").upper().replace("DST","DEF")
        p["nfl_team"]=team or p.get("nfl_team")
        p["position"]=position
        bye_row = None
        if allow_local_weekly_data:
            cur.execute("SELECT bye_week,source,source_recorded_at,retrieved_at,imported_at FROM bye_weeks WHERE season=%s AND team=%s",(season,team))
            bye_row=cur.fetchone(); bye=bye_row[0] if bye_row else p.get("bye_week")
        else:
            bye = None
        p["bye_week"]=bye
        p["is_bye"]=bool(bye==week)
        p["evidence_gaps"]=[]
        if bye is None: p["evidence_gaps"].append("BYE_WEEK_NOT_LOADED")
        sched = None
        if allow_local_weekly_data:
            cur.execute("""SELECT CASE WHEN home_team=%s THEN away_team ELSE home_team END,
                              CASE WHEN home_team=%s THEN 'HOME' ELSE 'AWAY' END,
                              game_time_pacific,source,source_recorded_at,retrieved_at,imported_at
                       FROM nfl_schedule
                       WHERE season=%s AND week=%s AND (home_team=%s OR away_team=%s)
                       LIMIT 1""",(team,team,season,week,team,team))
            sched=cur.fetchone()
        p["opponent"]=sched[0] if sched else None
        p["opponent_name"] = TEAM_NAMES.get(p["opponent"], p["opponent"])
        p["home_away"]=sched[1] if sched else None
        p["game_time_pacific"]=sched[2] if sched else None
        p["schedule_source"]=(sched[3] if sched and len(sched)>3 else None) or ("nfl_schedule" if sched else None)
        if not sched and not p["is_bye"]: p["evidence_gaps"].append("SCHEDULE_NOT_LOADED_FOR_WEEK")
        if position == "DEF":
            p["injury"] = None
            p["health_status_available"] = True
            p["injury_status"] = "Not applicable"
        elif p.get("health_status_available") is not None:
            p["injury"] = None
            if not p.get("injury_status") or p.get("injury_status")=="Unknown":
                p["evidence_gaps"].append("INJURY_STATUS_UNRESOLVED")
        elif allow_local_health_fallback:
            cur.execute("""SELECT injury,status FROM injury_reports
                           WHERE season=%s AND REGEXP_REPLACE(LOWER(player_name),'[^a-z0-9]','','g')=
                                 REGEXP_REPLACE(LOWER(%s),'[^a-z0-9]','','g')
                           ORDER BY report_date DESC LIMIT 1""",(season,p.get("player")))
            inj=cur.fetchone()
            if inj:
                p["injury"] = inj[0]
                if not p.get("injury_source"):
                    p["injury_status"] = inj[1] or p.get("injury_status")
            else:
                p["injury"] = None
                if not p.get("injury_status") or p.get("injury_status")=="Unknown": p["evidence_gaps"].append("INJURY_STATUS_UNRESOLVED")
        matchup_pos="DEF" if position=="DEF" else position
        m = None
        if allow_local_weekly_data:
            cur.execute(
            """SELECT defense_rank,fp_per_game_allowed,source,retrieved_at,completeness_state,blocker,
                              version,checksum,source_recorded_at,lineage,completed_games
                                     FROM defense_matchups WHERE season=%s AND position=%s AND defense_team=%s
                                         AND source LIKE 'automated:nflverse%%' AND completeness_state='COMPLETE'
                                     UNION ALL
                                      SELECT defense_rank,fp_per_game_allowed,source,retrieved_at,completeness_state,blocker,
                                          version,checksum,source_recorded_at,lineage,completed_games
                                     FROM defense_matchups WHERE season=%s AND position=%s AND defense_team=%s
                                         AND source LIKE 'csv:%%' AND NOT EXISTS (
                                             SELECT 1 FROM defense_matchups WHERE season=%s AND position=%s AND defense_team=%s
                                                 AND source LIKE 'automated:nflverse%%' AND completeness_state='COMPLETE')""",
                (season,p.get("position"),p.get("opponent"),season-1,matchup_pos,p.get("opponent"),season,p.get("position"),p.get("opponent")),
            )
            m=cur.fetchone()
        rank=m[0] if m else None
        p["matchup_rank"]=rank; p["fp_allowed"]=float(m[1]) if m else None
        matchup_source=m[2] if m and len(m)>2 and m[2] else "Unavailable"
        matchup_retrieved_at=m[3] if m and len(m)>3 else None
        p["matchup_source"]=f"nfl_schedule + {matchup_source}" if sched and matchup_source != "Unavailable" else matchup_source
        p["matchup_source_authority"] = "automated" if matchup_source.startswith("automated:") else "UNVERIFIED"
        p["matchup_version"] = m[6] if m and len(m)>6 else None
        p["matchup_checksum"] = m[7] if m and len(m)>7 else None
        p["matchup_source_recorded_at"] = m[8] if m and len(m)>8 else None
        p["matchup_publication_lineage"] = m[9] if m and len(m)>9 else None
        p["matchup_sample_size"] = m[10] if m and len(m)>10 else None
        p["matchup_retrieved_at"]=matchup_retrieved_at
        p["matchup_lineage"]={"source":p["matchup_source"],"source_recorded_at":p["matchup_source_recorded_at"],"retrieved_at":matchup_retrieved_at,"publication":p["matchup_publication_lineage"]}
        p["matchup_completeness"]="COMPLETE" if sched and m and matchup_retrieved_at else "UNAVAILABLE"
        if not m or not sched:
            p["evidence_gaps"].append("MATCHUP_EVIDENCE_UNAVAILABLE")
        p["matchup_modifier"]=matchup_modifier(rank)
        season_projection=float(p.get("projection") or 0)
        projection_retrieved_at=p.get("projection_retrieved_at")
        p["projection_source"]="players.projected_points" if p.get("projection") is not None else "Unavailable"
        p["projection_lineage"]={"source":p["projection_source"],"source_recorded_at":None,"retrieved_at":projection_retrieved_at}
        p["projection_completeness"]="COMPLETE" if p.get("projection") is not None and projection_retrieved_at else "UNAVAILABLE"
        p["weekly_baseline"]=round(season_projection/17.0,2) if allow_local_weekly_data else None
        mult=injury_multiplier(p.get("injury_status"))
        p["injury_multiplier"]=mult
        p["weekly_score"]=(0.0 if p["is_bye"] else round(p["weekly_baseline"]*(1+p["matchup_modifier"])*mult,2)) if allow_local_weekly_data else None
        if not allow_local_weekly_data:
            p["evidence_gaps"].extend(["BYE_WEEK_UNAVAILABLE", "SCHEDULE_UNAVAILABLE", "MATCHUP_EVIDENCE_UNAVAILABLE", "WEEKLY_VALUE_UNAVAILABLE"])
        if require_automated_weekly_evidence:
            p["weekly_evidence"] = {
                "schedule": schedule_bye_evidence_contract("schedule", source=(sched[3] if sched and len(sched)>3 else None), source_recorded_at=(sched[4] if sched and len(sched)>4 else None), retrieved_at=(sched[5] if sched and len(sched)>5 else None), imported_at=(sched[6] if sched and len(sched)>6 else None)),
                "bye": schedule_bye_evidence_contract("bye", source=(bye_row[1] if bye_row and len(bye_row)>1 else None), source_recorded_at=(bye_row[2] if bye_row and len(bye_row)>2 else None), retrieved_at=(bye_row[3] if bye_row and len(bye_row)>3 else None), imported_at=(bye_row[4] if bye_row and len(bye_row)>4 else None)),
                "matchup": weekly_evidence_contract(domain="matchup", blocker="MATCHUP_AUTOMATED_SOURCE_UNAVAILABLE"),
                "projection": weekly_evidence_contract(domain="projection", blocker="PROJECTION_AUTOMATED_SOURCE_UNAVAILABLE"),
            }
            hard_evidence_blocked = any(
                not item["authoritative"]
                and domain != "projection"
                for domain, item in p["weekly_evidence"].items()
            )
            projection_missing = p.get("projection") is None or not p.get("projection_retrieved_at")
            if hard_evidence_blocked or projection_missing:
                p["weekly_baseline"] = None
                p["weekly_score"] = None
            p["lineup_evidence"] = build_lineup_evidence(
                build_projection_evidence(p, season=season, week=week),
                build_matchup_evidence(p, season=season, week=week),
            )
        else:
            p["weekly_evidence"] = {}
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
