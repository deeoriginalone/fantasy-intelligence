"""Fail-closed UX evidence helpers. No external writes or synthetic metrics."""
from datetime import datetime, timezone
EVIDENCE_STATES={"AVAILABLE","UNKNOWN","STALE","UNSUPPORTED","NOT_APPLICABLE"}
def evidence(value=None,*,state=None,source=None,updated_at=None,blocker=None):
    state=str(state or ("AVAILABLE" if value not in (None,"") else "UNKNOWN")).upper()
    if state not in EVIDENCE_STATES: state="UNKNOWN"
    return {"value":value,"state":state,"source":source or "UNVERIFIED","updated_at":updated_at,"blocker":blocker}
def dashboard_contract(*,league_row=None,source="league_info",error=None):
    row=list(tuple(league_row or ())[:4]); row += [None]*(4-len(row))
    names=("league_name","team_name","teams","scoring_type")
    fields={n:evidence(v,source=source,blocker=error) for n,v in zip(names,row)}
    return {"ready":all(x["state"]=="AVAILABLE" for x in fields.values()) and not error,"source":source,"fields":fields,"blockers":[error] if error else [],"generated_at":datetime.now(timezone.utc).isoformat()}
def roster_lineage(players):
    rows=[]
    for p in players or []:
        rows.append({"player":p.get("player") or p.get("player_name") or "UNKNOWN","position":evidence(p.get("position"),source=p.get("position_source")),"ownership":evidence(p.get("ownership"),source=p.get("ownership_source")),"health":evidence(p.get("injury_status"),source=p.get("health_source"),updated_at=p.get("injury_updated_at")),"matchup":evidence(p.get("matchup_rank"),source=p.get("matchup_source"),updated_at=p.get("matchup_updated_at")),"projection":evidence(p.get("weekly_score") if p.get("weekly_score") is not None else p.get("projection"),source=p.get("projection_source"),updated_at=p.get("projection_updated_at"))})
    return rows
def filter_available_waivers(candidates,owned_names):
    owned={str(x).strip().casefold() for x in owned_names or [] if str(x).strip()}
    return [c for c in candidates or [] if str(c.get("player") or c.get("player_name") or c.get("name") or "").strip().casefold() not in owned]

def page_evidence(*, page, fields=None, blockers=None, source=None):
    normalized={}
    for name,value in dict(fields or {}).items():
        normalized[name]=value if isinstance(value,dict) and "state" in value else evidence(value,source=source)
    blockers=list(blockers or [])
    return {"page":str(page),"ready":bool(normalized) and all(v.get("state")=="AVAILABLE" for v in normalized.values()) and not blockers,"fields":normalized,"blockers":blockers}

def lineup_explanations(data):
    data=dict(data or {})
    return {"decisions":[{"slot":r.get("slot"),"action":r.get("action"),"why":r.get("reason") or "No verified explanation supplied.","confidence":r.get("confidence") or {"label":"UNKNOWN","score":0}} for r in data.get("start_sit_decisions") or []],"blockers":list(data.get("blockers") or [])}

def waiver_explanations(candidates,owned_names=None):
    rows=filter_available_waivers(candidates,owned_names or [])
    return [{"player":r.get("player") or r.get("player_name") or "UNKNOWN","reason":r.get("reason") or r.get("faab_reason") or "No verified explanation supplied."} for r in rows]

def gm_action_evidence(data):
    data=dict(data or {})
    return {"actions":[{"action":r.get("action"),"urgency":r.get("urgency") or "UNKNOWN","blockers":list(r.get("blockers") or []),"source":r.get("source") or "UNVERIFIED","reason":r.get("reason") or "No verified explanation supplied."} for r in data.get("actions") or []]}

def _fact_value(value):
    if isinstance(value, dict) and "state" in value:
        return value.get("value") if value.get("state") == "AVAILABLE" else None
    return value


def shared_league_facts(league=None, *, source="Sleeper API", blocker=None):
    # Fail-closed season and league-status facts shared by active routes.
    league = dict(league or {})
    return {
        "season": evidence(league.get("season"), source=source, blocker=blocker),
        "league_status": evidence(league.get("status"), source=source, blocker=blocker),
    }


