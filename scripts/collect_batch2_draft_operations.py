#!/usr/bin/env python3
"""Collect exact inputs required for Draft Operations Hardening Batch 2.

Read-only. Does not modify application files or database rows. It extracts active manual
pick/undo/roster mutation code and inspects the live schemas those paths touch. Secret
values are never written to the report.
"""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "batch2_draft_operations_discovery.txt"
APP = ROOT / "app.py"
TARGET_HINTS = (
    "draft", "pick", "undo", "roster", "manual", "owner", "reset", "remove"
)
TABLES = (
    "draft_board", "league_rosters", "league_teams", "my_roster",
    "sleeper_draft_picks", "draft_mutation_history", "draft_sessions",
    "draft_sync_audit", "draft_player_quarantine", "players"
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def connect():
    kwargs = dict(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
    )
    if any(v in (None, "") for v in kwargs.values()):
        raise RuntimeError("DB_* environment configuration is incomplete")
    import psycopg2
    return psycopg2.connect(**kwargs)


def extract_functions(text: str) -> list[tuple[str, int, int, str]]:
    tree = ast.parse(text)
    lines = text.splitlines()
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = node.name.lower()
        src = "\n".join(lines[node.lineno - 1:node.end_lineno])
        lower = src.lower()
        relevant = any(h in name for h in TARGET_HINTS) and any(
            token in lower for token in (
                "draft_board", "league_rosters", "my_roster",
                "sleeper_draft_picks", "draft_mutation_history"
            )
        )
        if relevant:
            found.append((node.name, node.lineno, node.end_lineno, src))
    return sorted(found, key=lambda x: x[1])


def main() -> int:
    if not APP.exists():
        print("ERROR: Run from ~/fantasy-intelligence")
        return 2
    text = APP.read_text(encoding="utf-8", errors="replace")
    parts = [
        "BATCH 2 DRAFT OPERATIONS DISCOVERY",
        "READ ONLY: no application files or database rows were modified.",
        "Secret values are excluded.",
        "\n===== GIT STATUS =====",
        subprocess.run(["git", "status", "--short", "--branch"], cwd=ROOT,
                       text=True, capture_output=True).stdout.rstrip(),
        "\n===== ACTIVE FUNCTION EXTRACTS =====",
    ]
    funcs = extract_functions(text)
    if not funcs:
        parts.append("<no matching functions found>")
    for name, start, end, src in funcs:
        parts.append(f"\n----- {name} app.py:{start}-{end} -----")
        parts.append(src)

    parts.append("\n===== ROUTE REGISTRATIONS AROUND DRAFT OPERATIONS =====")
    for i, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if ("@app.route" in low or "@app." in low) and any(h in low for h in TARGET_HINTS):
            parts.append(f"{i}: {line}")

    load_env(ROOT / ".env")
    conn = connect()
    conn.set_session(readonly=True, autocommit=False)
    cur = conn.cursor()
    try:
        parts.append("\n===== LIVE DATABASE STRUCTURES =====")
        for table in TABLES:
            parts.append(f"\n----- {table} -----")
            cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
            if cur.fetchone()[0] is None:
                parts.append("<missing>")
                continue
            cur.execute(f'SELECT COUNT(*) FROM public."{table}"')
            parts.append(f"row_count={cur.fetchone()[0]}")
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
            """, (table,))
            parts.append("columns:")
            parts.extend(" | ".join("" if x is None else str(x) for x in row)
                         for row in cur.fetchall())
            cur.execute("""
                SELECT c.conname, c.contype, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid=c.conrelid
                JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname='public' AND t.relname=%s
                ORDER BY c.conname
            """, (table,))
            rows = cur.fetchall()
            parts.append("constraints:")
            parts.extend(" | ".join(str(x) for x in row) for row in rows)
            if not rows:
                parts.append("<none>")

        parts.append("\n===== INVARIANT DIAGNOSTICS =====")
        checks = {
            "drafted players absent from league_rosters": """
              SELECT COUNT(*) FROM draft_board d
              WHERE d.drafted=TRUE AND NOT EXISTS
              (SELECT 1 FROM league_rosters r WHERE r.player_name=d.player_name)
            """,
            "league_roster players not marked drafted": """
              SELECT COUNT(*) FROM league_rosters r
              WHERE NOT EXISTS
              (SELECT 1 FROM draft_board d WHERE d.player_name=r.player_name AND d.drafted=TRUE)
            """,
            "players owned by multiple teams": """
              SELECT COUNT(*) FROM (
                SELECT player_name FROM league_rosters
                GROUP BY player_name HAVING COUNT(DISTINCT team_name)>1
              ) x
            """,
            "my_roster players absent from league_rosters": """
              SELECT COUNT(*) FROM my_roster m
              WHERE NOT EXISTS
              (SELECT 1 FROM league_rosters r WHERE r.player_name=m.player_name)
            """,
        }
        for label, sql in checks.items():
            try:
                cur.execute(sql)
                parts.append(f"{label}: {cur.fetchone()[0]}")
            except Exception as exc:
                conn.rollback(); conn.set_session(readonly=True, autocommit=False)
                cur = conn.cursor()
                parts.append(f"{label}: <unavailable: {exc.__class__.__name__}>")
    finally:
        conn.rollback(); cur.close(); conn.close()

    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Created: {OUT}")
    print(f"Bytes: {OUT.stat().st_size}")
    print(f"Functions captured: {len(funcs)}")
    print("No application files or database rows were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
