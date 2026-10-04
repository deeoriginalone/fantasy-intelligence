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

def _package_rejection(intel, has_packages):
    if not intel.get("allowed") or has_packages:
        return None
    owner=intel.get("owner_profile") or {}
    partner=intel.get("partner_profile") or {}
    owner_needs=owner.get("needs") or {}
    partner_needs=partner.get("needs") or {}
    owner_surplus=owner.get("surplus") or {}
    partner_surplus=partner.get("surplus") or {}
    owner_overlap=sorted(position for position, need in owner_needs.items() if need and partner_surplus.get(position, 0))
    partner_overlap=sorted(position for position, need in partner_needs.items() if need and owner_surplus.get(position, 0))
    evidence=[]
    evidence.extend(f"Owner needs {position}; partner has {position} surplus." for position in owner_overlap)
    evidence.extend(f"Partner needs {position}; owner has {position} surplus." for position in partner_overlap)
    if evidence:
        reason="Roster needs and surplus overlap, but no qualifying package is available for the current rosters."
        takeaway=f"Monitor this team. Re-evaluate if the {', '.join(sorted(set(owner_overlap + partner_overlap)))} roster balance changes."
    else:
        evidence.append("Current roster needs and surpluses do not overlap by position.")
        reason="No qualifying package is available for the current rosters."
        takeaway="Monitor this team. Re-evaluate after roster changes."
    return {"state":"NO_QUALIFYING_PACKAGE","reason":reason,"evidence":evidence,"takeaway":takeaway}

POSITIONS=("QB","RB","WR","TE","K","DEF")
FLEX_POSITIONS=("RB","WR","TE")

def _side_coverage(profile, outgoing, incoming, side):
    counts=profile.get("counts") or {}
    needs=profile.get("needs") or {}
    surplus=profile.get("surplus") or {}
    if any(position not in counts or position not in needs or position not in surplus for position in POSITIONS):
        return None,[f"{side}: Required roster coverage is unavailable."],[]
    before={position:int(counts[position] or 0) for position in POSITIONS}
    minimum={position:max(0,before[position]+int(needs[position] or 0)-int(surplus[position] or 0)) for position in POSITIONS}
    vacancy_slots=[str(slot).upper() for slot in (profile.get("vacancies") or [])]
    vacancies_before={position:sum(slot.startswith(position) for slot in vacancy_slots) for position in POSITIONS}
    vacancies_before["FLEX"]=sum(slot=="FLEX" for slot in vacancy_slots)
    after=dict(before)
    for player in outgoing:
        position=player.get("position")
        if position not in after:
            return None,[f"{side}: Player position is unavailable."],[]
        after[position]-=1
    for player in incoming:
        position=player.get("position")
        if position not in after:
            return None,[f"{side}: Player position is unavailable."],[]
        after[position]+=1
    flex_before=sum(before[position] for position in FLEX_POSITIONS)
    flex_after=sum(after[position] for position in FLEX_POSITIONS)
    vacancies_after={position:max(0,minimum[position]-after[position])+max(0,vacancies_before[position]-max(0,minimum[position]-before[position])) for position in POSITIONS}
    vacancies_after["FLEX"]=max(0,vacancies_before["FLEX"]+flex_before-flex_after)
    reasons=[]
    changes=[]
    deficits_before={}
    deficits_after={}
    for position in POSITIONS:
        before_deficit=max(0,minimum[position]-before[position],vacancies_before[position])
        after_deficit=max(0,minimum[position]-after[position],vacancies_after[position])
        deficits_before[position]=before_deficit
        deficits_after[position]=after_deficit
        if after_deficit>before_deficit:
            reason=f"Would increase {position} deficit." if before_deficit else f"Would leave {position} below minimum coverage."
            reasons.append(f"{side}: {reason}")
        if before[position]!=after[position]:
            changes.append({"position":position,"before":before[position],"after":after[position],"minimum":minimum[position],"deficit_before":before_deficit,"deficit_after":after_deficit})
    if flex_after<flex_before:
        reasons.append(f"{side}: Would reduce FLEX depth.")
    return {"before":before,"after":after,"minimum":minimum,"deficits_before":deficits_before,"deficits_after":deficits_after,"position_changes":changes,"flex_before":flex_before,"flex_after":flex_after,"starter_vacancies_before":vacancies_before,"starter_vacancies_after":vacancies_after},reasons,changes

