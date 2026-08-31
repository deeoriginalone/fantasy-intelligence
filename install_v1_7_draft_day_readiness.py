#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import ast,os,py_compile,shutil
import psycopg2
R=Path.cwd();P=R/'payload';A=R/'app.py';T=R/'templates/draftboard.html';BASE=R/'templates/base.html';B=R/'backups/v1-7-draft-readiness'/datetime.now().strftime('%Y%m%d-%H%M%S')
def cp(s,d):d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,d)
def backup(p):
 if p.exists():d=B/p.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
def main():
 req=[A,T,BASE,R/'draft_outcome_tracker.py',R/'model_calibration.py',P/'draft_readiness.py',P/'draft_health_routes.py',P/'templates/draft_health.html',P/'templates/_draft_readiness.html',P/'migrations/007_draft_day_readiness.sql',P/'validate_draft_readiness.py']
 for p in req:
  if not p.exists():raise SystemExit('STOPPED missing '+str(p.relative_to(R)))
 for p in (A,T,BASE,R/'draft_outcome_tracker.py'):backup(p)
 for s,d in [(P/'draft_readiness.py',R/'draft_readiness.py'),(P/'draft_health_routes.py',R/'draft_health_routes.py'),(P/'templates/draft_health.html',R/'templates/draft_health.html'),(P/'templates/_draft_readiness.html',R/'templates/_draft_readiness.html'),(P/'migrations/007_draft_day_readiness.sql',R/'migrations/007_draft_day_readiness.sql'),(P/'validate_draft_readiness.py',R/'validate_draft_readiness.py')]:cp(s,d)
 pw=os.getenv('DB_PASSWORD')
 if not pw:raise SystemExit('STOPPED DB_PASSWORD is not set')
 conn=psycopg2.connect(host=os.getenv('DB_HOST','localhost'),port=os.getenv('DB_PORT','5433'),dbname=os.getenv('DB_NAME','fantasy_intelligence'),user=os.getenv('DB_USER','fantasy'),password=pw);cur=conn.cursor();cur.execute((R/'migrations/007_draft_day_readiness.sql').read_text());conn.commit();cur.close();conn.close()
 a=A.read_text();imports='from draft_readiness import build_draft_readiness, validate_runtime\nfrom draft_health_routes import create_draft_health_blueprint\n'
 if 'from draft_readiness import build_draft_readiness' not in a:
  e=a.find('\n',a.find('from flask import'))+1;a=a[:e]+imports+a[e:]
 rs=a.find('def draftboard():');re=a.find('\n@app.route(',rs+1);re=re if re>=0 else len(a);r=a[rs:re]
 if 'draft_readiness = build_draft_readiness(' not in r:
  anchor='    draft_outcome_status = log_and_resolve('
  pos=r.find(anchor)
  if pos<0:raise RuntimeError('outcome tracker anchor missing')
  block='    readiness_conn = get_db_connection()\n    readiness_cur = readiness_conn.cursor()\n    draft_readiness = build_draft_readiness(readiness_cur, SLEEPER_LEAGUE_ID, 2026, sleeper_draft_signals, current_model_health)\n    draft_validation = validate_runtime(recommendation_candidates, sleeper_draft_signals, current_model_health)\n    readiness_cur.close()\n    readiness_conn.close()\n\n'
  r=r[:pos]+block+r[pos:]
  render='    return render_template(\n        "draftboard.html",\n';r=r.replace(render,render+'        draft_readiness=draft_readiness,\n        draft_validation=draft_validation,\n',1);a=a[:rs]+r+a[re:]
 reg='app.register_blueprint(create_draft_health_blueprint(get_db_connection, SLEEPER_LEAGUE_ID, 2026, build_sleeper_draft_signals, model_health))\n'
 if 'create_draft_health_blueprint(get_db_connection' not in a:
  marker='if __name__ == "__main__":\n' if 'if __name__ == "__main__":\n' in a else "if __name__ == '__main__':\n";a=a.replace(marker,reg+'\n'+marker,1)
 ast.parse(a);A.write_text(a)
 t=T.read_text();inc='{% include "_draft_readiness.html" %}'
 if inc not in t:
  anchor='{% include "_draft_model_health.html" %}'
  if anchor not in t:raise RuntimeError('model health include missing')
  t=t.replace(anchor,inc+'\n'+anchor,1);T.write_text(t)
 base=BASE.read_text();link="<a href=\"{{ url_for('draft_health.home') }}\">Readiness</a>"
 if 'draft_health.home' not in base:
  marker="<a href=\"{{ url_for('draft_accuracy.home') }}\">";i=base.find(marker)
  if i<0:raise RuntimeError('Accuracy navigation anchor missing')
  close=base.find('</a>',i)+4;base=base[:close]+link+base[close:];BASE.write_text(base)
 for p in (A,R/'draft_readiness.py',R/'draft_health_routes.py',R/'validate_draft_readiness.py'):py_compile.compile(str(p),doraise=True)
 print('PASS v1.7 Draft Day Readiness installed');print('Backup:',B.relative_to(R));print('Run python validate_draft_readiness.py and open /draft-health/')
if __name__=='__main__':main()
