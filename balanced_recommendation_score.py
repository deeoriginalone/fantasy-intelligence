import math

def clamp(v,lo,hi):
 try:v=float(v or 0)
 except (TypeError,ValueError):v=0.0
 return max(lo,min(hi,v))
def calculate_balanced_score(rank,need,scarcity,tier,strategy,league):
 try:rank=max(1,float(rank))
 except (TypeError,ValueError):rank=999.0
 talent=round(120*math.exp(-(rank-1)/70),2)
 parts={'talent':talent,'need':round(clamp(need,0,100)*.25,2),'scarcity':round(clamp(scarcity,0,50)*.30,2),'tier':round(clamp(tier,0,20)*.75,2),'strategy':round(clamp(strategy,-20,20)*.50,2),'league':round(clamp(league,-20,20)*.50,2)}
 parts['total']=round(sum(parts.values()),2);parts['raw']={'rank':rank,'need':need,'scarcity':scarcity,'tier':tier,'strategy':strategy,'league':league};return parts
