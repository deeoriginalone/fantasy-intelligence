#!/usr/bin/env python3
import ast,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
R=Path.cwd();P=Path(__file__).parent;A=R/'app.py'
def run(x):print('+',' '.join(x));subprocess.run(x,cwd=R,check=True)
t=A.read_text();tree=ast.parse(t);lines=t.splitlines(); repl={'track_draft':["def track_draft():","    return track(request,get_db_connection,fetch_available_players,SLEEPER_DRAFT_ID)"],'undo_draft_pick':["def undo_draft_pick():","    return undo(request,get_db_connection,SLEEPER_DRAFT_ID)"]};nodes={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in repl}
if set(nodes)!=set(repl):raise SystemExit('Expected draft functions missing')
if 'Draft operations hardening batch 2' in t:raise SystemExit('Already installed')
run([sys.executable,'-m','pytest','-q']);B=R/'backups'/('draft-operations-'+datetime.now().strftime('%Y%m%d-%H%M%S'));B.mkdir(parents=True);shutil.copy2(A,B/'app.py')
for n in sorted(nodes.values(),key=lambda x:x.lineno,reverse=True):lines[n.lineno-1:n.end_lineno]=repl[n.name]
text='from draft_operations_hardening import blueprint,track,undo\n'+'\n'.join(lines)+'\n';m='app.register_blueprint(create_sandbox_blueprint(get_db_connection))';h='# === Draft operations hardening batch 2 ===\napp.register_blueprint(blueprint(get_db_connection,SLEEPER_DRAFT_ID))\n# === End draft operations hardening batch 2 ===\n';
if m not in text:raise SystemExit('Registration marker missing')
shutil.copy2(P/'draft_operations_hardening.py',R/'draft_operations_hardening.py');shutil.copy2(P/'test_draft_operations_hardening.py',R/'tests/test_draft_operations_hardening.py');A.write_text(text.replace(m,h+m,1))
try:run([sys.executable,'-m','py_compile','app.py','draft_operations_hardening.py']);run([sys.executable,'-m','pytest','-q','tests/test_draft_operations_hardening.py']);run([sys.executable,'-m','pytest','-q'])
except:shutil.copy2(B/'app.py',A);print('FAILED; app.py restored from',B);raise
print('BATCH 2 COMPLETE');print('Backup:',B);print('Health: /draft-operations/health')
