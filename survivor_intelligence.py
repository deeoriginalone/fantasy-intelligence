from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite

MODEL_VERSION='survivor-intelligence-v1.0.0'

# Implementation-owned freshness thresholds for survivor market evidence (not externally verified).
FRESHNESS_THRESHOLD_ID='survivor-market-intelligence-v1'
FRESHNESS_AGING_HOURS=12
FRESHNESS_STALE_HOURS=24

def evidence_freshness_state(updated_at,now=None):
    if not updated_at: return 'UNAVAILABLE'
    now=now or datetime.now(timezone.utc)
    age_hours=(now-updated_at).total_seconds()/3600
    if age_hours<0: age_hours=0
    if age_hours<=FRESHNESS_AGING_HOURS: return 'FRESH'
    if age_hours<=FRESHNESS_STALE_HOURS: return 'AGING'
    return 'STALE'

def team_universe(schedule_rows):
    teams=set()
    for row in schedule_rows:
        teams.add(row['home_team']); teams.add(row['away_team'])
    return teams

LOCKED_WEEK_STATES=('PENDING_RESULT','COMPLETED')

def result_label(status):
    return {'pending':'Pending','won':'Win','lost':'Loss','void':'Void'}.get(status,status)

def determine_week_state(existing_selection,schedule_weeks,week):
    """Derive OPEN/PENDING_RESULT/COMPLETED/UNAVAILABLE only from verified repository data."""
    if existing_selection is not None:
        status=existing_selection.get('status')
        if status in ('won','lost','void'):
            return 'COMPLETED',result_label(status)
        return 'PENDING_RESULT',result_label(status or 'pending')
    if schedule_weeks and week not in schedule_weeks:
        return 'UNAVAILABLE',None
    return 'OPEN',None

def next_verified_week(schedule_weeks,week):
    """Only report a next week that actually has verified schedule evidence; never guess."""
    candidate=week+1
    return candidate if candidate in schedule_weeks else None

def build_status(*,season,week,history_status,used_teams,schedule_rows,current_rows,candidates,week_state='OPEN',now=None):
    """Manager-facing survivor_status evidence contract. Never claims READY without complete, fresh evidence."""
    now=now or datetime.now(timezone.utc)
    universe=team_universe(schedule_rows)
    blocker=None
    degrade_reason=None
    if history_status!='verified':
        state='BLOCKED'; freshness='UNAVAILABLE'
        blocker='SURVIVOR_HISTORY_READ_FAILED'
        last_verified=None
    elif week_state=='UNAVAILABLE':
        state='UNAVAILABLE'; freshness='UNAVAILABLE'
        blocker='SURVIVOR_WEEK_UNVERIFIED'
        last_verified=None
    elif week_state in LOCKED_WEEK_STATES:
        state=week_state; freshness='UNAVAILABLE'; blocker=None
        last_verified=None
    elif not current_rows:
        state='UNAVAILABLE'; freshness='UNAVAILABLE'
        blocker='SURVIVOR_WEEK_EVIDENCE_MISSING'
        last_verified=None
    else:
        timestamps=[r.get('market_updated_at') for r in current_rows if r.get('market_updated_at')]
        oldest=min(timestamps) if timestamps else None
        freshness=evidence_freshness_state(oldest,now)
        last_verified=oldest.isoformat() if oldest else None
        if freshness in ('UNAVAILABLE','STALE'):
            state='BLOCKED'; blocker=f'SURVIVOR_EVIDENCE_{freshness}'
        elif not candidates:
            state='UNAVAILABLE'; blocker='SURVIVOR_NO_ELIGIBLE_TEAMS'
        elif freshness=='AGING':
            state='DEGRADED'
        else:
            state='READY'
            primary=candidates[0]
            if not primary.get('future_available',True):
                state='DEGRADED'; degrade_reason='SURVIVOR_FUTURE_VALUE_UNAVAILABLE'
    return {
        'season':season,'active_week':week,'history_status':history_status,'week_state':week_state,
        'used_team_count':len(used_teams) if history_status=='verified' else None,
        'remaining_team_count':(len(universe)-len(used_teams)) if history_status=='verified' and universe else None,
        'evidence_state':freshness,'freshness_state':freshness,
        'blocker_reason':blocker,'degrade_reason':degrade_reason,'last_verified':last_verified,'state':state,
    }

def clamp(v,lo=0.0,hi=1.0): return min(hi,max(lo,float(v)))

def team_probability(row,team):
    if row.get('model_home_probability') is not None:
        home_probability=float(row['model_home_probability'])
        return home_probability if team==row['home_team'] else 1-home_probability
    if row.get('model_probability') is not None and row.get('model_pick'):
        selected_probability=float(row['model_probability'])
        return selected_probability if team==row['model_pick'] else 1-selected_probability
    return None

def remaining_schedule_value(schedule_rows,team,current_week,predictions_by_game):
    """Returns an explicit future-value contract; never fabricates a neutral value when future evidence is missing."""
    future=[]
    weeks=[]
    for row in schedule_rows:
        if int(row['week'])<=int(current_week): continue
        if team not in (row['away_team'],row['home_team']): continue
        game_key=(int(row['week']),row['away_team'],row['home_team'])
        prediction=predictions_by_game.get(game_key)
        if prediction:
            probability=team_probability(prediction,team)
            if probability is not None:
                future.append(probability)
                weeks.append(int(row['week']))
    if not future:
        return {'available':False,'value':None,'weeks':[],'missing_reason':'SURVIVOR_FUTURE_EVIDENCE_UNAVAILABLE'}
    # High future probability means the team is valuable to preserve.
    ranked=sorted(zip(future,weeks),reverse=True)[:3]
    value=sum(p for p,_ in ranked)/len(ranked)
    return {'available':True,'value':value,'weeks':sorted(w for _,w in ranked),'missing_reason':None}

