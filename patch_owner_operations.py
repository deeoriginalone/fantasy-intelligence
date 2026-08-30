from pathlib import Path
import py_compile, shutil
from datetime import datetime
ROOT=Path(__file__).resolve().parent
APP=ROOT/'app.py'; BASE=ROOT/'templates'/'base.html'; BACKUP=ROOT/'backups'/'owner-operations'
IMPORT='from owner_operations import create_owner_operations_blueprint\n'
REGISTER='app.register_blueprint(create_owner_operations_blueprint(get_db_connection, get_league, get_users, get_rosters, get_all_players, normalize_player_name))\n\n'
MAIN='if __name__ == "__main__":\n'
NAV='<a href="{{ url_for(\'season_sandbox.sandbox_home\') }}">Season Sandbox</a>'
ADD=NAV+'<a href="{{ url_for(\'owner_ops.team_page\') }}">My Team</a><a href="{{ url_for(\'owner_ops.lineup_page\') }}">Lineup</a><a href="{{ url_for(\'owner_ops.waivers_page\') }}">Waivers</a><a href="{{ url_for(\'owner_ops.trades_page\') }}">Trades</a><a href="{{ url_for(\'owner_ops.gm_page\') }}">GM Center</a>'
def backup(p):
    BACKUP.mkdir(parents=True,exist_ok=True); t=BACKUP/f"{p.name}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"; shutil.copy2(p,t); print('Backup:',t.relative_to(ROOT))
def main():
    a=APP.read_text(); b=BASE.read_text()
    if IMPORT.strip() not in a:
        backup(APP); end=a.find('\n',a.find('from flask import'))+1; a=a[:end]+IMPORT+a[end:]
    if 'create_owner_operations_blueprint(get_db_connection' not in a:
        if MAIN not in a: raise SystemExit('STOPPED: main anchor missing')
        a=a.replace(MAIN,REGISTER+MAIN,1)
    APP.write_text(a)
    if 'owner_ops.team_page' not in b:
        if NAV not in b: raise SystemExit('STOPPED: Season Sandbox navigation anchor missing')
        backup(BASE); BASE.write_text(b.replace(NAV,ADD,1))
    py_compile.compile(str(APP),doraise=True); py_compile.compile(str(ROOT/'owner_operations.py'),doraise=True)
    from jinja2 import Environment
    for name in ['team.html','lineup.html','waivers.html','trades.html','gm.html']:
        Environment().parse((ROOT/'templates'/name).read_text())
    print('PASS: Owner Operations registered and validated')
if __name__=='__main__': main()
