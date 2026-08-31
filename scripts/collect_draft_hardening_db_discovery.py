#!/usr/bin/env python3
"""Read-only PostgreSQL discovery for Draft Hardening Batch 1.

Loads .env without printing values, connects using DB_* settings, and writes schema,
constraints, indexes, row counts, and duplicate diagnostics for draft-related tables.
No database objects or rows are modified.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "draft_hardening_db_discovery.txt"
TABLES = [
    "application_state", "draft_board", "draft_decision_outcomes",
    "league_info", "league_rosters", "league_teams", "my_roster",
    "players", "sleeper_api_snapshots", "sleeper_draft_picks",
    "sleeper_drafts", "sleeper_player_map", "sleeper_sync_runs",
]


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def connect():
    kwargs = {
        "host": os.environ.get("DB_HOST"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ.get("DB_NAME"),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
    }
    missing = [k for k, v in kwargs.items() if v in (None, "")]
    if missing:
        raise RuntimeError("Missing environment settings: " + ", ".join(missing))
    try:
        import psycopg2
        return psycopg2.connect(**kwargs)
    except ImportError:
        import psycopg
        return psycopg.connect(**kwargs)


def rows(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def main() -> int:
    if not (ROOT / "app.py").exists():
        print("ERROR: run from the fantasy-intelligence project root")
        return 2
    load_env(ROOT / ".env")
    conn = connect()
    conn.set_session(readonly=True, autocommit=False)
    cur = conn.cursor()
    parts = [
        "FANTASY INTELLIGENCE DRAFT-HARDENING DATABASE DISCOVERY",
        "READ ONLY: no database objects or rows were modified.",
    ]
    try:
        parts.append("\n===== SERVER =====")
        for row in rows(cur, "SELECT current_database(), current_user, version()"):
            parts.append(" | ".join(str(x) for x in row))

        for table in TABLES:
            parts.append(f"\n===== TABLE: {table} =====")
            exists = rows(cur, "SELECT to_regclass(%s)", (f"public.{table}",))[0][0]
            if not exists:
                parts.append("<missing>")
                continue
            count = rows(cur, f'SELECT COUNT(*) FROM public."{table}"')[0][0]
            parts.append(f"row_count={count}")
            parts.append("-- columns --")
            for r in rows(cur, """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
            """, (table,)):
                parts.append(" | ".join("" if x is None else str(x) for x in r))
            parts.append("-- constraints --")
            constraint_rows = rows(cur, """
                SELECT c.conname, c.contype, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid=c.conrelid
                JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname='public' AND t.relname=%s
                ORDER BY c.conname
            """, (table,))
            parts.extend(" | ".join(str(x) for x in r) for r in constraint_rows)
            if not constraint_rows:
                parts.append("<none>")
            parts.append("-- indexes --")
            index_rows = rows(cur, """
                SELECT indexname, indexdef FROM pg_indexes
                WHERE schemaname='public' AND tablename=%s ORDER BY indexname
            """, (table,))
            parts.extend(" | ".join(str(x) for x in r) for r in index_rows)
            if not index_rows:
                parts.append("<none>")

        parts.append("\n===== DUPLICATE DIAGNOSTICS =====")
        diagnostics = [
            ("sleeper_draft_picks draft_id,pick_no", """
                SELECT draft_id, pick_no, COUNT(*)
                FROM sleeper_draft_picks
                GROUP BY draft_id, pick_no HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, draft_id, pick_no LIMIT 100
            """),
            ("sleeper_draft_picks draft_id,player_id", """
                SELECT draft_id, player_id, COUNT(*)
                FROM sleeper_draft_picks
                WHERE player_id IS NOT NULL AND BTRIM(player_id) <> ''
                GROUP BY draft_id, player_id HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, draft_id, player_id LIMIT 100
            """),
            ("league_rosters player_name", """
                SELECT player_name, COUNT(*) FROM league_rosters
                WHERE player_name IS NOT NULL AND BTRIM(player_name) <> ''
                GROUP BY player_name HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, player_name LIMIT 100
            """),
            ("my_roster player_name", """
                SELECT player_name, COUNT(*) FROM my_roster
                WHERE player_name IS NOT NULL AND BTRIM(player_name) <> ''
                GROUP BY player_name HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, player_name LIMIT 100
            """),
        ]
        for label, sql in diagnostics:
            parts.append(f"-- {label} --")
            try:
                found = rows(cur, sql)
                parts.extend(" | ".join(str(x) for x in r) for r in found)
                if not found:
                    parts.append("<none>")
            except Exception as exc:
                conn.rollback()
                conn.set_session(readonly=True, autocommit=False)
                cur = conn.cursor()
                parts.append(f"<unavailable: {exc.__class__.__name__}>")

        parts.append("\n===== SAMPLE STATE, IDS ONLY =====")
        sample_queries = [
            ("sleeper_drafts", "SELECT draft_id, league_id, season, status FROM sleeper_drafts ORDER BY draft_id LIMIT 20"),
            ("application_state", "SELECT state_key FROM application_state ORDER BY state_key LIMIT 50"),
            ("snapshots", "SELECT resource_type, resource_key, season, week, fetched_at FROM sleeper_api_snapshots ORDER BY fetched_at DESC LIMIT 30"),
        ]
        for label, sql in sample_queries:
            parts.append(f"-- {label} --")
            try:
                found = rows(cur, sql)
                parts.extend(" | ".join(str(x) for x in r) for r in found)
                if not found:
                    parts.append("<none>")
            except Exception as exc:
                conn.rollback()
                conn.set_session(readonly=True, autocommit=False)
                cur = conn.cursor()
                parts.append(f"<unavailable: {exc.__class__.__name__}>")
    finally:
        conn.rollback()
        cur.close()
        conn.close()

    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Created: {OUT}")
    print(f"Bytes: {OUT.stat().st_size}")
    print("No database objects or rows were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
