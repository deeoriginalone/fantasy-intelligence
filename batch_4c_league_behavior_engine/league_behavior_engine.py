"""Batch 4C League Behavior Engine.

Derives room profiles, owner tendencies, position runs, and pressure snapshots
from actual Sleeper draft picks plus the existing opponent forecast. It never
creates synthetic picks and returns INSUFFICIENT_DATA when observations do not
support a behavior claim.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from statistics import mean
import json
from flask import Blueprint, jsonify, request

CORE=("QB","RB","WR","TE")
ROOM_TYPES=("INSUFFICIENT_DATA","BALANCED","RB_HEAVY","WR_HEAVY","EARLY_QB","TE_AGGRESSIVE")

def _int(value, default=0):
    try:return int(value)
    except (TypeError,ValueError):return default

def _position(pick):
    return str(((pick or {}).get("metadata") or {}).get("position") or (pick or {}).get("position") or "").upper()

def _pick_no(pick):return _int((pick or {}).get("pick_no") or (pick or {}).get("pick_number"))
def _round(pick):return _int((pick or {}).get("round") or (pick or {}).get("round_num"))

def classify_room(counts,total):
    """Classify only observed offensive picks. Fewer than 10 is insufficient."""
    total=_int(total)
    if total<10:return "INSUFFICIENT_DATA"
    rates={p:100*float((counts or {}).get(p,0))/total for p in CORE}
    if rates["RB"]>=40:return "RB_HEAVY"
    if rates["WR"]>=40:return "WR_HEAVY"
    if rates["QB"]>=20:return "EARLY_QB"
    if rates["TE"]>=15:return "TE_AGGRESSIVE"
    return "BALANCED"

def confidence_for(total):
    total=_int(total)
    if total<=0:return 0.0
    return round(min(100.0,total/30*100),2)

def room_profile(picks):
    ordered=sorted((p for p in (picks or []) if _position(p) in CORE),key=_pick_no)
    counts=Counter(_position(p) for p in ordered);total=len(ordered)
    rates={p:round(100*counts[p]/total,2) if total else 0.0 for p in CORE}
    return {"room_type":classify_room(counts,total),"counts":dict(counts),"rates":rates,"total_observations":total,"confidence":confidence_for(total),"analysis_pick_count":max((_pick_no(p) for p in ordered),default=0),"sample_status":"NO DATA" if total==0 else "EARLY SAMPLE" if total<10 else "DEVELOPING" if total<30 else "ESTABLISHED"}

def detect_runs(picks,min_length=2):
    ordered=sorted((p for p in (picks or []) if _position(p) in CORE and _pick_no(p)>0),key=_pick_no)
    runs=[];current=[];last_no=None;last_pos=None
    def flush(active=False):
        if len(current)>=min_length:
            runs.append({"position":last_pos,"start_pick":_pick_no(current[0]),"end_pick":_pick_no(current[-1]),"run_length":len(current),"active":active})
    for pick in ordered:
        no=_pick_no(pick);pos=_position(pick)
        if current and pos==last_pos and no==last_no+1:current.append(pick)
        else:
            flush(False);current=[pick]
        last_no=no;last_pos=pos
    flush(True)
    return runs

def owner_histories(picks,rosters,users,draft):
    users_by={str(u.get("user_id")):u for u in users or []}
    roster_info={}
    for r in rosters or []:
        rid=_int(r.get("roster_id"));uid=str(r.get("owner_id") or "");u=users_by.get(uid,{})
        md=u.get("metadata") or {};roster_info[rid]={"owner_id":uid or f"roster:{rid}","owner_name":md.get("team_name") or u.get("display_name") or f"Roster {rid}"}
    slot_by={_int(rid):_int(slot) for slot,rid in ((draft or {}).get("slot_to_roster_id") or {}).items()}
    rows=[]
    for p in sorted(picks or [],key=_pick_no):
        pos=_position(p);rid=_int(p.get("roster_id"))
        if pos not in CORE or rid not in roster_info:continue
        md=p.get("metadata") or {};name=" ".join(x for x in [md.get("first_name"),md.get("last_name")] if x).strip() or str(p.get("player_name") or p.get("player_id") or "")
        rows.append({**roster_info[rid],"roster_id":rid,"draft_slot":slot_by.get(rid),"pick_number":_pick_no(p),"round":_round(p),"player_name":name,"position":pos})
    return rows

def owner_tendencies(history):
    grouped=defaultdict(list)
    for row in history or []:grouped[(row["owner_id"],row["owner_name"],row.get("draft_slot"))].append(row)
    out=[]
    for (oid,oname,slot),rows in grouped.items():
        counts=Counter(r["position"] for r in rows);n=len(rows);rates={p:round(100*counts[p]/n,2) for p in CORE}
        avgs={p:(round(mean(r["round"] for r in rows if r["position"]==p),2) if counts[p] else None) for p in CORE}
        strategy="INSUFFICIENT_DATA" if n<3 else max(CORE,key=lambda p:(counts[p],-CORE.index(p)))+"_LEAN"
        out.append({"owner_id":oid,"owner_name":oname,"draft_slot":slot,"observations":n,"counts":dict(counts),"rates":rates,"average_rounds":avgs,"preferred_strategy":strategy,"confidence":round(min(100,n/8*100),2)})
    return sorted(out,key=lambda x:(x.get("draft_slot") is None,x.get("draft_slot") or 999,x["owner_id"]))

def pressure_snapshot(forecast):
    f=forecast or {};pressure=f.get("position_pressure") or {};need=f.get("teams_needing_position") or {};gone=f.get("projected_gone") or {}
    return {"pick_count":_int(f.get("pick_count") or f.get("current_pick")),"next_pick":f.get("next_pick"),"position_pressure":{p:_int(pressure.get(p)) for p in CORE},"teams_needing_position":{p:_int(need.get(p)) for p in CORE},"projected_gone":{p:_int(gone.get(p)) for p in CORE},"source":f.get("source") or "existing_opponent_forecast","pre_draft_caution":bool(f.get("pre_draft_caution"))}

def build_behavior(picks,rosters,users,draft,forecast):
    profile=room_profile(picks);history=owner_histories(picks,rosters,users,draft);runs=detect_runs(picks);owners=owner_tendencies(history);snap=pressure_snapshot(forecast)
    current_run=runs[-1] if runs and runs[-1]["active"] else None
    return {"profile":profile,"current_run":current_run,"runs":runs,"owners":owners,"owner_pick_history":history,"pressure":snap,"data_sufficient":profile["room_type"]!="INSUFFICIENT_DATA","canonical_score_unchanged":True}

def ensure_tables(c):
    c.execute("CREATE TABLE IF NOT EXISTS league_behavior_profiles(id bigserial primary key,league_id varchar(50) not null,draft_id varchar(50) not null,pick_count integer not null,room_type varchar(30) not null,rb_rate numeric(6,2) not null,wr_rate numeric(6,2) not null,qb_rate numeric(6,2) not null,te_rate numeric(6,2) not null,confidence numeric(6,2) not null,total_observations integer not null,payload jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count))")
    c.execute("CREATE TABLE IF NOT EXISTS owner_tendencies(id bigserial primary key,league_id varchar(50) not null,draft_id varchar(50) not null,pick_count integer not null,owner_id varchar(50) not null,owner_name text,draft_slot integer,preferred_strategy varchar(50) not null,confidence numeric(6,2) not null,observations integer not null,payload jsonb not null default '{}'::jsonb,updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count,owner_id))")
    c.execute("CREATE TABLE IF NOT EXISTS position_run_history(id bigserial primary key,league_id varchar(50) not null,draft_id varchar(50) not null,snapshot_pick_count integer not null,position varchar(10) not null,start_pick integer not null,end_pick integer not null,run_length integer not null,active boolean not null,created_at timestamptz not null default now(),UNIQUE(draft_id,snapshot_pick_count,position,start_pick,end_pick))")
    c.execute("CREATE TABLE IF NOT EXISTS owner_pick_history(id bigserial primary key,league_id varchar(50) not null,draft_id varchar(50) not null,owner_id varchar(50) not null,owner_name text,roster_id integer,draft_slot integer,pick_number integer not null,round_num integer,player_name text not null,position varchar(10) not null,created_at timestamptz not null default now(),UNIQUE(draft_id,pick_number))")
    c.execute("CREATE TABLE IF NOT EXISTS league_pressure_snapshots(id bigserial primary key,league_id varchar(50) not null,draft_id varchar(50) not null,pick_count integer not null,next_pick integer,position_pressure jsonb not null default '{}'::jsonb,teams_needing_position jsonb not null default '{}'::jsonb,projected_gone jsonb not null default '{}'::jsonb,source varchar(50),pre_draft_caution boolean not null default false,payload jsonb not null default '{}'::jsonb,created_at timestamptz not null default now(),updated_at timestamptz not null default now(),UNIQUE(draft_id,pick_count))")

def persist(db,league_id,draft_id,data):
    cn=db();c=cn.cursor();profile=data["profile"];pc=profile["analysis_pick_count"]
    try:
        ensure_tables(c)
        rates=profile["rates"]
        c.execute("INSERT INTO league_behavior_profiles(league_id,draft_id,pick_count,room_type,rb_rate,wr_rate,qb_rate,te_rate,confidence,total_observations,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(draft_id,pick_count) DO UPDATE SET room_type=excluded.room_type,rb_rate=excluded.rb_rate,wr_rate=excluded.wr_rate,qb_rate=excluded.qb_rate,te_rate=excluded.te_rate,confidence=excluded.confidence,total_observations=excluded.total_observations,payload=excluded.payload,updated_at=now() RETURNING id",(str(league_id),str(draft_id),pc,profile["room_type"],rates["RB"],rates["WR"],rates["QB"],rates["TE"],profile["confidence"],profile["total_observations"],json.dumps(profile)));profile_id=c.fetchone()[0]
        c.execute("DELETE FROM owner_tendencies WHERE draft_id=%s AND pick_count=%s",(str(draft_id),pc))
        for x in data["owners"]:c.execute("INSERT INTO owner_tendencies(league_id,draft_id,pick_count,owner_id,owner_name,draft_slot,preferred_strategy,confidence,observations,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",(str(league_id),str(draft_id),pc,x["owner_id"],x["owner_name"],x.get("draft_slot"),x["preferred_strategy"],x["confidence"],x["observations"],json.dumps(x)))
        for x in data["owner_pick_history"]:c.execute("INSERT INTO owner_pick_history(league_id,draft_id,owner_id,owner_name,roster_id,draft_slot,pick_number,round_num,player_name,position) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(draft_id,pick_number) DO UPDATE SET owner_id=excluded.owner_id,owner_name=excluded.owner_name,roster_id=excluded.roster_id,draft_slot=excluded.draft_slot,round_num=excluded.round_num,player_name=excluded.player_name,position=excluded.position",(str(league_id),str(draft_id),x["owner_id"],x["owner_name"],x["roster_id"],x.get("draft_slot"),x["pick_number"],x["round"],x["player_name"],x["position"]))
        c.execute("DELETE FROM position_run_history WHERE draft_id=%s AND snapshot_pick_count=%s",(str(draft_id),pc))
        for x in data["runs"]:c.execute("INSERT INTO position_run_history(league_id,draft_id,snapshot_pick_count,position,start_pick,end_pick,run_length,active) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(str(league_id),str(draft_id),pc,x["position"],x["start_pick"],x["end_pick"],x["run_length"],x["active"]))
        p=data["pressure"];c.execute("INSERT INTO league_pressure_snapshots(league_id,draft_id,pick_count,next_pick,position_pressure,teams_needing_position,projected_gone,source,pre_draft_caution,payload) VALUES(%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s::jsonb) ON CONFLICT(draft_id,pick_count) DO UPDATE SET next_pick=excluded.next_pick,position_pressure=excluded.position_pressure,teams_needing_position=excluded.teams_needing_position,projected_gone=excluded.projected_gone,source=excluded.source,pre_draft_caution=excluded.pre_draft_caution,payload=excluded.payload,updated_at=now()",(str(league_id),str(draft_id),pc,p.get("next_pick"),json.dumps(p["position_pressure"]),json.dumps(p["teams_needing_position"]),json.dumps(p["projected_gone"]),p.get("source"),p.get("pre_draft_caution"),json.dumps(p)))
        cn.commit();return profile_id
    except Exception:cn.rollback();raise
    finally:c.close();cn.close()

def create_blueprint(db,league_id,draft_id):
    bp=Blueprint("league_behavior",__name__,url_prefix="/league-behavior")
    def query(sql,args=()):
        cn=db();c=cn.cursor();ensure_tables(c);cn.commit();c.execute(sql,args);rows=c.fetchall();c.close();cn.close();return rows
    @bp.get("/profile")
    def profile():
        r=query("SELECT id,payload,created_at,updated_at FROM league_behavior_profiles WHERE draft_id=%s ORDER BY pick_count DESC,updated_at DESC LIMIT 1",(str(draft_id),));return jsonify({"available":False,"reason":"No behavior profile has been persisted"} if not r else {"available":True,"profile_id":r[0][0],**r[0][1],"created_at":r[0][2],"updated_at":r[0][3]})
    @bp.get("/runs")
    def runs():
        rows=query("SELECT position,start_pick,end_pick,run_length,active,created_at FROM position_run_history WHERE draft_id=%s ORDER BY snapshot_pick_count DESC,start_pick DESC LIMIT 50",(str(draft_id),));return jsonify([{"position":r[0],"start_pick":r[1],"end_pick":r[2],"run_length":r[3],"active":r[4],"created_at":r[5]} for r in rows])
    @bp.get("/owners")
    def owners():
        rows=query("SELECT owner_id,owner_name,draft_slot,preferred_strategy,confidence,observations,payload,updated_at FROM owner_tendencies WHERE draft_id=%s ORDER BY pick_count DESC,draft_slot NULLS LAST LIMIT 100",(str(draft_id),));return jsonify([{"owner_id":r[0],"owner_name":r[1],"draft_slot":r[2],"preferred_strategy":r[3],"confidence":r[4],"observations":r[5],"details":r[6],"updated_at":r[7]} for r in rows])
    @bp.get("/latest")
    def latest():
        profile_rows=query("SELECT payload FROM league_behavior_profiles WHERE draft_id=%s ORDER BY pick_count DESC LIMIT 1",(str(draft_id),));pressure_rows=query("SELECT payload FROM league_pressure_snapshots WHERE draft_id=%s ORDER BY pick_count DESC LIMIT 1",(str(draft_id),));return jsonify({"profile":profile_rows[0][0] if profile_rows else None,"pressure":pressure_rows[0][0] if pressure_rows else None})
    return bp