def _package_roster_impact(package, owner, partner):
    owner_impact,owner_reasons,_=_side_coverage(owner,package["send"],package["receive"],"Owner")
    partner_impact,partner_reasons,_=_side_coverage(partner,package["receive"],package["send"],"Partner")
    reasons=list(dict.fromkeys([*owner_reasons,*partner_reasons]))
    position_change=f"{' + '.join(player.get('position') or 'Unknown' for player in package['send'])} → {' + '.join(player.get('position') or 'Unknown' for player in package['receive'])}"
    helps=[]; need_improvement=0
    if owner_impact:
        for position in POSITIONS:
            reduction=owner_impact["deficits_before"][position]-owner_impact["deficits_after"][position]
            has_need=bool(owner.get("needs",{}).get(position,0) or owner_impact["starter_vacancies_before"].get(position,0))
            if reduction>0 and has_need:
                helps.append(f"Addresses {position} deficit.")
                need_improvement+=reduction
        flex_improvement=max(owner_impact["flex_after"]-owner_impact["flex_before"],owner_impact["starter_vacancies_before"]["FLEX"]-owner_impact["starter_vacancies_after"]["FLEX"])
        if flex_improvement>0:
            helps.append("Improves FLEX coverage.")
            need_improvement+=flex_improvement
    if not need_improvement:
        reasons.append("Does not improve any verified team need.")
    impact={"position_change":position_change,"owner":owner_impact,"partner":partner_impact,"helps":list(dict.fromkeys(helps)),"hurts":reasons,"need_improvement":need_improvement,"new_risk_count":len(reasons)}
    return impact,reasons

def _closest_trade_path(rejected, package_rejection):
    if rejected:
        candidate=min(rejected,key=lambda row:(len(row["reasons"]),row["package_type"],row["position_change"]))
        receive_positions=sorted({player.get("position") for player in candidate["receive"] if player.get("position")})
        helps=[position for position in receive_positions if (candidate.get("owner_needs") or {}).get(position,0)]
        if "Does not improve any verified team need." in candidate["reasons"]:
            summary=f"Position change {candidate['position_change']} leaves verified needs unchanged."
        else:
            summary=f"Partner has {', '.join(helps)} available for an owner need." if helps else f"Candidate partner assets are {', '.join(receive_positions) or 'unavailable'}; current coverage blocks this package."
        monitor=[]
        for reason in candidate["reasons"]:
            if not reason.startswith(("Owner:","Partner:")):
                monitor.append("Re-evaluate if an owner need or roster coverage changes.")
                continue
            side,detail=reason.split(":",1)
            position=next((item for item in POSITIONS if item in detail),None)
            if position:
                monitor.append(f"Re-evaluate if {side.lower()} {position} coverage changes.")
            elif "FLEX" in detail:
                monitor.append(f"Re-evaluate if {side.lower()} FLEX-eligible depth changes.")
            else:
                monitor.append(f"Re-evaluate if {side.lower()} roster coverage can be verified.")
        return {"summary":summary,"current_obstacle":candidate["reasons"][0],"monitor_if":"; ".join(dict.fromkeys(monitor)) or "Re-evaluate after a roster change.","rejected_package":candidate}
    if package_rejection:
        return {"summary":package_rejection["reason"],"current_obstacle":package_rejection["evidence"][0] if package_rejection["evidence"] else package_rejection["reason"],"monitor_if":package_rejection["takeaway"],"rejected_package":None}
    return None

