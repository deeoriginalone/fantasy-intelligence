#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
p=Path("sleeper_intelligence.py"); text=p.read_text()
if "def waiver_candidates(" in text: raise SystemExit("ERROR: patch already applied")
marker="def build(cur,league_id,week,season=2026):\n"
if text.count(marker)!=1: raise SystemExit(f"ERROR: build marker count={text.count(marker)}")
function='''def waiver_candidates(trending_available,my_team,position_pressure,limit=10):
    """Rank unowned Sleeper trending adds with existing need and pressure signals."""
    if not trending_available: return []
    team=my_team or {};needs=team.get("needs") or {};primary=str(team.get("primary_need") or "").upper();press=position_pressure or {};rows=[]
    for item in trending_available:
        pos=str(item.get("position") or "").upper()
        if pos not in CORE: continue
        trend=int(item.get("count") or 0);need=int(needs.get(pos) or 0);pressure_score=int(press.get(pos) or 0);primary_match=bool(primary and pos==primary)
        reasons=[]
        if primary_match: reasons.append(f"{pos} is the primary roster need")
        elif need: reasons.append(f"{pos} depth is {need} below target")
        if trend: reasons.append(f"{trend} recent trending adds")
        if pressure_score: reasons.append(f"league pressure score {pressure_score}")
        rows.append({**item,"position":pos,"trend_count":trend,"need_score":need,"pressure_score":pressure_score,"primary_need_match":primary_match,"waiver_score":trend+need*25+pressure_score*5,"reason":"; ".join(reasons) or "Available Sleeper trending player"})
    return sorted(rows,key=lambda x:(x["waiver_score"],x["trend_count"],x["name"]),reverse=True)[:limit]

'''
text=text.replace(marker,function+marker)
old='    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure(active),"recent_picks":recent,"position_run_counts":run_counts,"trending_available":available_trending(trends or [],rosters or [],players),"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}\n'
new='    pressure_map=pressure(active);trending_available=available_trending(trends or [],rosters or [],players);my_team=next((team for team in roster_teams if team.get("manager")=="My Team"),None)\n    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure_map,"recent_picks":recent,"position_run_counts":run_counts,"trending_available":trending_available,"waiver_candidates":waiver_candidates(trending_available,my_team,pressure_map),"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}\n'
if text.count(old)!=1: raise SystemExit(f"ERROR: return anchor count={text.count(old)}")
backup=Path(f"sleeper_intelligence.py.before_f3d1_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}");backup.write_text(p.read_text());p.write_text(text.replace(old,new));print(f"Patched: {p}");print(f"Backup: {backup}")
