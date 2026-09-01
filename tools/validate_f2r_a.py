from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg2


def fail(message: str) -> None:
    print("STATUS=FAILED")
    print("ERROR=" + message)
    raise SystemExit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"missing environment variable: {name}")
    return value


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    app_text = (repo / "app.py").read_text(encoding="utf-8")
    if "projected_points, tier, adp, player_id" in app_text:
        fail("app.py still selects nonexistent players.player_id")
    if "projected_points, tier, adp, id" not in app_text:
        fail("reviewed mock_pool query selecting players.id was not found")

    conn = psycopg2.connect(
        host=require_env("DB_HOST"),
        port=require_env("DB_PORT"),
        dbname=require_env("DB_NAME"),
        user=require_env("DB_USER"),
        password=require_env("DB_PASSWORD"),
    )
    try:
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='players'
                  AND column_name IN ('id', 'player_id', 'sleeper_player_id')
                ORDER BY column_name
            """)
            columns = dict(cur.fetchall())
            if columns.get("id") != "integer":
                fail(f"expected players.id integer; found {columns.get('id')!r}")
            if "player_id" in columns:
                fail("players.player_id now exists; this batch must be re-reviewed before use")

            cur.execute("""
                SELECT id, player_name, UPPER(position), ranking
                FROM players
                WHERE id IS NOT NULL
                  AND UPPER(position) IN ('QB','RB','WR','TE','K','DEF')
                ORDER BY ranking NULLS LAST, player_name
                LIMIT 1
            """)
            row = cur.fetchone()
            if row is None:
                fail("players table has no draftable row for read-only validation")
            local_id, player_name, position, ranking = row
            print("STATUS=PASSED")
            print("LOCAL_ID_TYPE=" + type(local_id).__name__)
            print("LOCAL_ID_PRESENT=" + str(local_id is not None))
            print("PLAYER_NAME_PRESENT=" + str(bool(player_name)))
            print("POSITION=" + str(position))
            print("RANKING_PRESENT=" + str(ranking is not None))
            print("TRANSACTION_READ_ONLY=True")
    finally:
        conn.rollback()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
