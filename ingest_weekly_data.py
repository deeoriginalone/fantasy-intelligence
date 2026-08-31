#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,os
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from ingestion_validation import validate_rows
from ingestion_store import persist,update_readiness

def load(path):
    if path.suffix.lower()=='.json':
        data=json.loads(path.read_text()); return data if isinstance(data,list) else data.get("records",[])
    with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def connect(url):
    import psycopg2
    return psycopg2.connect(url) if url else psycopg2.connect(host=os.getenv('DB_HOST','localhost'),port=os.getenv('DB_PORT','5432'),dbname=os.getenv('DB_NAME'),user=os.getenv('DB_USER'),password=os.getenv('DB_PASSWORD'))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True,choices=['schedule','market','crowd','ratings','situations','weather']); p.add_argument('--file',required=True); p.add_argument('--season',type=int,required=True); p.add_argument('--week',type=int,required=True); p.add_argument('--database-url',default=os.getenv('DATABASE_URL')); p.add_argument('--dry-run',action='store_true'); a=p.parse_args()
    path=Path(a.file); rows=load(path); good,bad=validate_rows(a.source,rows,a.season,a.week)
    report={"source":a.source,"file":str(path),"received":len(rows),"accepted":len(good),"rejected":len(bad),"rejections":bad}
    if bad: report["status"]="REJECTED"; print(json.dumps(report,indent=2)); raise SystemExit(2)
    if a.dry_run: report["status"]="VALIDATED"; print(json.dumps(report,indent=2)); return
    conn=connect(a.database_url)
    try: report["run_id"]=persist(conn,a.source,good,a.season,a.week,path.name); update_readiness(conn,a.season,a.week); report["status"]="LOADED"
    finally: conn.close()
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
