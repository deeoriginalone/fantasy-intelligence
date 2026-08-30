from __future__ import annotations
from collections import defaultdict
from math import isfinite

MODEL_VERSION='survivor-intelligence-v1.0.0'

def clamp(v,lo=0.0,hi=1.0): return min(hi,max(lo,float(v)))

def team_probability(row,team):
    hp=float(row['model_home_probability'])
    return hp if team==row['home_team'] else 1-hp

def remaining_schedule_value(schedule_rows,team,current_week,predictions_by_game):
    future=[]
    for row in schedule_rows:
        if int(row['week'])<=int(current_week): continue
        if team not in (row['away_team'],row['home_team']): continue
        game_key=(int(row['week']),row['away_team'],row['home_team'])
        prediction=predictions_by_game.get(game_key)
        if prediction:
            future.append(team_probability(prediction,team))
    if not future: return 0.50
    # High future probability means the team is valuable to preserve.
    return sum(sorted(future,reverse=True)[:3])/min(3,len(future))

def stability_score(row):
    market=float(row.get('market_home_probability') or .5)
    elo=float(row.get('elo_home_probability') or .5)
    situation=float(row.get('situation_home_probability') or .5)
    spread=max(market,elo,situation)-min(market,elo,situation)
    return clamp(1-spread*2)

def build_recommendations(current_rows,schedule_rows,used_teams,predictions_by_game,strategy='balanced'):
    candidates=[]
    used=set(used_teams)
    for row in current_rows:
        pick=row['model_pick']
        if pick in used: continue
        current=clamp(row['model_probability'])
        future=remaining_schedule_value(schedule_rows,pick,row['week'],predictions_by_game)
        stability=stability_score(row)
        future_preservation=1-future
        if strategy=='protect-lead': weights=(.78,.12,.10)
        elif strategy=='gain-ground': weights=(.66,.24,.10)
        else: weights=(.72,.18,.10)
        score=clamp(current*weights[0]+future_preservation*weights[1]+stability*weights[2])
        candidates.append({
          'team':pick,'opponent':row['away_team'] if pick==row['home_team'] else row['home_team'],
          'home_away':'HOME' if pick==row['home_team'] else 'AWAY','week':int(row['week']),
          'current_probability':current,'future_value':future,'future_preservation':future_preservation,
          'stability':stability,'survivor_score':score,'signal':row.get('signal',''),
          'game_id':row['game_id'],'market_updated_at':row.get('market_updated_at'),
          'reason':_reason(current,future,stability)
        })
    return sorted(candidates,key=lambda x:(x['survivor_score'],x['current_probability']),reverse=True)

def _reason(current,future,stability):
    reasons=[]
    if current>=.70: reasons.append('high current-week win probability')
    elif current>=.60: reasons.append('positive current-week edge')
    else: reasons.append('limited current-week margin')
    if future>=.70: reasons.append('meaningful future value to preserve')
    elif future<=.58: reasons.append('limited future value, suitable to use now')
    if stability>=.85: reasons.append('model components are closely aligned')
    elif stability<.65: reasons.append('model components show elevated disagreement')
    return '; '.join(reasons)

def summarize(candidates):
    return {'primary':candidates[0] if candidates else None,'fallbacks':candidates[1:3],
            'avoid':list(reversed(candidates[-3:])) if candidates else []}
