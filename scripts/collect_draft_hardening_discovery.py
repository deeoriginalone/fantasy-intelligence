#!/usr/bin/env python3
"""Collect a focused, redacted snapshot for the Fantasy Intelligence draft-hardening batch.

This script does not modify application code or the database. It creates one text report
that can be provided for review before generating an upgrade batch.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "draft_hardening_discovery.txt"
MAX_FILE_BYTES = 2_000_000

INCLUDE_FILES = [
    "app.py",
    "config.py",
    "auth.py",
    "README.md",
    "DEVELOPMENT_ROADMAP.md",
    "requirements.txt",
    "pyproject.toml",
    "setup.cfg",
    ".gitignore",
    "owner_operations.py",
    "draft_outcome_tracker.py",
    "draft_readiness.py",
    "readiness.py",
    "sleeper_hub.py",
    "sleeper_intelligence.py",
    "sleeper_intelligence_routes.py",
    "services/sleeper_service.py",
    "mocklab/simulator.py",
]

SECRET_NAME_RE = re.compile(
    r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential)"
)
ENV_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def redact_line(line: str) -> str:
    match = ENV_ASSIGN_RE.match(line.strip())
    if match and SECRET_NAME_RE.search(match.group(1)):
        return f"{match.group(1)}=<REDACTED>"
    # Redact common Python/config assignments while retaining the variable name.
    if SECRET_NAME_RE.search(line) and "=" in line:
        left, _, _right = line.partition("=")
        return left.rstrip() + " = <REDACTED>"
    return line.rstrip("\n")


def run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        return result.stdout.rstrip()
    except Exception as exc:
        return f"<command failed: {exc}>"


def add_file(parts: list[str], rel: str) -> None:
    path = ROOT / rel
    parts.append(f"\n===== FILE: {rel} =====")
    if not path.exists():
        parts.append("<missing>")
        return
    if not path.is_file():
        parts.append("<not a regular file>")
        return
    if path.stat().st_size > MAX_FILE_BYTES:
        parts.append(f"<skipped: {path.stat().st_size} bytes exceeds limit>")
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        parts.append(f"<read failed: {exc}>")
        return
    parts.extend(redact_line(line) for line in text.splitlines())


def main() -> int:
    if not (ROOT / "app.py").exists():
        print("ERROR: Run this script from the fantasy-intelligence project root.")
        return 2

    parts: list[str] = []
    parts.append("FANTASY INTELLIGENCE DRAFT-HARDENING DISCOVERY")
    parts.append(f"Project root: {ROOT}")
    parts.append("This report is read-only and redacts obvious secret assignments.")

    parts.append("\n===== GIT STATUS =====")
    parts.append(run(["git", "status", "--short", "--branch"]))

    parts.append("\n===== RECENT COMMITS =====")
    parts.append(run(["git", "log", "-n", "8", "--oneline", "--decorate"]))

    parts.append("\n===== TOP-LEVEL TREE =====")
    entries = []
    for path in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        if path.name in {".git", "venv", ".venv", "__pycache__", "backups"}:
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(path.name + suffix)
    parts.extend(entries)

    parts.append("\n===== TEST FILES =====")
    tests = ROOT / "tests"
    if tests.exists():
        parts.extend(str(p.relative_to(ROOT)) for p in sorted(tests.rglob("test_*.py")))
    else:
        parts.append("<tests directory missing>")

    parts.append("\n===== SQL/MIGRATION FILES =====")
    sql_files = []
    for pattern in ("*.sql", "migrations/**/*.py", "migrations/**/*.sql"):
        sql_files.extend(ROOT.glob(pattern))
    for path in sorted(set(sql_files)):
        if ".git" not in path.parts and "venv" not in path.parts and "backups" not in path.parts:
            parts.append(str(path.relative_to(ROOT)))
    if not sql_files:
        parts.append("<none found>")

    parts.append("\n===== ENVIRONMENT CONTRACT (NAMES ONLY) =====")
    for rel in (".env", ".env.pickem", ".env.market", ".env.example"):
        path = ROOT / rel
        if not path.exists():
            continue
        parts.append(f"[{rel}]")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = ENV_ASSIGN_RE.match(line.strip())
            if m:
                parts.append(m.group(1))

    for rel in INCLUDE_FILES:
        add_file(parts, rel)

    # Include all active test sources, but not caches or backups.
    if tests.exists():
        for path in sorted(tests.rglob("test_*.py")):
            add_file(parts, str(path.relative_to(ROOT)))

    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Created: {OUT}")
    print(f"Bytes: {OUT.stat().st_size}")
    print("No application files or database objects were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
