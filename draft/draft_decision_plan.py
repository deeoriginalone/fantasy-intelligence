def norm(v): return ' '.join(str(v or '').lower().split())
def pname(p):
 if isinstance(p,(list,tuple)) and len(p)>1:return str(p[1])
 if isinstance(p,dict):return str(p.get('player_name') or p.get('name') or '')
 return str(p or '')
def find(rows,name,keys=('player','name')):
 return next((r for r in (rows or []) if any(norm(r.get(k))==norm(name) for k in keys)),None)
def build_decision_plan(team,top,ev,mc,survival,overlay,dnw):
 name=pname(team);er=find((ev or {}).get('players'),name);mr=find((mc or {}).get('players'),name);sr=find((survival or {}).get('rows'),name,('name',));orr=find((overlay or {}).get('rows'),name,('name',));decision=str((dnw or {}).get('decision') or 'BALANCED');avail=float((dnw or {}).get('availability_pct') or 50);loss=float((er or {}).get('expected_value_loss') or 0);disagree=float((dnw or {}).get('model_disagreement_pct') or 0)
 fall=[];fb=str((er or {}).get('fallback') or '')
 if fb:fall.append(fb)
 for c in top or []:
  n=pname(c.get('player') if isinstance(c,dict) else c)
  if n and norm(n)!=norm(name) and norm(n) not in {norm(x) for x in fall}:fall.append(n)
  if len(fall)>=3:break
 conf=55+abs(avail-50)*.45-min(25,disagree*.25)+(8 if loss<5 or loss>=25 else (4 if loss>=15 else 0));conf=round(max(35,min(95,conf)));label='HIGH' if conf>=80 else ('MEDIUM' if conf>=60 else 'LOW')
 evidence=[f'Unified decision: {decision} with {label} evidence confidence ({conf}%).',f'Reconciled next-pick availability is {avail:.1f}%.',f'Expected-value loss from waiting is {loss:.1f} points.']
 if mr:evidence.append(f"Monte Carlo availability is {float(mr.get('availability_pct') or 0):.1f}%.")
 if sr:evidence.append(f"Sleeper survival estimate is {float(sr.get('survival_pct') or 0):.1f}%.")
 if orr and float(orr.get('sleeper_bonus') or 0):evidence.append(f"Live Sleeper pressure contributes an advisory +{float(orr.get('sleeper_bonus')):.1f} overlay.")
 if fall:evidence.append('Recovery plan if unavailable: '+', '.join(fall)+'.')
 if disagree>=25:evidence.append(f'Model disagreement remains material at {disagree:.1f} percentage points.')
 return {'player':name,'decision':decision,'confidence':conf,'confidence_label':label,'availability_pct':round(avail,1),'expected_value_loss':round(loss,1),'fallbacks':fall,'evidence':evidence,'canonical_score_unchanged':True}
def fuse_decision_plan(coach,plan):
 if not isinstance(coach,dict):return coach
 out=dict(coach);reasons=list(out.get('reasons') or []);seen={norm(x) for x in reasons}
 for x in (plan or {}).get('evidence') or []:
  if norm(x) not in seen:reasons.append(x);seen.add(norm(x))
 out['reasons']=reasons;out['decision_plan']=plan or {};out['decision_confidence']=(plan or {}).get('confidence');out['decision_confidence_label']=(plan or {}).get('confidence_label');out['confidence']=(plan or {}).get('confidence');out['confidence_score']=(plan or {}).get('confidence');out['confidence_pct']=(plan or {}).get('confidence');out['confidence_label']=(plan or {}).get('confidence_label');out['fallbacks']=(plan or {}).get('fallbacks') or [];return out
