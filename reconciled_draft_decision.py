def _num(v,d=None):
 try:return float(v)
 except (TypeError,ValueError):return d
def _name(p):
 if isinstance(p,(list,tuple)) and len(p)>1:return str(p[1])
 if isinstance(p,dict):return str(p.get('player_name') or p.get('name') or '')
 return str(p or '')
def _find(rows,name,keys=('player','name')):
 target=' '.join(name.lower().split())
 return next((r for r in (rows or []) if any(' '.join(str(r.get(k) or '').lower().split())==target for k in keys)),None)
def reconcile_draft_now_wait(dnw,player,mc,ev,survival,signals):
 out=dict(dnw or {});name=_name(player);mr=_find((mc or {}).get('players'),name);er=_find((ev or {}).get('players'),name);sr=_find((survival or {}).get('rows'),name,('name',));m=_num((mr or {}).get('availability_pct'));old=_num(out.get('availability_pct',out.get('chance_at_next_pick')));s=_num((sr or {}).get('survival_pct'));loss=_num((er or {}).get('expected_value_loss'),0) or 0
 vals=[]
 if m is not None:vals.append((m,.6))
 if old is not None:vals.append((old,.2))
 if s is not None:vals.append((s,.2))
 consensus=round(sum(v*w for v,w in vals)/sum(w for v,w in vals),1) if vals else 50.0;spread=round(max([v for v,w in vals])-min([v for v,w in vals]),1) if len(vals)>1 else 0
 if (m is not None and m<=35) or consensus<=35 or (loss>=25 and consensus<60):decision='DRAFT NOW'
 elif m is not None and m>=70 and loss<5:decision='WAIT MAY BE SAFE'
 elif consensus<55 or loss>=15:decision='HIGH RISK'
 elif consensus<75 or loss>=5:decision='BALANCED'
 else:decision='WAIT MAY BE SAFE'
 risk='HIGH' if consensus<45 else ('MEDIUM' if consensus<70 else 'LOW');reasons=[]
 if m is not None:reasons.append(f'Monte Carlo estimates {m:.1f}% availability at the next pick.')
 if old is not None:reasons.append(f'Opponent-model availability estimate is {old:.1f}%.')
 if s is not None:reasons.append(f'Sleeper survival heuristic estimates {s:.1f}%.')
 reasons.append(f'Expected-value loss from waiting is {loss:.1f} points.')
 if spread>=25:reasons.append(f'Availability models disagree by {spread:.1f} percentage points; Monte Carlo receives the highest weight.')
 out.update({'decision':decision,'risk':risk,'risk_level':risk,'risk_label':risk,'availability_pct':consensus,'chance_at_next_pick':consensus,'availability':consensus,'estimated_chance':consensus,'next_pick_chance':consensus,'next_pick_availability':consensus,'estimated_chance':consensus,'estimated_chance_pct':consensus,'next_pick_chance':consensus,'next_pick_availability':consensus,'available_next_pick_pct':consensus,'reasons':reasons,'reconciled':True,'model_disagreement_pct':spread,'expected_value_loss':round(loss,1),'source_estimates':{'monte_carlo':m,'opponent_model':old,'sleeper_survival':s}});return out
