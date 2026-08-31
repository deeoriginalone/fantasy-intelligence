#!/usr/bin/env python3
import shutil,subprocess,sys
from pathlib import Path
from datetime import datetime
r=Path.cwd();p=Path(__file__).parent;a=r/'app.py'
marker='app.register_blueprint(create_sandbox_blueprint(get_db_connection))'
text=a.read_text()
if marker not in text: raise SystemExit('Expected app.py marker missing. No changes made.')
if 'Draft state hardening batch 1' in text: raise SystemExit('Already installed.')
subprocess.run([sys.executable,'-m','pytest','-q'],check=True)
b=r/'backups'/('draft-state-hardening-'+datetime.now().strftime('%Y%m%d-%H%M%S'));b.mkdir(parents=True);shutil.copy2(a,b/'app.py')
shutil.copy2(p/'draft_state_hardening.py',r/'draft_state_hardening.py');shutil.copy2(p/'test_draft_state_hardening.py',r/'tests/test_draft_state_hardening.py')
hook="""# === Draft state hardening batch 1 ===
_original_sync_sleeper_draft_picks = sync_sleeper_draft_picks
sync_sleeper_draft_picks = build_hardened_sync(_original_sync_sleeper_draft_picks, get_db_connection, get_draft, get_draft_picks, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID)
app.register_blueprint(create_blueprint(get_db_connection, get_draft, SLEEPER_LEAGUE_ID, SLEEPER_DRAFT_ID))
# === End draft state hardening batch 1 ===
"""
text='from draft_state_hardening import build_hardened_sync, create_blueprint\n'+text.replace(marker,hook+'\n'+marker,1);a.write_text(text)
subprocess.run([sys.executable,'-m','py_compile','app.py','draft_state_hardening.py'],check=True);subprocess.run([sys.executable,'-m','pytest','-q'],check=True)
print('INSTALL COMPLETE');print('Backup:',b);print('Start Flask, then open /draft-hardening/status')
