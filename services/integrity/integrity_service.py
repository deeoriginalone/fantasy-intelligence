"""Shared read-only integrity, freshness, completeness, and confidence evaluation."""
from datetime import datetime, timezone
import os
from typing import Dict, List, Optional
DEFAULT_FRESHNESS_LIMITS={"roster":3600,"injury":86400,"matchup":86400,"projection":86400}
SCHEDULE_EVIDENCE_THRESHOLD_ID="schedule.evidence.v1"
BYE_EVIDENCE_THRESHOLD_ID="bye.evidence.v1"
MATCHUP_SAMPLE_THRESHOLD_ID="matchup.sample.v1"

def _positive_env_seconds(name, environ=None):
    value=(environ or os.environ).get(name)
    try:
        seconds=int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None

def schedule_bye_freshness_limits(environ=None):
    return {
        "schedule":{"id":SCHEDULE_EVIDENCE_THRESHOLD_ID,"seconds":_positive_env_seconds("SCHEDULE_EVIDENCE_MAX_AGE_SECONDS", environ)},
        "bye":{"id":BYE_EVIDENCE_THRESHOLD_ID,"seconds":_positive_env_seconds("BYE_EVIDENCE_MAX_AGE_SECONDS", environ)},
    }

def matchup_sample_threshold(environ=None):
    value=(environ or os.environ).get("MATCHUP_MIN_COMPLETED_GAMES")
    try:
        games=int(str(value).strip())
    except (TypeError, ValueError):
        games=None
    return {"id":MATCHUP_SAMPLE_THRESHOLD_ID,"completed_games":games if games and games > 0 else None}
TIMESTAMP_FIELDS={"roster":("roster_updated_at","roster_sync_time"),"injury":("injury_updated_at","health_updated_at","last_health_update"),"matchup":("matchup_updated_at","matchup_sync_time","matchup_retrieved_at"),"projection":("projection_updated_at","projection_sync_time","projection_retrieved_at")}
def _utc_now(now=None):
    v=now or datetime.now(timezone.utc); return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
def _parse_timestamp(value):
    if value in (None,""): return None
    if isinstance(value,datetime): p=value
    elif isinstance(value,(int,float)): p=datetime.fromtimestamp(value,tz=timezone.utc)
    elif isinstance(value,str):
        x=value.strip(); x=x[:-1]+"+00:00" if x.endswith("Z") else x
        try: p=datetime.fromisoformat(x)
        except ValueError: return None
    else: return None
    return p.replace(tzinfo=timezone.utc) if p.tzinfo is None else p.astimezone(timezone.utc)
def calculate_freshness(record:Dict,domain:str,now:Optional[datetime]=None,max_age_seconds:Optional[int]=None)->Dict:
    fields=TIMESTAMP_FIELDS.get(domain,()); source_field=next((f for f in fields if record.get(f) not in (None,"")),None); stamp=_parse_timestamp(record.get(source_field) if source_field else None); source=record.get(f"{domain}_source") or source_field or "Unavailable"; limit=max_age_seconds if max_age_seconds is not None else DEFAULT_FRESHNESS_LIMITS.get(domain,86400)
    if stamp is None: return {"domain":domain,"source":source,"lineage":{"source":source,"timestamp_field":source_field,"timestamp":None},"status":"UNKNOWN","score":0,"age_seconds":None,"max_age_seconds":limit,"source_field":source_field,"timestamp":None,"completeness_state":"UNAVAILABLE","recommendation_impact":"BLOCKED","blocker":f"{domain.upper()}_FRESHNESS_UNKNOWN"}
    age=max(0,int((_utc_now(now)-stamp).total_seconds()))
    if age<=limit*.8: status,score,blocker="FRESH",100,None
    elif age<=limit: status,score,blocker="AGING",75,None
    elif age<=limit*2: status,score,blocker="STALE",50,f"{domain.upper()}_DATA_STALE"
    else: status,score,blocker="EXPIRED",0,f"{domain.upper()}_DATA_EXPIRED"
    impact="AVAILABLE" if status=="FRESH" else "DEGRADED" if status=="AGING" else "BLOCKED"
    return {"domain":domain,"source":source,"lineage":{"source":source,"timestamp_field":source_field,"timestamp":stamp.isoformat()},"status":status,"score":score,"age_seconds":age,"max_age_seconds":limit,"source_field":source_field,"timestamp":stamp.isoformat(),"completeness_state":"COMPLETE","recommendation_impact":impact,"blocker":blocker}
