from collections import Counter
CORE=('QB','RB','WR','TE')
def num(v,d=0):
 try:return float(v)
 except (TypeError,ValueError):return d
def reconcile_opponent_forecast(legacy,live):
 old=dict(legacy or {});live=live or {};picks=int(live.get('pick_count') or 0);before=list(live.get('teams_before_next') or []);lw=.35 if picks==0 else .75;ow=1-lw;n=len(before)
 primary=Counter(str(x.get('primary_need') or '').upper() for x in before);positive=Counter()
 for x in before:
  for p,v in (x.get('needs') or {}).items():
   if str(p).upper() in CORE and num(v)>0:positive[str(p).upper()]+=1
 total=sum(primary[p] for p in CORE);shares={p:(primary[p]/total if total else num((live.get('position_risk_pct') or {}).get(p))/max(1,sum(num((live.get('position_risk_pct') or {}).get(q)) for q in CORE))) for p in CORE}
 pressure={};needing={};raw={};diag={}
 for p in CORE:
  op=num((old.get('position_pressure') or {}).get(p));lp=num((live.get('position_risk_pct') or {}).get(p));pressure[p]=round(op*ow+lp*lw)
  on=num((old.get('teams_needing_position') or {}).get(p));needing[p]=min(n,round(on*ow+positive[p]*lw)) if n else round(on*ow)
  og=num((old.get('projected_gone') or {}).get(p));lg=n*shares[p];raw[p]=max(0,og*ow+lg*lw);diag[p]={'legacy_pressure':op,'live_pressure':lp,'primary_need_teams':primary[p],'positive_need_teams':positive[p],'legacy_projected':og,'live_projected':round(lg,2)}
 proj={p:int(raw[p]) for p in CORE};target=min(n,round(sum(raw.values())));rem=target-sum(proj.values())
 for p in sorted(CORE,key=lambda q:raw[q]-int(raw[q]),reverse=True)[:max(0,rem)]:proj[p]+=1
 out=dict(old);out.update({'next_pick':live.get('next_pick') or old.get('next_pick'),'teams_before_next_pick':before or old.get('teams_before_next_pick') or [],'position_pressure':pressure,'teams_needing_position':needing,'projected_gone':proj,'source':'blended_sleeper_live','live_weight':lw,'legacy_weight':ow,'pre_draft_caution':picks==0,'pick_count':picks,'diagnostics':diag,'legacy_forecast':old,'note':'Pre-draft live signals are downweighted because empty rosters show target deficits, not proven manager intent.'});return out
