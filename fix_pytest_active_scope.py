#!/usr/bin/env python3
"""Constrain pytest to the active runtime test suite.

The repository contains installer/package bundles with their own tests. Those bundle tests
use package-local import layouts and should not be collected as active runtime tests.
This script creates or safely updates pytest.ini, backs up any existing file, clears only
pytest/Python caches, then performs collection and a full active-suite run.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
PYTEST_INI = ROOT / "pytest.ini"
EXPECTED = """[pytest]
testpaths = tests
norecursedirs =
    backups
    venv
    .venv
    .* 
    *_package
    *_batch
python_files = test_*.py
"""


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    if not (ROOT / "app.py").exists() or not (ROOT / "tests").is_dir():
        print("ERROR: Run from ~/fantasy-intelligence. No changes made.")
        return 2

    backup = None
    if PYTEST_INI.exists():
        existing = PYTEST_INI.read_text(encoding="utf-8")
        if existing.strip() != EXPECTED.strip():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_dir = ROOT / "backups" / f"pytest-scope-fix-{stamp}"
            backup_dir.mkdir(parents=True, exist_ok=False)
            backup = backup_dir / "pytest.ini"
            shutil.copy2(PYTEST_INI, backup)
    PYTEST_INI.write_text(EXPECTED, encoding="utf-8")

    for cache in ROOT.rglob("__pycache__"):
        if "venv" not in cache.parts and ".venv" not in cache.parts:
            shutil.rmtree(cache, ignore_errors=True)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    try:
        run([sys.executable, "-m", "pytest", "--collect-only", "-q"])
        run([sys.executable, "-m", "pytest", "-q"])
    except subprocess.CalledProcessError as exc:
        if backup:
            shutil.copy2(backup, PYTEST_INI)
            print("Validation failed. Original pytest.ini restored from:", backup)
        elif PYTEST_INI.exists():
            PYTEST_INI.unlink()
            print("Validation failed. Newly created pytest.ini removed.")
        return exc.returncode or 1

    print("PYTEST SCOPE FIX COMPLETE")
    print("Active test root: tests/")
    print("Package, batch, backup, and virtual-environment directories are excluded.")
    if backup:
        print("Previous pytest.ini backup:", backup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
