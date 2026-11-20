"""Sleeper snapshot persistence (sleeper_api_snapshots) and the explicit transaction-history refresh used by the Waivers FAAB market.

store_snapshot is the snapshot upsert shared with the Sleeper hub: one row per resource type, key, season and week, replaced with
the latest provider payload and stamped with fetched_at (retrieval time, never event time). refresh_transaction_history is the
only writer W5 adds; it runs explicitly (refresh_sleeper_transactions.py) and never during a page view. read_transaction_history
is read-only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

TRANSACTIONS_RESOURCE = "transactions"
REFRESH_SCOPE = "transaction_history"
SNAPSHOT_UPSERT = ("INSERT INTO sleeper_api_snapshots(resource_type,resource_key,season,week,payload,fetched_at) VALUES(%s,%s,%s,%s,%s::jsonb,NOW()) "
                   "ON CONFLICT(resource_type,resource_key,season,week) DO UPDATE SET payload=EXCLUDED.payload,fetched_at=NOW()")
SNAPSHOT_UPSERT_AT = ("INSERT INTO sleeper_api_snapshots(resource_type,resource_key,season,week,payload,fetched_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s) "
                      "ON CONFLICT(resource_type,resource_key,season,week) DO UPDATE SET payload=EXCLUDED.payload,fetched_at=EXCLUDED.fetched_at")
HISTORY_QUERY = ("SELECT week, payload, fetched_at, resource_key, season FROM sleeper_api_snapshots "
                 "WHERE resource_type = %s AND resource_key = %s AND season = %s ORDER BY week")
# Season 0 is an attempt that failed before the league's season was known; it still counts as the latest attempt.
LATEST_REFRESH_QUERY = ("SELECT id, status, resources, error_message, started_at, completed_at FROM sleeper_sync_runs "
                        "WHERE league_id = %s AND season IN (%s, 0) AND resources->>'scope' = %s ORDER BY id DESC LIMIT 1")


def store_snapshot(cur, kind, key, payload, season=0, week=0, fetched_at=None):
    """Upsert one snapshot. fetched_at defaults to the database time of the write; W5 passes the time each request was sent."""
    if fetched_at is None:
        cur.execute(SNAPSHOT_UPSERT, (kind, str(key), season, week, json.dumps(payload)))
    else:
        cur.execute(SNAPSHOT_UPSERT_AT, (kind, str(key), season, week, json.dumps(payload), fetched_at))


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


def refresh_transaction_history(conn, *, league_id: Any, season: int | None = None, get_league: Callable, get_transactions: Callable,
                                dry_run: bool = False, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict[str, Any]:
    """Retrieve each transaction week of the league's season once (read-only Sleeper GETs) and store every successful week.

    The league's current transaction week (settings.leg) bounds the weeks retrieved. A week that fails is reported by number and
    its previously stored snapshot is left untouched. Each week is stored with the time its request was sent, the earliest moment
    its response can describe. The run is recorded as running before the first request, so an interrupted refresh stays visible;
    successful weeks and the run outcome are then written in one database transaction, so a failed write changes nothing.
    """
    league_id = str(league_id or "").strip()
    result = {"league_id": league_id, "season": season, "status": "failed", "league_leg": None, "start_week": None, "weeks": {}, "requests": 0,
              "error": None, "run_id": None, "dry_run": dry_run, "failed_weeks": []}
    if not league_id:
        return {**result, "error": "No Sleeper league id is configured."}
    cur = conn.cursor() if not dry_run else None
    try:
        if not dry_run:
            cur.execute("INSERT INTO sleeper_sync_runs(league_id,season,week,status,resources) VALUES(%s,%s,%s,'running',%s::jsonb) RETURNING id",
                        (league_id, season or 0, 0, json.dumps({"scope": REFRESH_SCOPE})))
            result["run_id"] = cur.fetchone()[0]
            conn.commit()
        result["requests"] += 1
        try:
            league = get_league(league_id)
        except Exception as exc:
            league, result["error"] = None, f"League: {_error(exc)}"
        settings = (league or {}).get("settings") if isinstance(league, dict) else None
        leg, start = _int((settings or {}).get("leg")), _int((settings or {}).get("start_week"))
        try:
            league_season = int((league or {}).get("season"))
        except (TypeError, ValueError):
            league_season = None
        if result["error"] is None:
            if league_season is None or leg is None or start is None or leg < 1 or start < 1:
                result["error"] = "League: Sleeper did not return a usable season, current transaction week (settings.leg) and start week."
            elif season is not None and int(season) != league_season:
                result["error"] = f"League: the league's season is {league_season}, not {season}."
            elif str(league.get("league_id") or league_id) != league_id:
                result["error"] = "League: Sleeper returned a different league."
        result.update(season=season if season is not None else league_season, league_leg=leg, start_week=start)
        payloads, requested = {}, {}
        if result["error"] is None:
            for week in range(start, leg + 1):
                result["requests"] += 1
                requested[week] = now()
                try:
                    payload = get_transactions(league_id, week)
                except Exception as exc:
                    result["weeks"][week] = {"ok": False, "error": _error(exc)}
                    continue
                if not isinstance(payload, list):
                    result["weeks"][week] = {"ok": False, "error": f"Sleeper returned {type(payload).__name__}, not a transaction list."}
                    continue
                payloads[week] = payload
                result["weeks"][week] = {"ok": True, "count": len(payload), "requested_at": requested[week].isoformat()}
        failures = [f"Week {week}: {entry['error']}" for week, entry in result["weeks"].items() if not entry["ok"]]
        result["status"] = "success" if payloads and not failures else "partial" if payloads else "failed"
        result["error"] = result["error"] or (failures[0] if failures else None)
        result["failed_weeks"] = [week for week, entry in result["weeks"].items() if not entry["ok"]]
        if dry_run:
            return result
        for week, payload in payloads.items():
            store_snapshot(cur, TRANSACTIONS_RESOURCE, league_id, payload, result["season"], week, fetched_at=requested[week])
        resources = {"scope": REFRESH_SCOPE, "league_leg": leg, "start_week": start, "requests": result["requests"],
                     "weeks": {str(week): entry for week, entry in result["weeks"].items()}}
        cur.execute("UPDATE sleeper_sync_runs SET season=%s,week=%s,status=%s,resources=%s::jsonb,error_message=%s,completed_at=NOW() WHERE id=%s",
                    (result["season"] or 0, leg or 0, result["status"], json.dumps(resources), result["error"], result["run_id"]))
        conn.commit()
        return result
    except Exception:
        if not dry_run:
            conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()


def read_transaction_history(cur, league_id: Any, season: Any) -> dict[str, Any]:
    """Stored transaction weeks and the latest W5 refresh attempt for one league and season (SELECT only)."""
    cur.execute(HISTORY_QUERY, (TRANSACTIONS_RESOURCE, str(league_id), season))
    rows = [{"week": row[0], "payload": row[1], "fetched_at": row[2], "league_id": row[3], "season": row[4]} for row in cur.fetchall() or []]
    cur.execute(LATEST_REFRESH_QUERY, (str(league_id), season, REFRESH_SCOPE))
    run = cur.fetchone()
    latest = ({"id": run[0], "status": run[1], "resources": run[2], "error": run[3], "started_at": run[4], "completed_at": run[5]} if run else None)
    return {"state": "READ", "rows": rows, "latest_refresh": latest}
