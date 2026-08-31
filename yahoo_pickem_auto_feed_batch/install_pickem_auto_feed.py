from __future__ import annotations
import ast,shutil,sys
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
def backup(p,b,project):
    if p.exists(): d=b/p.relative_to(project); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,d)
def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python install_pickem_auto_feed.py /path/to/fantasy-intelligence')
    project=Path(sys.argv[1]).resolve(); b=project/'backups'/('pickem-auto-feed-'+datetime.now().strftime('%Y%m%d-%H%M%S')); b.mkdir(parents=True)
    files=['pickem_auto_feed.py','pickem_feed_routes.py','providers/base.py','providers/http_json.py','migrations/005_pickem_feed_runs.sql','templates/pickem_feed_health.html','static/pickem_feed.css','scheduler/pickem_refresh.sh','scheduler/pickem-refresh.service','scheduler/pickem-refresh.timer','.env.pickem.example']
    for rel in files:
        s=HERE/rel; d=project/rel; d.parent.mkdir(parents=True,exist_ok=True); backup(d,b,project); shutil.copy2(s,d)
    app=project/'app.py'; text=app.read_text(); imp='from pickem_feed_routes import pickem_feed_bp'
    if imp not in text:
        lines=text.splitlines(); idx=max([i+1 for i,x in enumerate(lines) if x.startswith(('import ','from '))] or [0]); lines.insert(idx,imp); text='\n'.join(lines)+'\n'
    if 'app.register_blueprint(pickem_feed_bp)' not in text:
        marker='app.register_blueprint(pickem_bp)'
        if marker not in text: raise SystemExit('pickem_bp registration not found')
        text=text.replace(marker,marker+'\napp.register_blueprint(pickem_feed_bp)',1)
    ast.parse(text); backup(app,b,project); app.write_text(text)
    base=project/'templates/base.html'; t=base.read_text(); css='<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'pickem_feed.css\') }}">'
    if 'pickem_feed.css' not in t: backup(base,b,project); base.write_text(t.replace('</head>',css+'</head>',1))
    sys.path.insert(0,str(project)); from pickem_pg_store import connect
    conn=connect(); sql=(project/'migrations/005_pickem_feed_runs.sql').read_text()
    try:
        with conn.cursor() as cur: cur.execute(sql)
        conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()
    print('Pickem Auto Feed installed'); print('backup='+str(b)); print('configure '+str(project/'.env.pickem'))
if __name__=='__main__': main()
