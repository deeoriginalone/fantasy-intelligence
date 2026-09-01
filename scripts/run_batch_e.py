#!/usr/bin/env python3
from pathlib import Path
import argparse,json
from batch_e_common import load_environment,connect,validation
import batch_e_market_bridge as market
import batch_e_ratings as ratings
import batch_e_injuries as injuries
import batch_e_weather as weather
def main():
 p=argparse.ArgumentParser();p.add_argument('--season',type=int,required=True);p.add_argument('--week',type=int,required=True);p.add_argument('--dry-run',action='store_true');p.add_argument('--only',choices=['market','ratings','injuries','weather']);a=p.parse_args();root=Path(__file__).resolve().parent;load_environment(root);conn=connect();out=[]
 try:
  for name,module in [('market',market),('ratings',ratings),('injuries',injuries),('weather',weather)]:
   if a.only and a.only!=name:continue
   try:out.append(module.run(conn,a.season,a.week,a.dry_run));conn.commit() if not a.dry_run else None
   except Exception as e:conn.rollback();out.append({'source':name,'status':'FAILED','error':str(e)})
  if not a.dry_run:validation(conn,a.season,a.week);conn.commit()
 finally:conn.close()
 print(json.dumps(out,indent=2,default=str));raise SystemExit(1 if any(x.get('status')=='FAILED' for x in out) else 0)
if __name__=='__main__':main()
