"""Sleeper intelligence derived from cached league, player, roster, and draft data."""
from collections import Counter, defaultdict

CORE=("QB","RB","WR","TE")
DEPTH_TARGETS={"QB":1,"RB":4,"WR":5,"TE":2}
STARTER_TARGETS={"QB":1,"RB":2,"WR":2,"TE":1}

def _latest(cur, resource, league_id=None, week=None, season=None):
    sql="SELECT payload,resource_key,fetched_at FROM sleeper_api_snapshots WHERE resource_type=%s"
    params=[resource]
    if league_id is not None:
        sql+=" AND resource_key=%s";params.append(str(league_id))
    if week is not None:
        sql+=" AND week=%s";params.append(int(week))
    if season is not None:
        sql+=" AND season=%s";params.append(int(season))
    sql+=" ORDER BY fetched_at DESC LIMIT 1"
    cur.execute(sql,params);row=cur.fetchone()
    return (row[0],row[1],row[2]) if row else (None,None,None)

def _players(cur,league_id,season):
    data,_,_= _latest(cur,"players",league_id,season=season)
    return {str(k):v for k,v in (data or {}).items()}

def _position(player):
    return str((player or {}).get("position") or "").upper()

def _owner_names(users):
    return {str(u.get("user_id")):u.get("metadata",{}).get("team_name") or u.get("display_name") or str(u.get("user_id")) for u in users or []}

def _draft_slot_names(draft,users):
    user_names=_owner_names(users);metadata=(draft or {}).get("metadata") or {};slot_to_roster=(draft or {}).get("slot_to_roster_id") or {};order=(draft or {}).get("draft_order") or {}
    result={}
    for user_id,slot in order.items(): result[int(slot)]=user_names.get(str(user_id),str(user_id))
    for slot,roster_id in slot_to_roster.items(): result.setdefault(int(slot),f"Roster {roster_id}")
    return result

def _pick_player_id(pick):
    return str(pick.get("player_id") or (pick.get("metadata") or {}).get("player_id") or "")

def draft_construction(picks,players,draft,users):
    names=_draft_slot_names(draft,users);counts=defaultdict(Counter);last_by_pos=Counter();recent=[]
    for pick in sorted(picks or [],key=lambda p:int(p.get("pick_no") or 0)):
        slot=int(pick.get("draft_slot") or 0);pid=_pick_player_id(pick);meta=pick.get("metadata") or {};pdata=players.get(pid,{})
        pos=str(meta.get("position") or _position(pdata)).upper();name=meta.get("first_name","")+" "+meta.get("last_name","");name=name.strip() or pdata.get("full_name") or pid
        if pos: counts[slot][pos]+=1;last_by_pos[pos]+=1
        recent.append({"pick_no":pick.get("pick_no"),"round":pick.get("round"),"slot":slot,"manager":names.get(slot,f"Slot {slot}"),"player":name,"position":pos})
    teams=[];slots=sorted(set(names)|set(counts))
    for slot in slots:
        c=counts[slot];need={p:max(0,DEPTH_TARGETS[p]-c[p]) for p in CORE};primary=max(CORE,key=lambda p:(need[p],STARTER_TARGETS[p]-c[p]))
        teams.append({"draft_slot":slot,"manager":names.get(slot,f"Slot {slot}"),"counts":{p:c[p] for p in CORE},"needs":need,"primary_need":primary,"picks":sum(c.values())})
    return teams,recent[-12:],dict(last_by_pos)

def roster_construction(rosters,players,users):
    names=_owner_names(users);teams=[]
    for r in rosters or []:
        c=Counter(_position(players.get(str(pid),{})) for pid in (r.get("players") or []));need={p:max(0,DEPTH_TARGETS[p]-c[p]) for p in CORE};primary=max(CORE,key=lambda p:(need[p],STARTER_TARGETS[p]-c[p]))
        teams.append({"roster_id":r.get("roster_id"),"manager":names.get(str(r.get("owner_id")),f"Roster {r.get('roster_id')}"),"counts":{p:c[p] for p in CORE},"needs":need,"primary_need":primary,"players":len(r.get("players") or [])})
    return teams

def pressure(teams):
    out=Counter()
    for t in teams: out.update(t.get("needs") or {})
    return {p:out[p] for p in CORE}

def available_trending(trends,rosters,players,limit=15):
    owned={str(pid) for r in rosters or [] for pid in (r.get("players") or [])};out=[]
    for item in trends or []:
        pid=str(item.get("player_id"));p=players.get(pid,{})
        if pid in owned: continue
        out.append({"player_id":pid,"name":p.get("full_name") or pid,"position":p.get("position"),"team":p.get("team"),"count":item.get("count",0)})
    return sorted(out,key=lambda x:x["count"],reverse=True)[:limit]

def build(cur,league_id,week,season=2026):
    users,_,_=_latest(cur,"users",league_id,season=season);rosters,_,_=_latest(cur,"rosters",league_id,season=season);players=_players(cur,league_id,season)
    drafts,_,_=_latest(cur,"drafts",league_id,season=season);draft=(drafts or [{}])[0] if isinstance(drafts,list) else (drafts or {})
    draft_id=str(draft.get("draft_id") or "");picks,_,_=_latest(cur,"draft_picks",draft_id if draft_id else None,season=season)
    trends,_,_=_latest(cur,"trending_add",league_id,season=season);transactions,_,_=_latest(cur,"transactions",league_id,week=week,season=season);matchups,_,_=_latest(cur,"matchups",league_id,week=week,season=season);nfl_state,_,_=_latest(cur,"nfl_state",league_id,season=season)
    draft_teams,recent,run_counts=draft_construction(picks or [],players,draft,users or [])
    roster_teams=roster_construction(rosters or [],players,users or [])
    roster_has_players=any(t.get("players",0)>0 for t in roster_teams)
    active=draft_teams if (picks and not roster_has_players) else roster_teams
    source="draft_picks" if active is draft_teams else "rosters"
    tx_types=Counter(x.get("type","unknown") for x in (transactions or []));games=defaultdict(list)
    for x in matchups or []:games[x.get("matchup_id")].append({"roster_id":x.get("roster_id"),"points":x.get("points",0)})
    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure(active),"recent_picks":recent,"position_run_counts":run_counts,"trending_available":available_trending(trends or [],rosters or [],players),"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}
