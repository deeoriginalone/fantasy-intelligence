import json
from flask import Blueprint, jsonify
LABELS={"talent":"Talent","need":"Roster Need","scarcity":"Scarcity","tier":"Tier Advantage","strategy":"Strategy Fit","league":"League Pressure"}
def name(c):
 p=(c or {}).get("player")
 return str(p[1]) if isinstance(p,(list,tuple)) and len(p)>1 else str((p or {}).get("player_name") or (p or {}).get("name") or "") if isinstance(p,dict) else ""
def pos(c):
 p=(c or {}).get("player")
 return str(p[2]) if isinstance(p,(list,tuple)) and len(p)>2 else str((p or {}).get("position") or "") if isinstance(p,dict) else ""
def find(rows,n,key):
 t=" ".join(str(n).lower().split());return next((r for r in rows or [] if " ".join(str(r.get(key) or "").lower().split())==t),None)
def build_explanation(candidates,survival=None,ev=None,plan=None):
 rows=list(candidates or [])
 if not rows:return {"available":False,"reason":"No recommendation candidates available","factors":[],"alternatives":[]}
 w=rows[0];n=name(w);comp=w.get("weighted_components") or {};f=[]
 for k in ("talent","need","scarcity","tier","strategy","league"):
  if k in comp:
   v=round(float(comp.get(k) or 0),2);f.append({"key":k,"label":LABELS[k],"value":v,"direction":"positive" if v>0 else "negative" if v<0 else "neutral"})
 positive=sorted((x for x in f if x["value"]>0),key=lambda x:(-x["value"],x["label"]));primary=f"{positive[0]['label']} contributes {positive[0]['value']:.2f} points." if positive else "The recommendation leads on the combined canonical score."
 score=float(w.get("draft_score") or 0);alts=[]
 for c in rows[1:4]:
  s=float(c.get("draft_score") or 0);alts.append({"player":name(c),"position":pos(c),"draft_score":round(s,2),"score_gap":round(score-s,2)})
 gap=alts[0]["score_gap"] if alts else 0;confidence=max(35,min(95,round(55+max(0,gap)*4))) if alts else 55
 sr=find((survival or {}).get("rows"),n,"name");er=find((ev or {}).get("players"),n,"player");sp=float(sr.get("survival_pct")) if sr and sr.get("survival_pct") is not None else None;loss=float(er.get("expected_value_loss")) if er and er.get("expected_value_loss") is not None else None
 risk="HIGH" if sp is not None and sp<40 else "MEDIUM" if sp is not None and sp<70 else "LOW";warnings=[]
 if alts and gap<2:warnings.append("The top candidates are separated by fewer than 2 score points.")
 if sp is not None and sp<40:warnings.append(f"Next-pick survival is {sp:.1f}%.")
 if loss is not None and loss>=25:warnings.append(f"Expected value loss from waiting is {loss:.1f} points.")
 return {"available":True,"player":n,"position":pos(w),"draft_score":round(score,2),"confidence":confidence,"confidence_label":"HIGH" if confidence>=80 else "MEDIUM" if confidence>=60 else "LOW","risk":risk,"primary_reason":primary,"factors":f,"alternatives":alts,"warnings":warnings,"survival_pct":sp,"expected_value_loss":loss,"decision":(plan or {}).get("decision"),"canonical_score_unchanged":True}
def ensure_table(c):
 c.execute("CREATE TABLE IF NOT EXISTS recommendation_explanations(id bigserial primary key,draft_id varchar(50) not null,pick_count integer not null default 0,player_name text not null,position varchar(10),draft_score numeric,confidence integer,risk varchar(10),primary_reason text,factors jsonb not null default '[]'::jsonb,alternatives jsonb not null default '[]'::jsonb,warnings jsonb not null default '[]'::jsonb,payload jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count,player_name))")
def persist(db,draft,picks,x):
 if not x.get("available"):return None
 cn=db();c=cn.cursor()
 try:
  ensure_table(c);c.execute("INSERT INTO recommendation_explanations(draft_id,pick_count,player_name,position,draft_score,confidence,risk,primary_reason,factors,alternatives,warnings,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb) ON CONFLICT(draft_id,pick_count,player_name) DO UPDATE SET position=excluded.position,draft_score=excluded.draft_score,confidence=excluded.confidence,risk=excluded.risk,primary_reason=excluded.primary_reason,factors=excluded.factors,alternatives=excluded.alternatives,warnings=excluded.warnings,payload=excluded.payload,updated_at=now() RETURNING id",(str(draft),int(picks or 0),x["player"],x.get("position"),x.get("draft_score"),x.get("confidence"),x.get("risk"),x.get("primary_reason"),json.dumps(x.get("factors") or []),json.dumps(x.get("alternatives") or []),json.dumps(x.get("warnings") or []),json.dumps(x)));i=c.fetchone()[0];cn.commit();return i
 except Exception:cn.rollback();raise
 finally:c.close();cn.close()
def blueprint(db,draft):
 bp=Blueprint("recommendation_explainer",__name__,url_prefix="/recommendation-explainer")
 @bp.get("/")
 def latest():
  cn=db();c=cn.cursor();ensure_table(c);cn.commit();c.execute("SELECT payload,created_at,updated_at FROM recommendation_explanations WHERE draft_id=%s ORDER BY pick_count DESC,updated_at DESC LIMIT 1",(str(draft),));r=c.fetchone();c.close();cn.close();return jsonify({"available":False,"reason":"No explanation has been generated"} if not r else {**r[0],"created_at":r[1],"updated_at":r[2]})
 return bp
