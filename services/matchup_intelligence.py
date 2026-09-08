"""F4-B weekly matchup intelligence using existing enriched roster evidence."""
from __future__ import annotations

POSITIONS=("QB","RB","WR","TE","K","DEF")

def _n(v,d=0.0):
    try:return float(v)
    except (TypeError,ValueError):return d

def _row(p):
    gaps=list(p.get("evidence_gaps") or [])
    rank=p.get("matchup_rank"); mod=_n(p.get("matchup_modifier"))
    kind="BYE" if p.get("is_bye") else "UNKNOWN" if rank is None else "FAVORABLE" if mod>=.05 else "DIFFICULT" if mod<=-.05 else "NEUTRAL"
    score=max(0,100-25*len(gaps)); score=min(score,50) if p.get("opponent") is None and not p.get("is_bye") else score
    return {"player":str(p.get("player") or "").strip(),"position":str(p.get("position") or "").upper().replace("DST","DEF"),"opponent":p.get("opponent"),"home_away":p.get("home_away"),"matchup_rank":rank,"fp_allowed":p.get("fp_allowed"),"matchup_modifier":round(mod,4),"weekly_baseline":round(_n(p.get("weekly_baseline")),2),"weekly_score":round(_n(p.get("weekly_score")),2),"injury_status":p.get("injury_status") or "Unknown","is_bye":bool(p.get("is_bye")),"classification":kind,"confidence":{"label":"HIGH" if score>=80 else "MEDIUM" if score>=60 else "LOW","score":score},"evidence_gaps":gaps}

def build_matchup_intelligence(roster,starters=None):
    rows=[_row(p) for p in (roster or [])]
    names={str(p.get("player") or "").strip() for p in (starters or []) if not p.get("vacant") and p.get("player")}
    rows=[r for r in rows if not names or r["player"] in names]
    favorable=sorted([r for r in rows if r["classification"]=="FAVORABLE"],key=lambda r:(-r["matchup_modifier"],-r["weekly_score"],r["player"]))
    difficult=sorted([r for r in rows if r["classification"]=="DIFFICULT"],key=lambda r:(r["matchup_modifier"],r["weekly_score"],r["player"]))
    unavailable=sorted([r for r in rows if r["classification"] in {"BYE","UNKNOWN"}],key=lambda r:(r["classification"],r["position"],r["player"]))
    edges=[]
    for pos in POSITIONS:
        group=[r for r in rows if r["position"]==pos]; known=[r for r in group if r["matchup_rank"] is not None and not r["is_bye"]]
        if group: edges.append({"position":pos,"player_count":len(group),"known_matchups":len(known),"average_matchup_modifier":round(sum(r["matchup_modifier"] for r in known)/len(known),4) if known else None,"projected_weekly_score":round(sum(r["weekly_score"] for r in group),2),"best_player":max(known,key=lambda r:(r["matchup_modifier"],r["weekly_score"]),default=None),"weakest_player":min(known,key=lambda r:(r["matchup_modifier"],r["weekly_score"]),default=None)})
    return {"allowed":bool(rows),"blockers":sorted({g for r in rows for g in r["evidence_gaps"]}),"favorable_matchups":favorable,"difficult_matchups":difficult,"unavailable_matchups":unavailable,"position_edges":edges,"starter_count":len(rows),"methodology":"Uses existing weekly baseline, opponent, matchup rank, matchup modifier, injury, bye, and weekly score evidence. Missing evidence is not inferred."}
