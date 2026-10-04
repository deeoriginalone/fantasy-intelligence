"""Evidence-based trade decision support.

Uses only roster rows supplied by owner_operations. It never submits trades and
never invents projections or player identity.
"""
from services.weekly_lineup_intelligence import optimize_lineup
from services.integrity import build_integrity_report, calculate_freshness

TARGETS={"QB":2,"RB":4,"WR":4,"TE":2,"K":1,"DEF":1}
CORE={"QB","RB","WR","TE"}
HEALTHY={"","healthy","healthy / not listed","none","not listed"}


def number(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return default


def evidence_ready(player, allow_preliminary=False):
    weekly_evidence = player.get("weekly_evidence") or {}
    # Matchup uncertainty reduces confidence (see matchup_uncertain) rather
    # than blocking trade visibility when roster/health/projection evidence exists.
    if not allow_preliminary and weekly_evidence and any(
        not item.get("authoritative")
        and domain not in ("projection", "matchup")
        for domain, item in weekly_evidence.items()
    ):
        return False
    if not allow_preliminary and weekly_evidence.get("projection") and not player.get("projection_retrieved_at"):
        return False
    return bool(player.get("player")) and player.get("position") in TARGETS and (player.get("projection") is not None or player.get("weekly_score") is not None or player.get("rank") is not None)


def matchup_uncertain(player):
    """True when matchup evidence is not authoritative for this player."""
    matchup = (player.get("weekly_evidence") or {}).get("matchup")
    return bool(matchup) and not matchup.get("authoritative")


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


def enriched(player,profile,allow_preliminary=False):
    row=dict(player)
    row["trade_value"]=trade_value(row)
    row["is_starter"]=row.get("player") in profile["starter_names"]
    row["evidence_ready"]=evidence_ready(row,allow_preliminary)
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
    # Matchup evidence is informational; unavailable matchup data reduces
    # confidence without being invented or granted ranking authority.
    if any(matchup_uncertain(p) for p in players):
        score=max(0,score-15)
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


def _informational_roster(roster):
    evidence_fields = (
        "source", "source_recorded_at", "retrieved_at", "imported_at",
        "freshness_state", "completeness_state", "blocker",
        "recommendation_impact", "authoritative",
    )
    rows = []
    for player in roster or []:
        weekly = player.get("weekly_evidence") or {}
        rows.append({
            "player_id": next((player.get(field) for field in ("source_player_id", "local_player_id", "player_id") if player.get(field) not in (None, "")), None),
            "player_name": player.get("player"),
            "position": player.get("position"),
            "opponent": player.get("opponent"),
            "game_time_pacific": player.get("game_time_pacific"),
            "bye_week": player.get("bye_week"),
            "is_bye": player.get("is_bye"),
            "injury_status": player.get("injury_status"),
            "health_status_available": player.get("health_status_available"),
            "injury_source": player.get("injury_source"),
            "injury_retrieved_at": next((player.get(field) for field in ("injury_updated_at", "health_updated_at", "last_health_update") if player.get(field) not in (None, "")), None),
            "matchup_rank": player.get("matchup_rank"),
            "matchup_source": player.get("matchup_source"),
            "matchup_retrieved_at": player.get("matchup_retrieved_at"),
            "schedule_evidence": {key: (weekly.get("schedule") or {}).get(key) for key in evidence_fields} if weekly.get("schedule") else None,
            "bye_evidence": {key: (weekly.get("bye") or {}).get(key) for key in evidence_fields} if weekly.get("bye") else None,
            "matchup_evidence": {key: (weekly.get("matchup") or {}).get(key) for key in evidence_fields} if weekly.get("matchup") else None,
        })
    return rows


def _preliminary_analysis(my_roster, target_roster, owner_profile, partner_profile, blockers, allowed, ownership_verified):
    owner_rows = list(my_roster or [])
    partner_rows = list(target_roster or [])
    all_rows = [*owner_rows, *partner_rows]
    roster_complete = bool(owner_rows) and bool(partner_rows) and all(
        player.get("player") and player.get("position") in TARGETS
        for player in all_rows
    )
    identity_ids = [
        next((player.get(field) for field in ("source_player_id", "local_player_id", "player_id") if player.get(field) not in (None, "")), None)
        for player in all_rows
    ]
    identity_complete = bool(all_rows) and all(
        player.get("identity_state") == "RESOLVED" and identity_id is not None
        for player, identity_id in zip(all_rows, identity_ids)
    ) and len(set(identity_ids)) == len(identity_ids)
    contradictory = any(
        any(token in str(value).upper() for token in ("CONTRADICTORY", "CONFLICT", "AMBIGUOUS"))
        for player in all_rows
        for value in [*(player.get("evidence_gaps") or []), player.get("identity_state"), *[(item or {}).get("blocker") for item in (player.get("weekly_evidence") or {}).values()]]
        if value not in (None, "")
    )
    corrupted = any(
        "CORRUPT" in str(value).upper()
        for player in all_rows
        for value in [*(player.get("evidence_gaps") or []), *[(item or {}).get("blocker") for item in (player.get("weekly_evidence") or {}).values()]]
        if value not in (None, "")
    )
    ownership_unresolved = any(
        "OWNERSHIP_UNRESOLVED" in str(value).upper()
        or str(value).upper() in {"UNRESOLVED", "UNKNOWN", "BLOCKED"}
        for player in all_rows
        for value in [player.get("ownership_state"), (player.get("weekly_evidence") or {}).get("ownership", {}).get("state"), (player.get("weekly_evidence") or {}).get("ownership", {}).get("blocker")]
        if value not in (None, "")
    )
    needs_available = bool(owner_profile.get("needs")) and bool(partner_profile.get("needs")) and roster_complete

    def has_schedule(player):
        evidence = (player.get("weekly_evidence") or {}).get("schedule")
        return bool(player.get("opponent") or player.get("game_time_pacific") or evidence)

    def has_bye(player):
        return player.get("bye_week") is not None or bool((player.get("weekly_evidence") or {}).get("bye"))

    def has_matchup(player):
        return player.get("matchup_rank") is not None

    def has_projection(player):
        return player.get("projection") is not None

    evidence_domains = {
        "schedule": "PRELIMINARY" if any(has_schedule(player) for player in all_rows) else "UNAVAILABLE",
        "bye": "PRELIMINARY" if any(has_bye(player) for player in all_rows) else "UNAVAILABLE",
        "matchup_signal": "PRELIMINARY" if any(has_matchup(player) for player in all_rows) else "UNAVAILABLE",
        "projection_source": "UNVERIFIED" if any(has_projection(player) for player in all_rows) else "UNAVAILABLE",
    }
    supported_context = any(value != "UNAVAILABLE" for value in evidence_domains.values())
    owner_need_partner_surplus = sorted(
        position for position, need in (owner_profile.get("needs") or {}).items()
        if need and (partner_profile.get("surplus") or {}).get(position, 0)
    )
    partner_need_owner_surplus = sorted(
        position for position, need in (partner_profile.get("needs") or {}).items()
        if need and (owner_profile.get("surplus") or {}).get(position, 0)
    )
    roster_fit_available = bool(owner_need_partner_surplus or partner_need_owner_surplus)
    supported_context = supported_context or needs_available or roster_fit_available
    eligible = roster_complete and ownership_verified and identity_complete and not ownership_unresolved and not contradictory and not corrupted and supported_context
    state = "AUTHORITATIVE" if allowed and eligible else "PRELIMINARY" if eligible else "BLOCKED"
    return {
        "state": state,
        "eligibility": {
            "owner_roster_complete": bool(owner_rows) and all(player.get("player") and player.get("position") in TARGETS for player in owner_rows),
            "partner_roster_complete": bool(partner_rows) and all(player.get("player") and player.get("position") in TARGETS for player in partner_rows),
            "ownership_verified": ownership_verified and not ownership_unresolved,
            "identity_complete": identity_complete,
            "team_needs_available": needs_available,
            "roster_fit_available": roster_fit_available,
            "noncontradictory_evidence": not contradictory and not corrupted,
            "supported_context_available": supported_context,
        },
        "evidence_domains": evidence_domains,
        "benefits": {
            "owner_needs_addressable_by_partner_surplus": owner_need_partner_surplus,
            "partner_needs_addressable_by_owner_surplus": partner_need_owner_surplus,
            "roster_fit_basis_available": roster_fit_available,
        },
        "risks": list(dict.fromkeys(blockers)),
        "limitations": ["PRELIMINARY only; authority gaps remain.", "Existing package and fit calculations do not establish acceptance or transaction outcomes."],
    }


def _diagnostic_row(player, side, domain, failed_predicate, missing_field, blocker_code, *, source_field=None, timestamp_fields=(), evidence=None, freshness=None, completeness_field=None):
    evidence = evidence or {}
    freshness = freshness or {}
    source = player.get(source_field) if source_field else None
    if source is None:
        source = evidence.get("source")
    retrieved_at = next((player.get(field) for field in timestamp_fields if player.get(field) not in (None, "")), None)
    if retrieved_at is None:
        retrieved_at = evidence.get("retrieved_at")
    freshness_state = freshness.get("status") or evidence.get("freshness_state") or "UNAVAILABLE"
    completeness_state = player.get(completeness_field) if completeness_field else None
    if completeness_state is None:
        completeness_state = evidence.get("completeness_state")
    return {
        "player_id": next((player.get(field) for field in ("source_player_id", "local_player_id", "player_id") if player.get(field) not in (None, "")), None),
        "player_name": player.get("player"),
        "roster_side": side,
        "domain": domain,
        "failed_predicate": failed_predicate,
        "missing_field": missing_field,
        "source": source,
        "retrieved_at": retrieved_at,
        "freshness_state": freshness_state,
        "completeness_state": completeness_state or "UNAVAILABLE",
        "blocker_code": blocker_code,
        "recommendation_impact": freshness.get("recommendation_impact") or evidence.get("recommendation_impact") or "BLOCKED",
    }


def _player_blocker_diagnostics(my_roster, target_roster):
    diagnostics = []
    freshness_domains = (
        ("projection", "PROJECTION", "projection_source", ("projection_retrieved_at", "projection_updated_at", "projection_sync_time"), "projection_completeness"),
        ("matchup", "MATCHUP", "matchup_source", ("matchup_retrieved_at", "matchup_updated_at", "matchup_sync_time"), "matchup_completeness"),
        ("roster", "TRADE_EVIDENCE", "roster_source", ("roster_updated_at", "roster_sync_time"), None),
        ("injury", "TRADE_EVIDENCE", "injury_source", ("injury_updated_at", "health_updated_at", "last_health_update"), None),
    )

    def add(player, side, domain, predicate, missing_field, blocker_code, **kwargs):
        diagnostics.append(_diagnostic_row(player, side, domain, predicate, missing_field, blocker_code, **kwargs))

    for side, roster in (("OWNER", my_roster or []), ("PARTNER", target_roster or [])):
        for player in roster:
            gaps = set(player.get("evidence_gaps") or [])
            weekly = player.get("weekly_evidence") or {}

            for freshness_domain, diagnostic_domain, source_field, timestamp_fields, completeness_field in freshness_domains:
                if freshness_domain == "matchup" and (player.get("is_bye") or player.get("position") in {"K", "DEF"}):
                    continue
                if freshness_domain == "injury" and player.get("position") == "DEF":
                    continue
                freshness = calculate_freshness(player, freshness_domain)
                if freshness.get("blocker"):
                    missing_field = None
                    if freshness.get("status") == "UNKNOWN":
                        missing_field = timestamp_fields[0]
                    add(
                        player,
                        side,
                        diagnostic_domain,
                        f"{freshness_domain} freshness must be FRESH or AGING; observed {freshness.get('status')}",
                        missing_field,
                        freshness["blocker"],
                        source_field=source_field,
                        timestamp_fields=timestamp_fields,
                        freshness=freshness,
                        completeness_field=completeness_field,
                    )

            for evidence_domain in ("schedule", "bye", "identity"):
                evidence = weekly.get(evidence_domain)
                if evidence and not evidence.get("authoritative"):
                    if evidence_domain == "schedule":
                        diagnostic_domain = "SCHEDULE"
                        missing_field = "opponent" if not player.get("opponent") and not player.get("is_bye") else None
                        source_field = "schedule_source"
                    elif evidence_domain == "bye":
                        diagnostic_domain = "BYE"
                        missing_field = "bye_week" if player.get("bye_week") is None else None
                        source_field = None
                    else:
                        diagnostic_domain = "IDENTITY"
                        missing_field = "identity_state" if player.get("identity_state") is None else None
                        source_field = None
                    field_check = next((field for field in ("source", "retrieved_at", "freshness_state", "completeness_state") if evidence.get(field) in (None, "")), None)
                    missing_field = missing_field or field_check
                    add(
                        player,
                        side,
                        diagnostic_domain,
                        f"weekly_evidence.{evidence_domain}.authoritative must be true",
                        missing_field,
                        evidence.get("blocker") or "TRADE_EVIDENCE_INCOMPLETE",
                        source_field=source_field,
                        timestamp_fields=(f"{evidence_domain}_retrieved_at",),
                        evidence=evidence,
                    )

            if "SCHEDULE_NOT_LOADED_FOR_WEEK" in gaps or "SCHEDULE_UNAVAILABLE" in gaps:
                code = "SCHEDULE_NOT_LOADED_FOR_WEEK" if "SCHEDULE_NOT_LOADED_FOR_WEEK" in gaps else "SCHEDULE_UNAVAILABLE"
                add(player, side, "SCHEDULE", "opponent is required unless the player is on bye", "opponent" if not player.get("opponent") and not player.get("is_bye") else None, code, source_field="schedule_source", timestamp_fields=("schedule_retrieved_at",), evidence=weekly.get("schedule"))

            if "BYE_WEEK_NOT_LOADED" in gaps or "BYE_WEEK_UNAVAILABLE" in gaps:
                code = "BYE_WEEK_NOT_LOADED" if "BYE_WEEK_NOT_LOADED" in gaps else "BYE_WEEK_UNAVAILABLE"
                add(player, side, "BYE", "bye_week evidence is required", "bye_week" if player.get("bye_week") is None else None, code, evidence=weekly.get("bye"))

            if "MATCHUP_EVIDENCE_UNAVAILABLE" in gaps:
                context = f"opponent={player.get('opponent')!r}, position={player.get('position')!r}"
                if player.get("position") not in {"K", "DEF"} and player.get("matchup_rank") is None and not player.get("is_bye"):
                    add(player, side, "MATCHUP", f"matchup_rank is required for {context}", "matchup_rank", "MATCHUP_EVIDENCE_UNAVAILABLE", source_field="matchup_source", timestamp_fields=("matchup_retrieved_at", "matchup_updated_at", "matchup_sync_time"), evidence=weekly.get("matchup"))
                if not player.get("opponent") and not player.get("is_bye"):
                    add(player, side, "SCHEDULE", "opponent is required unless the player is on bye", "opponent", "MATCHUP_EVIDENCE_UNAVAILABLE", source_field="schedule_source", timestamp_fields=("schedule_retrieved_at",), evidence=weekly.get("schedule"))

            known_gaps = {
                "INJURY_STATUS_UNRESOLVED": ("TRADE_EVIDENCE", "injury_status must be resolved", "injury_status", "injury_source", ("injury_updated_at", "health_updated_at", "last_health_update")),
                "WEEKLY_VALUE_UNAVAILABLE": ("TRADE_EVIDENCE", "weekly_score must be available", "weekly_score", None, ()),
            }
            handled_gaps = {
                "SCHEDULE_NOT_LOADED_FOR_WEEK", "SCHEDULE_UNAVAILABLE",
                "BYE_WEEK_NOT_LOADED", "BYE_WEEK_UNAVAILABLE",
                "MATCHUP_EVIDENCE_UNAVAILABLE",
            }
            for gap in sorted(gaps - handled_gaps):
                diagnostic_domain, predicate, missing_field, source_field, timestamp_fields = known_gaps.get(
                    gap,
                    ("TRADE_EVIDENCE", f"evidence_gaps contains {gap}", None, None, ()),
                )
                add(player, side, diagnostic_domain, predicate, missing_field, gap, source_field=source_field, timestamp_fields=timestamp_fields)

            if not player.get("player"):
                add(player, side, "TRADE_EVIDENCE", "player must be non-empty", "player", "TRADE_EVIDENCE_INCOMPLETE")
            if player.get("position") not in TARGETS:
                add(player, side, "TRADE_EVIDENCE", f"position must be one of {','.join(sorted(TARGETS))}", "position" if player.get("position") is None else None, "TRADE_EVIDENCE_INCOMPLETE")
            if player.get("projection") is None and player.get("weekly_score") is None and player.get("rank") is None:
                add(player, side, "TRADE_EVIDENCE", "projection, weekly_score, or rank must be present", "projection|weekly_score|rank", "TRADE_EVIDENCE_INCOMPLETE")

    domain_order = {name: index for index, name in enumerate(("PROJECTION", "MATCHUP", "SCHEDULE", "BYE", "IDENTITY", "TRADE_EVIDENCE"))}
    diagnostics.sort(key=lambda row: (
        0 if row["roster_side"] == "OWNER" else 1,
        domain_order[row["domain"]],
        str(row["player_id"] or ""),
        str(row["player_name"] or ""),
        str(row["blocker_code"] or ""),
        str(row["failed_predicate"] or ""),
        str(row["missing_field"] or ""),
    ))
    unique = []
    seen = set()
    for diagnostic in diagnostics:
        key = tuple(diagnostic[field] for field in diagnostic)
        if key not in seen:
            seen.add(key)
            unique.append(diagnostic)
    return unique


def generate_one_for_one(my_roster,target_roster,limit=12,allow_preliminary=False):
    mine=roster_profile(my_roster);theirs=roster_profile(target_roster)
    offers=[enriched(p,mine,allow_preliminary) for p in my_roster if evidence_ready(p,allow_preliminary)]
    targets=[enriched(p,theirs,allow_preliminary) for p in target_roster if evidence_ready(p,allow_preliminary)]
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


def generate_two_for_one(my_roster,target_roster,limit=8,allow_preliminary=False):
    mine=roster_profile(my_roster);theirs=roster_profile(target_roster)
    offers=[enriched(p,mine,allow_preliminary) for p in my_roster if evidence_ready(p,allow_preliminary) and not (p.get("player") in mine["starter_names"] and mine["surplus"].get(p.get("position"),0)==0)]
    targets=[enriched(p,theirs,allow_preliminary) for p in target_roster if evidence_ready(p,allow_preliminary)]
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
    integrity_allowed=bool(my_roster) and bool(target_roster) and integrity["recommendation_ready"] and not blockers
    roster_freshness=integrity["freshness"]["domains"]["roster"]["status"]
    ownership_verified=roster_freshness in {"FRESH","AGING"}
    preliminary_analysis=_preliminary_analysis(my_roster,target_roster,owner,target,blockers,integrity_allowed,ownership_verified)
    authoritative_allowed=preliminary_analysis["state"]=="AUTHORITATIVE"
    preliminary_allowed=preliminary_analysis["state"]=="PRELIMINARY"
    allowed=authoritative_allowed or preliminary_allowed
    publication_state="READY" if authoritative_allowed and not integrity["freshness"].get("has_aging") else "DEGRADED" if authoritative_allowed else "PRELIMINARY" if preliminary_allowed else "BLOCKED"
    integrity["diagnostics"] = _player_blocker_diagnostics(my_roster, target_roster) if not authoritative_allowed else []
    return {"allowed":allowed,"blockers":blockers,"partner":partner or {},"owner_profile":owner,"partner_profile":target,"informational_rosters":{"owner":_informational_roster(my_roster),"partner":_informational_roster(target_roster)},"preliminary_analysis":preliminary_analysis,"missing_evidence_players":missing,"freshness_metadata":freshness_metadata,"evidence_coverage":trade_evidence_coverage(my_roster,target_roster),"identity_lineage":trade_identity_lineage(my_roster,target_roster),"integrity":integrity,"publication_state":publication_state,"one_for_one":generate_one_for_one(my_roster,target_roster,allow_preliminary=preliminary_allowed) if allowed else [],"two_for_one":generate_two_for_one(my_roster,target_roster,allow_preliminary=preliminary_allowed) if allowed else [],"methodology":"Uses supplied projection, weekly score, rank, tier, injury availability, and verified roster position counts. It does not submit trades and is not a fairness guarantee."}
