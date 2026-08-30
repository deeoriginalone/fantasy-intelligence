"""Guarded calibration of Draft HQ probability-model weights."""
DEFAULT_WEIGHTS={"monte_carlo":0.60,"opponent":0.20,"survival":0.20}
MIN_SAMPLES=25
MIN_WEIGHT=0.10
MAX_WEIGHT=0.70

def _clip(v,lo,hi): return max(lo,min(hi,float(v)))
def _normalize(weights):
 total=sum(weights.values()) or 1.0
 return {k:v/total for k,v in weights.items()}
def _bounded_normalize(raw):
 weights=_normalize(raw)
 for _ in range(10):
  weights={k:_clip(v,MIN_WEIGHT,MAX_WEIGHT) for k,v in weights.items()}
  weights=_normalize(weights)
 return {k:round(v,4) for k,v in weights.items()}
def calibration_metrics(cur):
 cur.execute("SELECT monte_carlo_pct,opponent_pct,survival_pct,actual_available FROM draft_decision_outcomes WHERE actual_available IS NOT NULL")
 rows=cur.fetchall();models={"monte_carlo":0,"opponent":1,"survival":2};metrics={}
 for name,index in models.items():
  vals=[(float(r[index]),bool(r[3])) for r in rows if r[index] is not None]
  if not vals:metrics[name]={"samples":0,"accuracy":None,"brier":None,"skill":None};continue
  accuracy=100*sum((p>=50)==a for p,a in vals)/len(vals)
  brier=sum(((p/100)-(1 if a else 0))**2 for p,a in vals)/len(vals)
  skill=max(0.01,1-brier)
  metrics[name]={"samples":len(vals),"accuracy":round(accuracy,1),"brier":round(brier,4),"skill":round(skill,4)}
 return metrics
def calibrated_weights(cur):
 metrics=calibration_metrics(cur)
 eligible=all(metrics[m]["samples"]>=MIN_SAMPLES for m in DEFAULT_WEIGHTS)
 if not eligible:
  return {"active":False,"weights":DEFAULT_WEIGHTS.copy(),"metrics":metrics,"minimum_samples":MIN_SAMPLES,"reason":"Minimum resolved sample threshold not reached."}
 raw={m:metrics[m]["skill"] for m in DEFAULT_WEIGHTS}
 learned=_bounded_normalize(raw)
 # Damp movement to 50% learned, 50% defaults to prevent sudden changes.
 blended={m:(DEFAULT_WEIGHTS[m]*0.5+learned[m]*0.5) for m in DEFAULT_WEIGHTS}
 weights=_bounded_normalize(blended)
 return {"active":True,"weights":weights,"metrics":metrics,"minimum_samples":MIN_SAMPLES,"reason":"Weights use Brier skill with bounds and 50% shrinkage to defaults."}
def model_health(cur):
 result=calibrated_weights(cur)
 result["resolved"]=max([v["samples"] for v in result["metrics"].values()] or [0])
 return result
