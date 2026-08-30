from pathlib import Path
import py_compile
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
BASE = ROOT / "templates" / "base.html"
OWNER = ROOT / "owner_operations.py"
BACKUP = ROOT / "backups" / "package-d"


def backup(path):
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / f"{path.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, target)
    print("Backup:", target.relative_to(ROOT))


def main():
    for required in (APP, BASE, OWNER, ROOT / "weekly_intelligence.py", ROOT / "weekly_routes.py"):
        if not required.exists():
            raise SystemExit(f"STOPPED: missing {required.relative_to(ROOT)}")

    app_text = APP.read_text(encoding="utf-8")
    base_text = BASE.read_text(encoding="utf-8")
    owner_text = OWNER.read_text(encoding="utf-8")

    if "from weekly_routes import create_weekly_blueprint" not in app_text:
        backup(APP)
        import_end = app_text.find("\n", app_text.find("from flask import")) + 1
        if import_end <= 0:
            raise SystemExit("STOPPED: Flask import anchor missing")
        app_text = app_text[:import_end] + "from weekly_routes import create_weekly_blueprint\n" + app_text[import_end:]

    if "create_weekly_blueprint(get_db_connection)" not in app_text:
        anchor = 'if __name__ == "__main__":\n'
        if anchor not in app_text:
            raise SystemExit("STOPPED: app main anchor missing")
        app_text = app_text.replace(
            anchor,
            "app.register_blueprint(create_weekly_blueprint(get_db_connection))\n\n" + anchor,
            1,
        )
    APP.write_text(app_text, encoding="utf-8")

    if "weekly_data.weekly_home" not in base_text:
        nav_anchor = '<a href="{{ url_for(\'owner_ops.gm_page\') }}">GM Center</a>'
        if nav_anchor not in base_text:
            raise SystemExit("STOPPED: GM Center navigation anchor missing")
        backup(BASE)
        base_text = base_text.replace(
            nav_anchor,
            nav_anchor + '<a href="{{ url_for(\'weekly_data.weekly_home\') }}">Weekly Intelligence</a>',
            1,
        )
        BASE.write_text(base_text, encoding="utf-8")

    changed_owner = False
    if "from weekly_intelligence import enrich_players" not in owner_text:
        import_anchor = "from flask import Blueprint, current_app, render_template, request, session\n"
        if import_anchor not in owner_text:
            raise SystemExit("STOPPED: owner operations import anchor missing")
        owner_text = owner_text.replace(
            import_anchor,
            import_anchor + "from weekly_intelligence import enrich_players, current_week, upcoming_byes\n",
            1,
        )
        changed_owner = True

    mock_marker = '            roster = mock_roster(cur, context["draft_id"], row[2] if row else 5)\n'
    mock_enrich = mock_marker + "            roster = enrich_players(cur, roster, current_week(cur))\n"
    if "roster = enrich_players(cur, roster, current_week(cur))" not in owner_text:
        if mock_marker not in owner_text:
            raise SystemExit("STOPPED: mock roster anchor missing")
        owner_text = owner_text.replace(mock_marker, mock_enrich, 1)
        live_marker = "        roster, league = live_roster(cur)\n"
        if live_marker not in owner_text:
            raise SystemExit("STOPPED: live roster anchor missing")
        owner_text = owner_text.replace(
            live_marker,
            live_marker + "        roster = enrich_players(cur, roster, current_week(cur))\n",
            1,
        )
        changed_owner = True

    old_sort = 'available = sorted(roster, key=lambda p: (-p["projection"], p["rank"] or 9999))'
    new_sort = 'available = sorted(roster, key=lambda p: (-p.get("weekly_score", 0), p["rank"] or 9999))'
    if old_sort in owner_text:
        owner_text = owner_text.replace(old_sort, new_sort, 1)
        changed_owner = True

    if changed_owner:
        backup(OWNER)
        OWNER.write_text(owner_text, encoding="utf-8")

    for path in (APP, OWNER, ROOT / "weekly_intelligence.py", ROOT / "weekly_routes.py"):
        py_compile.compile(str(path), doraise=True)
    print("PASS: Package D registered and Python syntax is valid")


if __name__ == "__main__":
    main()
