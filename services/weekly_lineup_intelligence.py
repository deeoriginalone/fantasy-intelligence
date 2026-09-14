"""Weekly lineup decision support from already-enriched roster rows.

No lineup transaction is submitted. The engine ranks only supplied players and
reports missing evidence instead of inventing projections, opponents, or status.
"""
from services.integrity import build_integrity_report
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

def decision(player,preferred="START"):
    if player.get("vacant") or not evidence_ready(player):return "MONITOR"
    health=str(player.get("injury_status") or "").strip().lower()
    if health in {"", "unknown", "not available", "unavailable"} or player.get("evidence_gaps"):
        return "MONITOR"
    return preferred

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
        used.add(candidate.get("player"));candidate.update({"slot":slot,"vacant":False,"evidence_ready":evidence_ready(candidate),"decision":decision(candidate,"FLEX" if slot=="FLEX" else "START")})
        candidate["reason"]=explain(candidate);candidate["confidence"]=confidence(candidate);starters.append(candidate)
    bench=[]
    for player in available:
        if player.get("player") in used:continue
        player.update({"vacant":False,"evidence_ready":evidence_ready(player),"decision":"SIT" if evidence_ready(player) and eligible(player) else "MONITOR"});player["reason"]=explain(player);player["confidence"]=confidence(player);bench.append(player)
    for order,player in enumerate(bench,1):player["bench_order"]=order
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
        alt=choices[0] if choices else None
        delta=round(number(alt.get("weekly_score"))-number(starter.get("weekly_score")),2) if alt else 0.0
        preferred="FLEX" if starter.get("slot")=="FLEX" else "START"
        selected=alt if alt and delta>0.01 else starter
        selected_decision=decision(selected,preferred)
        decisions.append({"decision":selected_decision,"slot":starter.get("slot"),"start":selected,"sit":starter if selected is not starter else alt,"weekly_score_delta":abs(delta),"reason":f"{alt.get('player')} has a {delta:.2f} higher weekly score." if alt and delta>0.01 else f"{starter.get('player')} remains the supported {preferred.lower()} recommendation." if selected_decision != "MONITOR" else f"{starter.get('player')} needs monitoring because lineup evidence is incomplete or uncertain.","confidence":confidence(selected),"alternative":alt if selected is starter else starter})
    return decisions

def build_lineup_verdict(starters, decisions, blockers, vacancies, total, total_available):
    monitored=[player for player in starters if player.get("decision")=="MONITOR"]
    blocked=bool(vacancies)
    status="BLOCKED" if blocked else "MONITOR" if blockers or monitored else "READY"
    confidence_values=[int((player.get("confidence") or {}).get("score") or 0) for player in starters if not player.get("vacant")]
    confidence_percent=round(sum(confidence_values)/len(confidence_values)) if confidence_values else 0
    risk="No active lineup risk identified."
    action="Review the selected lineup before lock."
    expected_gain=None
    change=None
    if vacancies:
        risk=f"Starter slot unavailable: {', '.join(vacancies)}."
        action=f"Fill {vacancies[0]} before lineup lock."
    elif monitored:
        risk=f"{monitored[0].get('player')} needs evidence review before lock."
        action=f"Monitor {monitored[0].get('player')} before lineup lock."
    else:
        upgrades=[item for item in decisions if item.get("weekly_score_delta",0)>0.01 and item.get("start")]
        if upgrades:
            upgrade=upgrades[0]
            action=f"START {upgrade['start'].get('player')} over {upgrade['sit'].get('player')}"
            expected_gain=upgrade.get("weekly_score_delta")
            risk=f"The {upgrade.get('slot')} decision carries a {expected_gain:.2f}-point supported value edge."
    return {"status":status,"weekly_score":total if total_available else None,"confidence_percent":confidence_percent,"biggest_risk":risk,"action":action,"expected_gain":expected_gain,"why":("Supported weekly value and available matchup evidence favor the recommendation." if status=="READY" else "Confidence is reduced because the affected evidence or starter slot needs review.")}

def build_lineup_risks(starters, blockers, vacancies):
    risks=[]
    for slot in vacancies:
        risks.append({"title":f"{slot} starter slot is vacant","affected":slot,"impact":"Lineup readiness is blocked.","action":f"Add an eligible player for {slot}.","severity":"HIGH"})
    for player in starters:
        if player.get("decision") != "MONITOR":continue
        gaps=player.get("evidence_gaps") or []
        reason="Weekly or health evidence is incomplete."
        if gaps:reason=f"Evidence gap: {', '.join(gaps)}."
        risks.append({"title":f"Monitor {player.get('player')}","affected":player.get("slot"),"impact":"Confidence is reduced for this recommendation.","action":f"Review {player.get('player')} before lineup lock.","severity":"MEDIUM","reason":reason})
    if "WEEKLY_EVIDENCE_INCOMPLETE" in blockers and not any(item.get("affected") for item in risks):
        risks.append({"title":"Weekly value evidence is incomplete","affected":"Lineup score","impact":"Unavailable values are excluded from confidence.","action":"Use supported evidence only.","severity":"MEDIUM"})
    return risks or [{"title":"No material risk detected","affected":"Lineup","impact":"Current supported evidence is internally consistent.","action":"Review before lock.","severity":"LOW"}]

def build_lineup_intelligence(roster,freshness_metadata=None):
    starters,bench,total,vacancies=optimize_lineup(roster)
    missing=sorted({p.get("player") for p in [*starters,*bench] if not p.get("vacant") and not p.get("evidence_ready")})
    blockers=[]
    if not roster:blockers.append("ROSTER_EMPTY")
    if vacancies:blockers.append("STARTER_SLOTS_VACANT")
    if missing:blockers.append("WEEKLY_EVIDENCE_INCOMPLETE")
    blocker_impacts=[]
    if "STARTER_SLOTS_VACANT" in blockers:blocker_impacts.append("A vacant starter slot prevents lineup readiness for the affected slot(s): "+", ".join(vacancies)+".")
    if "WEEKLY_EVIDENCE_INCOMPLETE" in blockers:blocker_impacts.append("Players with incomplete weekly evidence are marked MONITOR; their values are not treated as verified zero.")
    total_available=all(p.get("weekly_score") is not None for p in starters if not p.get("vacant"))
    decisions=build_start_sit_decisions(starters,bench)
    return {"allowed":bool(roster) and not vacancies,"readiness":"READY" if bool(roster) and not vacancies and not missing else "REVIEW","blockers":blockers,"blocker_impacts":blocker_impacts,"starters":starters,"bench":bench,"weekly_total":total,"weekly_total_available":total_available,"vacancies":vacancies,"missing_evidence_players":missing,"start_sit_decisions":decisions,"verdict":build_lineup_verdict(starters,decisions,blockers,vacancies,total,total_available),"risks":build_lineup_risks(starters,blockers,vacancies),"changes":{"status":"UNAVAILABLE","message":"No prior-week lineup snapshot is supplied; changes are not inferred."},"metric_definitions":{"baseline":"Expected value before weekly adjustments.","weekly_score":"Expected starting value after matchup and availability adjustments.","confidence":"How trustworthy the recommendation is based on evidence completeness and agreement."},"methodology":"Ranks supplied roster players by existing weekly_score after bye and injury availability checks. No lineup is submitted.","freshness_metadata":dict(freshness_metadata or {}),"integrity":build_integrity_report(roster,freshness_metadata=freshness_metadata)}
