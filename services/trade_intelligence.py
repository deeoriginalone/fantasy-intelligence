"""Evidence-based trade decision support.

Uses only roster rows supplied by owner_operations. It never submits trades and
never invents projections or player identity.
"""
from services.weekly_lineup_intelligence import optimize_lineup

TARGETS={"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1}
CORE={"QB","RB","WR","TE"}
HEALTHY={"","healthy","healthy / not listed","none","not listed"}


def number(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return default


def evidence_ready(player):
    return bool(player.get("player")) and player.get("position") in TARGETS and (player.get("projection") is not None or player.get("weekly_score") is not None or player.get("rank") is not None)


def unavailable(player):
    text=str(player.get("injury_status") or "").lower()
    return player.get("is_bye") is True or number(player.get("injury_multiplier"),1.0)<=0 or any(x in text for x in ("out","ir","reserve-ret"))


def trade_value(player):
    """Score only stored projection/rank/tier and current weekly evidence."""
    projection=number(player.get("projection"))
    weekly=number(player.get("weekly_score"))
    rank=player.get("rank")
    rank_value=max(0.0,201-number(rank,201))
    tier=player.get("tier")
    tier_value=max(0.0,8-number(tier,8))*8
    health=0.70 if unavailable(player) else 0.90 if str(player.get("injury_status") or "").lower() not in HEALTHY else 1.0
    score=(projection*0.45+weekly*8+rank_value*0.35+tier_value)*health
    return round(score,2)


def roster_profile(roster):
    rows=[dict(p) for p in (roster or [])]
    counts={p:sum(1 for x in rows if x.get("position")==p) for p in TARGETS}
    needs={p:max(0,TARGETS[p]-counts[p]) for p in TARGETS}
    surplus={p:max(0,counts[p]-TARGETS[p]) for p in TARGETS}
    starters,bench,_,vacancies=optimize_lineup(rows)
    starter_names={p.get("player") for p in starters if not p.get("vacant")}
    return {"counts":counts,"needs":needs,"surplus":surplus,"vacancies":vacancies,"starter_names":starter_names,"bench_names":{p.get("player") for p in bench}}


def fit_adjustment(player,recipient_profile):
    pos=player.get("position")
    need=recipient_profile["needs"].get(pos,0)
    vacancy_bonus=35 if any(slot.startswith(pos) or (slot=="FLEX" and pos in CORE) for slot in recipient_profile["vacancies"]) else 0
    return need*18+vacancy_bonus


def enriched(player,profile):
    row=dict(player)
    row["trade_value"]=trade_value(row)
    row["is_starter"]=row.get("player") in profile["starter_names"]
    row["evidence_ready"]=evidence_ready(row)
    return row


def verdict(net_value):
    if net_value>=25:return "STRONG ACCEPT"
    if net_value>=8:return "LEAN ACCEPT"
    if net_value>=-8:return "BALANCED"
    if net_value>=-25:return "LEAN DECLINE"
    return "DECLINE"


def confidence(players):
    ready=sum(evidence_ready(p) for p in players)
    score=round(ready/max(len(players),1)*100)
    return {"score":score,"label":"HIGH" if score>=90 else "MEDIUM" if score>=70 else "LOW"}


def generate_one_for_one(my_roster,target_roster,limit=12):
    mine=roster_profile(my_roster);theirs=roster_profile(target_roster)
    offers=[enriched(p,mine) for p in my_roster if evidence_ready(p)]
    targets=[enriched(p,theirs) for p in target_roster if evidence_ready(p)]
    rows=[]
    for target in targets:
        for offer in offers:
            owner_gain=target["trade_value"]+fit_adjustment(target,mine)-offer["trade_value"]
            partner_gain=offer["trade_value"]+fit_adjustment(offer,theirs)-target["trade_value"]
            balance=abs(owner_gain-partner_gain)
            if owner_gain < -35 or partner_gain < -35:continue
            conf=confidence([offer,target])
            rows.append({"receive":[target],"send":[offer],"owner_gain":round(owner_gain,2),"partner_gain":round(partner_gain,2),"balance_gap":round(balance,2),"verdict":verdict(owner_gain),"confidence":conf,"reason":f"Receive {target['position']} value while sending {offer['position']} value; partner fit is scored from the partner roster's verified position counts."})
    rows.sort(key=lambda x:(x["balance_gap"],-x["owner_gain"],-x["partner_gain"],x["receive"][0]["player"]))
    return rows[:limit]


def generate_two_for_one(my_roster,target_roster,limit=8):
    mine=roster_profile(my_roster);theirs=roster_profile(target_roster)
    offers=[enriched(p,mine) for p in my_roster if evidence_ready(p) and not (p.get("player") in mine["starter_names"] and mine["surplus"].get(p.get("position"),0)==0)]
    targets=[enriched(p,theirs) for p in target_roster if evidence_ready(p)]
    rows=[]
    for target in targets:
        for i,first in enumerate(offers):
            for second in offers[i+1:]:
                sent=first["trade_value"]+second["trade_value"]
                received=target["trade_value"]
                owner_gain=received+fit_adjustment(target,mine)-sent
                partner_gain=sent+fit_adjustment(first,theirs)+fit_adjustment(second,theirs)-received
                balance=abs(owner_gain-partner_gain)
                if owner_gain < -45 or partner_gain < -45:continue
                conf=confidence([first,second,target])
                rows.append({"receive":[target],"send":[first,second],"owner_gain":round(owner_gain,2),"partner_gain":round(partner_gain,2),"balance_gap":round(balance,2),"verdict":verdict(owner_gain),"confidence":conf,"reason":f"Consolidation package for {target['player']}; both outgoing players are unique and evaluated from supplied evidence."})
    rows.sort(key=lambda x:(x["balance_gap"],-x["owner_gain"],x["receive"][0]["player"]))
    return rows[:limit]


def build_trade_intelligence(my_roster,target_roster,partner=None):
    blockers=[]
    if not my_roster:blockers.append("OWNER_ROSTER_EMPTY")
    if partner is not None and not target_roster:blockers.append("PARTNER_ROSTER_EMPTY")
    missing=sorted({p.get("player") or "Unknown" for p in [*(my_roster or []),*(target_roster or [])] if not evidence_ready(p)})
    if missing:blockers.append("TRADE_EVIDENCE_INCOMPLETE")
    owner=roster_profile(my_roster);target=roster_profile(target_roster)
    return {"allowed":bool(my_roster) and bool(target_roster),"blockers":blockers,"partner":partner or {},"owner_profile":owner,"partner_profile":target,"missing_evidence_players":missing,"one_for_one":generate_one_for_one(my_roster,target_roster),"two_for_one":generate_two_for_one(my_roster,target_roster),"methodology":"Uses supplied projection, weekly score, rank, tier, injury availability, and verified roster position counts. It does not submit trades and is not a fairness guarantee."}
