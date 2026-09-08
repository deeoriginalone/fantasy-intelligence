"""Weekly lineup decision support from already-enriched roster rows.

No lineup transaction is submitted. The engine ranks only supplied players and
reports missing evidence instead of inventing projections, opponents, or status.
"""
STARTER_SLOTS=(("QB",("QB",)),("RB1",("RB",)),("RB2",("RB",)),("WR1",("WR",)),("WR2",("WR",)),("TE",("TE",)),("FLEX",("RB","WR","TE")),("K",("K",)),("DEF",("DEF",)))
HEALTHY={"","healthy","healthy / not listed","none","not listed"}

def number(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return default

def status(player):return str(player.get("injury_status") or "").strip().lower()

def evidence_ready(player):
    return player.get("weekly_score") is not None and (player.get("weekly_baseline") is not None or player.get("projection") is not None)

def eligible(player):
    return not player.get("is_bye") and number(player.get("injury_multiplier"),1.0)>0 and not any(x in status(player) for x in ("out","ir","reserve-ret"))

def sort_key(player):
    return (0 if eligible(player) else 1,-number(player.get("weekly_score")),player.get("rank") or 9999,str(player.get("player") or ""))

def confidence(player):
    if player.get("vacant") or not eligible(player):return {"label":"BLOCKED","score":0}
    checks=(player.get("weekly_score") is not None,player.get("weekly_baseline") is not None,bool(player.get("opponent")),player.get("matchup_rank") is not None,bool(player.get("injury_status")))
    score=round(sum(checks)/len(checks)*100)
    return {"label":"HIGH" if score>=80 else "MEDIUM" if score>=60 else "LOW","score":score}

def explain(player):
    if player.get("vacant"):return "No eligible roster player is available for this slot."
    reasons=[]
    if player.get("is_bye"):reasons.append("Unavailable because of a bye week")
    raw=str(player.get("injury_status") or "Unknown")
    if raw.strip().lower() not in HEALTHY:reasons.append(f"Injury designation: {raw}")
    rank=player.get("matchup_rank");modifier=number(player.get("matchup_modifier"))
    if rank is not None:
        direction="favorable" if modifier>0 else "difficult" if modifier<0 else "neutral"
        reasons.append(f"{direction.capitalize()} matchup, defense rank {rank} vs {player.get('position')}")
    elif player.get("opponent"):reasons.append("Opponent known; defensive matchup rank unavailable")
    else:reasons.append("Opponent or matchup evidence unavailable")
    if player.get("weekly_baseline") is not None:reasons.append(f"weekly baseline {number(player.get('weekly_baseline')):.2f}")
    return "; ".join(reasons)+"."

def vacancy(slot,allowed):
    return {"slot":slot,"player":"Vacant","position":"/".join(allowed),"nfl_team":"--","rank":None,"projection":0.0,"weekly_baseline":0.0,"weekly_score":0.0,"matchup_modifier":0.0,"injury_multiplier":1.0,"injury_status":"Needs roster move","opponent":None,"is_bye":False,"vacant":True,"evidence_ready":False,"reason":"No eligible roster player is available for this slot.","confidence":{"label":"BLOCKED","score":0}}

def optimize_lineup(roster):
    available=sorted((dict(p) for p in (roster or [])),key=sort_key);used=set();starters=[]
    for slot,allowed in STARTER_SLOTS:
        candidate=next((p for p in available if p.get("player") not in used and p.get("position") in allowed and eligible(p)),None)
        if candidate is None:starters.append(vacancy(slot,allowed));continue
        used.add(candidate.get("player"));candidate.update({"slot":slot,"vacant":False,"evidence_ready":evidence_ready(candidate)})
        candidate["reason"]=explain(candidate);candidate["confidence"]=confidence(candidate);starters.append(candidate)
    bench=[]
    for player in available:
        if player.get("player") in used:continue
        player.update({"vacant":False,"evidence_ready":evidence_ready(player)});player["reason"]=explain(player);player["confidence"]=confidence(player);bench.append(player)
    total=round(sum(number(p.get("weekly_score")) for p in starters),2)
    vacancies=[p["slot"] for p in starters if p.get("vacant")]
    return starters,bench,total,vacancies

def slot_allows(slot,position):
    return any(name==slot and position in allowed for name,allowed in STARTER_SLOTS)

def build_start_sit_decisions(starters,bench):
    decisions=[]
    for starter in starters or []:
        if starter.get("vacant"):continue
        choices=sorted([p for p in (bench or []) if slot_allows(starter.get("slot"),p.get("position")) and eligible(p)],key=sort_key)
        if not choices:continue
        alt=choices[0];delta=round(number(alt.get("weekly_score"))-number(starter.get("weekly_score")),2)
        swap=delta>0.01
        decisions.append({"action":"SWAP" if swap else "HOLD","slot":starter.get("slot"),"start":alt if swap else starter,"sit":starter if swap else alt,"weekly_score_delta":abs(delta),"reason":f"{alt.get('player')} has a {delta:.2f} higher weekly score." if swap else f"{starter.get('player')} remains ahead of the best eligible bench alternative.","confidence":confidence(alt if swap else starter)})
    return decisions

def build_lineup_intelligence(roster):
    starters,bench,total,vacancies=optimize_lineup(roster)
    missing=sorted({p.get("player") for p in [*starters,*bench] if not p.get("vacant") and not p.get("evidence_ready")})
    blockers=[]
    if not roster:blockers.append("ROSTER_EMPTY")
    if vacancies:blockers.append("STARTER_SLOTS_VACANT")
    if missing:blockers.append("WEEKLY_EVIDENCE_INCOMPLETE")
    return {"allowed":bool(roster) and not vacancies,"blockers":blockers,"starters":starters,"bench":bench,"weekly_total":total,"vacancies":vacancies,"missing_evidence_players":missing,"start_sit_decisions":build_start_sit_decisions(starters,bench),"methodology":"Ranks supplied roster players by existing weekly_score after bye and injury availability checks. No lineup is submitted."}
