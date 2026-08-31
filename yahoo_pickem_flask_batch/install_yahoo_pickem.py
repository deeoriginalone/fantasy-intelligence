"""Conservative installer for the Fantasy Intelligence Flask repository.

Usage from the extracted batch directory:
  python install_yahoo_pickem.py /home/deeoriginalone/fantasy-intelligence

It creates a timestamped backup, copies new files, registers the Blueprint when a
recognizable Flask app factory/global app is found, and adds template partials only
when safe closing tags/blocks are found. Re-running is idempotent.
"""
from __future__ import annotations
import re, shutil, sys
from datetime import datetime
from pathlib import Path

BATCH = Path(__file__).resolve().parent
SOURCE_FILES = [
    "yahoo_pickem.py", "pickem_store.py", "pickem_routes.py",
    "migrations/003_yahoo_pickem.sql", "templates/_pickem_panel.html",
    "templates/_pickem_dashboard_card.html", "templates/pickem.html",
    "static/pickem.css", "tests/test_yahoo_pickem.py",
    "data/pickem_games.example.json", "audit_yahoo_pickem.py",
]


def backup_file(target: Path, backup_root: Path, project: Path) -> None:
    if target.exists():
        destination = backup_root / target.relative_to(project)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, destination)


def insert_before(text: str, marker: str, addition: str) -> tuple[str, bool]:
    if addition.strip() in text or marker not in text: return text, False
    return text.replace(marker, addition + "\n" + marker, 1), True


def patch_app(project: Path, backup_root: Path) -> str:
    path = project / "app.py"
    if not path.exists(): return "app.py missing; Blueprint registration not applied"
    original = path.read_text()
    if "pickem_bp" in original: return "app.py already registered"
    text = original
    import_line = "from pickem_routes import pickem_bp"
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + ("\n" if original.endswith("\n") else "")
    registrations = list(re.finditer(r"(?m)^([ \t]*)(app)\s*=\s*Flask\(", text))
    if registrations:
        match = registrations[0]
        next_newline = text.find("\n", match.end())
        addition = "\napp.register_blueprint(pickem_bp)"
        text = text[:next_newline] + addition + text[next_newline:]
    else:
        factory = re.search(r"(?m)^def create_app\([^)]*\):", text)
        return "app.py import added, but registration needs manual placement inside create_app()" if factory else "app.py import added; Flask app construction was not recognized"
    backup_file(path, backup_root, project)
    path.write_text(text)
    return "app.py Blueprint registered"


def patch_template(project: Path, backup_root: Path, name: str, include: str) -> str:
    path = project / "templates" / name
    if not path.exists(): return f"templates/{name} missing; skipped"
    text = path.read_text()
    if include in text: return f"templates/{name} already patched"
    addition = f'\n{{% include "{include}" %}}\n'
    for marker in ("{% endblock %}", "</main>", "</body>"):
        patched, changed = insert_before(text, marker, addition)
        if changed:
            backup_file(path, backup_root, project)
            path.write_text(patched)
            return f"templates/{name} patched before {marker}"
    return f"templates/{name} has no safe insertion marker; include manually: {addition.strip()}"


def patch_css_link(project: Path, backup_root: Path) -> str:
    path = project / "templates" / "base.html"
    if not path.exists(): return "templates/base.html missing; CSS link skipped"
    text = path.read_text()
    needle = "pickem.css"
    if needle in text: return "Pick'em CSS already linked"
    link = "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='pickem.css') }}\">"
    patched, changed = insert_before(text, "</head>", link)
    if not changed: return "base.html has no </head>; add the Pick'em stylesheet manually"
    backup_file(path, backup_root, project)
    path.write_text(patched)
    return "Pick'em CSS linked in base.html"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python install_yahoo_pickem.py /path/to/fantasy-intelligence")
        return 2
    project = Path(sys.argv[1]).resolve()
    if not (project / "app.py").exists() or not (project / "templates").is_dir():
        print("target does not look like the Fantasy Intelligence Flask repository")
        return 2
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = project / "backups" / f"yahoo-pickem-{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)
    report = []
    for relative in SOURCE_FILES:
        source, target = BATCH / relative, project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_file(target, backup_root, project)
        shutil.copy2(source, target)
        report.append(f"copied {relative}")
    report.append(patch_app(project, backup_root))
    report.append(patch_template(project, backup_root, "weekly.html", "_pickem_panel.html"))
    report.append(patch_template(project, backup_root, "dashboard.html", "_pickem_dashboard_card.html"))
    report.append(patch_css_link(project, backup_root))
    report_path = project / "YAHOO_PICKEM_INSTALL_REPORT.txt"
    report_path.write_text("\n".join(report) + f"\nbackup={backup_root}\n")
    print(report_path.read_text())
    print("Next: python -m unittest tests/test_yahoo_pickem.py")
    print("Then: python audit_yahoo_pickem.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
