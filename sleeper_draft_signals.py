from collections import Counter, defaultdict
CORE=('QB','RB','WR','TE');TARGET={'QB':1,'RB':4,'WR':5,'TE':2}
def snap(cur,resource,key,season):
 cur.execute('SELECT payload FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s AND season=%s ORDER BY fetched_at DESC LIMIT 1',(resource,str(key),season));r=cur.fetchone();return r[0] if r else None
def snake_slot(p,teams):
 rnd=(p-1)//teams+1;inside=(p-1)%teams+1;return teams-inside+1 if rnd%2==0 else inside
def next_pick(current,teams,slot,rounds):
 return next((p for p in range(current+1,teams*rounds+1) if snake_slot(p,teams)==slot),None)
def build_sleeper_draft_signals(cur,league_id,season=2026,user_slot=5):
 users=snap(cur,'users',league_id,season) or [];players=snap(cur,'players',league_id,season) or {};drafts=snap(cur,'drafts',league_id,season) or [];draft=(drafts[0] if isinstance(drafts,list) and drafts else drafts) or {};did=str(draft.get('draft_id') or '');picks=snap(cur,'draft_picks',did,season) or []
 settings=draft.get('settings') or {};teams=int(settings.get('teams') or 10);rounds=int(settings.get('rounds') or 14);names={str(u.get('user_id')):u.get('metadata',{}).get('team_name') or u.get('display_name') for u in users};slots={int(v):names.get(str(k),str(k)) for k,v in (draft.get('draft_order') or {}).items()};counts=defaultdict(Counter);totals=Counter();recent=[]
 for x in sorted(picks,key=lambda z:int(z.get('pick_no') or 0)):
  pno=int(x.get('pick_no') or 0);slot=int(x.get('draft_slot') or snake_slot(pno,teams));meta=x.get('metadata') or {};pid=str(x.get('player_id') or meta.get('player_id') or '');pos=str(meta.get('position') or players.get(pid,{}).get('position') or '').upper();name=((meta.get('first_name') or '')+' '+(meta.get('last_name') or '')).strip() or players.get(pid,{}).get('full_name') or pid
  if pos in CORE:counts[slot][pos]+=1;totals[pos]+=1
  recent.append({'pick_no':pno,'manager':slots.get(slot,f'Slot {slot}'),'player':name,'position':pos})
 current=max([int(x.get('pick_no') or 0) for x in picks] or [0]);nxt=next_pick(current,teams,user_slot,rounds);before=[]
 for pno in range(current+1,nxt or current+1):
  slot=snake_slot(pno,teams);c=counts[slot];needs={p:max(0,TARGET[p]-c[p]) for p in CORE};before.append({'pick_no':pno,'manager':slots.get(slot,f'Slot {slot}'),'primary_need':max(CORE,key=lambda p:(needs[p],-c[p])),'needs':needs})
 pressure=Counter();[pressure.update(x['needs']) for x in before];peak=max(pressure.values() or [0]);risk={p:(round(100*pressure[p]/peak) if peak else 0) for p in CORE}
 return {'available':bool(did),'draft_id':did,'draft_status':draft.get('status') or 'unknown','user_slot':user_slot,'pick_count':len(picks),'next_pick':nxt,'picks_until_next':(nxt-current-1 if nxt else None),'teams_before_next':before,'position_pressure':{p:pressure[p] for p in CORE},'position_risk_pct':risk,'position_totals':{p:totals[p] for p in CORE},'highest_risk_position':max(CORE,key=lambda p:risk[p]) if before else None,'recent_picks':recent[-10:]}
