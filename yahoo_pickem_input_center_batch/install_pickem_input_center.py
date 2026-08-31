from __future__ import annotations
import ast, shutil, sys
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent

def backup(path,root,project):
    if path.exists():
        dest=root/path.relative_to(project); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,dest)

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python install_pickem_input_center.py /path/to/fantasy-intelligence')
    project=Path(sys.argv[1]).resolve(); stamp=datetime.now().strftime('%Y%m%d-%H%M%S'); root=project/'backups'/f'pickem-input-center-{stamp}'; root.mkdir(parents=True,exist_ok=True)
    for rel in ['pickem_inputs_routes.py','templates/pickem_inputs.html','static/pickem_inputs.css']:
        src=HERE/rel; dst=project/rel; dst.parent.mkdir(parents=True,exist_ok=True); backup(dst,root,project); shutil.copy2(src,dst)
    app=project/'app.py'; text=app.read_text(); original=text
    imp='from pickem_inputs_routes import pickem_inputs_bp'
    if imp not in text:
        lines=text.splitlines(); idx=max([i+1 for i,x in enumerate(lines) if x.startswith(('import ','from '))] or [0]); lines.insert(idx,imp); text='\n'.join(lines)+'\n'
    if 'app.register_blueprint(pickem_inputs_bp)' not in text:
        marker='app.register_blueprint(pickem_bp)'
        if marker not in text: raise SystemExit('pickem_bp registration marker not found; no app.py changes written')
        text=text.replace(marker,marker+'\napp.register_blueprint(pickem_inputs_bp)',1)
    ast.parse(text); backup(app,root,project); app.write_text(text)
    base=project/'templates/base.html'; b=base.read_text()
    css='<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'pickem_inputs.css\') }}">'
    if 'pickem_inputs.css' not in b:
        if '</head>' not in b: raise SystemExit('base.html has no </head>')
        backup(base,root,project); base.write_text(b.replace('</head>',css+'</head>',1))
    panel=project/'templates/_pickem_panel.html'; p=panel.read_text()
    link='<a class="fi-pickem__inputs-link" href="{{ url_for(\'pickem_inputs.inputs_home\', season=pickem_season, week=pickem_week) }}">Update weekly inputs</a>'
    if 'pickem_inputs.inputs_home' not in p:
        marker='<div class="fi-pickem__header">'
        if marker not in p: raise SystemExit('_pickem_panel.html header marker not found')
        backup(panel,root,project); panel.write_text(p.replace(marker,marker+link,1))
    report=f'Pick’em Input Center installed\nroute=/pickem/inputs\nbackup={root}\n'; (project/'PICKEM_INPUT_CENTER_REPORT.txt').write_text(report); print(report)
if __name__=='__main__': main()
