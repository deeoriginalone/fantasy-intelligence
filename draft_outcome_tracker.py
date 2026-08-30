"""Persist and resolve Draft HQ predictions against Sleeper draft outcomes."""
from __future__ import annotations

def norm(v): return " ".join(str(v or "").lower().split())
def player_name(p):
 if isinstance(p,(list,tuple)) and len(p)>1:return str(p[1])
 if isinstance(p,dict):return str(p.get("player_name") or p.get("name") or "")
 return str(p or "")
def find(rows,name,keys=("player","name")):
 return next((r for r in (rows or []) if any(norm(r.get(k))==norm(name) for k in keys)),None)
def latest_picks(cur,draft_id,season):
 cur.execute("SELECT payload FROM sleeper_api_snapshots WHERE resource_type='draft_picks' AND resource_key=%s AND season=%s ORDER BY fetched_at DESC LIMIT 1",(str(draft_id),int(season)));row=cur.fetchone();return row[0] if row else []
def log_and_resolve(db,league_id,season,team,signals,dnw,mc,survival,ev,plan):
 signals=signals or {};draft_id=str(signals.get("draft_id") or "");current=int(signals.get("pick_count") or 0);next_pick=signals.get("next_pick");name=player_name(team)
 if not draft_id or not next_pick or not name:return {"logged":False,"reason":"incomplete draft context"}
 mr=find((mc or {}).get("players"),name);sr=find((survival or {}).get("rows"),name,("name",));er=find((ev or {}).get("players"),name);sources=(dnw or {}).get("source_estimates") or {}
 conn=db();cur=conn.cursor()
 try:
  picks=latest_picks(cur,draft_id,season);latest=max([int(x.get("pick_no") or 0) for x in picks] or [0])
  cur.execute("SELECT id,player_name,decision_pick,next_pick FROM draft_decision_outcomes WHERE draft_id=%s AND actual_available IS NULL",(draft_id,))
  for oid,pname,start,end in cur.fetchall():
   gone=any(start<int(p.get("pick_no") or 0)<end and norm(((p.get("metadata") or {}).get("first_name","")+" "+(p.get("metadata") or {}).get("last_name","")).strip())==norm(pname) for p in picks)
   if gone or latest>=end:
    cur.execute("UPDATE draft_decision_outcomes SET actual_available=%s,resolved_at=NOW(),updated_at=NOW() WHERE id=%s",(not gone,oid))
  position=str(team[2] if isinstance(team,(list,tuple)) and len(team)>2 else "")
  cur.execute("""INSERT INTO draft_decision_outcomes(league_id,draft_id,decision_pick,next_pick,player_name,position,decision,confidence,reconciled_pct,monte_carlo_pct,opponent_pct,survival_pct,expected_value_loss)
  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
  ON CONFLICT(draft_id,decision_pick,player_name) DO UPDATE SET decision=EXCLUDED.decision,confidence=EXCLUDED.confidence,reconciled_pct=EXCLUDED.reconciled_pct,monte_carlo_pct=EXCLUDED.monte_carlo_pct,opponent_pct=EXCLUDED.opponent_pct,survival_pct=EXCLUDED.survival_pct,expected_value_loss=EXCLUDED.expected_value_loss,updated_at=NOW()""",
  (str(league_id),draft_id,current,int(next_pick),name,position,(dnw or {}).get("decision"),(plan or {}).get("confidence"),(dnw or {}).get("availability_pct"),(mr or {}).get("availability_pct"),sources.get("opponent_model"),(sr or {}).get("survival_pct"),(er or {}).get("expected_value_loss")))
  conn.commit();return {"logged":True,"resolved_through":latest}
 finally:cur.close();conn.close()
def accuracy_summary(cur):
 cur.execute("SELECT decision,reconciled_pct,monte_carlo_pct,opponent_pct,survival_pct,actual_available FROM draft_decision_outcomes WHERE actual_available IS NOT NULL")
 rows=cur.fetchall();result={"resolved":len(rows),"models":{}}
 for label,index in (("reconciled",1),("monte_carlo",2),("opponent",3),("survival",4)):
  vals=[(float(r[index]),bool(r[5])) for r in rows if r[index] is not None]
  if not vals:result["models"][label]={"samples":0,"accuracy":None,"brier":None};continue
  correct=sum((p>=50)==actual for p,actual in vals);brier=sum(((p/100)-(1 if actual else 0))**2 for p,actual in vals)/len(vals)
  result["models"][label]={"samples":len(vals),"accuracy":round(100*correct/len(vals),1),"brier":round(brier,4)}
 cur.execute("SELECT id,player_name,decision,confidence,reconciled_pct,actual_available,created_at,resolved_at FROM draft_decision_outcomes ORDER BY id DESC LIMIT 50")
 result["recent"]=[{"id":r[0],"player":r[1],"decision":r[2],"confidence":float(r[3]) if r[3] is not None else None,"predicted":float(r[4]) if r[4] is not None else None,"available":r[5],"created":str(r[6]),"resolved":str(r[7]) if r[7] else None} for r in cur.fetchall()];return result
