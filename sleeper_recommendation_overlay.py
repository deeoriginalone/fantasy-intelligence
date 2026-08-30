"""Explainable Sleeper overlay for existing Draft HQ recommendations.
Does not mutate the canonical draft_score.
"""
CORE=("QB","RB","WR","TE")

def _candidate_position(candidate):
    player=candidate.get("player") if isinstance(candidate,dict) else None
    if isinstance(player,(list,tuple)) and len(player)>2:
        return str(player[2] or "").upper()
    if isinstance(player,dict):
        return str(player.get("position") or "").upper()
    return str((candidate or {}).get("position") or "").upper()

def _candidate_name(candidate):
    player=candidate.get("player") if isinstance(candidate,dict) else None
    if isinstance(player,(list,tuple)) and len(player)>1:return str(player[1])
    if isinstance(player,dict):return str(player.get("player_name") or player.get("name") or "")
    return str((candidate or {}).get("player_name") or (candidate or {}).get("name") or "")

def build_recommendation_overlay(recommendations,signals,max_bonus=8):
    signals=signals or {};risk=signals.get("position_risk_pct") or {};pressure=signals.get("position_pressure") or {};before=signals.get("teams_before_next") or []
    rows=[]
    for rank,candidate in enumerate(recommendations or [],1):
        pos=_candidate_position(candidate);base=float(candidate.get("draft_score") or 0);risk_pct=int(risk.get(pos,0) or 0)
        bonus=round(max_bonus*risk_pct/100,2) if pos in CORE else 0.0
        adjusted=round(base+bonus,2);interested=sum(1 for team in before if team.get("primary_need")==pos)
        reasons=[]
        if risk_pct:reasons.append(f"{pos} has {risk_pct}% relative live pressure before the next pick")
        if interested:reasons.append(f"{interested} intervening selection(s) currently project {pos} as the primary need")
        if not reasons:reasons.append("No additional live Sleeper pressure detected")
        rows.append({"original_rank":rank,"name":_candidate_name(candidate),"position":pos,"base_score":round(base,2),"sleeper_bonus":bonus,"adjusted_score":adjusted,"risk_pct":risk_pct,"need_pressure":pressure.get(pos,0),"interested_teams":interested,"reasons":reasons})
    rows.sort(key=lambda x:(-x["adjusted_score"],x["original_rank"]))
    for i,row in enumerate(rows,1):row["overlay_rank"]=i;row["rank_change"]=row["original_rank"]-i
    leader=rows[0] if rows else None
    return {"rows":rows,"leader":leader,"max_bonus":max_bonus,"active":bool(before),"pick_count":signals.get("pick_count",0),"next_pick":signals.get("next_pick"),"note":"Sleeper-adjusted score is a validation overlay. The canonical Draft Coach score is unchanged."}
