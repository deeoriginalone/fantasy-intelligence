from __future__ import annotations
import argparse,json
from datetime import datetime
from psycopg2.extras import Json,RealDictCursor
from pickem_pg_store import connect,seed_from_schedule
from providers.the_odds_api import TheOddsAPI
from market_intelligence import build_week,summarize,MODEL_VERSION,no_vig_home

def migrate(conn):
    from pathlib import Path
    with conn.cursor() as c:c.execute((Path(__file__).parent/'migrations/006_market_intelligence.sql').read_text())
    conn.commit()
def current_week(conn):
    with conn.cursor() as c:c.execute("SELECT state_value FROM application_state WHERE state_key='current_week'"); r=c.fetchone(); return int(r[0].get('week',1)) if r and r[0] else 1
def run(season,week,strategy='balanced',dry_run=False):
    seed_from_schedule(season,week); conn=connect(); migrate(conn); errors=[]
    with conn.cursor() as c:c.execute("INSERT INTO market_intelligence_runs(season,week) VALUES(%s,%s) RETURNING id",(season,week)); rid=c.fetchone()[0]
    conn.commit()
    try:
        games,usage=TheOddsAPI().fetch_nfl(); matched=0
        with conn.cursor() as c:
            for g in games:
                try:
                    away_ml = float(g.away_moneyline)
                    home_ml = float(g.home_moneyline)
                    if abs(away_ml) < 50 or abs(home_ml) < 50:
                        raise ValueError(
                            f"Invalid moneyline {g.away_team}@{g.home_team}: "
                            f"{g.away_moneyline}/{g.home_moneyline}"
                        )
                    prob=no_vig_home(away_ml,home_ml)
                    c.execute('''UPDATE yahoo_pickem_games SET away_moneyline=%s,home_moneyline=%s,market_home_probability=%s,projected_total=%s,market_source=%s,market_updated_at=NOW(),source_updated_at=NOW(),updated_at=NOW() WHERE season=%s AND week=%s AND away_team=%s AND home_team=%s''',(g.away_moneyline,g.home_moneyline,prob,g.projected_total,g.source,season,week,g.away_team,g.home_team))
                    if c.rowcount==1: matched+=1
                except Exception as e: errors.append({'game':f'{g.away_team}@{g.home_team}','error':str(e)})
        if dry_run or errors: conn.rollback()
        else: conn.commit()
        predictions=[]
        if not dry_run and not errors:
            with conn.cursor(cursor_factory=RealDictCursor) as c:
                c.execute('SELECT * FROM yahoo_pickem_games WHERE season=%s AND week=%s AND market_home_probability IS NOT NULL ORDER BY kickoff',(season,week)); rows=[dict(x) for x in c.fetchall()]
            predictions=build_week(rows,strategy)
            with conn.cursor() as c:
                for p in predictions:
                    explanation={'market':p['market_home_probability'],'elo':p['elo_home_probability'],'situation':p['situation_home_probability']}
                    c.execute('''INSERT INTO market_intelligence_predictions(game_id,model_version,strategy,model_pick,model_probability,market_home_probability,elo_home_probability,situation_home_probability,confidence_points,expected_correct_value,signal,explanation) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(game_id,model_version,strategy) DO UPDATE SET model_pick=EXCLUDED.model_pick,model_probability=EXCLUDED.model_probability,market_home_probability=EXCLUDED.market_home_probability,elo_home_probability=EXCLUDED.elo_home_probability,situation_home_probability=EXCLUDED.situation_home_probability,confidence_points=EXCLUDED.confidence_points,expected_correct_value=EXCLUDED.expected_correct_value,signal=EXCLUDED.signal,explanation=EXCLUDED.explanation,generated_at=NOW()''',(p['game_id'],MODEL_VERSION,strategy,p['model_pick'],p['model_probability'],p['market_home_probability'],p['elo_home_probability'],p['situation_home_probability'],p['confidence_points'],p['expected_correct_value'],p['signal'],Json(explanation)))
            conn.commit()
        status='dry-run' if dry_run else ('failed' if errors else 'success')
        with conn.cursor() as c:c.execute('''UPDATE market_intelligence_runs SET finished_at=NOW(),status=%s,request_cost=%s,requests_remaining=%s,games_received=%s,games_matched=%s,predictions_written=%s,errors=%s,details=%s WHERE id=%s''',(status,usage.get('last'),usage.get('remaining'),len(games),0 if dry_run else matched,len(predictions),Json(errors),Json({'strategy':strategy}),rid))
        conn.commit(); return {'run_id':rid,'status':status,'games_received':len(games),'games_matched':0 if dry_run else matched,'predictions':len(predictions),'usage':usage,'errors':errors}
    except Exception as e:
        conn.rollback(); errors.append({'feed':str(e)})
        with conn.cursor() as c:c.execute('UPDATE market_intelligence_runs SET finished_at=NOW(),status=%s,errors=%s WHERE id=%s',('failed',Json(errors),rid))
        conn.commit(); return {'run_id':rid,'status':'failed','errors':errors}
    finally:conn.close()
def main():
    p=argparse.ArgumentParser();p.add_argument('--season',type=int,default=2026);p.add_argument('--week',type=int);p.add_argument('--strategy',default='balanced');p.add_argument('--dry-run',action='store_true');a=p.parse_args();c=connect();w=a.week or current_week(c);c.close();result=run(a.season,w,a.strategy,a.dry_run);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status'] in ('success','dry-run') else 1)
if __name__=='__main__':main()
