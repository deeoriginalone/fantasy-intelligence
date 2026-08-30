"""Player-level next-pick survival estimates for Draft HQ.
Advisory only. Does not modify canonical draft_score or Sleeper overlay score.
"""
import math

CORE=("QB","RB","WR","TE")

def _player(candidate):
    return candidate.get("player") if isinstance(candidate,dict) else None

def _field(candidate,index,*keys,default=None):
    player=_player(candidate)
    if isinstance(player,(list,tuple)) and len(player)>index:
        value=player[index]
        if value is not None:return value
    if isinstance(player,dict):
        for key in keys:
            if player.get(key) is not None:return player[key]
    if isinstance(candidate,dict):
        for key in keys:
            if candidate.get(key) is not None:return candidate[key]
    return default

def _number(value,default=None):
    try:
        number=float(value)
        return number if math.isfinite(number) else default
    except (TypeError,ValueError):
        return default

def estimate_player_survival(recommendations,signals,current_pick=None):
    signals=signals or {}
    picks_before=int(signals.get("picks_until_next") or 0)
    signal_current=int(signals.get("pick_count") or 0)
    current=int(current_pick if current_pick is not None else signal_current)
    next_pick=signals.get("next_pick")
    risk=signals.get("position_risk_pct") or {}
    pressure=signals.get("position_pressure") or {}
    teams=signals.get("teams_before_next") or []
    rows=[]
    for rank,candidate in enumerate(recommendations or [],1):
        name=str(_field(candidate,1,"player_name","name",default=""))
        position=str(_field(candidate,2,"position",default="")).upper()
        overall_rank=_number(_field(candidate,0,"ranking","overall_rank","rank"))
        adp=_number(_field(candidate,8,"adp","average_draft_position"))
        base_score=_number((candidate or {}).get("draft_score") if isinstance(candidate,dict) else None,0.0)
        risk_pct=float(risk.get(position,0) or 0)
        interested=sum(1 for team in teams if team.get("primary_need")==position)
        market_pick=adp if adp and adp<999 else overall_rank
        if picks_before<=0:
            survival=100.0
        else:
            relative_market=0.5
            if market_pick is not None:
                relative_market=max(-1.0,min(2.0,(market_pick-current)/max(1,picks_before)))
            market_hazard=max(0.05,1.35-(0.55*relative_market))
            demand_hazard=0.35+(risk_pct/100.0)*1.05
            team_hazard=1.0+(interested/max(1,picks_before))*0.8
            hazard=(picks_before/10.0)*market_hazard*demand_hazard*team_hazard
            survival=max(1.0,min(99.0,100.0*math.exp(-hazard)))
        survival=round(survival,1)
        if survival<30:decision="DRAFT NOW"
        elif survival<60:decision="HIGH RISK"
        elif survival<80:decision="BALANCED"
        else:decision="LIKELY TO SURVIVE"
        reasons=[]
        if picks_before:reasons.append(f"{picks_before} selection(s) occur before the next turn")
        if risk_pct:reasons.append(f"{position} live pressure is {int(risk_pct)}%")
        if interested:reasons.append(f"{interested} intervening manager(s) project {position} as the primary need")
        if market_pick is not None:reasons.append(f"market reference is pick {round(market_pick,1)}")
        if not reasons:reasons.append("No intervening selections are currently projected")
        rows.append({"original_rank":rank,"name":name,"position":position,"overall_rank":overall_rank,"adp":adp,"base_score":round(base_score,2),"survival_pct":survival,"selection_risk_pct":round(100-survival,1),"decision":decision,"risk_pct":int(risk_pct),"interested_teams":interested,"reasons":reasons})
    rows.sort(key=lambda row:(row["survival_pct"],row["original_rank"]))
    urgent=rows[0] if rows else None
    return {"rows":rows,"urgent":urgent,"current_pick":current,"next_pick":next_pick,"picks_before":picks_before,"active":bool(picks_before),"method":"Heuristic survival estimate using live position pressure, teams before the next pick, rank/ADP, and current draft position. It is not a calibrated probability or guarantee.","canonical_score_unchanged":True}
