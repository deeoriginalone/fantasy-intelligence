#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
R=Path.cwd();P=Path(__file__).parent;A=R/'app.py';T=R/'templates/draftboard.html'
def run(x):print('+',' '.join(x),flush=True);subprocess.run(x,cwd=R,check=True)
if not A.exists() or not T.exists():raise SystemExit('Run from project root')
a=A.read_text();t=T.read_text()
if 'Recommendation explainability batch 4A' in a:raise SystemExit('Already installed')
for x in ['    draft_outcome_status = log_and_resolve(','        draft_outcome_status=draft_outcome_status,','app.register_blueprint(create_sandbox_blueprint(get_db_connection))']:
 if x not in a:raise SystemExit('Missing app.py anchor: '+x)
heading='<h2>🏅 Top 5 Recommendations</h2>'
if heading not in t:raise SystemExit('Missing template heading anchor')
run([sys.executable,'-m','pytest','-q']);B=R/'backups'/('recommendation-explainability-'+datetime.now().strftime('%Y%m%d-%H%M%S'));B.mkdir(parents=True);(B/'templates').mkdir();shutil.copy2(A,B/'app.py');shutil.copy2(T,B/'templates/draftboard.html')
shutil.copy2(P/'recommendation_explainer.py',R/'recommendation_explainer.py');shutil.copy2(P/'test_recommendation_explainer.py',R/'tests/test_recommendation_explainer.py')
a='from recommendation_explainer import build_explanation, blueprint as recommendation_blueprint, persist as persist_explanation\n'+a
anchor='    draft_outcome_status = log_and_resolve('
block='    # === Recommendation explainability batch 4A ===\n    recommendation_explanation = build_explanation(top_recommendations, player_survival, expected_value_analysis, draft_decision_plan)\n    recommendation_explanation["audit_id"] = persist_explanation(get_db_connection, SLEEPER_DRAFT_ID, sleeper_draft_signals.get("pick_count", 0), recommendation_explanation)\n\n'
a=a.replace(anchor,block+anchor,1).replace('        draft_outcome_status=draft_outcome_status,','        draft_outcome_status=draft_outcome_status,\n        recommendation_explanation=recommendation_explanation,',1)
m='app.register_blueprint(create_sandbox_blueprint(get_db_connection))';a=a.replace(m,'# === Recommendation explainability batch 4A route ===\napp.register_blueprint(recommendation_blueprint(get_db_connection, SLEEPER_DRAFT_ID))\n'+m,1);A.write_text(a);T.write_text(t.replace(heading,(P/'panel.html').read_text()+heading,1))
try:run([sys.executable,'-m','py_compile','app.py','recommendation_explainer.py']);run([sys.executable,'-m','pytest','-q','tests/test_recommendation_explainer.py']);run([sys.executable,'-m','pytest','-q'])
except Exception:
 shutil.copy2(B/'app.py',A);shutil.copy2(B/'templates/draftboard.html',T)
 for n in ['recommendation_explainer.py','tests/test_recommendation_explainer.py']:
  q=R/n
  if q.exists():q.unlink()
 print('FAILED; restored from',B);raise
print('BATCH 4A COMPLETE');print('Backup:',B);print('API: /recommendation-explainer/')
