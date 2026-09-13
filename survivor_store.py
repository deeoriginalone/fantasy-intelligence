from __future__ import annotations
from pathlib import Path
from psycopg2.extras import RealDictCursor,Json
from datetime import datetime, date

class SurvivorConflictError(Exception):
    """Raised when a write would silently overwrite a different team already recorded for a season/week."""

class SurvivorHistoryReadError(Exception):
    """Raised when survivor history cannot be verified; callers must block eligibility, not assume empty history."""

def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


from pickem_pg_store import connect

def migrate():
    conn=connect()
    try:
        with conn.cursor() as cur: cur.execute((Path(__file__).parent/'migrations/007_survivor_intelligence.sql').read_text())
        conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()

def ensure_pool(pool_key='default',pool_name='My Survivor Pool',season=2026):
    conn=connect()
    try:
        with conn.cursor() as cur: cur.execute('''INSERT INTO survivor_pools(pool_key,pool_name,season) VALUES(%s,%s,%s) ON CONFLICT(pool_key) DO UPDATE SET pool_name=EXCLUDED.pool_name,season=EXCLUDED.season,updated_at=NOW()''',(pool_key,pool_name,season))
        conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()

def week_selection(pool_key,season,week):
    try:
        conn=connect()
    except Exception as e:
        raise SurvivorHistoryReadError(str(e)) from e
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM survivor_selections WHERE pool_key=%s AND season=%s AND week=%s',(pool_key,season,week))
            row=cur.fetchone();return dict(row) if row else None
    except Exception as e:
        raise SurvivorHistoryReadError(str(e)) from e
    finally:conn.close()

def delete_selection(pool_key,season,week,team):
    """Remove a recorded pick so the week reopens for a fresh recommendation. Requires the exact team to avoid deleting the wrong week's fact by mistake."""
    conn=connect()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM survivor_selections WHERE pool_key=%s AND season=%s AND week=%s AND team=%s',(pool_key,season,week,team))
            deleted=cur.rowcount
        conn.commit()
        return deleted
    except Exception:conn.rollback();raise
    finally:conn.close()
def used_teams(pool_key,season):
    try:
        conn=connect()
    except Exception as e:
        raise SurvivorHistoryReadError(str(e)) from e
    try:
        with conn.cursor() as cur:cur.execute("SELECT team FROM survivor_selections WHERE pool_key=%s AND season=%s AND status<>'void'",(pool_key,season));return [r[0] for r in cur.fetchall()]
    except Exception as e:
        raise SurvivorHistoryReadError(str(e)) from e
    finally:conn.close()
def current_predictions(season,week,strategy):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''SELECT p.*,g.season,g.week,g.away_team,g.home_team,g.kickoff,g.market_updated_at FROM market_intelligence_predictions p JOIN yahoo_pickem_games g USING(game_id) WHERE g.season=%s AND g.week=%s AND p.strategy=%s ORDER BY p.confidence_points DESC''',(season,week,strategy));return [dict(r) for r in cur.fetchall()]
    finally:conn.close()
def all_schedule(season):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:cur.execute('SELECT season,week,away_team,home_team FROM nfl_schedule WHERE season=%s ORDER BY week',(season,));return [dict(r) for r in cur.fetchall()]
    finally:conn.close()
def future_predictions(season,strategy):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''SELECT p.*,g.week,g.away_team,g.home_team FROM market_intelligence_predictions p JOIN yahoo_pickem_games g USING(game_id) WHERE g.season=%s AND p.strategy=%s''',(season,strategy));rows=[dict(r) for r in cur.fetchall()]
        return {(int(r['week']),r['away_team'],r['home_team']):r for r in rows}
    finally:conn.close()
def save_selection(pool_key,season,week,team,status,probability,score,notes=''):
    conn=connect()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT team FROM survivor_selections WHERE pool_key=%s AND season=%s AND week=%s',(pool_key,season,week))
            existing=cur.fetchone()
            if existing and existing[0]!=team:
                raise SurvivorConflictError(f'Week {week} already has a recorded selection ({existing[0]}); refusing to overwrite with {team}.')
            cur.execute('''INSERT INTO survivor_selections(pool_key,season,week,team,status,model_probability,survivor_score,notes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(pool_key,season,week) DO UPDATE SET team=EXCLUDED.team,status=EXCLUDED.status,model_probability=EXCLUDED.model_probability,survivor_score=EXCLUDED.survivor_score,notes=EXCLUDED.notes,updated_at=NOW()''',(pool_key,season,week,team,status,probability,score,notes))
        conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
def history(pool_key,season):
    conn=connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:cur.execute('SELECT * FROM survivor_selections WHERE pool_key=%s AND season=%s ORDER BY week',(pool_key,season));return [dict(r) for r in cur.fetchall()]
    finally:conn.close()
def save_run(pool_key,season,week,strategy,summary):
    conn=connect()
    try:
        primary=summary['primary']['team'] if summary.get('primary') else None
        with conn.cursor() as cur:cur.execute('INSERT INTO survivor_recommendation_runs(pool_key,season,week,strategy,primary_team,details) VALUES(%s,%s,%s,%s,%s,%s)',(pool_key,season,week,strategy,primary,Json(_json_safe(summary))))
        conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
