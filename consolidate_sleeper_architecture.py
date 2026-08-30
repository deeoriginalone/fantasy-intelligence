#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import ast,json,py_compile,shutil
R=Path.cwd();A=R/'app.py';B=R/'templates/base.html';K=R/'backups/sleeper-consolidation'/datetime.now().strftime('%Y%m%d-%H%M%S')
redundant=[R/'services/sleeper_full_service.py',R/'sleeper_api_routes.py',R/'sleeper_sync.py']
artifacts=[R/'payload',R/'install_sleeper_api_expansion.py',R/'install_sleeper_full_integration.py',R/'install_sleeper_intelligence.py',R/'sleeper_full_integration.zip',R/'sleeper_intelligence_layer.zip',R/'README.txt']
required=[A,B,R/'services/sleeper_service.py',R/'services/import_rankings.py',R/'sleeper_hub.py',R/'sleeper_intelligence.py',R/'sleeper_intelligence_routes.py',R/'templates/sleeper_hub.html',R/'templates/sleeper_sync_result.html',R/'templates/sleeper_intelligence.html',R/'migrations/005_sleeper_full_integration.sql']
def backup(p):
 if p.exists() and p.is_file():
  d=K/'working-files'/p.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
def archive(p):
 if p.exists():
  d=K/'archived-artifacts'/p.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(p),str(d));print('Archived:',p.relative_to(R))
def main():
 missing=[str(p.relative_to(R)) for p in required if not p.exists()]
 if missing:raise SystemExit('STOPPED missing: '+', '.join(missing))
 for p in [A,B,R/'services/sleeper_service.py']+redundant+artifacts:backup(p)
 t=A.read_text()
 for block,label in [('from sleeper_api_routes import create_sleeper_api_blueprint\n','legacy API import'),('app.register_blueprint(create_sleeper_api_blueprint(get_db_connection))\n','legacy API registration')]:
  if block in t:t=t.replace(block,'',1);print('Removed:',label)
 dup='from services.sleeper_service import (\n    get_league,\n    get_users,\n    get_rosters\n)\n'
 if t.count('from services.sleeper_service import (')>1 and dup in t:t=t.replace(dup,'',1);print('Removed: duplicate service import')
 ast.parse(t);assert 'create_sleeper_hub_blueprint' in t and 'create_sleeper_intelligence_blueprint' in t;A.write_text(t)
 for p in redundant+artifacts:archive(p)
 active=[A,R/'services/sleeper_service.py',R/'services/import_rankings.py',R/'sleeper_hub.py',R/'sleeper_intelligence.py',R/'sleeper_intelligence_routes.py']
 for p in active:py_compile.compile(str(p),doraise=True)
 checks={'legacy_removed':'sleeper_api_routes' not in A.read_text(),'hub_registered':'create_sleeper_hub_blueprint(get_db_connection)' in A.read_text(),'intelligence_registered':'create_sleeper_intelligence_blueprint(get_db_connection)' in A.read_text(),'migrations':all((R/'migrations'/n).exists() for n in ['001_mock_draft_lab.sql','002_season_sandbox.sql','003_owner_operations.sql','004_weekly_intelligence.sql','005_sleeper_full_integration.sql'])}
 if not all(checks.values()):raise RuntimeError(json.dumps(checks))
 (R/'SLEEPER_CONSOLIDATION_REPORT.json').write_text(json.dumps({'status':'pass','backup':str(K.relative_to(R)),'checks':checks,'canonical_client':'services/sleeper_service.py','canonical_sync':'sleeper_hub.py','canonical_intelligence':'sleeper_intelligence.py'},indent=2))
 print('PASS: Sleeper architecture consolidated');print('Backup:',K.relative_to(R));print('Restart app and verify /sleeper/, /sleeper-intelligence/, /draftboard')
if __name__=='__main__':main()
