from batch_e_common import games,store,ready
def run(conn,season,week,dry=False):
 gs=games(conn,season,week);records=[]
 for g in gs:
  if g['away_moneyline'] is None or g['home_moneyline'] is None or g['market_home_probability'] is None:continue
  records.append({'game_id':g['game_id'],'away_team':g['away_team'],'home_team':g['home_team'],'moneyline_away':g['away_moneyline'],'moneyline_home':g['home_moneyline'],'market_probability_home':float(g['market_home_probability']),'projected_total':float(g['projected_total']) if g['projected_total'] is not None else None,'captured_at':g['market_updated_at'],'provider':g['market_source']})
 score=len(records)/len(gs) if gs else 0;out={'source':'market','expected':len(gs),'loaded':len(records),'coverage':score}
 if not dry:
  if records:out['run_id']=store(conn,'market',records,season,week,'market_refresh_bridge')
  ready(conn,season,week,'market',score,None if score>=.999 else f'market coverage {len(records)}/{len(gs)}')
 return out