def stability_score(row):
    """Evidence agreement across market/Elo/situational signals. None (Unavailable) when any component is missing, never a fabricated spread."""
    market=row.get('market_home_probability')
    elo=row.get('elo_home_probability')
    situation=row.get('situation_home_probability')
    if market is None or elo is None or situation is None:
        return None
    spread=max(float(market),float(elo),float(situation))-min(float(market),float(elo),float(situation))
    return clamp(1-spread*2)

def build_recommendations(current_rows,schedule_rows,used_teams,predictions_by_game,strategy='balanced'):
    candidates=[]
    used=set(used_teams)
    for row in current_rows:
        pick=row['model_pick']
        if pick in used: continue
        current=clamp(row['model_probability'])
        future_info=remaining_schedule_value(schedule_rows,pick,row['week'],predictions_by_game)
        stability=stability_score(row)
        stability_available=stability is not None
        future_available=future_info['available']
        future_value=future_info['value']
        future_preservation=(1-future_value) if future_available else None
        if future_available and stability_available:
            # Policy: full 3-component score when future and evidence-agreement inputs are both supported.
            if strategy=='protect-lead': weights=(.78,.12,.10)
            elif strategy=='gain-ground': weights=(.66,.24,.10)
            else: weights=(.72,.18,.10)
            score=clamp(current*weights[0]+future_preservation*weights[1]+stability*weights[2])
            score_basis='current_future_stability'
        elif stability_available:
            # Policy: recompute from supported components only (no neutral future substitute); disclosed reduced scope.
            if strategy=='protect-lead': weights=(.90,.10)
            elif strategy=='gain-ground': weights=(.85,.15)
            else: weights=(.88,.12)
            score=clamp(current*weights[0]+stability*weights[1])
            score_basis='current_stability_only'
        else:
            # Evidence agreement is unavailable; do not fabricate a confidence value or fold it into the score.
            score=clamp(current)
            score_basis='current_only'
        candidates.append({
          'team':pick,'opponent':row['away_team'] if pick==row['home_team'] else row['home_team'],
          'home_away':'HOME' if pick==row['home_team'] else 'AWAY','week':int(row['week']),
          'current_probability':current,
          'future_available':future_available,'future_value':future_value,'future_weeks':future_info['weeks'],
          'future_missing_reason':future_info['missing_reason'],'future_preservation':future_preservation,
          'stability_available':stability_available,'stability':stability,
          'survivor_score':score,'survivor_score_basis':score_basis,'signal':row.get('signal',''),
          'game_id':row['game_id'],'market_updated_at':row.get('market_updated_at'),
          'reason':_reason(current,future_available,future_value,stability_available,stability)
        })
    return sorted(candidates,key=lambda x:(x['survivor_score'],x['current_probability']),reverse=True)

def _reason(current,future_available,future_value,stability_available,stability):
    reasons=[]
    if current>=.70: reasons.append('high current-week win probability')
    elif current>=.60: reasons.append('positive current-week edge')
    else: reasons.append('limited current-week margin')
    if future_available:
        if future_value>=.70: reasons.append('meaningful future value to preserve')
        elif future_value<=.58: reasons.append('limited future value, suitable to use now')
    else:
        reasons.append('future opportunity cost is unavailable (no supported future schedule evidence)')
    if not stability_available:
        reasons.append('evidence agreement is unavailable (missing model component)')
    elif stability>=.85: reasons.append('model components are closely aligned')
    elif stability<.65: reasons.append('model components show elevated disagreement')
    return '; '.join(reasons)

def summarize(candidates):
    primary=candidates[0] if candidates else None
    fallbacks=candidates[1:3]
    shown={c['team'] for c in ([primary] if primary else [])+fallbacks}
    save_for_later=[c for c in candidates if c['team'] not in shown and c['future_available'] and c['future_value']>=0.70][:3]
    avoid=[c for c in reversed(candidates[-3:]) if c['team'] not in shown] if candidates else []
    risks=[]
    for c in ([primary] if primary else [])+fallbacks:
        if not c['stability_available']:
            risks.append({'affected_recommendation':c['team'],'risk':'Evidence agreement could not be computed (a market/Elo/situational component is missing).',
                          'impact':'Confidence is Unavailable, not a numeric agreement score, for this candidate.',
                          'manager_response':'Treat this pick as current-week-probability-only until evidence agreement is restored.',
                          'evidence_state':'UNAVAILABLE'})
        elif c['stability']<0.65:
            risks.append({'affected_recommendation':c['team'],'risk':'Model components show elevated disagreement (market/Elo/situational signals diverge).',
                          'impact':'Confidence should be treated as lower than the raw win probability implies.',
                          'manager_response':'Re-check before locking in; consider a fallback if disagreement persists near kickoff.',
                          'evidence_state':'DEGRADED'})
    return {'primary':primary,'fallbacks':fallbacks,'avoid':avoid,'save_for_later':save_for_later,
            'risks':risks,
            'multi_week_roadmap':{'state':'UNAVAILABLE','reason':'SURVIVOR_MULTI_WEEK_MODEL_UNAVAILABLE',
                                   'explanation':'No supported multi-week survivor optimizer exists yet; only the active week is modeled.'}}
