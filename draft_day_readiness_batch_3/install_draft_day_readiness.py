#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
R=Path.cwd();P=Path(__file__).parent
FILES=['draft_readiness.py','draft_health_routes.py','tests/test_draft_day_readiness.py']
def run(x):print('+',' '.join(x),flush=True);subprocess.run(x,cwd=R,check=True)
if not (R/'app.py').exists():raise SystemExit('Run from project root')
run([sys.executable,'-m','pytest','-q'])
B=R/'backups'/('draft-day-readiness-'+datetime.now().strftime('%Y%m%d-%H%M%S'));B.mkdir(parents=True)
for n in FILES:
 s=R/n
 if s.exists():(B/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,B/n)
shutil.copy2(P/'draft_readiness.py',R/'draft_readiness.py');shutil.copy2(P/'draft_health_routes.py',R/'draft_health_routes.py');shutil.copy2(P/'test_draft_day_readiness.py',R/'tests/test_draft_day_readiness.py')
try:
 run([sys.executable,'-m','py_compile','draft_readiness.py','draft_health_routes.py']);run([sys.executable,'-m','pytest','-q','tests/test_draft_day_readiness.py']);run([sys.executable,'-m','pytest','-q'])
except Exception:
 for n in FILES:
  old=B/n;dst=R/n
  if old.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,dst)
  elif dst.exists():dst.unlink()
 print('VALIDATION FAILED; files restored from',B);raise
print('BATCH 3 COMPLETE');print('Backup:',B);print('JSON: /draft-health/json');print('Record reconciliation: POST /draft-health/reconcile')
