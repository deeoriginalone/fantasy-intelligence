"""F4-E playoff intelligence from supplied standings and remaining matchups.
Decision support only. No roster, waiver, lineup, or trade transaction is submitted.
"""
from __future__ import annotations

def number(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return default

def clamp(value, low=0.0, high=100.0): return max(low, min(high, value))

def normalize_team(row):
    r=dict(row or {})
    wins=int(number(r.get('wins'))); losses=int(number(r.get('losses'))); ties=int(number(r.get('ties')))
    games=wins+losses+ties
    r.update({'wins':wins,'losses':losses,'ties':ties,'games':games,
              'points_for':number(r.get('points_for') or r.get('fpts')),
              'points_against':number(r.get('points_against') or r.get('fpts_against'))})
    r['win_pct']=round((wins+0.5*ties)/games,4) if games else 0.0
    return r

def standings_order(teams):
    rows=[normalize_team(x) for x in (teams or [])]
    return sorted(rows,key=lambda x:(-x['win_pct'],-x['points_for'],x.get('name') or ''))

def schedule_score(remaining_matchups, by_name):
    scores=[]; missing=[]
    for game in remaining_matchups or []:
        opponent=game.get('opponent') if isinstance(game,dict) else game
        row=by_name.get(opponent)
        if not row: missing.append(opponent or 'Unknown'); continue
        scores.append(row['win_pct']*70 + min(30,row['points_for']/100))
    if not scores: return {'score':None,'label':'UNKNOWN','missing_opponents':missing}
    score=round(sum(scores)/len(scores),2)
    return {'score':score,'label':'HIGH' if score>=62 else 'MEDIUM' if score>=45 else 'LOW','missing_opponents':missing}

def playoff_probability(owner, ordered, playoff_teams, weeks_remaining, schedule):
    if not ordered or playoff_teams<=0: return 0
    rank=next((i+1 for i,x in enumerate(ordered) if x.get('name')==owner.get('name')),len(ordered))
    cut=max(1,min(playoff_teams,len(ordered)))
    seed_component=50 + (cut-rank)*12
    win_component=(owner['win_pct']-0.5)*80
    points_rank=next((i+1 for i,x in enumerate(sorted(ordered,key=lambda x:-x['points_for'])) if x.get('name')==owner.get('name')),len(ordered))
    points_component=(len(ordered)-points_rank)*2
    urgency_penalty=max(0,3-int(weeks_remaining))*3
    schedule_penalty=0 if schedule['score'] is None else max(-12,min(12,(schedule['score']-50)*0.35))
    return round(clamp(seed_component+win_component+points_component-urgency_penalty-schedule_penalty),1)

def build_playoff_intelligence(teams, owner_name, playoff_teams, weeks_remaining, remaining_matchups=None):
    ordered=standings_order(teams)
    blockers=[]
    if not ordered: blockers.append('STANDINGS_EMPTY')
    if not owner_name: blockers.append('OWNER_TEAM_UNKNOWN')
    owner=next((x for x in ordered if x.get('name')==owner_name),None)
    if owner is None: blockers.append('OWNER_TEAM_NOT_FOUND')
    if int(number(playoff_teams))<=0: blockers.append('PLAYOFF_TEAM_COUNT_UNKNOWN')
    if owner is None:
        return {'allowed':False,'blockers':blockers,'playoff_probability':0,'projected_seed':None,'must_win':False,'risk_level':'UNKNOWN','schedule_strength':{'score':None,'label':'UNKNOWN','missing_opponents':[]},'recommendations':[],'standings':ordered,'methodology':'Uses only supplied standings and schedule evidence. No transaction is submitted.'}
    by_name={x.get('name'):x for x in ordered}
    schedule=schedule_score(remaining_matchups,by_name)
    if remaining_matchups is None: blockers.append('REMAINING_SCHEDULE_UNKNOWN')
    elif schedule['missing_opponents']: blockers.append('SCHEDULE_EVIDENCE_INCOMPLETE')
    seed=next(i+1 for i,x in enumerate(ordered) if x.get('name')==owner_name)
    probability=playoff_probability(owner,ordered,int(number(playoff_teams)),int(number(weeks_remaining)),schedule)
    games_left=max(0,int(number(weeks_remaining)))
    cutoff=int(number(playoff_teams))
    must_win=games_left>0 and (seed>cutoff or probability<45) and games_left<=4
    risk='HIGH' if probability<35 else 'MEDIUM' if probability<70 else 'LOW'
    recommendations=[]
    if must_win: recommendations.append({'priority':1,'action':'MUST_WIN','reason':'Current seed, probability, and weeks remaining create an urgent playoff path.'})
    if schedule['label']=='HIGH': recommendations.append({'priority':2,'action':'HARD_SCHEDULE','reason':'Remaining opponents rate as a difficult schedule from supplied standings.'})
    if owner['points_for'] < (sum(x['points_for'] for x in ordered)/max(len(ordered),1)):
        recommendations.append({'priority':3,'action':'IMPROVE_SCORING','reason':'Owner points for are below the supplied league average.'})
    if not recommendations: recommendations.append({'priority':4,'action':'HOLD_POSITION','reason':'Current supplied evidence does not trigger an urgent playoff warning.'})
    return {'allowed':not any(x in blockers for x in ('STANDINGS_EMPTY','OWNER_TEAM_UNKNOWN','OWNER_TEAM_NOT_FOUND','PLAYOFF_TEAM_COUNT_UNKNOWN')),'blockers':blockers,'playoff_probability':probability,'projected_seed':seed,'must_win':must_win,'risk_level':risk,'schedule_strength':schedule,'weeks_remaining':games_left,'owner':owner,'recommendations':recommendations,'standings':ordered,'methodology':'Deterministic decision support from supplied wins, losses, ties, points for, playoff-team count, weeks remaining, and optional opponent standings. No transaction is submitted.'}
