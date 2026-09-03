#!/usr/bin/env python3
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEST_FILE = "tests/test_f3_b4_readiness.py"
OUT = Path("audit/f3_b4/verification")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", TEST_FILE]
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, text=True, capture_output=True)
    finished = datetime.now(timezone.utc)
    evidence = {
        "phase": "F3-B.4",
        "scope": "centralized read-only readiness and publication gates",
        "command": command,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    (OUT / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (OUT / "pytest_output.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    (OUT / "VERIFICATION_RESULTS.md").write_text(
        "# F3-B.4 Readiness Verification Results\n\n"
        f"- Result: **{'PASS' if evidence['passed'] else 'FAIL'}**\n"
        f"- Started: `{evidence['started_at']}`\n"
        f"- Finished: `{evidence['finished_at']}`\n"
        f"- Return code: `{result.returncode}`\n\n"
        "## Test output\n\n```text\n" + result.stdout + result.stderr + "\n```\n",
        encoding="utf-8",
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    print(f"Evidence: {OUT}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
