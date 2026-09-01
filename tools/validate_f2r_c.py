from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import psycopg2
from phase_f.identity_repository import PostgresIdentityRepository
from phase_f.player_mapper import PlayerMapper, MappingStatus

def required(name):
    value=os.environ.get(name)
    if not value: raise SystemExit(f"missing environment variable: {name}")
    return value

def connection_factory():
    return psycopg2.connect(host=required("DB_HOST"),port=required("DB_PORT"),dbname=required("DB_NAME"),user=required("DB_USER"),password=required("DB_PASSWORD"))

def main():
    conn=connection_factory()
    try:
        conn.set_session(readonly=True,autocommit=False)
        with conn.cursor() as cur:
            cur.execute("""SELECT sleeper_player_id FROM sleeper_player_map WHERE matched=TRUE AND local_player_name IS NOT NULL ORDER BY sleeper_player_id LIMIT 1""")
            row=cur.fetchone()
            if not row: raise SystemExit("no matched Sleeper mapping available")
            sleeper_id=row[0]
    finally:
        conn.rollback(); conn.close()
    result=PlayerMapper(PostgresIdentityRepository(connection_factory)).resolve_sleeper_id(sleeper_id)
    print("STATUS="+result.status.value)
    print("SLEEPER_ID_PRESENT="+str(bool(result.sleeper_player_id)))
    print("LOCAL_ID_PRESENT="+str(bool(result.local_player_id)))
    print("PLAYER_NAME_PRESENT="+str(bool(result.player_name)))
    print("READ_ONLY=True")
    if result.status is not MappingStatus.MATCHED: raise SystemExit(1)
if __name__=="__main__": main()
