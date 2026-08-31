from __future__ import annotations
import json, os
from contextlib import contextmanager
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor, Json

from config import Config

MIGRATION = Path(__file__).with_name('migrations') / '004_yahoo_pickem_postgres.sql'

def connect():
    return psycopg2.connect(**Config.db_kwargs())

def migrate():
    conn=connect()
    try:
        with conn.cursor() as cur: cur.execute(MIGRATION.read_text())
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

def seed_from_schedule(season=2026, week=None):
    migrate(); conn=connect(); inserted=0
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql='SELECT season,week,home_team,away_team,game_time_pacific FROM nfl_schedule WHERE season=%s'
            params=[season]
            if week is not None: sql+=' AND week=%s'; params.append(week)
            sql+=' ORDER BY week,game_time_pacific'
            cur.execute(sql,params)
            for row in cur.fetchall():
                game_id=f"{row['season']}-w{row['week']}-{row['away_team'].lower()}-{row['home_team'].lower()}"
                cur.execute('''INSERT INTO yahoo_pickem_games(game_id,season,week,kickoff,away_team,home_team)
                    VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(game_id) DO NOTHING''',
                    (game_id,row['season'],row['week'],row['game_time_pacific'],row['away_team'],row['home_team']))
                inserted += cur.rowcount
        conn.commit(); return inserted
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

def list_complete_games(season,week):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''SELECT * FROM yahoo_pickem_games WHERE season=%s AND week=%s
                AND yahoo_away_pct IS NOT NULL AND yahoo_home_pct IS NOT NULL
                AND market_home_probability IS NOT NULL ORDER BY kickoff''',(season,week))
            return [dict(r) for r in cur.fetchall()]
    finally: conn.close()

def save_predictions(rows,model_version,strategy):
    if not rows: return
    conn=connect()
    try:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute('''INSERT INTO yahoo_pickem_predictions
                    (game_id,model_version,strategy,model_pick,model_probability,crowd_pick,crowd_percentage,
                     contrarian_edge,signal,confidence_points,expected_confidence_value,component_json)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(game_id,model_version,strategy) DO UPDATE SET
                    model_pick=EXCLUDED.model_pick,model_probability=EXCLUDED.model_probability,
                    crowd_pick=EXCLUDED.crowd_pick,crowd_percentage=EXCLUDED.crowd_percentage,
                    contrarian_edge=EXCLUDED.contrarian_edge,signal=EXCLUDED.signal,
                    confidence_points=EXCLUDED.confidence_points,
                    expected_confidence_value=EXCLUDED.expected_confidence_value,
                    component_json=EXCLUDED.component_json,generated_at=NOW()''',
                    (r['game_id'],model_version,strategy,r['model_pick'],r['pick_probability'],r['crowd_pick'],
                     r['crowd_percentage'],r['contrarian_edge'],r['signal'],r['confidence_points'],
                     r['expected_confidence_value'],Json(r,default=str)))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
