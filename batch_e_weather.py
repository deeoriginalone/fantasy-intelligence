from datetime import datetime,timezone
import requests
from batch_e_common import games,store,ready
URL='https://api.open-meteo.com/v1/forecast'
COORDS={'ARI':(33.5276,-112.2626),'ATL':(33.7554,-84.4008),'BAL':(39.278,-76.6227),'BUF':(42.7738,-78.787),'CAR':(35.2258,-80.8528),'CHI':(41.8623,-87.6167),'CIN':(39.0954,-84.516),'CLE':(41.5061,-81.6995),'DAL':(32.7473,-97.0945),'DEN':(39.7439,-105.0201),'DET':(42.34,-83.0456),'GB':(44.5013,-88.0622),'HOU':(29.6847,-95.4107),'IND':(39.7601,-86.1639),'JAX':(30.3239,-81.6373),'KC':(39.0489,-94.4839),'LA':(33.9535,-118.3392),'LAR':(33.9535,-118.3392),'LAC':(33.9535,-118.3392),'LV':(36.0908,-115.183),'MIA':(25.958,-80.2389),'MIN':(44.9736,-93.2575),'NE':(42.0909,-71.2643),'NO':(29.9511,-90.0812),'NYG':(40.8135,-74.0745),'NYJ':(40.8135,-74.0745),'PHI':(39.9008,-75.1675),'PIT':(40.4468,-80.0158),'SEA':(47.5952,-122.3316),'SF':(37.403,-121.97),'TB':(27.9759,-82.5033),'TEN':(36.1665,-86.7713),'WAS':(38.9077,-76.8645)}
def run(conn,season,week,dry=False):
 gs=games(conn,season,week);records=[];missing=[]
 for g in gs:
  coord=COORDS.get(g['home_team'])
  if not coord:missing.append(g['home_team']);continue
  p={'latitude':coord[0],'longitude':coord[1],'hourly':'temperature_2m,precipitation,wind_speed_10m','timezone':'UTC','forecast_days':16};r=requests.get(URL,params=p,timeout=30);r.raise_for_status();h=r.json().get('hourly',{});times=h.get('time',[])
  if not times:missing.append(f"{g['away_team']}@{g['home_team']}");continue
  k=g['kickoff'];target=k.astimezone(timezone.utc).replace(tzinfo=None) if getattr(k,'tzinfo',None) else k;idx=min(range(len(times)),key=lambda i:abs(datetime.fromisoformat(times[i])-target));records.append({'game_id':g['game_id'],'away_team':g['away_team'],'home_team':g['home_team'],'kickoff':k,'temperature_2m':h['temperature_2m'][idx],'precipitation':h['precipitation'][idx],'wind_speed_10m':h['wind_speed_10m'][idx],'source_url':URL})
 score=len(records)/len(gs) if gs else 0;out={'source':'weather','expected':len(gs),'loaded':len(records),'coverage':score,'missing':missing}
 if not dry:
  if records:out['run_id']=store(conn,'weather',records,season,week,'open_meteo')
  ready(conn,season,week,'weather',score,None if score>=.999 else f'weather coverage {len(records)}/{len(gs)}')
 return out
