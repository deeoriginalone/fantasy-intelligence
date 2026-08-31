#!/usr/bin/env python3
"""Create one compact, secret-free Batch C evidence file.

Run from the fantasy-intelligence repository root. This script is read-only for
Git and PostgreSQL. It writes batch_c_verified_input.txt and nothing else.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
OUT = ROOT / "batch_c_verified_input.txt"
FILES = [
    "app.py",
    "season_sandbox.py",
    "owner_operations.py",
    "weekly_intelligence.py",
    "draft_state_hardening.py",
    "draft_readiness.py",
    "draft_outcome_tracker.py",
]
TABLES = [
    "application_state",
    "draft_sessions",
    "draft_decision_outcomes",
    "drafted_players",
    "league_rosters",
    "draft_board",
    "available_players",
    "my_roster",
]

def run(cmd, env=None):
    p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, env=env)
    return p.returncode, p.stdout

def section(name, body):
    return f"\n===== {name} =====\n{body.rstrip()}\n"

def load_dotenv_without_printing():
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

def db_metadata():
    load_dotenv_without_printing()
    names = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    presence = "\n".join(f"{n}={'set' if os.getenv(n) else 'missing'}" for n in names)
    if not all(os.getenv(n) for n in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")):
        return section("DATABASE CONFIG PRESENCE", presence) + section(
            "DATABASE METADATA", "Skipped because required DB settings were not loaded."
        )
    port = os.getenv("DB_PORT", "5432")
    base = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-At",
            "-h", os.environ["DB_HOST"], "-p", port,
            "-U", os.environ["DB_USER"], "-d", os.environ["DB_NAME"]]
    env = dict(os.environ)
    env["PGPASSWORD"] = os.environ["DB_PASSWORD"]
    quoted = ",".join("'" + t.replace("'", "''") + "'" for t in TABLES)
    queries = {
        "DB TABLES": f"SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ({quoted}) ORDER BY table_name;",
        "DB COLUMNS": f"SELECT table_name||'|'||ordinal_position||'|'||column_name||'|'||data_type||'|'||is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name IN ({quoted}) ORDER BY table_name,ordinal_position;",
        "DB CONSTRAINTS": f"SELECT tc.table_name||'|'||tc.constraint_name||'|'||tc.constraint_type||'|'||coalesce(string_agg(kcu.column_name,',' ORDER BY kcu.ordinal_position),'') FROM information_schema.table_constraints tc LEFT JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema WHERE tc.table_schema='public' AND tc.table_name IN ({quoted}) GROUP BY tc.table_name,tc.constraint_name,tc.constraint_type ORDER BY tc.table_name,tc.constraint_name;",
        "DB INDEXES": f"SELECT tablename||'|'||indexname||'|'||indexdef FROM pg_indexes WHERE schemaname='public' AND tablename IN ({quoted}) ORDER BY tablename,indexname;",
    }
    out = section("DATABASE CONFIG PRESENCE", presence)
    for title, sql in queries.items():
        rc, text = run(base + ["-c", sql], env=env)
        out += section(title, f"return_code={rc}\n{text}")
    return out

def main():
    if not (ROOT / ".git").exists() or not (ROOT / "app.py").exists():
        print("ERROR: run from the fantasy-intelligence repository root", file=sys.stderr)
        return 2
    chunks = []
    for title, cmd in {
        "GIT BRANCH": ["git", "branch", "--show-current"],
        "GIT HEAD": ["git", "log", "-1", "--pretty=fuller"],
        "GIT STATUS": ["git", "status", "--short"],
        "PYTEST": [str(ROOT / "venv" / "bin" / "python"), "-m", "pytest", "-q"],
    }.items():
        rc, text = run(cmd)
        chunks.append(section(title, f"return_code={rc}\n{text}"))
    for name in FILES:
        path = ROOT / name
        if path.exists():
            chunks.append(section(f"FILE {name}", path.read_text(encoding="utf-8", errors="replace")))
        else:
            chunks.append(section(f"FILE {name}", "MISSING"))
    tests = sorted((ROOT / "tests").glob("*.py")) if (ROOT / "tests").exists() else []
    selected = [p for p in tests if any(k in p.name.lower() for k in (
        "sandbox", "owner", "weekly", "draft", "outcome", "state", "roster"
    ))]
    for path in selected:
        chunks.append(section(f"TEST {path.relative_to(ROOT)}", path.read_text(encoding="utf-8", errors="replace")))
    chunks.append(db_metadata())
    OUT.write_text("".join(chunks), encoding="utf-8")
    print(OUT)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
