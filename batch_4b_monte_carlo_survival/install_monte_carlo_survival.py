#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
R=Path.cwd();P=Path(__file__).parent;A=R/'app.py';T=R/'templates/draftboard.html'
def run(x):print('+',' '.join(x),flush=True);subprocess.run(x,cwd=R,check=True)
if not A.exists() or not T.exists():raise SystemExit('Run from project root')
a=A.read_text();t=T.read_text()
if 'Monte Carlo survival batch 4B' in a:raise SystemExit('Batch 4B already installed')
anchors=['    expected_value_analysis = build_expected_value_analysis(','        monte_carlo=monte_carlo,','app.register_blueprint(create_sandbox_blueprint(get_db_connection))']
for x in anchors:
 if x not in a:raise SystemExit('Missing app anchor: '+x)
heading='<h2>🎲 Availability Simulation</h2>'
if heading not in t:raise SystemExit('Missing availability template heading')
run([sys.executable,'-m','pytest','-q']);B=R/'backups'/('monte-carlo-survival-'+datetime.now().strftime('%Y%m%d-%H%M%S'));B.mkdir(parents=True);(B/'templates').mkdir();shutil.copy2(A,B/'app.py');shutil.copy2(T,B/'templates/draftboard.html')
shutil.copy2(P/'monte_carlo_survival.py',R/'monte_carlo_survival.py');shutil.copy2(P/'test_monte_carlo_survival.py',R/'tests/test_monte_carlo_survival.py')
a='from monte_carlo_survival import blueprint as monte_carlo_survival_blueprint, enhance as enhance_monte_carlo_survival, persist as persist_monte_carlo_survival\n'+a
anchor='    expected_value_analysis = build_expected_value_analysis('
block='    # === Monte Carlo survival batch 4B ===\n    monte_carlo = enhance_monte_carlo_survival(monte_carlo, pick_forecast, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), top_recommendations)\n    monte_carlo["run_id"] = persist_monte_carlo_survival(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), monte_carlo)\n\n'
a=a.replace(anchor,block+anchor,1);m='app.register_blueprint(create_sandbox_blueprint(get_db_connection))';a=a.replace(m,'# === Monte Carlo survival batch 4B route ===\napp.register_blueprint(monte_carlo_survival_blueprint(get_db_connection, SLEEPER_DRAFT_ID))\n'+m,1);A.write_text(a);T.write_text(t.replace(heading,(P/'panel.html').read_text()+heading,1))
try:run([sys.executable,'-m','py_compile','app.py','monte_carlo_survival.py']);run([sys.executable,'-m','pytest','-q','tests/test_monte_carlo_survival.py']);run([sys.executable,'-m','pytest','-q'])
except Exception:
 shutil.copy2(B/'app.py',A);shutil.copy2(B/'templates/draftboard.html',T)
 for n in ['monte_carlo_survival.py','tests/test_monte_carlo_survival.py']:
  q=R/n
  if q.exists():q.unlink()
 print('VALIDATION FAILED; restored from',B);raise
print('BATCH 4B COMPLETE');print('Backup:',B);print('API: /monte-carlo-survival/')
