#!/usr/bin/env python3
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
TEST_FILE="tests/test_f3_c2_draft_recommendation_publication.py"
OUT=Path("audit/f3_c2/verification")
OUT.mkdir(parents=True, exist_ok=True)
command=[sys.executable,"-m","pytest","-q",TEST_FILE]
started=datetime.now(timezone.utc); result=subprocess.run(command,text=True,capture_output=True); finished=datetime.now(timezone.utc)
evidence={"phase":"F3-C.2","scope":"guarded mock-draft recommendation publication","command":command,"started_at":started.isoformat(),"finished_at":finished.isoformat(),"return_code":result.returncode,"passed":result.returncode==0,"stdout":result.stdout,"stderr":result.stderr}
(OUT/"verification.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
(OUT/"pytest_output.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
(OUT/"VERIFICATION_RESULTS.md").write_text("# F3-C.2 Verification Results\n\n"+f"- Result: **{'PASS' if evidence['passed'] else 'FAIL'}**\n- Return code: `{result.returncode}`\n\n```text\n"+result.stdout+result.stderr+"\n```\n",encoding="utf-8")
print(result.stdout,end=""); print(f"Evidence: {OUT}")
raise SystemExit(result.returncode)
