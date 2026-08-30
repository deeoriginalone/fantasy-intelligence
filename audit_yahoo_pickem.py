from pathlib import Path
import ast, json, sys
ROOT = Path(__file__).resolve().parent
required = ["yahoo_pickem.py", "pickem_store.py", "pickem_routes.py", "migrations/003_yahoo_pickem.sql", "templates/_pickem_panel.html", "templates/pickem.html", "static/pickem.css"]
issues = []
for name in required:
    if not (ROOT / name).exists(): issues.append(f"missing: {name}")
for name in ["yahoo_pickem.py", "pickem_store.py", "pickem_routes.py", "install_yahoo_pickem.py"]:
    try: ast.parse((ROOT / name).read_text())
    except Exception as exc: issues.append(f"syntax: {name}: {exc}")
print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
sys.exit(1 if issues else 0)
