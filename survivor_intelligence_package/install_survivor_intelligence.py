from __future__ import annotations
import ast,shutil,sys
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
def backup(p,b,project):
    if p.exists(): d=b/p.relative_to(project);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
def main():
    if len(sys.argv)!=2:raise SystemExit('usage: python install_survivor_intelligence.py /path/to/fantasy-intelligence')
    project=Path(sys.argv[1]).resolve();b=project/'backups'/('survivor-intelligence-'+datetime.now().strftime('%Y%m%d-%H%M%S'));b.mkdir(parents=True)
    files=['survivor_intelligence.py','survivor_store.py','survivor_routes.py','migrations/007_survivor_intelligence.sql','templates/survivor_intelligence.html','static/survivor_intelligence.css']
    for rel in files:s=HERE/rel;d=project/rel;d.parent.mkdir(parents=True,exist_ok=True);backup(d,b,project);shutil.copy2(s,d)
    app=project/'app.py';text=app.read_text();imp='from survivor_routes import survivor_bp'
    if imp not in text:
        lines=text.splitlines();idx=max([i+1 for i,x in enumerate(lines) if x.startswith(('import ','from '))] or [0]);lines.insert(idx,imp);text='\n'.join(lines)+'\n'
    if 'app.register_blueprint(survivor_bp)' not in text:
        marker='app.register_blueprint(market_bp)'
        if marker not in text:raise SystemExit('market_bp registration marker not found')
        text=text.replace(marker,marker+'\napp.register_blueprint(survivor_bp)',1)
    ast.parse(text);backup(app,b,project);app.write_text(text)
    base=project/'templates/base.html';t=base.read_text();css='<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'survivor_intelligence.css\') }}">'
    if 'survivor_intelligence.css' not in t:t=t.replace('</head>',css+'</head>',1)
    if 'survivor.home' not in t:
        marker='<a href="{{ url_for(\'market_intelligence.home\') }}">Market Intelligence</a>';link='<a href="{{ url_for(\'survivor.home\') }}">Survivor</a>'
        if marker not in t:raise SystemExit('Market Intelligence navigation marker not found')
        t=t.replace(marker,marker+link,1)
    backup(base,b,project);base.write_text(t)
    sys.path.insert(0,str(project));from survivor_store import migrate,ensure_pool;migrate();ensure_pool()
    print('Survivor Intelligence installed');print('backup='+str(b));print('route=/survivor')
if __name__=='__main__':main()
