from __future__ import annotations
from math import exp,pow
MODEL_VERSION='market-intelligence-v1.0.0'

def clamp(v,lo=0,hi=1): return min(hi,max(lo,v))
def implied(ml):
    if ml==0: raise ValueError('moneyline cannot be zero')
    return 100/(ml+100) if ml>0 else abs(ml)/(abs(ml)+100)
def no_vig_home(away_ml,home_ml):
    a=implied(away_ml); h=implied(home_ml); return h/(a+h)
def elo_home(away_elo,home_elo,home_field=37.5): return 1/(1+pow(10,-(home_elo-away_elo+home_field)/400))
def situation_home(away_pts,home_pts,scale=6.5): return 1/(1+exp(-(home_pts-away_pts)/scale))
def weights(strategy):
    return {'protect-lead':(.70,.20,.10),'balanced':(.55,.25,.20),'gain-ground':(.45,.30,.25)}.get(strategy,(.55,.25,.20))
def calculate(row,strategy='balanced'):
    market=float(row['market_home_probability']); elo=elo_home(float(row.get('away_elo') or 1500),float(row.get('home_elo') or 1500)); situ=situation_home(float(row.get('away_situation_points') or 0),float(row.get('home_situation_points') or 0)); w=weights(strategy)
    hp=clamp(market*w[0]+elo*w[1]+situ*w[2]); home=hp>=.5; pick=row['home_team'] if home else row['away_team']; conf=hp if home else 1-hp
    signal='ELITE PICK' if conf>=.85 else 'STRONG PICK' if conf>=.72 else 'LEAN' if conf>=.60 else 'COIN FLIP'
    return {**row,'market_home_probability':market,'elo_home_probability':elo,'situation_home_probability':situ,'model_home_probability':hp,'model_pick':pick,'model_probability':conf,'signal':signal,'strategy':strategy,'model_version':MODEL_VERSION}
def build_week(rows,strategy='balanced'):
    out=[calculate(r,strategy) for r in rows]; ordered=sorted(out,key=lambda x:(x['model_probability'],x['game_id']))
    ranks={x['game_id']:i+1 for i,x in enumerate(ordered)}
    for x in out: x['confidence_points']=ranks[x['game_id']]; x['expected_correct_value']=x['model_probability']*x['confidence_points']
    return sorted(out,key=lambda x:x['confidence_points'],reverse=True)
def summarize(rows):
    return {'lock':rows[0] if rows else None,'expected_correct':sum(x['model_probability'] for x in rows),'strong_picks':[x for x in rows if x['signal'] in ('ELITE PICK','STRONG PICK')],'coin_flips':[x for x in rows if x['signal']=='COIN FLIP']}
