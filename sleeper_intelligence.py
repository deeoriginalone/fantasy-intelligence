"""Sleeper intelligence derived from cached league, player, roster, and draft data."""
from collections import Counter, defaultdict
from services.roster_slots import build_roster_slots

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

def estimate_faab(waiver_score,trend_count,primary_need_match,pressure_score,remaining_budget=None):
    """Return bounded decision-support FAAB guidance; never submits a claim."""
    score=float(waiver_score or 0)
    if score>=375: urgency,base,spread="CRITICAL",17,5
    elif score>=275: urgency,base,spread="HIGH",12,4
    elif score>=175: urgency,base,spread="MEDIUM",7,3
    elif score>=90: urgency,base,spread="LOW",3,2
    else: urgency,base,spread="WATCH",1,1
    recommended=min(25,base+(3 if primary_need_match else 0));low=max(0,recommended-spread);high=min(30,recommended+spread)
    if remaining_budget is None: budget=bid=bid_low=bid_high=None
    else:
        budget=int(remaining_budget)
        if budget<0: raise ValueError("remaining_budget must be non-negative")
        bid=round(budget*recommended/100);bid_low=round(budget*low/100);bid_high=round(budget*high/100)
    return {"urgency":urgency,"recommended_bid_pct":recommended,"bid_range_low_pct":low,"bid_range_high_pct":high,"remaining_budget":budget,"recommended_bid":bid,"bid_range_low":bid_low,"bid_range_high":bid_high,"faab_reason":f"{urgency} priority from waiver score {round(score,2)}"}

def waiver_candidates(trending_available,my_team,position_pressure,limit=10,remaining_budget=None):
    """Rank unowned Sleeper trending adds with existing need and pressure signals."""
    if not trending_available: return []
    team=my_team or {};needs=team.get("needs") or {};primary=str(team.get("primary_need") or "").upper();press=position_pressure or {};rows=[]
    for item in trending_available:
        pos=str(item.get("position") or "").upper()
        if pos not in CORE: continue
        trend=int(item.get("count") or 0);need=int(needs.get(pos) or 0);pressure_score=int(press.get(pos) or 0);primary_match=bool(primary and pos==primary)
        primary_need_bonus=50 if primary_match else 0
        reasons=[]
        if primary_match: reasons.append(f"{pos} is the primary roster need")
        elif need: reasons.append(f"{pos} depth is {need} below target")
        if trend: reasons.append(f"{trend} recent trending adds")
        if pressure_score: reasons.append(f"league pressure score {pressure_score}")
        waiver_score=trend+need*25+pressure_score*5+primary_need_bonus
        faab=estimate_faab(waiver_score,trend,primary_match,pressure_score,remaining_budget)
        rows.append({**item,"position":pos,"trend_count":trend,"need_score":need,"pressure_score":pressure_score,"primary_need_match":primary_match,"primary_need_bonus":primary_need_bonus,"waiver_score":waiver_score,"reason":"; ".join(reasons) or "Available Sleeper trending player",**faab})
    return sorted(rows,key=lambda x:(x["waiver_score"],x["trend_count"],x["name"]),reverse=True)[:limit]

def _bench_player(row):
    """Normalize app.py my_roster rows: id, player_name, position, slot."""
    if not isinstance(row,(list,tuple)) or len(row)<3: return None
    return {"roster_id":row[0],"player_name":row[1],"position":str(row[2] or "").upper(),"slot":row[3] if len(row)>3 else ""}


def identify_drop_candidates(bench,position_counts,need_scores,limit=10):
    """Rank only supplied bench rows; starters are never inferred."""
    counts=position_counts or {};needs=need_scores or {};rows=[]
    for raw in bench or []:
        player=_bench_player(raw)
        if not player or not player["player_name"] or player["position"] not in CORE: continue
        pos=player["position"];count=int(counts.get(pos) or 0);need=int(needs.get(pos) or 0);target=int(DEPTH_TARGETS.get(pos) or 0);surplus=max(0,count-target)
        score=surplus*40+(50 if need==0 else 0)-need
        reasons=["bench player"]
        if surplus: reasons.append(f"{pos} is {surplus} above depth target")
        if need==0: reasons.append(f"{pos} has no current roster need")
        else: reasons.append(f"{pos} need score {need} reduces drop priority")
        rows.append({**player,"surplus_depth":surplus,"need_score":need,"drop_score":score,"reason":"; ".join(reasons)})
    return sorted(rows,key=lambda x:(x["drop_score"],x["surplus_depth"],x["player_name"]),reverse=True)[:limit]


def build_waiver_action_plans(waiver_candidates,bench,position_counts,need_scores,limit=5):
    """Pair ranked adds with distinct ranked bench drops."""
    adds=[dict(x) for x in (waiver_candidates or [])]
    if not adds: return []
    drops=identify_drop_candidates(bench,position_counts,need_scores,limit=max(limit,len(adds)));plans=[]
    for i,add in enumerate(adds[:limit]):
        drop=drops[i] if i<len(drops) else None;action="ADD_DROP" if drop else "ADD_ONLY";summary=f"Add {add.get('name') or add.get('player_id')}"
        if drop: summary+=f" and drop {drop['player_name']}"
        plans.append({"priority":i+1,"action":action,"add":add,"drop":drop,"recommended_bid_pct":add.get("recommended_bid_pct"),"recommended_bid":add.get("recommended_bid"),"urgency":add.get("urgency"),"summary":summary})
    return plans


def build_local_roster_context(roster):
    """Build bench, counts, and need scores from authoritative local roster rows."""
    rows=list(roster or [])
    slots,bench=build_roster_slots(rows)
    counts={position:0 for position in CORE}
    for row in rows:
        if isinstance(row,(list,tuple)) and len(row)>=3:
            position=str(row[2] or "").upper()
            if position in counts: counts[position]+=1
    need_scores={}
    needs={}
    for position,target in DEPTH_TARGETS.items():
        missing=max(0,target-counts[position]);needs[position]=missing
        need_scores[position]=int((missing/target)*100) if target else 0
    primary=max(CORE,key=lambda position:(need_scores[position],STARTER_TARGETS[position]-counts[position]))
    return {"slots":slots,"bench":bench,"position_counts":counts,"need_scores":need_scores,
        "team":{"manager":"My Team","counts":counts,"needs":needs,"primary_need":primary,"players":len(rows)}}


def build(cur,league_id,week,season=2026):
    users,_,_=_latest(cur,"users",league_id,season=season);rosters,_,_=_latest(cur,"rosters",league_id,season=season);players=_players(cur,league_id,season)
    cur.execute("SELECT id,player_name,position,COALESCE(slot,'') FROM my_roster WHERE player_name IS NOT NULL AND BTRIM(player_name)<>'' ORDER BY drafted_at,id")
    local_roster=cur.fetchall();local_context=build_local_roster_context(local_roster)
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
    pressure_map=pressure(active);trending_available=available_trending(trends or [],rosters or [],players)
    candidate_rows=waiver_candidates(trending_available,local_context["team"],pressure_map)
    action_plans=build_waiver_action_plans(candidate_rows,local_context["bench"],local_context["position_counts"],local_context["need_scores"])
    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure_map,"recent_picks":recent,"position_run_counts":run_counts,"trending_available":trending_available,"waiver_candidates":candidate_rows,"waiver_action_plans":action_plans,"local_roster_context":{"position_counts":local_context["position_counts"],"need_scores":local_context["need_scores"],"bench_count":len(local_context["bench"])},"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}
