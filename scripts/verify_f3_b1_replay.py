#!/usr/bin/env python3
"""Run the F3-B.1 replay suite and write machine-readable evidence."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEST_FILE = "tests/test_f3_b1_replay_validation.py"
EVIDENCE_DIR = Path("audit/f3_b1/replay_validation")


def main():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", TEST_FILE]
    started_at = datetime.now(timezone.utc)
    completed = subprocess.run(command, text=True, capture_output=True)
    finished_at = datetime.now(timezone.utc)

    evidence = {
        "phase": "F3-B.1",
        "scope": "large-batch replay validation against DraftEventProcessor and InMemoryDraftEventStore",
        "command": command,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "return_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }

    json_path = EVIDENCE_DIR / "verification.json"
    txt_path = EVIDENCE_DIR / "pytest_output.txt"
    md_path = EVIDENCE_DIR / "VERIFICATION_RESULTS.md"

    json_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    txt_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    md_path.write_text(
        "# F3-B.1 Replay Verification Results\n\n"
        f"- Result: **{'PASS' if evidence['passed'] else 'FAIL'}**\n"
        f"- Started: `{evidence['started_at']}`\n"
        f"- Finished: `{evidence['finished_at']}`\n"
        f"- Command: `{' '.join(command)}`\n"
        f"- Return code: `{completed.returncode}`\n\n"
        "## Test output\n\n```text\n"
        + completed.stdout
        + completed.stderr
        + "\n```\n",
        encoding="utf-8",
    )

    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    print(f"Evidence: {EVIDENCE_DIR}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