def format_pacific_datetime(value):
    if value in (None, ""):
        return None
    try:
        from zoneinfo import ZoneInfo
        if isinstance(value, (int, float)):
            numeric = float(value)
            if numeric > 10_000_000_000:
                numeric /= 1000.0
            parsed = datetime.fromtimestamp(numeric, tz=timezone.utc)
        else:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%B %-d, %Y, %-I:%M %p %Z")
    except (TypeError, ValueError, OverflowError):
        return None


def dashboard_agreement_evidence(dashboard_facts=None, my_team_facts=None, command_center_facts=None):
    pages = {"dashboard": dict(dashboard_facts or {}), "my_team": dict(my_team_facts or {}), "weekly_command_center": dict(command_center_facts or {})}
    names = sorted(set().union(*(set(values) for values in pages.values())))
    checked, mismatches, unavailable = [], [], []
    for name in names:
        values = {page: _fact_value(facts.get(name)) for page, facts in pages.items()}
        available = {page: str(value).strip() for page, value in values.items() if value not in (None, "")}
        if len(available) < 2:
            unavailable.append(name)
            continue
        checked.append(name)
        if len({value.casefold() for value in available.values()}) > 1:
            mismatches.append({"field": name, "values": available})
    state = "BLOCKED" if mismatches else ("AVAILABLE" if checked else "UNKNOWN")
    blocker = "CROSS_PAGE_FACT_MISMATCH" if mismatches else (None if checked else "CROSS_PAGE_FACTS_UNAVAILABLE")
    return {"state": state, "agrees": state == "AVAILABLE", "checked_fields": checked, "mismatches": mismatches, "unavailable_fields": unavailable, "blocker": blocker, "source": "shared active-route facts"}


def dashboard_state_contract(league=None, draft=None, source="Sleeper API", error=None):
    league = dict(league or {})
    draft = dict(draft or {})
    raw_start = draft.get("start_time")
    display_start = format_pacific_datetime(raw_start)
    return {
        "season": evidence(league.get("season"), source=source, blocker=error),
        "league_status": evidence(league.get("status"), source=source, blocker=error),
        "draft_status": evidence(draft.get("status"), source=source, blocker=error),
        "draft_type": evidence(draft.get("type"), source=source, blocker=error),
        "draft_start_time": evidence(display_start, state="AVAILABLE" if display_start else "UNKNOWN", source=source, blocker=error or ("DRAFT_START_TIME_INVALID" if raw_start not in (None, "") and not display_start else None)),
    }


def roster_lineage_view(players):
    """UX.2/UX.7 reproducible player identity and evidence gaps."""
    rows = []
    for player in players or []:
        if not isinstance(player, dict):
            continue
        row = {
            "position": evidence(
                player.get("position"),
                source=player.get("position_source") or "roster",
            ),
            "ownership": evidence(
                player.get("ownership"),
                source=player.get("ownership_source") or "roster",
            ),
            "health": evidence(
                player.get("injury_status"),
                source=player.get("health_source"),
            ),
            "matchup": evidence(
                player.get("matchup_rank"),
                source=player.get("matchup_source"),
            ),
            "projection": evidence(
                player.get("projection"),
                source=player.get("projection_source"),
            ),
        }
        row["player"] = player.get("player") or player.get("player_name") or "UNKNOWN"
        row["unknown_fields"] = [name for name, item in row.items() if isinstance(item, dict) and item.get("state") != "AVAILABLE"]
        rows.append(row)
    return rows


def route_payload_evidence(page, count=None, blockers=None):
    """UX.3/UX.4/UX.6 active payload state shown by shared panels."""
    return page_evidence(page=page, fields={"route_payload_count": count}, blockers=blockers, source="active route payload")


WAIVER_FRESHNESS_STATES = ("FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED")


