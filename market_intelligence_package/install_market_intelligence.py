from __future__ import annotations
import ast,shutil,sys
from datetime import datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
def backup(p,b,project):
    if p.exists(): d=b/p.relative_to(project); d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,d)
def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python install_market_intelligence.py /path/to/fantasy-intelligence')
    project=Path(sys.argv[1]).resolve();b=project/'backups'/('market-intelligence-'+datetime.now().strftime('%Y%m%d-%H%M%S'));b.mkdir(parents=True)
    files=['market_intelligence.py','market_refresh.py','market_routes.py','providers/the_odds_api.py','migrations/006_market_intelligence.sql','templates/market_intelligence.html','static/market_intelligence.css','scheduler/market-refresh.service','scheduler/market-refresh.timer','.env.market.example']
    for rel in files:s=HERE/rel;d=project/rel;d.parent.mkdir(parents=True,exist_ok=True);backup(d,b,project);shutil.copy2(s,d)
    app=project/'app.py';text=app.read_text();imp='from market_routes import market_bp'
    if imp not in text:
        lines=text.splitlines();idx=max([i+1 for i,x in enumerate(lines) if x.startswith(('import ','from '))] or [0]);lines.insert(idx,imp);text='\n'.join(lines)+'\n'
    if 'app.register_blueprint(market_bp)' not in text:
        marker='app.register_blueprint(pickem_bp)'
        if marker not in text:raise SystemExit('pickem_bp registration marker not found')
        text=text.replace(marker,marker+'\napp.register_blueprint(market_bp)',1)
    ast.parse(text);backup(app,b,project);app.write_text(text)
    base=project/'templates/base.html';t=base.read_text();css='<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'market_intelligence.css\') }}">'
    if 'market_intelligence.css' not in t:t=t.replace('</head>',css+'</head>',1)
    if "market_intelligence.home" not in t:
        marker='<a href="{{ url_for(\'pickem.pickem_page\') }}">Pick\'em Center</a>'
        link='<a href="{{ url_for(\'market_intelligence.home\') }}">Market Intelligence</a>'
        if marker in t:t=t.replace(marker,marker+link,1)
        else:
            fallback='<a href="{{ url_for(\'sleeper_intelligence.home\') }}">Sleeper Intelligence</a>'
            if fallback not in t:raise SystemExit('navigation marker not found')
            t=t.replace(fallback,fallback+link,1)
    backup(base,b,project);base.write_text(t)
    sys.path.insert(0,str(project));from pickem_pg_store import connect
    conn=connect();sql=(project/'migrations/006_market_intelligence.sql').read_text()
    try:
        with conn.cursor() as c:c.execute(sql)
        conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
    print('Market Intelligence installed');print('backup='+str(b));print('next: cp .env.market.example .env.market and set ODDS_API_KEY')
if __name__=='__main__':main()
