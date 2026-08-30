"""Persist Sleeper snapshots. Import and call sync_sleeper_data(get_db_connection,...)."""
from __future__ import annotations
import json
from services.sleeper_full_service import (
 get_league,get_league_users,get_league_rosters,get_matchups,get_transactions,
 get_traded_picks,get_league_drafts,get_sport_state,get_trending_players,
 get_winners_bracket,get_losers_bracket,SleeperAPIError
)

def _upsert(cur, kind, key, payload, season=None, week=None):
    cur.execute("""INSERT INTO sleeper_api_snapshots(resource_type,resource_key,season,week,payload,fetched_at)
    VALUES(%s,%s,%s,%s,%s::jsonb,NOW())
    ON CONFLICT(resource_type,resource_key,season,week)
    DO UPDATE SET payload=EXCLUDED.payload,fetched_at=NOW()""",
    (kind,str(key),season,week,json.dumps(payload)))

def sync_sleeper_data(get_db_connection, league_id, season, week, include_brackets=False):
    conn=get_db_connection(); cur=conn.cursor(); run_id=None; results={}
    try:
        cur.execute("""INSERT INTO sleeper_sync_runs(league_id,season,week,status)
        VALUES(%s,%s,%s,'running') RETURNING id""",(str(league_id),season,week)); run_id=cur.fetchone()[0]
        jobs={
          "league": lambda:get_league(league_id), "users":lambda:get_league_users(league_id),
          "rosters":lambda:get_league_rosters(league_id), "matchups":lambda:get_matchups(league_id,week),
          "transactions":lambda:get_transactions(league_id,week), "traded_picks":lambda:get_traded_picks(league_id),
          "drafts":lambda:get_league_drafts(league_id), "nfl_state":lambda:get_sport_state("nfl"),
          "trending_add":lambda:get_trending_players("add"), "trending_drop":lambda:get_trending_players("drop")}
        if include_brackets:
            jobs.update(winners_bracket=lambda:get_winners_bracket(league_id),losers_bracket=lambda:get_losers_bracket(league_id))
        for name,fn in jobs.items():
            try:
                payload=fn(); _upsert(cur,name,league_id,payload,season,week if name in {"matchups","transactions"} else None)
                results[name]={"ok":True,"count":len(payload) if isinstance(payload,(list,dict)) else 1}
            except SleeperAPIError as exc:
                results[name]={"ok":False,"error":str(exc)}
        status="success" if all(x["ok"] for x in results.values()) else "partial"
        cur.execute("UPDATE sleeper_sync_runs SET status=%s,resources=%s::jsonb,completed_at=NOW() WHERE id=%s",(status,json.dumps(results),run_id))
        conn.commit(); return {"run_id":run_id,"status":status,"resources":results}
    except Exception as exc:
        conn.rollback()
        if run_id:
            cur.execute("UPDATE sleeper_sync_runs SET status='failed',error_message=%s,completed_at=NOW() WHERE id=%s",(str(exc),run_id)); conn.commit()
        raise
    finally: cur.close(); conn.close()
