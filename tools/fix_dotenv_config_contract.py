#!/usr/bin/env python3
"""Fix .env loading placement so config contract tests remain isolated.

Moves python-dotenv loading out of config.py and into the top of app.py, before app
imports auth/config. Creates timestamped backups, runs the targeted contract test,
then runs the full suite. Refuses to modify files if preflight expectations are not met.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "app.py"
CONFIG = ROOT / "config.py"


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    if not APP.exists() or not CONFIG.exists():
        print("ERROR: Run this script from ~/fantasy-intelligence")
        return 2

    app_text = APP.read_text(encoding="utf-8")
    config_text = CONFIG.read_text(encoding="utf-8")

    if "from auth import" not in app_text:
        print("ERROR: Expected 'from auth import' statement was not found in app.py. No changes made.")
        return 3

    dotenv_import = re.search(r"(?m)^from dotenv import load_dotenv\s*$", config_text)
    dotenv_call = re.search(r"(?m)^load_dotenv\(\)\s*$", config_text)

    if not dotenv_import or not dotenv_call:
        print("ERROR: config.py does not contain the expected python-dotenv import and load_dotenv() call.")
        print("No changes made.")
        return 4

    # Ensure python-dotenv is present before changing files.
    try:
        run([sys.executable, "-c", "from dotenv import load_dotenv"])
    except subprocess.CalledProcessError:
        print("ERROR: python-dotenv is unavailable in the active virtual environment. No changes made.")
        return 5

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / "backups" / f"dotenv-config-contract-fix-{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(APP, backup / "app.py")
    shutil.copy2(CONFIG, backup / "config.py")

    # Remove exactly one dotenv import and one zero-argument load call from config.py.
    new_config = re.sub(r"(?m)^from dotenv import load_dotenv\s*\n", "", config_text, count=1)
    new_config = re.sub(r"(?m)^load_dotenv\(\)\s*\n", "", new_config, count=1)

    # Load .env at the application entry point before auth imports config.
    loader_block = "from dotenv import load_dotenv\n\nload_dotenv()\n\n"
    if "from dotenv import load_dotenv" not in app_text:
        new_app = loader_block + app_text
    else:
        # If app.py already imports dotenv but does not call it before auth, refuse to guess.
        import_pos = app_text.find("from dotenv import load_dotenv")
        auth_pos = app_text.find("from auth import")
        call_pos = app_text.find("load_dotenv()")
        if import_pos < auth_pos and 0 <= call_pos < auth_pos:
            new_app = app_text
        else:
            print("ERROR: app.py has a nonstandard dotenv arrangement. Backups were created, but files were not changed.")
            print("Backup:", backup)
            return 6

    CONFIG.write_text(new_config, encoding="utf-8")
    APP.write_text(new_app, encoding="utf-8")

    try:
        run([sys.executable, "-m", "py_compile", "app.py", "config.py"])
        run([
            sys.executable, "-m", "pytest", "-q",
            "tests/test_db_config_contract.py::test_missing_required_db_configuration_raises_controlled_error",
        ])
        run([sys.executable, "-m", "pytest", "-q"])
    except subprocess.CalledProcessError as exc:
        shutil.copy2(backup / "app.py", APP)
        shutil.copy2(backup / "config.py", CONFIG)
        print("VALIDATION FAILED. app.py and config.py were restored automatically.")
        print("Backup:", backup)
        return exc.returncode or 1

    print("FIX COMPLETE")
    print("Backup:", backup)
    print("config.py now validates only the process environment.")
    print("app.py loads .env before importing auth/config.")
    print("You may now rerun the Batch 1 installer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
