from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

TEAM_FIELDS={"schedule":["away_team","home_team"],"market":["away_team","home_team"],"crowd":["away_team","home_team"],"ratings":["team"],"situations":["team"],"weather":["away_team","home_team"]}
REQUIRED={
 "schedule":["kickoff_time","away_team","home_team"],
 "market":["away_team","home_team","moneyline_away","moneyline_home"],
 "crowd":["away_team","home_team","yahoo_percentage_away","yahoo_percentage_home"],
 "ratings":["team","elo_rating"],
 "situations":["team"],
 "weather":["away_team","home_team","captured_at"],
}

def probability(v:Any)->float:
    x=float(v)
    if x>1: x=x/100
    if not 0<=x<=1: raise ValueError("probability outside 0..1")
    return x

def no_vig_home(away:float,home:float)->float:
    def implied(x): return 100/(x+100) if x>0 else (-x)/((-x)+100)
    a,h=implied(float(away)),implied(float(home)); return h/(a+h)

def normalize(source:str,row:Dict[str,Any],season:int,week:int)->Dict[str,Any]:
    out={str(k).strip():v for k,v in row.items()}; out["season"]=season; out["week"]=week
    for f in REQUIRED[source]:
        if out.get(f) in (None,""): raise ValueError(f"missing {f}")
    for f in TEAM_FIELDS[source]: out[f]=str(out[f]).strip().upper()
    if source=="schedule" and out["away_team"]==out["home_team"]: raise ValueError("away and home team cannot match")
    if source=="market":
        out["moneyline_away"]=float(out["moneyline_away"]); out["moneyline_home"]=float(out["moneyline_home"])
        out["market_probability_home"]=no_vig_home(out["moneyline_away"],out["moneyline_home"])
        if out.get("spread_home") not in (None,""): out["spread_home"]=float(out["spread_home"])
        if out.get("projected_total") not in (None,""): out["projected_total"]=float(out["projected_total"])
    if source=="crowd":
        out["yahoo_percentage_away"]=probability(out["yahoo_percentage_away"]); out["yahoo_percentage_home"]=probability(out["yahoo_percentage_home"])
        if abs(out["yahoo_percentage_away"]+out["yahoo_percentage_home"]-1)>0.02: raise ValueError("Yahoo percentages must sum to approximately 100%")
    if source=="ratings": out["elo_rating"]=float(out["elo_rating"])
    return out

def validate_rows(source:str,rows:Iterable[Dict[str,Any]],season:int,week:int)->Tuple[List[Dict[str,Any]],List[Dict[str,Any]]]:
    good,bad=[],[]; seen=set()
    for n,row in enumerate(rows,1):
        try:
            item=normalize(source,row,season,week)
            key=(source,season,week,*(item.get(x) for x in TEAM_FIELDS[source]))
            if source in {"schedule","market","crowd","weather"} and key in seen: raise ValueError("duplicate game record")
            seen.add(key); good.append(item)
        except Exception as e: bad.append({"row_number":n,"error":str(e),"record":row})
    return good,bad
