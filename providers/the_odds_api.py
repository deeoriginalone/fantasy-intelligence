from __future__ import annotations
import json, os
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TEAM_MAP={
'Arizona Cardinals':'ARI','Atlanta Falcons':'ATL','Baltimore Ravens':'BAL','Buffalo Bills':'BUF',
'Carolina Panthers':'CAR','Chicago Bears':'CHI','Cincinnati Bengals':'CIN','Cleveland Browns':'CLE',
'Dallas Cowboys':'DAL','Denver Broncos':'DEN','Detroit Lions':'DET','Green Bay Packers':'GB',
'Houston Texans':'HOU','Indianapolis Colts':'IND','Jacksonville Jaguars':'JAX','Kansas City Chiefs':'KC',
'Las Vegas Raiders':'LV','Los Angeles Chargers':'LAC','Los Angeles Rams':'LAR','Miami Dolphins':'MIA',
'Minnesota Vikings':'MIN','New England Patriots':'NE','New Orleans Saints':'NO','New York Giants':'NYG',
'New York Jets':'NYJ','Philadelphia Eagles':'PHI','Pittsburgh Steelers':'PIT','San Francisco 49ers':'SF',
'Seattle Seahawks':'SEA','Tampa Bay Buccaneers':'TB','Tennessee Titans':'TEN','Washington Commanders':'WAS'}

@dataclass(frozen=True)
class MarketGame:
    away_team:str; home_team:str; commence_time:str
    away_moneyline:int; home_moneyline:int; projected_total:float|None
    bookmaker_count:int; source:str

class TheOddsAPI:
    def __init__(self,api_key=None,base_url=None):
        self.api_key=api_key or os.getenv('ODDS_API_KEY','')
        self.base_url=base_url or os.getenv('ODDS_API_BASE_URL','https://api.the-odds-api.com/v4')
        if not self.api_key: raise RuntimeError('ODDS_API_KEY is not configured')
    def fetch_nfl(self):
        params={'apiKey':self.api_key,'regions':os.getenv('ODDS_API_REGIONS','us'),'markets':'h2h,totals','oddsFormat':'american','dateFormat':'iso'}
        url=self.base_url.rstrip('/')+'/sports/americanfootball_nfl/odds?'+urlencode(params)
        with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'FantasyIntelligence-Market/1.0'}),timeout=30) as r:
            body=json.loads(r.read().decode('utf-8')); headers={k.lower():v for k,v in r.headers.items()}
        return self._normalize(body), {'remaining':_int(headers.get('x-requests-remaining')),'used':_int(headers.get('x-requests-used')),'last':_int(headers.get('x-requests-last'))}
    def _normalize(self,events):
        result=[]
        for event in events:
            home=TEAM_MAP.get(event.get('home_team')); away=TEAM_MAP.get(event.get('away_team'))
            if not home or not away: continue
            away_prices=[]; home_prices=[]; totals=[]
            for book in event.get('bookmakers',[]):
                for market in book.get('markets',[]):
                    if market.get('key')=='h2h':
                        prices={x.get('name'):x.get('price') for x in market.get('outcomes',[])}
                        if event.get('away_team') in prices: away_prices.append(int(prices[event['away_team']]))
                        if event.get('home_team') in prices: home_prices.append(int(prices[event['home_team']]))
                    elif market.get('key')=='totals':
                        pts=[x.get('point') for x in market.get('outcomes',[]) if x.get('point') is not None]
                        if pts: totals.append(float(pts[0]))
            if not away_prices or not home_prices: continue
            result.append(MarketGame(away,home,event.get('commence_time',''),_median(away_prices),_median(home_prices),_median(totals) if totals else None,len(event.get('bookmakers',[])),'the-odds-api'))
        return result

def _median(values):
    values=sorted(values); n=len(values); mid=n//2
    return values[mid] if n%2 else (values[mid-1]+values[mid])/2

def _int(v):
    try:return int(v)
    except:return None
