"""Backup-first, idempotent bridge installer for Fantasy Intelligence."""
from __future__ import annotations
import ast, re, shutil, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def backup(path, root, project):
    if path.exists():
        dest = root / path.relative_to(project); dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, dest)


def patch_weekly_routes(project, backup_root):
    path = project / "weekly_routes.py"; text = path.read_text(); original = text
    import_line = "from pickem_weekly_bridge import build_weekly_pickem_context"
    if import_line not in text:
        lines = text.splitlines(); idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "): idx = i + 1
        lines.insert(idx, import_line); text = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    old = "return render_template('weekly.html',title='Weekly Intelligence',week=week,games=games,byes=byes)"
    new = """strategy=request.args.get('strategy','balanced')
        pickem_context=build_weekly_pickem_context(week=week,season=2026,strategy=strategy)
        return render_template('weekly.html',title='Weekly Intelligence',week=week,games=games,byes=byes,**pickem_context)"""
    if old in text:
        text = text.replace(old, new, 1)
    elif "build_weekly_pickem_context(week=week" not in text:
        raise SystemExit("weekly_routes.py shape not recognized; no changes written")
    ast.parse(text)
    if text != original: backup(path, backup_root, project); path.write_text(text)
    return "weekly_routes.py connected to Pick'em context"


def patch_nav(project, backup_root):
    path = project / "templates/base.html"; text = path.read_text(); original = text
    if "pickem.pickem_page" in text: return "Pick'em nav already present"
    # Repair the known stray anchor first, then insert after Sleeper Intelligence.
    text = text.replace("Sleeper Intelligence</a> </a><a", "Sleeper Intelligence</a><a")
    marker = '<a href="{{ url_for(\'sleeper_intelligence.home\') }}">Sleeper Intelligence</a>'
    addition = marker + '<a href="{{ url_for(\'pickem.pickem_page\') }}">Pick\'em Center</a>'
    if marker not in text: raise SystemExit("base.html nav marker not found; no nav changes written")
    text = text.replace(marker, addition, 1)
    # Basic Jinja delimiter sanity.
    if text.count("{{") != text.count("}}") or text.count("{%") != text.count("%}"):
        raise SystemExit("base.html Jinja delimiter check failed; no nav changes written")
    backup(path, backup_root, project); path.write_text(text)
    return "base.html nav repaired and Pick'em Center added"


def main():
    if len(sys.argv) != 2: raise SystemExit("usage: python install_pickem_weekly_bridge.py /path/to/fantasy-intelligence")
    project = Path(sys.argv[1]).resolve()
    for required in (project/"app.py", project/"weekly_routes.py", project/"templates/base.html"):
        if not required.exists(): raise SystemExit(f"missing required project file: {required}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = project/"backups"/f"pickem-weekly-bridge-{stamp}"; backup_root.mkdir(parents=True, exist_ok=True)
    copied=[]
    for rel in ["pickem_weekly_bridge.py","import_pickem_csv.py","data/pickem_import_template.csv"]:
        src=HERE/rel; dst=project/rel; dst.parent.mkdir(parents=True,exist_ok=True); backup(dst,backup_root,project); shutil.copy2(src,dst); copied.append(rel)
    report = copied + [patch_weekly_routes(project,backup_root), patch_nav(project,backup_root)]
    report_path=project/"PICKEM_WEEKLY_BRIDGE_REPORT.txt"
    report_path.write_text("\n".join(report)+f"\nbackup={backup_root}\n")
    print(report_path.read_text())

if __name__ == "__main__": main()
