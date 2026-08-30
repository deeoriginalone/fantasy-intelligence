#!/usr/bin/env python3
import os,sys
from app import get_db_connection,SLEEPER_LEAGUE_ID
from sleeper_draft_signals import build_sleeper_draft_signals
from model_calibration import model_health
from draft_readiness import build_draft_readiness

def main():
 conn=get_db_connection();cur=conn.cursor()
 try:
  signals=build_sleeper_draft_signals(cur,SLEEPER_LEAGUE_ID,season=2026,user_slot=5);health=model_health(cur);ready=build_draft_readiness(cur,SLEEPER_LEAGUE_ID,2026,signals,health)
 finally:cur.close();conn.close()
 print('Draft status:',ready['status']);print('Readiness score:',ready['score']);print('Data mode:',ready['mode'])
 for name,item in ready['snapshots'].items():print(name,item['state'],item['age_seconds'])
 return 0 if ready['score']>=65 else 1
if __name__=='__main__':raise SystemExit(main())
