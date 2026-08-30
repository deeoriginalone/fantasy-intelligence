from pathlib import Path
import py_compile
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
BASE = ROOT / "templates" / "base.html"
BACKUP = ROOT / "backups" / "season-sandbox"

IMPORT_LINE = "from season_sandbox import create_sandbox_blueprint\n"
REGISTER_LINE = "app.register_blueprint(create_sandbox_blueprint(get_db_connection))\n\n"
MAIN_ANCHOR = 'if __name__ == "__main__":\n'
NAV_ANCHOR = '<a href="{{ url_for(\'mock_draft_lab\') }}">Mock Drafts</a>'
NAV_REPLACEMENT = NAV_ANCHOR + '<a href="{{ url_for(\'season_sandbox.sandbox_home\') }}">Season Sandbox</a>'


def backup(path):
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / f"{path.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, target)
    print("Backup:", target.relative_to(ROOT))


def main():
    if not APP.exists() or not BASE.exists():
        raise SystemExit("STOPPED: Run from ~/fantasy-intelligence")

    app_text = APP.read_text(encoding="utf-8")
    base_text = BASE.read_text(encoding="utf-8")

    if IMPORT_LINE.strip() not in app_text:
        backup(APP)
        first_import_end = app_text.find("\n", app_text.find("from flask import")) + 1
        app_text = app_text[:first_import_end] + IMPORT_LINE + app_text[first_import_end:]

    if "create_sandbox_blueprint(get_db_connection)" not in app_text:
        if MAIN_ANCHOR not in app_text:
            raise SystemExit("STOPPED: app.py main anchor not found")
        app_text = app_text.replace(MAIN_ANCHOR, REGISTER_LINE + MAIN_ANCHOR, 1)

    APP.write_text(app_text, encoding="utf-8")

    if "season_sandbox.sandbox_home" not in base_text:
        if NAV_ANCHOR not in base_text:
            raise SystemExit("STOPPED: Mock Drafts navigation anchor not found")
        backup(BASE)
        BASE.write_text(base_text.replace(NAV_ANCHOR, NAV_REPLACEMENT, 1), encoding="utf-8")

    py_compile.compile(str(APP), doraise=True)
    py_compile.compile(str(ROOT / "season_sandbox.py"), doraise=True)
    print("PASS: Python syntax")

    from jinja2 import Environment
    Environment().parse((ROOT / "templates" / "season_sandbox.html").read_text(encoding="utf-8"))
    print("PASS: Jinja syntax")
    print("Season Sandbox registered successfully.")


if __name__ == "__main__":
    main()
