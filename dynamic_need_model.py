CORE=('QB','RB','WR','TE');STARTERS={'QB':1,'RB':2,'WR':2,'TE':1}
EARLY={1:{'QB':20,'RB':92,'WR':92,'TE':35},2:{'QB':25,'RB':90,'WR':90,'TE':42},3:{'QB':35,'RB':84,'WR':84,'TE':52},4:{'QB':48,'RB':76,'WR':76,'TE':62},5:{'QB':62,'RB':68,'WR':68,'TE':72},6:{'QB':75,'RB':60,'WR':60,'TE':80}}
def clamp(v):return max(0,min(100,float(v)))
def strategy_adj(s,p,r):
 s=str(s or '').lower().replace('_',' ').replace('-',' ');a=0;early=r<=5
 if 'wr' in s and 'heavy' in s:a+=14 if p=='WR' and early else (-5 if p=='QB' and early else 0)
 if 'rb' in s and 'heavy' in s:a+=14 if p=='RB' and early else (-5 if p=='QB' and early else 0)
 if 'zero rb' in s:a+=-26 if p=='RB' and r<=5 else (18 if p=='WR' and early else (24 if p=='RB' and 6<=r<=10 else 0))
 if 'hero rb' in s:a+=16 if p=='RB' and r<=2 else (-12 if p=='RB' and 3<=r<=7 else 0)
 if 'late qb' in s and p=='QB' and r<=7:a-=22
 if 'elite qb' in s and p=='QB' and r<=4:a+=20
 if 'te premium' in s and p=='TE' and r<=5:a+=18
 return a
def calculate_dynamic_need(position,current_round,counts,targets,strategy=None):
 p=str(position).upper();r=max(1,int(current_round or 1));cur=int((counts or {}).get(p,0) or 0);target=max(1,int((targets or {}).get(p,1) or 1));starter=STARTERS.get(p,1)
 if cur>=target:return {'score':0,'position':p,'round':r,'current':cur,'target':target,'starter_gap':0,'depth_gap':0,'timing':0,'strategy_adjustment':0}
 timing=(EARLY.get(r) or {'QB':86,'RB':52,'WR':52,'TE':88}).get(p,50)
 if r>=9:timing={'QB':92,'RB':48,'WR':45,'TE':92}.get(p,50)
 sg=max(0,starter-cur);dg=max(0,target-cur);su=(sg/max(1,starter))*34;du=(dg/target)*18
 if sg==0:su=0;timing*=.62
 adj=strategy_adj(strategy,p,r);score=round(clamp(timing*.48+su+du+adj),1)
 return {'score':score,'position':p,'round':r,'current':cur,'target':target,'starter_gap':sg,'depth_gap':dg,'timing':round(timing,1),'strategy_adjustment':adj}