def build_freshness_report(metadata=None,now=None,limits=None):
    metadata,limits=metadata or {},limits or {}; domains={d:calculate_freshness(metadata,d,now,limits.get(d)) for d in DEFAULT_FRESHNESS_LIMITS}; blockers=sorted(x["blocker"] for x in domains.values() if x.get("blocker")); scores=[x["score"] for x in domains.values()]
    return {"score":round(sum(scores)/len(scores)) if scores else 0,"domains":domains,"blockers":blockers,"has_unknown":any(x["status"]=="UNKNOWN" for x in domains.values()),"has_aging":any(x["status"]=="AGING" for x in domains.values()),"has_stale":any(x["status"] in {"STALE","EXPIRED"} for x in domains.values())}
def calculate_completeness_score(p:Dict)->int:
    checks=(bool(p.get("injury_status")),p.get("weekly_score") is not None,p.get("weekly_baseline") is not None,bool(p.get("opponent")) or bool(p.get("is_bye")),p.get("matchup_rank") is not None or bool(p.get("is_bye"))); return round(sum(bool(x) for x in checks)/len(checks)*100)
def calculate_confidence_score(p:Dict)->Dict:
    gaps=p.get("evidence_gaps") or []; unresolved=str(p.get("injury_status") or "").strip().lower() in {"","unknown"}; missing_weekly=p.get("weekly_score") is None or p.get("weekly_baseline") is None; missing_opponent=not p.get("opponent") and not p.get("is_bye"); missing_matchup=p.get("matchup_rank") is None and not p.get("is_bye"); score=max(0,100-len(gaps)*20)
    if any((unresolved,missing_weekly,missing_opponent,missing_matchup)): score=min(score,50)
    label="HIGH" if score>=80 else "MEDIUM" if score>=60 else "LOW"; return {"label":label,"score":score,"evidence_ready":not any((unresolved,missing_weekly,missing_opponent,missing_matchup))}
def _metadata_from_players(players):
    players = list(players or [])
    fields = {
        "roster": ("roster_updated_at", "roster_sync_time", "roster_source", "ownership_source"),
        "injury": ("injury_updated_at", "health_updated_at", "last_health_update", "injury_source", "health_source"),
        "matchup": ("matchup_updated_at", "matchup_sync_time", "matchup_retrieved_at", "matchup_source"),
        "projection": ("projection_updated_at", "projection_sync_time", "projection_retrieved_at", "projection_source"),
    }
    result = {}
    for domain, names in fields.items():
        timestamp_fields = names[:-2] if domain in {"roster", "injury"} else names[:-1]
        source_fields = names[-2:] if domain in {"roster", "injury"} else names[-1:]
        timestamps = [row.get(field) for row in players for field in timestamp_fields if row.get(field)]
        sources = [row.get(field) for row in players for field in source_fields if row.get(field)]
        if timestamps:
            timestamp_field = next((field for field in timestamp_fields if any(row.get(field) for row in players)), timestamp_fields[0])
            result[timestamp_field] = min(row.get(timestamp_field) for row in players if row.get(timestamp_field))
        if sources and len(set(map(str, sources))) == 1:
            result[f"{domain}_source"] = sources[0]
    return result


def build_integrity_report(players:List[Dict],freshness_metadata=None,now=None,freshness_limits=None)->Dict:
    if freshness_metadata is None:
        freshness_metadata = _metadata_from_players(players)
    freshness=build_freshness_report(freshness_metadata,now,freshness_limits)
    if not players: return {"player_count":0,"completeness_score":0,"confidence_score":0,"confidence":{"label":"BLOCKED","score":0},"blockers":freshness["blockers"],"freshness":freshness,"recommendation_ready":False,"healthy_players":0,"unknown_health_players":0,"missing_matchups":0}
    comp=[calculate_completeness_score(p) for p in players]; conf=[calculate_confidence_score(p)["score"] for p in players]; blockers=sorted({g for p in players for g in (p.get("evidence_gaps") or [])}|set(freshness["blockers"])); score=round(sum(conf)/len(conf)); score=min(score,50) if blockers else score; label="HIGH" if score>=80 else "MEDIUM" if score>=60 else "LOW"
    return {"player_count":len(players),"completeness_score":round(sum(comp)/len(comp)),"confidence_score":score,"confidence":{"label":label,"score":score},"blockers":blockers,"freshness":freshness,"recommendation_ready":not blockers and score>=60,"healthy_players":sum(str(p.get("injury_status","")).lower() in ("healthy","active") for p in players),"unknown_health_players":sum(str(p.get("injury_status","")).lower() in ("unknown","") for p in players),"missing_matchups":sum(p.get("matchup_rank") is None and not p.get("is_bye") for p in players)}
