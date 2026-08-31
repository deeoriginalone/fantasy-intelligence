"""Batch 4B.1: compare, persist, and expose survival-model disagreement."""
from __future__ import annotations
import json
from flask import Blueprint, jsonify, request

def _norm(value): return " ".join(str(value or "").lower().split())
def severity(diff):
    d=abs(float(diff)); return "LOW" if d < 10 else "MEDIUM" if d < 20 else "HIGH"
def availability_confidence(level): return {"LOW":"HIGH","MEDIUM":"MEDIUM","HIGH":"REDUCED"}[level]
def _find(rows, player, key):
    target=_norm(player); return next((r for r in rows or [] if _norm(r.get(key))==target),None)
def build_comparison(explanation, monte_carlo, sleeper_survival):
    if not (explanation or {}).get("available"): return {"available":False,"reason":"No recommendation explanation is available"}
    player=explanation.get("player"); mc=_find((monte_carlo or {}).get("players"),player,"player"); sleeper=_find((sleeper_survival or {}).get("rows"),player,"name")
    if not mc or mc.get("availability_pct") is None: return {"available":False,"player":player,"reason":"Monte Carlo availability is unavailable"}
    if not sleeper or sleeper.get("survival_pct") is None: return {"available":False,"player":player,"reason":"Sleeper survival is unavailable"}
    mp=round(float(mc["availability_pct"]),2); sp=round(float(sleeper["survival_pct"]),2); diff=round(abs(mp-sp),2); level=severity(diff)
    return {"available":True,"player":player,"position":explanation.get("position"),"monte_carlo_probability":mp,"sleeper_probability":sp,"probability_difference":diff,"severity":level,"availability_confidence":availability_confidence(level),"recommendation_score":explanation.get("draft_score"),"confidence":explanation.get("confidence"),"monte_carlo_run_id":monte_carlo.get("run_id"),"message":f"Availability models differ by {diff:.2f} percentage points.","canonical_score_unchanged":True}
def ensure_tables(c):
    c.execute("CREATE TABLE IF NOT EXISTS survival_model_comparison(id bigserial primary key,draft_id varchar(50) not null,pick_count integer not null,player_name text not null,position varchar(10),monte_carlo_run_id bigint,monte_carlo_probability numeric(6,2) not null,sleeper_probability numeric(6,2) not null,probability_difference numeric(6,2) not null,severity varchar(10) not null,availability_confidence varchar(15) not null,recommendation_score numeric(10,2),confidence integer,payload jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count,player_name))")
    c.execute("CREATE INDEX IF NOT EXISTS survival_model_comparison_draft_idx ON survival_model_comparison(draft_id,updated_at DESC)")
    c.execute("CREATE TABLE IF NOT EXISTS survival_model_outcomes(id bigserial primary key,comparison_id bigint not null references survival_model_comparison(id) on delete cascade,player_name text not null,current_pick_number integer,actual_pick_number integer,actual_survived boolean,monte_carlo_error numeric(10,4),sleeper_error numeric(10,4),recorded_at timestamptz not null default now(),UNIQUE(comparison_id))")
    c.execute("CREATE TABLE IF NOT EXISTS survival_model_accuracy(id bigserial primary key,model_name varchar(30) not null unique,observations integer not null default 0,mean_absolute_error numeric(10,4),accuracy_score numeric(10,4),updated_at timestamptz not null default now())")
    c.execute("INSERT INTO survival_model_accuracy(model_name) VALUES('MONTE_CARLO'),('SLEEPER') ON CONFLICT DO NOTHING")
def persist(db,draft_id,pick_count,x):
    if not x.get("available"): return None
    cn=db(); c=cn.cursor()
    try:
        ensure_tables(c)
        c.execute("INSERT INTO survival_model_comparison(draft_id,pick_count,player_name,position,monte_carlo_run_id,monte_carlo_probability,sleeper_probability,probability_difference,severity,availability_confidence,recommendation_score,confidence,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(draft_id,pick_count,player_name) DO UPDATE SET position=excluded.position,monte_carlo_run_id=excluded.monte_carlo_run_id,monte_carlo_probability=excluded.monte_carlo_probability,sleeper_probability=excluded.sleeper_probability,probability_difference=excluded.probability_difference,severity=excluded.severity,availability_confidence=excluded.availability_confidence,recommendation_score=excluded.recommendation_score,confidence=excluded.confidence,payload=excluded.payload,updated_at=now() RETURNING id",(str(draft_id),int(pick_count or 0),x["player"],x.get("position"),x.get("monte_carlo_run_id"),x["monte_carlo_probability"],x["sleeper_probability"],x["probability_difference"],x["severity"],x["availability_confidence"],x.get("recommendation_score"),x.get("confidence"),json.dumps(x)))
        i=c.fetchone()[0]; cn.commit(); return i
    except Exception: cn.rollback(); raise
    finally: c.close(); cn.close()
def refresh_accuracy(c):
    for model,col in (("MONTE_CARLO","monte_carlo_error"),("SLEEPER","sleeper_error")):
        c.execute(f"SELECT count(*),avg({col}) FROM survival_model_outcomes WHERE {col} IS NOT NULL"); n,mae=c.fetchone(); score=None if mae is None else max(0,round(100-float(mae),4)); c.execute("UPDATE survival_model_accuracy SET observations=%s,mean_absolute_error=%s,accuracy_score=%s,updated_at=now() WHERE model_name=%s",(n,mae,score,model))
def create_blueprint(db,draft_id):
    bp=Blueprint("survival_calibration",__name__,url_prefix="/survival-comparison")
    @bp.get("/latest")
    def latest():
        cn=db();c=cn.cursor();ensure_tables(c);cn.commit();c.execute("SELECT id,payload,created_at,updated_at FROM survival_model_comparison WHERE draft_id=%s ORDER BY pick_count DESC,updated_at DESC LIMIT 1",(str(draft_id),));r=c.fetchone();c.close();cn.close();return jsonify({"available":False,"reason":"No comparison has been generated"} if not r else {"available":True,"comparison_id":r[0],**r[1],"created_at":r[2],"updated_at":r[3]})
    @bp.get("/history")
    def history():
        limit=min(100,max(1,int(request.args.get("limit",25))));cn=db();c=cn.cursor();ensure_tables(c);cn.commit();c.execute("SELECT id,payload,created_at,updated_at FROM survival_model_comparison WHERE draft_id=%s ORDER BY updated_at DESC LIMIT %s",(str(draft_id),limit));rows=c.fetchall();c.close();cn.close();return jsonify([{"comparison_id":r[0],**r[1],"created_at":r[2],"updated_at":r[3]} for r in rows])
    @bp.get("/accuracy")
    def accuracy():
        cn=db();c=cn.cursor();ensure_tables(c);refresh_accuracy(c);cn.commit();c.execute("SELECT model_name,observations,mean_absolute_error,accuracy_score,updated_at FROM survival_model_accuracy ORDER BY model_name");rows=c.fetchall();c.close();cn.close();return jsonify({r[0]:{"observations":r[1],"mean_absolute_error":r[2],"accuracy_score":r[3],"updated_at":r[4]} for r in rows})
    return bp
