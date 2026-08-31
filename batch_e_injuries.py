import requests
from batch_e_common import games,store,ready
URL='https://api.sleeper.app/v1/players/nfl';QB={'Out':-4,'Doubtful':-3,'Questionable':-1,'IR':-4};OL={'C','G','T','OL'};DEF={'DL','DE','DT','LB','DB','CB','S'}
def run(conn,season,week,dry=False):
 res=requests.get(URL,timeout=60);res.raise_for_status();players=res.json();teams={x for g in games(conn,season,week) for x in (g['away_team'],g['home_team'])};records={t:{'team':t,'quarterback_points':0.0,'offensive_line_points':0.0,'defense_points':0.0,'weather_points':0.0,'rest_travel_points':0.0,'notes':[],'source_url':URL,'evaluated':True} for t in teams}
 for pid,p in players.items():
  team=(p.get('team') or '').upper();inj=p.get('injury_status');pos=p.get('position')
  if team not in records or not inj:continue
  if pos=='QB':records[team]['quarterback_points']+=QB.get(inj,0)
  elif pos in OL and inj in {'Out','Doubtful','IR'}:records[team]['offensive_line_points']-=.5
  elif pos in DEF and inj in {'Out','Doubtful','IR'}:records[team]['defense_points']-=.25
  records[team]['notes'].append(f"{p.get('full_name') or pid}: {pos}, {inj}")
 output=[]
 for r in records.values():r['status_notes']='; '.join(r.pop('notes')) or 'No Sleeper injury designation returned';output.append(r)
 score=len(output)/len(teams) if teams else 0;out={'source':'situations','expected':len(teams),'loaded':len(output),'coverage':score}
 if not dry:
  if output:out['run_id']=store(conn,'situations',output,season,week,'sleeper_players_nfl')
  ready(conn,season,week,'injuries',score,None if score>=.999 else f'injury coverage {len(output)}/{len(teams)}','Sleeper status is supplemental and not an official game-status guarantee')
 return out
