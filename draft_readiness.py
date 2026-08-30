"""Operational readiness checks for live Draft HQ use."""
from __future__ import annotations
from datetime import datetime, timezone

CORE_RESOURCES=("drafts","draft_picks","users","players")
LIVE_THRESHOLDS={"drafts":120,"draft_picks":60,"users":300,"players":86400}
PREDRAFT_THRESHOLDS={"drafts":86400,"draft_picks":86400,"users":86400,"players":86400}

def _age(value):
    if value is None:return None
    now=datetime.now(timezone.utc)
    if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
    return max(0,int((now-value).total_seconds()))

def _state(age,limit):
    if age is None:return "MISSING"
    if age<=limit:return "LIVE"
    if age<=limit*2:return "AGING"
    return "STALE"

def _table_exists(cur,name):
    cur.execute("SELECT to_regclass(%s)",(name,));row=cur.fetchone();return bool(row and row[0])

def build_draft_readiness(cur,league_id,season,signals=None,model_health=None):
    signals=signals or {}
    draft_status=str(signals.get("draft_status") or "").lower()
    thresholds=PREDRAFT_THRESHOLDS if draft_status in ("pre_draft","predraft") else LIVE_THRESHOLDS
    health=model_health or {}
    snapshots={}
    deductions=[]
    for resource in CORE_RESOURCES:
        key=str(signals.get("draft_id")) if resource=="draft_picks" and signals.get("draft_id") else str(league_id)
        cur.execute("SELECT fetched_at FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s AND season=%s ORDER BY fetched_at DESC LIMIT 1",(resource,key,int(season)))
        row=cur.fetchone();age=_age(row[0] if row else None);state=_state(age,thresholds[resource]);snapshots[resource]={"age_seconds":age,"state":state,"threshold_seconds":thresholds[resource]}
        if state=="MISSING":deductions.append((resource,15))
        elif state=="STALE":deductions.append((resource,10))
        elif state=="AGING":deductions.append((resource,4))
    checks={
      "sleeper_available":bool(signals.get("available")),
      "draft_id":bool(signals.get("draft_id")),
      "next_pick":signals.get("next_pick") is not None,
      "outcome_table":_table_exists(cur,"draft_decision_outcomes"),
      "calibration_engine":bool(health),
    }
    for key,ok in checks.items():
        if not ok:deductions.append((key,12))
    score=max(0,100-sum(points for _,points in deductions))
    draft_picks=snapshots.get("draft_picks",{});mode="LIVE" if draft_picks.get("state")=="LIVE" else ("CACHED" if draft_picks.get("state") in ("AGING","STALE") else "UNAVAILABLE")
    status="READY" if score>=85 else ("CAUTION" if score>=65 else "NOT READY")
    return {"score":score,"status":status,"mode":mode,"checks":checks,"snapshots":snapshots,"deductions":[{"check":k,"points":p} for k,p in deductions],"calibration_active":bool(health.get("active")),"resolved_predictions":int(health.get("resolved") or 0),"draft_id":signals.get("draft_id"),"draft_status":signals.get("draft_status"),"user_slot":signals.get("user_slot"),"pick_count":int(signals.get("pick_count") or 0),"next_pick":signals.get("next_pick")}

def validate_runtime(recommendations,signals,model_health):
    errors=[];warnings=[]
    if not signals.get("draft_id"):errors.append("Sleeper draft ID is missing")
    if signals.get("next_pick") is not None and int(signals.get("next_pick"))<=int(signals.get("pick_count") or 0):errors.append("Next pick is not after current pick")
    if len(recommendations or [])>100:errors.append("Recommendation pool exceeds 100 candidates")
    for c in recommendations or []:
        need=float(c.get("need_score") or 0);scarcity=float(c.get("scarcity_score") or 0)
        if not 0<=need<=100:errors.append("Need score outside 0..100")
        if not 0<=scarcity<=25:errors.append("Scarcity score outside 0..25")
    weights=(model_health or {}).get("weights") or {}
    if weights:
        total=sum(float(v) for v in weights.values())
        if abs(total-1)>0.002:errors.append("Model weights do not sum to 1.0")
        if any(not 0.10<=float(v)<=0.70 for v in weights.values()):errors.append("Model weight outside 10%..70%")
    if not recommendations:warnings.append("No recommendation candidates available")
    return {"passed":not errors,"errors":sorted(set(errors)),"warnings":sorted(set(warnings))}
