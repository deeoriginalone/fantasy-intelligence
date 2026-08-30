"""Normalized JSON providers.

Crowd endpoint response:
{"games":[{"season":2026,"week":1,"away_team":"ARI","home_team":"LAC","away_pct":42,"home_pct":58}]}

Odds endpoint response:
{"games":[{"season":2026,"week":1,"away_team":"ARI","home_team":"LAC","away_moneyline":140,"home_moneyline":-160,"total":46.5}]}
"""
from __future__ import annotations
import json, os
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from urllib.request import Request, urlopen
from .base import CrowdRecord, OddsRecord

ALIASES={'JAC':'JAX','KAN':'KC','GNB':'GB','LVR':'LV','NEP':'NE','NOS':'NO','SFO':'SF','TAM':'TB','WSH':'WAS'}
def team(v):
    x=str(v).strip().upper(); return ALIASES.get(x,x)

def _fetch(url, season, week, token_env):
    if not url: raise RuntimeError('Provider URL is not configured')
    parsed=urlparse(url); query=dict(parse_qsl(parsed.query)); query.update({'season':str(season),'week':str(week)})
    final=urlunparse(parsed._replace(query=urlencode(query)))
    headers={'Accept':'application/json','User-Agent':'FantasyIntelligence-Pickem/1.0'}
    token=os.getenv(token_env,'').strip()
    if token: headers['Authorization']='Bearer '+token
    with urlopen(Request(final,headers=headers),timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))

class HTTPJSONCrowdProvider:
    name='http-json-crowd'
    def __init__(self,url=None): self.url=url or os.getenv('PICKEM_CROWD_URL','')
    def fetch(self,season,week):
        data=_fetch(self.url,season,week,'PICKEM_CROWD_TOKEN'); out=[]
        for g in data.get('games',[]): 
            ap=float(g['away_pct']); hp=float(g['home_pct'])
            if ap>1: ap/=100
            if hp>1: hp/=100
            out.append(CrowdRecord(int(g.get('season',season)),int(g.get('week',week)),team(g['away_team']),team(g['home_team']),ap,hp,str(g.get('source',self.name))))
        return out

class HTTPJSONOddsProvider:
    name='http-json-odds'
    def __init__(self,url=None): self.url=url or os.getenv('PICKEM_ODDS_URL','')
    def fetch(self,season,week):
        data=_fetch(self.url,season,week,'PICKEM_ODDS_TOKEN'); out=[]
        for g in data.get('games',[]):
            out.append(OddsRecord(int(g.get('season',season)),int(g.get('week',week)),team(g['away_team']),team(g['home_team']),int(g['away_moneyline']),int(g['home_moneyline']),float(g['total']) if g.get('total') is not None else None,str(g.get('source',self.name))))
        return out
