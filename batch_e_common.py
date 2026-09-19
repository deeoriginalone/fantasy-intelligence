from __future__ import annotations
import hashlib,json,os,uuid
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

def load_environment(root):
 load_dotenv(Path(root)/'.env');load_dotenv(Path(root)/'.env.market')
def connect():
 return psycopg2.connect(host=os.getenv('DB_HOST'),port=int(os.getenv('DB_PORT','5432')),dbname=os.getenv('DB_NAME'),user=os.getenv('DB_USER'),password=os.getenv('DB_PASSWORD'))
def games(conn,season,week):
 sql='SELECT game_id,away_team,home_team,kickoff,away_moneyline,home_moneyline,market_home_probability,projected_total,market_source,market_updated_at FROM yahoo_pickem_games WHERE season=%s AND week=%s ORDER BY kickoff'
 with conn.cursor() as c:c.execute(sql,(season,week));names=[x[0] for x in c.description];return [dict(zip(names,r)) for r in c.fetchall()]
def canonical_schedule_games(conn,season,week):
 sql='SELECT season,week,match_number,game_time_utc,home_team,away_team FROM nfl_schedule WHERE season=%s AND week=%s ORDER BY game_time_utc,match_number'
 with conn.cursor() as c:
  c.execute(sql,(season,week)); rows=c.fetchall()
 return [{"season":row[0],"week":row[1],"game_id":f"{row[0]}-w{row[1]}-{row[5].lower()}-{row[4].lower()}","match_number":row[2],"scheduled_at":row[3],"home_team":row[4],"away_team":row[5]} for row in rows]
def fp(r):return hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest()
def store(conn,source,records,season,week,label):
 run=str(uuid.uuid4())
 with conn.cursor() as c:
  c.execute("INSERT INTO ingestion_runs(run_id,source_name,season,week,file_name,status,started_at) VALUES(%s,%s,%s,%s,%s,'RUNNING',NOW())",(run,source,season,week,label))
  for r in records:c.execute("INSERT INTO ingestion_records(run_id,source_name,season,week,record_key,payload,ingested_at) VALUES(%s,%s,%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(source_name,season,week,record_key) DO UPDATE SET run_id=EXCLUDED.run_id,payload=EXCLUDED.payload,ingested_at=NOW()",(run,source,season,week,fp(r),json.dumps(r,default=str)))
  c.execute("UPDATE ingestion_runs SET status='SUCCEEDED',accepted_count=%s,finished_at=NOW() WHERE run_id=%s",(len(records),run))
 conn.commit()
 return run
def ready(conn,season,week,name,score,blocker=None,warning=None):
 with conn.cursor() as c:c.execute("INSERT INTO intelligence_readiness_components(season,week,component_name,component_score,blocker,warning,evaluated_at) VALUES(%s,%s,%s,%s,%s,%s,NOW()) ON CONFLICT(season,week,component_name) DO UPDATE SET component_score=EXCLUDED.component_score,blocker=EXCLUDED.blocker,warning=EXCLUDED.warning,evaluated_at=NOW()",(season,week,name,max(0,min(1,float(score))),blocker,warning))
 conn.commit()
def validation(conn,season,week):
 required=['schedule','market','ratings','injuries','weather']
 with conn.cursor() as c:c.execute('SELECT component_name,component_score,blocker FROM intelligence_readiness_components WHERE season=%s AND week=%s',(season,week));rows={r[0]:(float(r[1]),r[2]) for r in c.fetchall()}
 ok=all(n in rows and rows[n][0]>=.999 and not rows[n][1] for n in required);ready(conn,season,week,'validation',1 if ok else 0,None if ok else 'not all required non-crowd source groups are complete')
