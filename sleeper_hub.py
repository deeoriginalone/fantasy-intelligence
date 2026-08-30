from flask import Blueprint,current_app,jsonify,render_template,request
import json,os
from services.sleeper_service import get_league,get_users,get_rosters,get_drafts,get_draft,get_draft_picks,get_matchups,get_transactions,get_traded_picks,get_winners_bracket,get_losers_bracket,get_draft_traded_picks,get_nfl_state,get_trending_adds,get_trending_drops

def create_sleeper_hub_blueprint(get_db_connection):
 bp=Blueprint("sleeper_hub",__name__,url_prefix="/sleeper")
 def lid(value=None): return str(value or current_app.config.get("SLEEPER_LEAGUE_ID") or os.getenv("SLEEPER_LEAGUE_ID") or "")
 def store(cur,kind,key,payload,season=0,week=0):
  cur.execute("INSERT INTO sleeper_api_snapshots(resource_type,resource_key,season,week,payload,fetched_at) VALUES(%s,%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(resource_type,resource_key,season,week) DO UPDATE SET payload=EXCLUDED.payload,fetched_at=NOW()",(kind,str(key),season,week,json.dumps(payload)))
 def run_sync(league_id,season,week,brackets=False):
  conn=get_db_connection();cur=conn.cursor();results={};run_id=None
  try:
   cur.execute("INSERT INTO sleeper_sync_runs(league_id,season,week,status) VALUES(%s,%s,%s,'running') RETURNING id",(league_id,season,week));run_id=cur.fetchone()[0];conn.commit()
   jobs={"league":lambda:get_league(league_id),"users":lambda:get_users(league_id),"rosters":lambda:get_rosters(league_id),"drafts":lambda:get_drafts(league_id),"matchups":lambda:get_matchups(league_id,week),"transactions":lambda:get_transactions(league_id,week),"traded_picks":lambda:get_traded_picks(league_id),"nfl_state":get_nfl_state,"trending_add":lambda:get_trending_adds(24,50),"trending_drop":lambda:get_trending_drops(24,50)}
   if brackets: jobs.update(winners_bracket=lambda:get_winners_bracket(league_id),losers_bracket=lambda:get_losers_bracket(league_id))
   drafts=[]
   for name,fn in jobs.items():
    try:
     data=fn();store(cur,name,league_id,data,season,week if name in {"matchups","transactions"} else 0);results[name]={"ok":True,"count":len(data) if isinstance(data,(list,dict)) else 1}
     if name=="drafts": drafts=data or []
    except Exception as exc: results[name]={"ok":False,"error":str(exc)[:500]}
   for draft in drafts:
    did=draft.get("draft_id")
    if not did: continue
    for name,fn in (("draft",lambda d=did:get_draft(d)),("draft_picks",lambda d=did:get_draft_picks(d)),("draft_traded_picks",lambda d=did:get_draft_traded_picks(d))):
     try:
      data=fn();store(cur,name,did,data,season,0);results[f"{name}:{did}"]={"ok":True,"count":len(data) if isinstance(data,(list,dict)) else 1}
     except Exception as exc: results[f"{name}:{did}"]={"ok":False,"error":str(exc)[:500]}
   status="success" if all(v["ok"] for v in results.values()) else "partial";cur.execute("UPDATE sleeper_sync_runs SET status=%s,resources=%s::jsonb,completed_at=NOW() WHERE id=%s",(status,json.dumps(results),run_id));conn.commit();return {"run_id":run_id,"status":status,"resources":results}
  finally: cur.close();conn.close()
 @bp.get("/")
 def home():
  conn=get_db_connection();cur=conn.cursor();cur.execute("SELECT id,league_id,season,week,status,started_at,completed_at FROM sleeper_sync_runs ORDER BY id DESC LIMIT 10");runs=cur.fetchall();cur.execute("SELECT resource_type,resource_key,season,week,fetched_at FROM sleeper_api_snapshots ORDER BY fetched_at DESC LIMIT 50");snapshots=cur.fetchall();cur.close();conn.close();return render_template("sleeper_hub.html",league_id=lid(request.args.get("league_id")),runs=runs,snapshots=snapshots)
 @bp.post("/sync")
 def sync():
  body=request.get_json(silent=True) or request.form;league_id=lid(body.get("league_id"))
  if not league_id:return jsonify(error="league_id required"),400
  result=run_sync(league_id,int(body.get("season") or 2026),int(body.get("week") or 1),str(body.get("include_brackets","")).lower() in {"1","true","yes","on"});return jsonify(result) if request.is_json else render_template("sleeper_sync_result.html",result=result)
 @bp.get("/status")
 def status():
  conn=get_db_connection();cur=conn.cursor();cur.execute("SELECT id,league_id,season,week,status,resources,error_message,started_at,completed_at FROM sleeper_sync_runs ORDER BY id DESC LIMIT 20");cols=[x[0] for x in cur.description];rows=[dict(zip(cols,r)) for r in cur.fetchall()];cur.close();conn.close();return jsonify(rows)
 @bp.get("/latest/<resource_type>")
 def latest(resource_type):
  key=request.args.get("key") or lid();conn=get_db_connection();cur=conn.cursor();cur.execute("SELECT payload,fetched_at,season,week FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s ORDER BY fetched_at DESC LIMIT 1",(resource_type,key));row=cur.fetchone();cur.close();conn.close();return (jsonify(error="not found"),404) if not row else jsonify(data=row[0],fetched_at=row[1],season=row[2],week=row[3])
 return bp