def waiver_roster_coverage(rosters, expected_count=None):
    """Validate active-roster coverage without treating a list as complete."""
    rows = list(rosters) if isinstance(rosters, list) else []
    roster_ids = [row.get("roster_id") for row in rows if isinstance(row, dict)]
    missing_ids = [index for index, roster_id in enumerate(roster_ids) if roster_id in (None, "")]
    normalized_ids = [str(roster_id) for roster_id in roster_ids if roster_id not in (None, "")]
    duplicate_ids = sorted({roster_id for roster_id in normalized_ids if normalized_ids.count(roster_id) > 1})
    blockers = []
    if not isinstance(rosters, list):
        blockers.append("WAIVER_ROSTER_DATA_UNAVAILABLE")
    if missing_ids:
        blockers.append("WAIVER_ROSTER_ID_MISSING")
    if duplicate_ids:
        blockers.append("WAIVER_DUPLICATE_ROSTER_IDS")
    if expected_count is None:
        blockers.append("WAIVER_EXPECTED_ROSTER_COUNT_UNAVAILABLE")
    elif len(normalized_ids) != int(expected_count):
        blockers.append("WAIVER_ROSTER_COVERAGE_INCOMPLETE")
    return {
        "expected_active_roster_count": expected_count,
        "observed_active_roster_count": len(rows),
        "unique_roster_ids": sorted(set(normalized_ids)),
        "missing_roster_id_indexes": missing_ids,
        "duplicate_roster_ids": duplicate_ids,
        "completeness_state": "COMPLETE" if not blockers else "INCOMPLETE",
        "blockers": blockers,
        "allowed": not blockers,
    }


def waiver_evidence_contract(
    *,
    domain,
    league_id=None,
    source=None,
    source_record_time=None,
    retrieved_at=None,
    age=None,
    freshness_threshold_id=None,
    freshness_state="UNAVAILABLE",
    completeness_state="INCOMPLETE",
    blocker=None,
    fallback_used=None,
    recommendation_impact="BLOCKED",
    expected_active_roster_count=None,
    observed_active_roster_count=None,
    unique_owned_player_ids=None,
    duplicate_conflicts=None,
    require_roster_coverage=False,
    require_timestamps=False,
):
    """Represent decision-critical waiver evidence without inventing freshness."""
    state = str(freshness_state or "UNAVAILABLE").upper()
    if state not in WAIVER_FRESHNESS_STATES:
        state = "BLOCKED"
        blocker = blocker or "WAIVER_FRESHNESS_STATE_INVALID"
    completeness = str(completeness_state or "INCOMPLETE").upper()
    if completeness not in {"COMPLETE", "INCOMPLETE", "UNKNOWN"}:
        completeness = "INCOMPLETE"
        blocker = blocker or "WAIVER_COMPLETENESS_STATE_INVALID"
    if not freshness_threshold_id:
        state = "BLOCKED"
        blocker = blocker or "WAIVER_FRESHNESS_THRESHOLD_UNVERIFIED"
    if state not in {"FRESH", "AGING"}:
        blocker = blocker or f"WAIVER_FRESHNESS_{state}"
    if require_timestamps and not source_record_time:
        blocker = blocker or "WAIVER_SOURCE_TIMESTAMP_MISSING"
    if require_timestamps and not retrieved_at:
        blocker = blocker or "WAIVER_RETRIEVED_AT_MISSING"
    if require_roster_coverage:
        if expected_active_roster_count is None or observed_active_roster_count is None:
            blocker = blocker or "WAIVER_ROSTER_COVERAGE_UNVERIFIED"
        elif expected_active_roster_count != observed_active_roster_count:
            blocker = blocker or "WAIVER_ROSTER_COVERAGE_INCOMPLETE"
        if duplicate_conflicts:
            blocker = blocker or "WAIVER_DUPLICATE_OWNERSHIP"
    if completeness != "COMPLETE":
        blocker = blocker or "WAIVER_EVIDENCE_INCOMPLETE"
    allowed = state in {"FRESH", "AGING"} and completeness == "COMPLETE" and not blocker
    if not allowed:
        recommendation_impact = "BLOCKED"
    return {
        "domain": domain,
        "league_id": league_id,
        "source": source or "UNVERIFIED",
        "source_record_time": source_record_time,
        "retrieved_at": retrieved_at,
        "age": age,
        "freshness_threshold_id": freshness_threshold_id,
        "freshness_state": state,
        "completeness_state": completeness,
        "blocker": blocker,
        "fallback_used": fallback_used,
        "expected_active_roster_count": expected_active_roster_count,
        "observed_active_roster_count": observed_active_roster_count,
        "unique_owned_player_ids": sorted({str(player_id) for player_id in unique_owned_player_ids or []}),
        "duplicate_conflicts": list(duplicate_conflicts or []),
        "recommendation_impact": recommendation_impact if allowed else "BLOCKED",
        "allowed": allowed,
    }


