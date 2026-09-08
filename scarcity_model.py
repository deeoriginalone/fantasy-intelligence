from collections import Counter
CORE=('QB','RB','WR','TE');BASE={'QB':10,'RB':20,'WR':20,'TE':10}
def num(v,d=0):
 try:return float(v)
 except (TypeError,ValueError):return d
def field(p,i,d=None):
 try:return d if p[i] is None else p[i]
 except (TypeError,IndexError,KeyError):return d
def pos(p):return str(field(p,2,'')).upper()
def tier(p):return int(num(field(p,7),99))
def projection(p):return num(field(p,6),0)
def runs(picks,window=6):
 recent=list(picks or [])[-window:];counts=Counter(str(x.get('position') or '').upper() for x in recent);size=max(1,len(recent));out={}
 for p in CORE:
  c=counts[p];share=c/size if recent else 0;label='HOT' if c>=3 and share>=.5 else ('WARM' if c>=2 and share>=.33 else ('COLD' if c==0 else 'NEUTRAL'));out[p]={'count':c,'share':round(share,3),'label':label}
 return out
def tier_gap(pool,p,t):
 current=[x for x in pool if pos(x)==p and tier(x)==t];later=[x for x in pool if pos(x)==p and tier(x)>t]
 return max(0,min([projection(x) for x in current] or [0])-max([projection(x) for x in later] or [0])) if current and later else 0
def calculate_dynamic_scarcity(player,pool,current_round,signals):
 p=pos(player);t=tier(player);r=max(1,int(current_round or 1));same=[x for x in pool if pos(x)==p];tr=[x for x in same if tier(x)==t];remaining=len(same);trn=len(tr);depth=(1-min(1,remaining/max(1,BASE.get(p,10))))*8;tierpart=7 if trn<=1 else (5 if trn==2 else (2.5 if trn<=4 else 0));gap=tier_gap(pool,p,t);cliff=min(4,gap/8);signals=signals or {};risk=num((signals.get('position_risk_pct') or {}).get(p));pressure=min(6,risk*(.035 if int(signals.get('pick_count') or 0)==0 else .065));run=runs(signals.get('recent_picks') or []);label=run.get(p, {'label': 'NEUTRAL'})['label'];runpart={'HOT':5,'WARM':3,'NEUTRAL':1,'COLD':0}[label];roundpart=(1.5 if p in ('RB','WR') else .5) if r<=4 else (1 if r<=8 else (1.5 if p in ('QB','TE') else .5));score=round(max(0,min(25,depth+tierpart+cliff+pressure+runpart+roundpart)),1)
 return {'score':score,'position':p,'tier':t,'position_remaining':remaining,'tier_remaining':trn,'projection_gap':round(gap,2),'live_risk_pct':risk,'run_label':label,'run_count':run.get(p, {'count': 0})['count'],'components':{'depth':round(depth,2),'tier':tierpart,'cliff':round(cliff,2),'pressure':round(pressure,2),'run':runpart,'round':roundpart}}
def scarcity_distribution(candidates):
 vals=[num(c.get('scarcity_score')) for c in candidates or []];b={'0-5':0,'6-10':0,'11-15':0,'16-20':0,'21-25':0}
 for v in vals:b['0-5' if v<=5 else '6-10' if v<=10 else '11-15' if v<=15 else '16-20' if v<=20 else '21-25']+=1
 return {'count':len(vals),'minimum':round(min(vals),1) if vals else None,'maximum':round(max(vals),1) if vals else None,'average':round(sum(vals)/len(vals),2) if vals else None,'buckets':b}