def build_trade_target_center(trade_intelligence, limit=10):
    intel=dict(trade_intelligence or {}); ranked=[]; rejected_packages=[]
    owner=intel.get("owner_profile") or {}; partner=intel.get("partner_profile") or {}
    source_packages={"ONE_FOR_ONE":intel.get("one_for_one") or [],"TWO_FOR_ONE":intel.get("two_for_one") or []}
    for package_type,packages in (("ONE_FOR_ONE",intel.get("one_for_one") or []),("TWO_FOR_ONE",intel.get("two_for_one") or [])):
     for package in packages:
        if not package.get("receive") or not package.get("send"): continue
        row=dict(package); row["package_type"]=package_type
        roster_impact,reasons=_package_roster_impact(row,owner,partner)
        if reasons:
            rejected_packages.append({"package_type":package_type,"receive":row["receive"],"send":row["send"],"position_change":roster_impact["position_change"],"reasons":reasons,"roster_impact":roster_impact,"owner_needs":owner.get("needs") or {}})
            continue
        row["roster_impact"]=roster_impact; row["opportunity_score"]=opportunity_score(row); row["target_signal"]=_signal(row["receive"][0]); row["send_signals"]=[_signal(p) for p in row["send"]]; ranked.append(row)
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
    metric_definitions={"modeled_owner_gain":"Change in the owner's supplied trade value plus verified roster-fit adjustment; higher is better.","modeled_partner_gain":"Same modeled value change for the partner; higher is better and does not predict acceptance.","balance_gap":"Absolute difference between modeled owner and partner gains; lower is more balanced and does not establish feasibility.","opportunity_score":"0-100 ranking signal built from modeled gains, balance gap, and evidence confidence; higher ranks first.","evidence_confidence":"Certainty of supplied package evidence, not player quality; missing evidence blocks publication.","trade_feasibility":"Unavailable without transaction history, manager behavior, market response, or negotiation evidence."}
    has_packages=bool(by_type["ONE_FOR_ONE"] or by_type["TWO_FOR_ONE"])
    package_rejection=_package_rejection(intel,has_packages)
    closest=_closest_trade_path(rejected_packages,package_rejection) if not has_packages else None
    published_one=by_type["ONE_FOR_ONE"][:limit]; published_two=by_type["TWO_FOR_ONE"][:limit]
    published_ids={id(row) for row in published_one+published_two}
    best_candidates=[row for row in ranked if id(row) in published_ids]
    best_package=min(best_candidates,key=lambda row:(-row["roster_impact"]["need_improvement"],row["roster_impact"]["new_risk_count"])) if best_candidates else None
    return {"allowed":bool(intel.get("allowed")),"blockers":list(intel.get("blockers") or []),"partner":intel.get("partner") or {},"integrity":intel.get("integrity"),"evidence_coverage":intel.get("evidence_coverage") or {},"publication_state":intel.get("publication_state","BLOCKED"),"ranked_opportunities":ranked[:limit],"one_for_one":published_one,"two_for_one":published_two,"best_package":best_package,"best_package_selection":"Largest verified owner need reduction, then lowest roster-coverage risk; ties preserve existing ranked order.","trade_targets":targets,"buy_low":buy[:limit],"sell_high":sell[:limit],"owner_needs":{k:v for k,v in (owner.get("needs") or {}).items() if v},"owner_surplus":{k:v for k,v in (owner.get("surplus") or {}).items() if v},"partner_needs":{k:v for k,v in (partner.get("needs") or {}).items() if v},"partner_surplus":{k:v for k,v in (partner.get("surplus") or {}).items() if v},"package_counts":{"generated":{"ONE_FOR_ONE":len(source_packages["ONE_FOR_ONE"]),"TWO_FOR_ONE":len(source_packages["TWO_FOR_ONE"])},"published":{"ONE_FOR_ONE":len(published_one),"TWO_FOR_ONE":len(published_two)},"rejected":len(rejected_packages)},"rejected_packages":rejected_packages,"closest_trade_path":closest,"package_rejection":package_rejection,"metric_definitions":metric_definitions,"methodology":"Ranks existing evidence-based packages using supplied owner gain, partner gain, balance gap, confidence, position needs, and surplus. Buy-low and sell-high labels compare only stored weekly score with stored season projection divided by 17. No trade is submitted."}
