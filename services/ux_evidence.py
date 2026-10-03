"""Fail-closed UX evidence helpers. No external writes or synthetic metrics."""
from datetime import datetime, timezone
from services.integrity.integrity_service import DEFAULT_FRESHNESS_LIMITS, calculate_freshness
EVIDENCE_STATES={"AVAILABLE","UNKNOWN","STALE","UNSUPPORTED","NOT_APPLICABLE"}


def weekly_evidence_contract(*, domain, source=None, source_recorded_at=None, retrieved_at=None, age=None, freshness_state="UNAVAILABLE", completeness_state="UNAVAILABLE", blocker=None, fallback_used=None, recommendation_impact=None):
    """Shared fail-closed contract for weekly decision inputs."""
    freshness_state = str(freshness_state or "UNAVAILABLE").upper()
    completeness_state = str(completeness_state or "UNAVAILABLE").upper()
    if freshness_state not in {"FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED"}:
        freshness_state = "UNAVAILABLE"
    if completeness_state not in {"COMPLETE", "INCOMPLETE", "UNAVAILABLE"}:
        completeness_state = "UNAVAILABLE"
    authoritative = freshness_state in {"FRESH", "AGING"} and completeness_state == "COMPLETE" and bool(source) and bool(retrieved_at) and not blocker
    return {
        "domain": domain,
        "source": source or "UNVERIFIED",
        "source_recorded_at": source_recorded_at,
        "retrieved_at": retrieved_at,
        "age": age,
        "freshness_state": freshness_state if authoritative else ("BLOCKED" if blocker else "UNAVAILABLE"),
        "completeness_state": completeness_state,
        "blocker": blocker or (None if authoritative else "WEEKLY_SOURCE_METADATA_UNAVAILABLE"),
        "fallback_used": fallback_used,
        "recommendation_impact": recommendation_impact or ("Supports the affected weekly decision." if authoritative else "The affected weekly decision is unavailable until automated source evidence is refreshed."),
        "authoritative": authoritative,
    }
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
    season = league.get("season")
    season_state = "AVAILABLE" if str(season or "").isdigit() else "UNKNOWN"
    season_blocker = error
    if season not in (None, "") and season_state != "AVAILABLE":
        season_state, season_blocker = "UNSUPPORTED", "SEASON_VALUE_UNSUPPORTED"
    draft_status = draft.get("status")
    draft_status_state = "AVAILABLE" if draft_status in {"pre_draft", "drafting", "paused", "complete"} else "UNKNOWN"
    draft_status_blocker = error
    if draft_status not in (None, "") and draft_status_state != "AVAILABLE":
        draft_status_state, draft_status_blocker = "UNSUPPORTED", "DRAFT_STATUS_UNSUPPORTED"
    draft_type = draft.get("type")
    draft_type_state = "AVAILABLE" if draft_type in {"snake", "linear", "auction", "mock"} else "UNKNOWN"
    draft_type_blocker = error
    if draft_type not in (None, "") and draft_type_state != "AVAILABLE":
        draft_type_state, draft_type_blocker = "UNSUPPORTED", "DRAFT_TYPE_UNSUPPORTED"
    return {
        "season": evidence(season, state=season_state, source=source, blocker=season_blocker),
        "league_status": evidence(league.get("status"), source=source, blocker=error),
        "draft_status": evidence(draft_status, state=draft_status_state, source=source, blocker=draft_status_blocker),
        "draft_type": evidence(draft_type, state=draft_type_state, source=source, blocker=draft_type_blocker),
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
    field = "visible_preliminary_candidate_count" if str(page).lower() == "waivers" else "route_payload_count"
    return page_evidence(page=page, fields={field: count}, blockers=blockers, source="active route payload")


WAIVER_FRESHNESS_STATES = ("FRESH", "AGING", "STALE", "UNAVAILABLE", "BLOCKED")
WAIVER_OWNERSHIP_THRESHOLD_ID = "integrity.roster.v1"


def resolve_waiver_candidate_identity(candidate, catalog, name_normalizer):
    """Resolve one waiver candidate to a catalog-backed Sleeper player ID."""
    candidate = dict(candidate or {})
    catalog = dict(catalog or {})
    input_player_id = str(candidate.get("player_id") or "").strip()
    candidate_name = candidate.get("player") or candidate.get("name")
    candidate_team = str(candidate.get("nfl_team") or candidate.get("team") or "").upper()
    candidate_position = str(candidate.get("position") or "").upper().replace("DST", "DEF")
    base = {
        "input_reference": candidate_name,
        "input_player_id": input_player_id or None,
        "resolved_player_id": None,
        "resolution_state": "UNRESOLVED",
        "resolution_method": None,
        "candidate_name": candidate_name,
        "candidate_team": candidate_team or None,
        "candidate_position": candidate_position or None,
        "catalog_name": None,
        "catalog_team": None,
        "catalog_position": None,
        "corroborating_fields": [],
        "conflicting_fields": [],
        "candidate_source": "local waiver candidate",
        "catalog_source": "Sleeper player catalog",
        "completeness_state": "INCOMPLETE",
        "blocker": "WAIVER_CANDIDATE_ID_UNRESOLVED",
        "recommendation_impact": "BLOCKED",
    }
    if input_player_id:
        raw = catalog.get(input_player_id)
        if raw is None:
            base.update(resolution_state="UNSUPPORTED", blocker="WAIVER_CANDIDATE_ID_UNSUPPORTED")
            return base
        matches = [(input_player_id, raw)]
        method = "DIRECT_SLEEPER_ID"
    else:
        normalized = name_normalizer(candidate_name or "")
        if not normalized:
            return base
        matches = [
            (str(player_id), raw or {})
            for player_id, raw in catalog.items()
            if name_normalizer(
                (raw or {}).get("full_name")
                or " ".join(
                    part
                    for part in ((raw or {}).get("first_name"), (raw or {}).get("last_name"))
                    if part
                )
            ) == normalized
        ]
        if not matches:
            return base
        if len(matches) != 1:
            base.update(resolution_state="AMBIGUOUS", blocker="WAIVER_CANDIDATE_ID_AMBIGUOUS")
            return base
        method = "UNIQUE_CANONICAL_MATCH"
    player_id, raw = matches[0]
    catalog_position = str(raw.get("position") or "").upper().replace("DST", "DEF")
    catalog_team = str(raw.get("team") or "").upper()
    catalog_name = raw.get("full_name") or " ".join(
        part for part in (raw.get("first_name"), raw.get("last_name")) if part
    )
    conflicts = []
    corroborating = []
    if candidate_position:
        if candidate_position != catalog_position:
            conflicts.append("position")
        else:
            corroborating.append("position")
    if candidate_team and candidate_team != "FA":
        if candidate_team != catalog_team:
            conflicts.append("team")
        else:
            corroborating.append("team")
    base.update(
        catalog_name=catalog_name or None,
        catalog_team=catalog_team or None,
        catalog_position=catalog_position or None,
        corroborating_fields=corroborating,
        conflicting_fields=conflicts,
    )
    if conflicts:
        base.update(resolution_state="CONFLICTING", blocker="WAIVER_CANDIDATE_ID_CONFLICTING")
        return base
    base.update(
        resolved_player_id=player_id,
        resolution_state="RESOLVED",
        resolution_method=method,
        completeness_state="COMPLETE",
        blocker=None,
        recommendation_impact="AVAILABLE",
    )
    return base


def waiver_ownership_freshness(
    *,
    source_record_time=None,
    retrieved_at=None,
    source="Sleeper API",
    now=None,
):
    """Derive waiver ownership freshness from the existing roster registry."""
    threshold = DEFAULT_FRESHNESS_LIMITS["roster"]
    base = {
        "domain": "waiver ownership",
        "source": source,
        "source_record_time": source_record_time,
        "retrieved_at": retrieved_at,
        "age": None,
        "freshness_threshold_id": WAIVER_OWNERSHIP_THRESHOLD_ID,
        "freshness_threshold_seconds": threshold,
        "freshness_state": "BLOCKED",
        "completeness_state": "UNKNOWN",
        "blocker": None,
        "recommendation_impact": "BLOCKED",
        "allowed": False,
    }
    if not retrieved_at:
        base["blocker"] = "WAIVER_RETRIEVED_AT_MISSING"
        return base
    freshness = calculate_freshness(
        {"roster_sync_time": retrieved_at},
        "roster",
        now=now,
        max_age_seconds=threshold,
    )
    base["age"] = freshness["age_seconds"]
    if freshness["status"] == "FRESH":
        base["freshness_state"] = "FRESH"
        base["completeness_state"] = "COMPLETE"
        base["recommendation_impact"] = "AVAILABLE"
        base["allowed"] = True
    elif freshness["status"] in {"STALE", "EXPIRED"}:
        base["freshness_state"] = "STALE"
        base["blocker"] = "WAIVER_OWNERSHIP_STALE"
    else:
        base["blocker"] = "WAIVER_OWNERSHIP_FRESHNESS_UNAVAILABLE"
    return base


def derived_waiver_availability(
    *,
    league_id,
    ownership,
    supported_player_ids,
    supported_positions,
    candidates=None,
    identity_diagnostics=None,
):
    """Derive available players from current roster ownership and a supported pool."""
    ownership = dict(ownership or {})
    supported_ids = {str(player_id) for player_id in supported_player_ids or []}
    positions = {str(position).upper() for position in supported_positions or []}
    owned_ids = {str(player_id) for player_id in ownership.get("owned_player_ids") or []}
    blockers = []
    if not supported_ids:
        blockers.append("WAIVER_SUPPORTED_PLAYER_UNIVERSE_UNAVAILABLE")
    if not positions:
        blockers.append("WAIVER_ROSTER_POSITION_RULES_UNAVAILABLE")
    unsupported_ids = set()
    missing_ids = set()
    for candidate in candidates or []:
        player_id = str((candidate or {}).get("player_id") or "")
        position = str((candidate or {}).get("position") or "").upper()
        if not player_id:
            missing_ids.add(player_id)
        elif player_id not in supported_ids or position not in positions:
            unsupported_ids.add(player_id)
    blocker = blockers[0] if blockers else None
    freshness_state = ownership.get("freshness_state", "UNAVAILABLE")
    completeness_state = ownership.get("completeness_state", "INCOMPLETE")
    availability = waiver_evidence_contract(
        domain="waiver availability",
        league_id=league_id,
        source="Derived from current Sleeper rosters and supported player pool",
        source_record_time=None,
        retrieved_at=ownership.get("retrieved_at"),
        age=ownership.get("age"),
        freshness_threshold_id=ownership.get("freshness_threshold_id"),
        freshness_state=freshness_state,
        completeness_state=completeness_state,
        blocker=blocker,
        authority_state="DERIVED",
        authority_detail=(
            "Availability is derived from current league roster ownership "
            "and the supported player pool."
        ),
        recommendation_impact="AVAILABLE",
    )
    availability.update(
        eligible_player_ids=supported_ids - owned_ids - unsupported_ids,
        excluded_rostered_player_ids=sorted(owned_ids),
        unsupported_player_ids=sorted(unsupported_ids),
        missing_candidate_id_count=len(missing_ids),
        derivation="supported player universe minus active-league rostered player IDs",
        identity_diagnostics=dict(identity_diagnostics or {}),
    )
    return availability


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
    authority_state="UNKNOWN",
    authority_detail=None,
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
        "authority_state": authority_state,
        "authority_detail": authority_detail,
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
    published_ids = set()
    for candidate in candidates or []:
        row = dict(candidate)
        player_id = str(row.get("player_id") or "")
        if (
            not player_id
            or player_id in owned_ids
            or player_id not in eligible_ids
            or player_id in published_ids
        ):
            continue
        row["verified_available"] = True
        row["ownership_evidence"] = ownership
        row["eligibility_evidence"] = eligibility
        published.append(row)
        published_ids.add(player_id)
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
