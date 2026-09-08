#!/usr/bin/env python3
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
out=Path("audit/f3_d1/verification");out.mkdir(parents=True,exist_ok=True);cmd=[sys.executable,"-m","pytest","-q","tests/test_f3_d1_sleeper_waiver_intelligence.py"]
s=datetime.now(timezone.utc);r=subprocess.run(cmd,text=True,capture_output=True);f=datetime.now(timezone.utc);e={"phase":"F3-D.1","started_at":s.isoformat(),"finished_at":f.isoformat(),"return_code":r.returncode,"passed":r.returncode==0,"stdout":r.stdout,"stderr":r.stderr}
(out/"verification.json").write_text(json.dumps(e,indent=2)+"\n");(out/"pytest_output.txt").write_text(r.stdout+r.stderr);(out/"VERIFICATION_RESULTS.md").write_text(f"# F3-D.1 Verification\n\n- Result: **{'PASS' if e['passed'] else 'FAIL'}**\n\n```text\n{r.stdout}{r.stderr}\n```\n");print(r.stdout,end="");print(f"Evidence: {out}");raise SystemExit(r.returncode)
