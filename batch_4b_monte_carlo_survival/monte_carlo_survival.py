"""Batch 4B: auditable survival curves derived from the active Monte Carlo run."""
from __future__ import annotations
import hashlib,json,math
from flask import Blueprint,jsonify
CORE=("QB","RB","WR","TE")
def seed_for(draft_id,current_pick,next_pick,simulations,candidates):
 raw="|".join([str(draft_id),str(current_pick),str(next_pick),str(simulations),",".join(str(c.get("player",("",""))[1]) for c in candidates or [])])
 return int(hashlib.sha256(raw.encode()).hexdigest()[:12],16)
def urgency(pct,run_risk):
 if pct<=35 or run_risk=="HIGH":return "DRAFT NOW"
 if pct<=65 or run_risk=="MEDIUM":return "WATCH CLOSELY"
 return "SAFE TO WAIT"
def run_risks(forecast):
 gone=forecast.get("projected_gone") or {};pressure=forecast.get("position_pressure") or {};need=forecast.get("teams_needing_position") or {}
 out={}
 for p in CORE:
  score=int(gone.get(p,0))*20+int(pressure.get(p,0))*0.35+int(need.get(p,0))*8
  out[p]={"score":round(score,1),"level":"HIGH" if score>=60 else "MEDIUM" if score>=30 else "LOW","projected_picks":int(gone.get(p,0)),"pressure":int(pressure.get(p,0)),"needy_teams":int(need.get(p,0))}
 return out
def curve(endpoint,steps):
 steps=max(0,int(steps));end=max(0,min(100,float(endpoint)))
 if steps==0:return [{"pick_offset":0,"survival_pct":100.0}]
 hazard=-math.log(max(end,0.1)/100.0)/steps
 return [{"pick_offset":i,"survival_pct":round(100*math.exp(-hazard*i),1)} for i in range(steps+1)]
def enhance(base,forecast,draft_id,current_pick,candidates):
 result=dict(base or {});sims=int(result.get("simulations") or 0);steps=int(result.get("picks_until_next") or 0);risks=run_risks(forecast or {});seed=seed_for(draft_id,current_pick,(forecast or {}).get("next_pick"),sims,candidates)
 rows=[]
 for row in result.get("players") or []:
  x=dict(row);x["survival_curve"]=curve(x.get("availability_pct",100),steps);rr=risks.get(x.get("position"),{"level":"LOW"});x["run_risk"]=rr;x["urgency"]=urgency(float(x.get("availability_pct",100)),rr["level"]);rows.append(x)
 result.update({"players":rows,"seed":seed,"position_run_risk":risks,"curve_method":"Monotonic hazard curve calibrated to the active Monte Carlo next-pick availability result.","canonical_score_unchanged":True})
 return result
def ensure_tables(c):
 c.execute("CREATE TABLE IF NOT EXISTS monte_carlo_runs(id bigserial primary key,draft_id varchar(50) not null,pick_count integer not null,seed bigint not null,simulation_count integer not null,picks_until_next integer not null,status varchar(30),position_run_risk jsonb not null default '{}'::jsonb,payload jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count,seed))")
 c.execute("CREATE TABLE IF NOT EXISTS player_survival_curves(id bigserial primary key,run_id bigint not null references monte_carlo_runs(id) on delete cascade,player_name text not null,position varchar(10),pick_offset integer not null,survival_probability numeric not null,urgency varchar(30),run_risk varchar(10),created_at timestamptz not null default now(),UNIQUE(run_id,player_name,pick_offset))")
def persist(db,draft_id,pick_count,data):
 cn=db();c=cn.cursor()
 try:
  ensure_tables(c);c.execute("INSERT INTO monte_carlo_runs(draft_id,pick_count,seed,simulation_count,picks_until_next,status,position_run_risk,payload) VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT(draft_id,pick_count,seed) DO UPDATE SET simulation_count=excluded.simulation_count,picks_until_next=excluded.picks_until_next,status=excluded.status,position_run_risk=excluded.position_run_risk,payload=excluded.payload,updated_at=now() RETURNING id",(str(draft_id),int(pick_count or 0),int(data.get("seed") or 0),int(data.get("simulations") or 0),int(data.get("picks_until_next") or 0),data.get("status"),json.dumps(data.get("position_run_risk") or {}),json.dumps(data)));run_id=c.fetchone()[0]
  c.execute("DELETE FROM player_survival_curves WHERE run_id=%s",(run_id,))
  for r in data.get("players") or []:
   for pt in r.get("survival_curve") or []:c.execute("INSERT INTO player_survival_curves(run_id,player_name,position,pick_offset,survival_probability,urgency,run_risk) VALUES(%s,%s,%s,%s,%s,%s,%s)",(run_id,r.get("player"),r.get("position"),pt["pick_offset"],pt["survival_pct"],r.get("urgency"),(r.get("run_risk") or {}).get("level")))
  cn.commit();return run_id
 except Exception:cn.rollback();raise
 finally:c.close();cn.close()
def blueprint(db,draft_id):
 bp=Blueprint("monte_carlo_survival",__name__,url_prefix="/monte-carlo-survival")
 @bp.get("/")
 def latest():
  cn=db();c=cn.cursor()
  try:
   ensure_tables(c);cn.commit();c.execute("SELECT id,payload,created_at,updated_at FROM monte_carlo_runs WHERE draft_id=%s ORDER BY pick_count DESC,updated_at DESC LIMIT 1",(str(draft_id),));r=c.fetchone()
  finally:c.close();cn.close()
  return jsonify({"available":False,"reason":"No survival run has been persisted"} if not r else {"available":True,"run_id":r[0],**r[1],"created_at":r[2],"updated_at":r[3]})
 return bp