def evaluate_waiver_availability(candidates, ownership, eligibility):
    """Publish only candidates covered by complete, fresh, stable-ID evidence."""
    ownership = dict(ownership or {})
    eligibility = dict(eligibility or {})
    blockers = [
        evidence.get("blocker")
        for evidence in (ownership, eligibility)
        if evidence.get("blocker") or not evidence.get("allowed")
    ]
    blockers = list(dict.fromkeys(blocker for blocker in blockers if blocker))
    if blockers:
        return {
            "candidates": [],
            "allowed": False,
            "blockers": blockers,
            "recommendation_impact": "BLOCKED",
            "ownership": ownership,
            "eligibility": eligibility,
        }

    owned_ids = {str(player_id) for player_id in ownership.get("owned_player_ids") or []}
    eligible_ids = {str(player_id) for player_id in eligibility.get("eligible_player_ids") or []}
    published = []
    for candidate in candidates or []:
        row = dict(candidate)
        player_id = str(row.get("player_id") or "")
        if not player_id or player_id in owned_ids or player_id not in eligible_ids:
            continue
        row["verified_available"] = True
        row["ownership_evidence"] = ownership
        row["eligibility_evidence"] = eligibility
        published.append(row)
    return {
        "candidates": published,
        "allowed": True,
        "blockers": [],
        "recommendation_impact": "AVAILABLE",
        "ownership": ownership,
        "eligibility": eligibility,
    }

UX_REQUIRED_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")


def freshness_evidence(updated_at=None, *, source=None, stale=False, blocker=None):
    if blocker:
        return evidence(None, state="UNKNOWN", source=source, updated_at=updated_at, blocker=blocker)
    if not updated_at:
        return evidence(None, state="UNKNOWN", source=source, blocker="UPDATED_AT_UNAVAILABLE")
    return evidence(updated_at, state="STALE" if stale else "AVAILABLE", source=source, updated_at=updated_at)


def roster_requirement_evidence(players, required_positions=None):
    required = tuple(required_positions or UX_REQUIRED_POSITIONS)
    present = set()

    for player in players or []:
        if not isinstance(player, dict):
            continue

        position = str(
            player.get("position") or ""
        ).upper().strip()

        if position == "DST":
            position = "DEF"

        present.add(position)

    missing = [
        position
        for position in required
        if position not in present
    ]
    return page_evidence(
        page="team",
        fields={"required_positions": list(required), "present_positions": sorted(present), "missing_positions": missing},
        blockers=["MISSING_REQUIRED_POSITIONS"] if missing else [],
        source="active roster payload",
    )


def waiver_availability_evidence(candidates, owned_names=None, eligibility_verified=False):
    available = filter_available_waivers(candidates, owned_names or [])
    blockers = [] if eligibility_verified else ["ELIGIBILITY_UNVERIFIED"]
    return {
        "candidates": available,
        "evidence": page_evidence(
            page="waivers",
            fields={"candidate_count": len(available), "owned_filter_applied": True, "eligibility_verified": bool(eligibility_verified)},
            blockers=blockers,
            source="active waiver payload",
        ),
    }


def payload_contract(page, payload, *, source="active route payload", blockers=None):
    count = len(payload) if hasattr(payload, "__len__") else None
    return page_evidence(
        page=page,
        fields={"payload_count": count, "payload_present": payload is not None},
        blockers=blockers,
        source=source,
    )


def gm_impact_evidence(data):
    base = gm_action_evidence(data)
    for item in base.get("actions", []):
        item["impact"] = item.get("impact") or "UNKNOWN"
    return base


def lineage_audit(rows):
    diagnostics = []
    for row in rows or []:
        unknown_fields = []
        fallbacks = []
        transformations = []
        for name, item in row.items():
            if not isinstance(item, dict):
                continue
            if item.get("state") != "AVAILABLE":
                unknown_fields.append(name)
            if item.get("fallback"):
                fallbacks.append({"field": name, "fallback": item.get("fallback")})
            if item.get("transformation"):
                transformations.append({"field": name, "transformation": item.get("transformation")})
        if unknown_fields or fallbacks or transformations:
            diagnostics.append({
                "player": row.get("player") or "UNKNOWN",
                "unknown_fields": unknown_fields,
                "fallbacks": fallbacks,
                "transformations": transformations,
            })
    return diagnostics
