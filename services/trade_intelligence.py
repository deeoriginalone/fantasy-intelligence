"""Evidence-based trade decision support.

Uses only roster rows supplied by owner_operations. It never submits trades and
never invents projections or player identity.
"""
from services.weekly_lineup_intelligence import optimize_lineup
from services.integrity import build_integrity_report

TARGETS={"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1}
CORE={"QB","RB","WR","TE"}
HEALTHY={"","healthy","healthy / not listed","none","not listed"}


def number(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return default


def evidence_ready(player):
    weekly_evidence = player.get("weekly_evidence") or {}
    if weekly_evidence and any(
        not item.get("authoritative")
        and domain != "projection"
        for domain, item in weekly_evidence.items()
    ):
        return False
    if weekly_evidence.get("projection") and not player.get("projection_retrieved_at"):
        return False
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


def package_explanation(receive, send, owner_profile, partner_profile):
    target=receive[0]
    target_need=owner_profile["needs"].get(target.get("position"),0)
    partner_needs=[player.get("position") for player in send if partner_profile["needs"].get(player.get("position"),0)]
    partner_fit="SUPPORTED" if partner_needs else "NOT_SUPPORTED"
    return {
        "target_fit":f"{target.get('position')} addresses a verified roster deficit." if target_need else f"{target.get('position')} is evaluated as value and depth, not a verified roster deficit.",
        "assets_given_up":", ".join(player.get("player") or "Unknown" for player in send),
        "partner_fit":f"Outgoing {', '.join(partner_needs)} asset(s) address the partner's verified need." if partner_needs else "No verified partner need is addressed by the outgoing asset; partner acceptance is not supported.",
        "partner_fit_state":partner_fit,
        "feasibility_state":"UNAVAILABLE",
        "feasibility_reason":"No transaction history, manager behavior, market response, or negotiation evidence is supplied.",
        "weekly_effect":"Modeled from stored weekly scores and the current roster-fit adjustment.",
        "depth_effect":f"Sends {len(send)} rostered asset(s) and receives 1 asset.",
        "risk_effect":"Injury, bye, and matchup evidence are reflected only when supplied; no transaction feasibility data is available.",
        "rest_of_season_effect":"Unavailable: no rest-of-season trade-impact model is supplied.",
    }


def modeled_value_state(owner_gain,partner_gain,balance_gap):
    if owner_gain >= 0 and partner_gain >= 0 and balance_gap <= 8:return "VALUE APPEARS BALANCED BY CURRENT MODEL"
    if owner_gain >= 0:return "OWNER VALUE POSITIVE BY CURRENT MODEL"
    return "OWNER VALUE NEGATIVE BY CURRENT MODEL"


def confidence(players):
    ready=sum(evidence_ready(p) for p in players)
    score=round(ready/max(len(players),1)*100)
    return {"score":score,"label":"HIGH" if score>=90 else "MEDIUM" if score>=70 else "LOW"}


def trade_freshness_metadata(my_roster, target_roster):
    """Return shared freshness inputs only when every applicable row supports them."""
    rows=[*(my_roster or []),*(target_roster or [])]

    def domain(timestamp_fields, source_fields, applicable=lambda row: True):
        applicable_rows=[row for row in rows if applicable(row)]
        timestamps=[]
        sources=[]
        for row in applicable_rows:
            timestamp=next((row.get(field) for field in timestamp_fields if row.get(field)),None)
            source=next((row.get(field) for field in source_fields if row.get(field)),None)
            if timestamp is None:
                return None, source or "Unavailable"
            timestamps.append(timestamp)
            if source:
                sources.append(source)
        return min(timestamps) if timestamps else None, sources[0] if sources and len(set(sources)) == 1 else "Unavailable"

    roster_time,roster_source=domain(("roster_updated_at","roster_sync_time"),("roster_source","ownership_source"))
    injury_time,injury_source=domain(("injury_updated_at","health_updated_at","last_health_update"),("injury_source",),lambda row: row.get("position") != "DEF")
    matchup_time,matchup_source=domain(("matchup_updated_at","matchup_sync_time","matchup_retrieved_at"),("matchup_source",),lambda row: not row.get("is_bye") and row.get("position") not in {"K","DEF"})
    projection_time,projection_source=domain(("projection_updated_at","projection_sync_time","projection_retrieved_at"),("projection_source",))
    if matchup_source == "Unavailable" and all(row.get("matchup_rank") is not None for row in rows if not row.get("is_bye")):
        matchup_source="Local matchup enrichment (timestamp unavailable)"
    if projection_source == "Unavailable" and all(row.get("projection") is not None for row in rows):
        projection_source="Local player projections (timestamp unavailable)"
    return {"roster_updated_at":roster_time,"roster_source":roster_source,"injury_updated_at":injury_time,"injury_source":injury_source,"matchup_updated_at":matchup_time,"matchup_source":matchup_source,"projection_updated_at":projection_time,"projection_source":projection_source}


def trade_evidence_coverage(my_roster, target_roster):
    rows=[*(my_roster or []),*(target_roster or [])]

    def coverage(name, applicable, complete):
        eligible=[row for row in rows if applicable(row)]
        covered=[row for row in eligible if complete(row)]
        return {"applicable":len(eligible),"covered":len(covered),"percentage":round(len(covered)/len(eligible)*100) if eligible else 100,"missing_player_ids":[row.get("source_player_id") or row.get("player") for row in eligible if not complete(row)]}

    return {
        "ownership":coverage("ownership",lambda row:True,lambda row:bool(row.get("roster_updated_at") or row.get("roster_sync_time"))),
        "health":coverage("health",lambda row:row.get("position") != "DEF",lambda row:bool(row.get("injury_updated_at") or row.get("health_updated_at") or row.get("last_health_update"))),
        "matchup":coverage("matchup",lambda row:not row.get("is_bye") and row.get("position") not in {"K","DEF"},lambda row:bool(row.get("matchup_retrieved_at") or row.get("matchup_updated_at") or row.get("matchup_sync_time")) and row.get("matchup_rank") is not None),
        "projection":coverage("projection",lambda row:True,lambda row:row.get("projection") is not None and bool(row.get("projection_retrieved_at") or row.get("projection_updated_at") or row.get("projection_sync_time"))),
    }


def trade_identity_lineage(my_roster, target_roster):
    return [
        {key: player.get(key) for key in ("source_player_id", "local_player_id", "player", "normalized_name", "identity_match_method", "identity_state", "projection_source", "projection_retrieved_at")}
        for player in [*(my_roster or []), *(target_roster or [])]
    ]


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
            rows.append({"receive":[target],"send":[offer],"owner_gain":round(owner_gain,2),"partner_gain":round(partner_gain,2),"balance_gap":round(balance,2),"modeled_value_state":modeled_value_state(owner_gain,partner_gain,balance),"confidence":conf,"explanation":package_explanation([target],[offer],mine,theirs),"reason":f"Receive {target['position']} value while sending {offer['position']} value; partner fit is scored from the partner roster's verified position counts."})
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
                rows.append({"receive":[target],"send":[first,second],"owner_gain":round(owner_gain,2),"partner_gain":round(partner_gain,2),"balance_gap":round(balance,2),"modeled_value_state":modeled_value_state(owner_gain,partner_gain,balance),"confidence":conf,"explanation":package_explanation([target],[first,second],mine,theirs),"reason":f"Consolidation package for {target['player']}; both outgoing players are unique and evaluated from supplied evidence."})
    rows.sort(key=lambda x:(x["balance_gap"],-x["owner_gain"],x["receive"][0]["player"]))
    return rows[:limit]


def build_trade_intelligence(
    my_roster,
    target_roster,
    partner=None,
    freshness_metadata=None,
):
    blockers=[]
    if not my_roster:blockers.append("OWNER_ROSTER_EMPTY")
    if partner is not None and not target_roster:blockers.append("PARTNER_ROSTER_EMPTY")
    missing=sorted({p.get("player") or "Unknown" for p in [*(my_roster or []),*(target_roster or [])] if not evidence_ready(p)})
    if missing:blockers.append("TRADE_EVIDENCE_INCOMPLETE")
    owner=roster_profile(my_roster);target=roster_profile(target_roster)
    freshness_metadata=freshness_metadata if freshness_metadata is not None else trade_freshness_metadata(my_roster,target_roster)
    integrity=build_integrity_report(
        [*(my_roster or []),*(target_roster or [])],
        freshness_metadata=freshness_metadata,
    )
    blockers=list(dict.fromkeys([*blockers,*integrity["blockers"]]))
    allowed=bool(my_roster) and bool(target_roster) and integrity["recommendation_ready"] and not blockers
    publication_state="BLOCKED" if not allowed else "DEGRADED" if integrity["freshness"].get("has_aging") else "READY"
    return {"allowed":allowed,"blockers":blockers,"partner":partner or {},"owner_profile":owner,"partner_profile":target,"missing_evidence_players":missing,"freshness_metadata":freshness_metadata,"evidence_coverage":trade_evidence_coverage(my_roster,target_roster),"identity_lineage":trade_identity_lineage(my_roster,target_roster),"integrity":integrity,"publication_state":publication_state,"one_for_one":generate_one_for_one(my_roster,target_roster) if allowed else [],"two_for_one":generate_two_for_one(my_roster,target_roster) if allowed else [],"methodology":"Uses supplied projection, weekly score, rank, tier, injury availability, and verified roster position counts. It does not submit trades and is not a fairness guarantee."}
