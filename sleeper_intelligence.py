from collections import Counter,defaultdict
CORE=("QB","RB","WR","TE"); TARGET={"QB":1,"RB":4,"WR":5,"TE":2}
def snap(cur,name,league,week=None):
 q="SELECT payload FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s"; p=[name,str(league)]
 if week is not None:q+=" AND week=%s";p.append(week)
 q+=" ORDER BY fetched_at DESC LIMIT 1";cur.execute(q,p);r=cur.fetchone();return r[0] if r else []
def build(cur,league,week):
 users=snap(cur,"users",league);rosters=snap(cur,"rosters",league);players=snap(cur,"players",league) or {};adds=snap(cur,"trending_add",league);tx=snap(cur,"transactions",league,week);games=snap(cur,"matchups",league,week)
 names={str(u.get("user_id")):u.get("metadata",{}).get("team_name") or u.get("display_name") for u in users};owned={str(x) for r in rosters for x in r.get("players",[])};needs=[];pressure=Counter()
 for r in rosters:
  c=Counter((players.get(str(x),{}).get("position") or "").upper() for x in r.get("players",[]));n={p:max(0,TARGET[p]-c[p]) for p in CORE};pressure.update(n);needs.append({"name":names.get(str(r.get("owner_id")),f"Roster {r.get('roster_id')}"),"counts":dict(c),"primary":max(CORE,key=lambda p:n[p])})
 trending=[]
 for x in adds:
  pid=str(x.get("player_id"));p=players.get(pid,{})
  if pid not in owned:trending.append({"name":p.get("full_name") or pid,"position":p.get("position"),"team":p.get("team"),"count":x.get("count",0)})
 types=Counter(x.get("type","unknown") for x in tx);groups=defaultdict(list)
 for x in games:groups[x.get("matchup_id")].append({"roster_id":x.get("roster_id"),"points":x.get("points",0)})
 return {"week":week,"needs":needs,"pressure":dict(pressure),"trending":sorted(trending,key=lambda x:x["count"],reverse=True)[:15],"transactions":dict(types),"matchups":dict(groups),"players_cached":bool(players)}
