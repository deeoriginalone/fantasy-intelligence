from __future__ import annotations
import ast,re,shutil,sys
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent

def backup(path,root,project):
    if path.exists():
        d=root/path.relative_to(project); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,d)

def patch_weekly(project,backup_root):
    p=project/'weekly_routes.py'; text=p.read_text(); original=text
    # Replace either the old SQLite bridge import or add the PostgreSQL import.
    text=text.replace(
        'from pickem_weekly_bridge import build_weekly_pickem_context',
        'from pickem_pg_context import build_pickem_context'
    )
    if 'from pickem_pg_context import build_pickem_context' not in text:
        lines=text.splitlines()
        idx=max([i+1 for i,x in enumerate(lines) if x.startswith(('import ','from '))] or [0])
        lines.insert(idx,'from pickem_pg_context import build_pickem_context')
        text='\n'.join(lines)+('\n' if original.endswith('\n') else '')
    # Replace the already-installed SQLite bridge call.
    text=text.replace(
        'pickem_context=build_weekly_pickem_context(week=week,season=2026,strategy=strategy)',
        'pickem_context=build_pickem_context(2026,week,strategy)'
    )
    # Support an untouched weekly route too.
    old="return render_template('weekly.html',title='Weekly Intelligence',week=week,games=games,byes=byes)"
    new="""strategy=request.args.get('strategy','balanced')
        pickem_context=build_pickem_context(2026,week,strategy)
        return render_template('weekly.html',title='Weekly Intelligence',week=week,games=games,byes=byes,**pickem_context)"""
    if old in text:
        text=text.replace(old,new,1)
    if 'pickem_context=build_pickem_context(2026,week,strategy)' not in text:
        raise SystemExit('weekly_routes.py PostgreSQL bridge target not found; nothing written')
    ast.parse(text)
    if text != original:
        backup(p,backup_root,project); p.write_text(text)

def patch_routes(project,backup_root):
    p=project/'pickem_routes.py'; text=p.read_text(); original=text
    text=text.replace('from pickem_store import PickemStore','from pickem_pg_context import build_pickem_context as build_pg_pickem_context')
    # Replace standalone page/api context calls while preserving endpoint names.
    text=text.replace('return render_template("pickem.html", **build_pickem_context(season, week, strategy))','return render_template("pickem.html", **build_pg_pickem_context(season, week, strategy))')
    text=text.replace('return jsonify(build_pickem_context(season, week, strategy))','return jsonify(build_pg_pickem_context(season, week, strategy))')
    # Disable SQLite-specific POST clearly; CSV importer is the supported ingestion path.
    start=text.find('@pickem_bp.post("/api/pickem/games")')
    end=text.find('@pickem_bp.get("/api/pickem/health")')
    if start!=-1 and end!=-1:
        replacement='''@pickem_bp.post("/api/pickem/games")\ndef upsert_pickem_game():\n    return jsonify({"ok": False, "error": "Use import_pickem_pg_csv.py for PostgreSQL ingestion"}), 410\n\n\n'''
        text=text[:start]+replacement+text[end:]
    # Replace health body without touching decorators.
    text=re.sub(r'def pickem_health\(\):\n(?:    .*\n)+', 'def pickem_health():\n    return jsonify({"ok": True, "model_version": MODEL_VERSION, "storage": "postgresql"})\n', text)
    ast.parse(text); backup(p,backup_root,project); p.write_text(text)

def patch_nav(project,backup_root):
    p=project/'templates/base.html'; text=p.read_text()
    if "pickem.pickem_page" in text: return
    marker='<a href="{{ url_for(\'sleeper_intelligence.home\') }}">Sleeper Intelligence</a>'
    if marker not in text: raise SystemExit('base.html Sleeper Intelligence marker not found; other changes already written')
    text=text.replace('Sleeper Intelligence</a> </a><a','Sleeper Intelligence</a><a')
    text=text.replace(marker,marker+'<a href="{{ url_for(\'pickem.pickem_page\') }}">Pick\'em Center</a>',1)
    backup(p,backup_root,project); p.write_text(text)

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python install_pickem_postgres_fix.py /path/to/fantasy-intelligence')
    project=Path(sys.argv[1]).resolve(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); root=project/'backups'/f'pickem-postgres-{stamp}'; root.mkdir(parents=True,exist_ok=True)
    for rel in ['pickem_pg_store.py','pickem_pg_context.py','import_pickem_pg_csv.py','migrations/004_yahoo_pickem_postgres.sql','data/pickem_pg_import_template.csv']:
        src=HERE/rel; dst=project/rel; dst.parent.mkdir(parents=True,exist_ok=True); backup(dst,root,project); shutil.copy2(src,dst)
    patch_weekly(project,root); patch_routes(project,root); patch_nav(project,root)
    sys.path.insert(0,str(project)); from pickem_pg_store import migrate,seed_from_schedule
    migrate(); count=seed_from_schedule(2026)
    report=f'PostgreSQL migration applied\nSchedule shells inserted={count}\nbackup={root}\n'
    (project/'PICKEM_POSTGRES_FIX_REPORT.txt').write_text(report); print(report)
if __name__=='__main__': main()
