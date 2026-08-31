from flask import Blueprint, jsonify
import json

def validate_identity(league_id,draft_id,remote):
 remote=remote or {}; errors=[]
 if str(remote.get("draft_id") or "")!=str(draft_id): errors.append("Configured draft ID does not match Sleeper draft ID")
 if str(remote.get("league_id") or "")!=str(league_id): errors.append("Configured league ID does not match Sleeper draft league ID")
 return {"valid":not errors,"errors":errors,"draft_id":remote.get("draft_id"),"league_id":remote.get("league_id"),"season":remote.get("season"),"status":remote.get("status")}

def ensure_schema(cur):
 statements=[
 "CREATE TABLE IF NOT EXISTS draft_sessions (draft_id varchar(50) PRIMARY KEY,league_id varchar(50) NOT NULL,season varchar(10),status varchar(25),authoritative boolean NOT NULL DEFAULT false,last_validated_at timestamptz,created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now())",
 "CREATE UNIQUE INDEX IF NOT EXISTS draft_sessions_one_authoritative_uidx ON draft_sessions ((authoritative)) WHERE authoritative=true",
 "CREATE TABLE IF NOT EXISTS draft_sync_audit (id bigserial PRIMARY KEY,draft_id varchar(50) NOT NULL,league_id varchar(50) NOT NULL,status varchar(25) NOT NULL,received_count integer NOT NULL DEFAULT 0,stored_count integer NOT NULL DEFAULT 0,matched_count integer NOT NULL DEFAULT 0,quarantined_count integer NOT NULL DEFAULT 0,details jsonb NOT NULL DEFAULT '{}'::jsonb,created_at timestamptz NOT NULL DEFAULT now())",
 "CREATE TABLE IF NOT EXISTS draft_player_quarantine (id bigserial PRIMARY KEY,draft_id varchar(50) NOT NULL,pick_no integer,player_id varchar(50),sleeper_name text,normalized_name text,reason text NOT NULL,payload jsonb NOT NULL DEFAULT '{}'::jsonb,status varchar(25) NOT NULL DEFAULT 'OPEN',created_at timestamptz NOT NULL DEFAULT now(),resolved_at timestamptz)",
 "CREATE UNIQUE INDEX IF NOT EXISTS draft_player_quarantine_open_uidx ON draft_player_quarantine(draft_id,pick_no) WHERE status='OPEN' AND pick_no IS NOT NULL",
 "CREATE TABLE IF NOT EXISTS draft_mutation_history (id bigserial PRIMARY KEY,draft_id varchar(50) NOT NULL,action varchar(50) NOT NULL,player_name text,team_name text,source varchar(25) NOT NULL,before_state jsonb,after_state jsonb,metadata jsonb NOT NULL DEFAULT '{}'::jsonb,created_at timestamptz NOT NULL DEFAULT now())",
 "CREATE UNIQUE INDEX IF NOT EXISTS sleeper_draft_player_uidx ON sleeper_draft_picks(draft_id,player_id) WHERE player_id IS NOT NULL AND btrim(player_id)<>''",
 "CREATE UNIQUE INDEX IF NOT EXISTS my_roster_player_name_uidx ON my_roster(player_name) WHERE player_name IS NOT NULL AND btrim(player_name)<>''"]
 for s in statements: cur.execute(s)

def build_hardened_sync(original,db,get_draft,get_picks,league_id,draft_id):
 def run():
  remote=get_draft(draft_id) or {}; ident=validate_identity(league_id,draft_id,remote)
  if not ident['valid']: raise RuntimeError('; '.join(ident['errors']))
  conn=db();cur=conn.cursor()
  try:
   ensure_schema(cur);cur.execute("UPDATE draft_sessions SET authoritative=false WHERE authoritative=true AND draft_id<>%s",(str(draft_id),));cur.execute("INSERT INTO draft_sessions(draft_id,league_id,season,status,authoritative,last_validated_at) VALUES(%s,%s,%s,%s,true,now()) ON CONFLICT(draft_id) DO UPDATE SET league_id=excluded.league_id,season=excluded.season,status=excluded.status,authoritative=true,last_validated_at=now(),updated_at=now()",(str(draft_id),str(league_id),ident['season'],ident['status']));conn.commit()
  except Exception: conn.rollback();raise
  finally:cur.close();conn.close()
  result=original(); picks=get_picks(draft_id) or []; q=0;conn=db();cur=conn.cursor()
  try:
   ensure_schema(cur)
   for p in picks:
    pid=str(p.get('player_id') or '');cur.execute("SELECT local_player_name,matched,sleeper_name,normalized_name FROM sleeper_player_map WHERE sleeper_player_id=%s",(pid,));row=cur.fetchone()
    if row and row[0] and row[1]: continue
    meta=p.get('metadata') or {};name=' '.join(x for x in [meta.get('first_name'),meta.get('last_name')] if x).strip() or (row[2] if row else pid)
    cur.execute("INSERT INTO draft_player_quarantine(draft_id,pick_no,player_id,sleeper_name,normalized_name,reason,payload) VALUES(%s,%s,%s,%s,%s,'No verified local player match',%s::jsonb) ON CONFLICT (draft_id,pick_no) WHERE status='OPEN' AND pick_no IS NOT NULL DO UPDATE SET player_id=excluded.player_id,sleeper_name=excluded.sleeper_name,payload=excluded.payload",(str(draft_id),p.get('pick_no'),pid,name,row[3] if row else None,json.dumps(p)));q+=1
   cur.execute("INSERT INTO draft_sync_audit(draft_id,league_id,status,received_count,stored_count,matched_count,quarantined_count,details) VALUES(%s,%s,'SUCCESS',%s,%s,%s,%s,%s::jsonb)",(str(draft_id),str(league_id),result.get('received',0),result.get('stored',0),result.get('matched_to_rankings',0),q,json.dumps(ident)));conn.commit();result=dict(result);result.update(identity_valid=True,quarantined=q);return result
  except Exception:conn.rollback();raise
  finally:cur.close();conn.close()
 return run

def create_blueprint(db,get_draft,league_id,draft_id):
 bp=Blueprint('draft_state_hardening',__name__,url_prefix='/draft-hardening')
 @bp.get('/status')
 def status():
  ident=validate_identity(league_id,draft_id,get_draft(draft_id) or {});conn=db();cur=conn.cursor()
  try:
   ensure_schema(cur);conn.commit();cur.execute("SELECT draft_id,league_id,season,status,authoritative,last_validated_at FROM draft_sessions WHERE authoritative=true");session=cur.fetchone();cur.execute("SELECT count(*) FROM draft_player_quarantine WHERE draft_id=%s AND status='OPEN'",(str(draft_id),));q=cur.fetchone()[0]
  finally:cur.close();conn.close()
  return jsonify(identity=ident,authoritative_session=session,open_quarantine=q)
 return bp
