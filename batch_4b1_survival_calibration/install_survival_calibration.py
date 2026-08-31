#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
R=Path.cwd();P=Path(__file__).parent;A=R/'app.py';T=R/'templates/draftboard.html'
def run(x):print('+',' '.join(x),flush=True);subprocess.run(x,cwd=R,check=True)
if not A.exists() or not T.exists():raise SystemExit('Run from project root')
a=A.read_text();t=T.read_text()
if 'Survival calibration batch 4B.1' in a:raise SystemExit('Batch 4B.1 already installed')
anchor='    recommendation_explanation = build_explanation(top_recommendations, player_survival, expected_value_analysis, draft_decision_plan)'
render='        recommendation_explanation=recommendation_explanation,'
route='app.register_blueprint(create_sandbox_blueprint(get_db_connection))'
heading='<h2>⏱️ Draft Now vs. Wait</h2>'
[(None if x in a else (_ for _ in ()).throw(SystemExit('Missing app anchor: '+x))) for x in (anchor,render,route)]
if heading not in t:raise SystemExit('Missing Draft Now vs. Wait template heading')
run([sys.executable,'-m','pytest','-q'])
B=R/'backups'/('survival-calibration-'+datetime.now().strftime('%Y%m%d-%H%M%S'));B.mkdir(parents=True);(B/'templates').mkdir();shutil.copy2(A,B/'app.py');shutil.copy2(T,B/'templates/draftboard.html')
shutil.copy2(P/'survival_calibration.py',R/'survival_calibration.py');shutil.copy2(P/'test_survival_calibration.py',R/'tests/test_survival_calibration.py')
a='from survival_calibration import build_comparison as build_survival_comparison, create_blueprint as survival_calibration_blueprint, persist as persist_survival_comparison\n'+a
block='    # === Survival calibration batch 4B.1 ===\n    survival_comparison = build_survival_comparison(recommendation_explanation, monte_carlo, player_survival)\n    survival_comparison["comparison_id"] = persist_survival_comparison(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), survival_comparison)\n    if survival_comparison.get("available"):\n        recommendation_explanation["survival_comparison"] = survival_comparison\n        if survival_comparison.get("severity") == "HIGH":\n            recommendation_explanation.setdefault("warnings", []).append(survival_comparison["message"])'
a=a.replace(anchor,anchor+'\n'+block,1).replace(render,render+'\n        survival_comparison=survival_comparison,',1).replace(route,'# === Survival calibration batch 4B.1 route ===\napp.register_blueprint(survival_calibration_blueprint(get_db_connection, SLEEPER_DRAFT_ID))\n'+route,1)
A.write_text(a);T.write_text(t.replace(heading,(P/'panel.html').read_text()+heading,1))
try:run([sys.executable,'-m','py_compile','app.py','survival_calibration.py']);run([sys.executable,'-m','pytest','-q','tests/test_survival_calibration.py']);run([sys.executable,'-m','pytest','-q'])
except Exception:shutil.copy2(B/'app.py',A);shutil.copy2(B/'templates/draftboard.html',T);print('VALIDATION FAILED; restored from',B);raise
print('BATCH 4B.1 COMPLETE');print('Backup:',B);print('APIs: /survival-comparison/latest /history /accuracy')
