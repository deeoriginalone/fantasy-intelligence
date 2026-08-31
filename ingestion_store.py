from __future__ import annotations
import hashlib,json,uuid
from datetime import datetime,timezone

TABLES={"schedule":"fi_games_ingest","market":"fi_market_ingest","crowd":"fi_crowd_ingest","ratings":"fi_ratings_ingest","situations":"fi_situations_ingest","weather":"fi_weather_ingest"}

def fingerprint(record): return hashlib.sha256(json.dumps(record,sort_keys=True,default=str).encode()).hexdigest()

def persist(conn,source,records,season,week,file_name):
    run_id=str(uuid.uuid4()); cur=conn.cursor(); accepted=0
    try:
        cur.execute("INSERT INTO ingestion_runs(run_id,source_name,season,week,file_name,status,started_at) VALUES(%s,%s,%s,%s,%s,'RUNNING',NOW())",(run_id,source,season,week,file_name))
        for r in records:
            cur.execute("INSERT INTO ingestion_records(run_id,source_name,season,week,record_key,payload,ingested_at) VALUES(%s,%s,%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(source_name,season,week,record_key) DO UPDATE SET run_id=EXCLUDED.run_id,payload=EXCLUDED.payload,ingested_at=NOW()",(run_id,source,season,week,fingerprint(r),json.dumps(r,default=str)))
            accepted+=1
        cur.execute("UPDATE ingestion_runs SET status='SUCCEEDED',accepted_count=%s,finished_at=NOW() WHERE run_id=%s",(accepted,run_id)); conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: cur.close()
    return run_id

def update_readiness(conn,season,week):
    cur=conn.cursor()
    try:
        mapping={"schedule":"schedule","market":"market","ratings":"ratings","situations":"injuries","weather":"weather"}
        for source,component in mapping.items():
            cur.execute("SELECT COUNT(*) FROM ingestion_records WHERE source_name=%s AND season=%s AND week=%s",(source,season,week)); count=cur.fetchone()[0]
            score=1.0 if count>0 else 0.0
            cur.execute("INSERT INTO intelligence_readiness_components(season,week,component_name,component_score,blocker,warning,evaluated_at) VALUES(%s,%s,%s,%s,%s,NULL,NOW()) ON CONFLICT(season,week,component_name) DO UPDATE SET component_score=EXCLUDED.component_score,blocker=EXCLUDED.blocker,warning=NULL,evaluated_at=NOW()",(season,week,component,score,None if count else f"no {source} records loaded"))
        # Validation is only complete when all six source groups have records.
        cur.execute("SELECT COUNT(DISTINCT source_name) FROM ingestion_records WHERE season=%s AND week=%s",(season,week)); complete=cur.fetchone()[0]>=5
        cur.execute("INSERT INTO intelligence_readiness_components(season,week,component_name,component_score,blocker,warning,evaluated_at) VALUES(%s,%s,'validation',%s,%s,NULL,NOW()) ON CONFLICT(season,week,component_name) DO UPDATE SET component_score=EXCLUDED.component_score,blocker=EXCLUDED.blocker,evaluated_at=NOW()",(season,week,1.0 if complete else 0.0,None if complete else "not all required non-crowd source groups are loaded"))
        conn.commit()
    except Exception: conn.rollback(); raise
    finally: cur.close()
