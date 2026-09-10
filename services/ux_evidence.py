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
