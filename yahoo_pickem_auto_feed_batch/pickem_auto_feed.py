from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from psycopg2.extras import Json
from pickem_pg_store import connect, seed_from_schedule
from pickem_pg_context import build_pickem_context
from providers.http_json import HTTPJSONCrowdProvider, HTTPJSONOddsProvider

def american_implied(odds):
    if odds==0: raise ValueError('moneyline cannot be zero')
    return 100/(odds+100) if odds>0 else abs(odds)/(abs(odds)+100)

def no_vig_home(away_ml,home_ml):
    a=american_implied(away_ml); h=american_implied(home_ml); return h/(a+h)

def validate_crowd(r):
    if not (0<=r.yahoo_away_pct<=1 and 0<=r.yahoo_home_pct<=1): raise ValueError('crowd percentages outside 0..1')
    if abs(r.yahoo_away_pct+r.yahoo_home_pct-1)>0.02: raise ValueError('crowd percentages must total approximately 1.0')

def migrate(conn):
    from pathlib import Path
    sql=(Path(__file__).parent/'migrations'/'005_pickem_feed_runs.sql').read_text()
    with conn.cursor() as cur: cur.execute(sql)
    conn.commit()

def current_week(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT state_value FROM application_state WHERE state_key='current_week'"); row=cur.fetchone()
        return int(row[0].get('week',1)) if row and row[0] else 1

def start_run(conn,season,week,provider):
    with conn.cursor() as cur:
        cur.execute('INSERT INTO pickem_feed_runs(season,week,provider) VALUES(%s,%s,%s) RETURNING id',(season,week,provider)); rid=cur.fetchone()[0]
    conn.commit(); return rid

def finish_run(conn,rid,status,received,updated,errors,details):
    with conn.cursor() as cur:
        cur.execute('''UPDATE pickem_feed_runs SET finished_at=NOW(),status=%s,games_received=%s,games_updated=%s,errors=%s,details=%s WHERE id=%s''',(status,received,updated,Json(errors),Json(details),rid))
    conn.commit()

def refresh(season,week,dry_run=False):
    seed_from_schedule(season,week)
    conn=connect(); migrate(conn); run_id=start_run(conn,season,week,'crowd+odds'); errors=[]; received=updated=0
    try:
        crowd=HTTPJSONCrowdProvider().fetch(season,week); odds=HTTPJSONOddsProvider().fetch(season,week); received=len(crowd)+len(odds)
        crowd_map={(r.away_team,r.home_team):r for r in crowd}; odds_map={(r.away_team,r.home_team):r for r in odds}
        keys=sorted(set(crowd_map)&set(odds_map))
        with conn.cursor() as cur:
            for key in keys:
                c=crowd_map[key]; o=odds_map[key]
                try:
                    validate_crowd(c); market=no_vig_home(o.away_moneyline,o.home_moneyline)
                    cur.execute('''UPDATE yahoo_pickem_games SET yahoo_away_pct=%s,yahoo_home_pct=%s,
                      away_moneyline=%s,home_moneyline=%s,market_home_probability=%s,projected_total=%s,
                      crowd_source=%s,market_source=%s,crowd_updated_at=NOW(),market_updated_at=NOW(),
                      source_updated_at=NOW(),updated_at=NOW()
                      WHERE season=%s AND week=%s AND away_team=%s AND home_team=%s''',
                      (c.yahoo_away_pct,c.yahoo_home_pct,o.away_moneyline,o.home_moneyline,market,o.projected_total,c.source,o.source,season,week,key[0],key[1]))
                    if cur.rowcount!=1: raise ValueError('schedule match not found')
                    updated+=1
                except Exception as exc: errors.append({'game':f'{key[0]}@{key[1]}','error':str(exc)})
        if dry_run: conn.rollback()
        elif errors: conn.rollback()
        else: conn.commit()
        status='dry-run' if dry_run else ('failed' if errors else 'success')
        details={'crowd_games':len(crowd),'odds_games':len(odds),'matched_games':len(keys)}
        finish_run(conn,run_id,status,received,0 if dry_run or errors else updated,errors,details)
        if not dry_run and not errors: build_pickem_context(season,week,'balanced')
        return {'run_id':run_id,'status':status,'received':received,'updated':0 if dry_run or errors else updated,'errors':errors,'details':details}
    except Exception as exc:
        conn.rollback(); errors.append({'feed':str(exc)}); finish_run(conn,run_id,'failed',received,0,errors,{}); return {'run_id':run_id,'status':'failed','received':received,'updated':0,'errors':errors}
    finally: conn.close()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--season',type=int,default=2026); p.add_argument('--week',type=int); p.add_argument('--dry-run',action='store_true'); a=p.parse_args()
    conn=connect(); week=a.week or current_week(conn); conn.close(); result=refresh(a.season,week,a.dry_run); print(json.dumps(result,indent=2)); raise SystemExit(0 if result['status'] in ('success','dry-run') else 1)
if __name__=='__main__': main()
