from statistics import mean

def audit_recommendation_candidates(candidates):
    rows=[]
    for c in candidates or []:
        total=float(c.get('draft_score',0))
        row={k:float(c.get(k,0) or 0) for k in ['rank_score','need_score','scarcity_score','tier_bonus','strategy_bonus','league_bonus']}
        row['total']=total
        rows.append(row)
    if not rows:return {'status':'no data'}
    comps=['rank_score','need_score','scarcity_score','tier_bonus','strategy_bonus','league_bonus']
    averages={k:round(mean(r[k] for r in rows),2) for k in comps}
    maxes={k:max(r[k] for r in rows) for k in comps}
    warnings=[]
    if averages['need_score']>averages['rank_score']*0.8:warnings.append('Need score is approaching rank-score influence.')
    if averages['scarcity_score']>averages['rank_score']*0.6:warnings.append('Scarcity score is large relative to rank score.')
    if averages['tier_bonus']+averages['scarcity_score']>averages['rank_score']:warnings.append('Scarcity and tier effects may outweigh talent ranking.')
    return {'averages':averages,'maxes':maxes,'warnings':warnings,'candidate_count':len(rows)}
