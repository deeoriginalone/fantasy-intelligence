"""F4-D Trade Target Center built on existing evidence-based trade packages."""
from __future__ import annotations

def _n(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return default

def opportunity_score(package):
    confidence=max(0.0,min(100.0,_n((package.get("confidence") or {}).get("score"))))
    score=50+_n(package.get("owner_gain"))*1.5+max(0,_n(package.get("partner_gain")))*.5-max(0,_n(package.get("balance_gap")))*.8+(confidence-50)*.2
    return round(max(0.0,min(100.0,score)),2)

def _signal(player):
    projection=_n(player.get("projection")); weekly=_n(player.get("weekly_score"))
    if projection<=0 or weekly<=0: return "INSUFFICIENT_EVIDENCE"
    ratio=weekly/(projection/17.0)
    return "BUY_LOW_SIGNAL" if ratio<=.80 else "SELL_HIGH_SIGNAL" if ratio>=1.20 else "NEUTRAL"

def _with_signal(player):
    row=dict(player); row["market_signal"]=_signal(row); row["signal_basis"]="Stored weekly score compared with stored season projection divided by 17."; return row

def build_trade_target_center(trade_intelligence, limit=10):
    intel=dict(trade_intelligence or {}); ranked=[]
    for package_type,packages in (("ONE_FOR_ONE",intel.get("one_for_one") or []),("TWO_FOR_ONE",intel.get("two_for_one") or [])):
     for package in packages:
        if not package.get("receive") or not package.get("send"): continue
        row=dict(package); row["package_type"]=package_type; row["opportunity_score"]=opportunity_score(row); row["target_signal"]=_signal(row["receive"][0]); row["send_signals"]=[_signal(p) for p in row["send"]]; ranked.append(row)
    ranked.sort(key=lambda r:(-r["opportunity_score"],r.get("balance_gap",0),-r.get("owner_gain",0),r["receive"][0].get("player") or ""))
    by_type={"ONE_FOR_ONE":[],"TWO_FOR_ONE":[]}
    for row in ranked:
        by_type[row["package_type"]].append(row)
    for rows in by_type.values():
        for rank,row in enumerate(rows,1): row["type_rank"]=rank
    targets=[]; seen=set()
    for package in ranked:
        player=package["receive"][0]; name=player.get("player")
        if not name or name in seen: continue
        seen.add(name); targets.append({"player":name,"position":player.get("position"),"trade_value":player.get("trade_value"),"market_signal":package["target_signal"],"opportunity_score":package["opportunity_score"],"best_package":package})
        if len(targets)>=limit: break
    buy=[]; seen=set()
    for p in [_with_signal(x["receive"][0]) for x in ranked]:
        if p["market_signal"]=="BUY_LOW_SIGNAL" and p.get("player") not in seen: seen.add(p.get("player")); buy.append(p)
    sell=[]; seen=set()
    for p in [_with_signal(p) for x in ranked for p in x.get("send",[])]:
        if p["market_signal"]=="SELL_HIGH_SIGNAL" and p.get("player") not in seen: seen.add(p.get("player")); sell.append(p)
    owner=intel.get("owner_profile") or {}; partner=intel.get("partner_profile") or {}
    metric_definitions={"modeled_owner_gain":"Change in the owner's supplied trade value plus verified roster-fit adjustment; higher is better.","modeled_partner_gain":"Same modeled value change for the partner; higher is better and does not predict acceptance.","balance_gap":"Absolute difference between modeled owner and partner gains; lower is more balanced and does not establish feasibility.","opportunity_score":"0-100 ranking signal built from modeled gains, balance gap, and evidence confidence; higher ranks first.","evidence_confidence":"Certainty of supplied package evidence, not player quality; missing evidence blocks publication.","trade_feasibility":"Unavailable without transaction history, manager behavior, market response, or negotiation evidence."}
    return {"allowed":bool(intel.get("allowed")),"blockers":list(intel.get("blockers") or []),"partner":intel.get("partner") or {},"integrity":intel.get("integrity"),"evidence_coverage":intel.get("evidence_coverage") or {},"publication_state":intel.get("publication_state","BLOCKED"),"ranked_opportunities":ranked[:limit],"one_for_one":by_type["ONE_FOR_ONE"][:limit],"two_for_one":by_type["TWO_FOR_ONE"][:limit],"trade_targets":targets,"buy_low":buy[:limit],"sell_high":sell[:limit],"owner_needs":{k:v for k,v in (owner.get("needs") or {}).items() if v},"owner_surplus":{k:v for k,v in (owner.get("surplus") or {}).items() if v},"partner_needs":{k:v for k,v in (partner.get("needs") or {}).items() if v},"partner_surplus":{k:v for k,v in (partner.get("surplus") or {}).items() if v},"metric_definitions":metric_definitions,"methodology":"Ranks existing evidence-based packages using supplied owner gain, partner gain, balance gap, confidence, position needs, and surplus. Buy-low and sell-high labels compare only stored weekly score with stored season projection divided by 17. No trade is submitted."}
