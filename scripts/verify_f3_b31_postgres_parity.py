#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEST_FILE = "tests/test_f3_b31_postgres_parity.py"
OUT = Path("audit/f3_b31/postgres_parity")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "-q", TEST_FILE]
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, text=True, capture_output=True, env=os.environ.copy())
    finished = datetime.now(timezone.utc)
    factory_set = bool(os.environ.get("F3_POSTGRES_STORE_FACTORY"))
    evidence = {
        "phase": "F3-B.3.1",
        "scope": "InMemoryDraftEventStore and PostgresDraftEventStore contract parity",
        "postgres_factory_configured": factory_set,
        "batch_size": int(os.environ.get("F3_PARITY_BATCH_SIZE", "1000")),
        "replay_passes": int(os.environ.get("F3_PARITY_REPLAY_PASSES", "10")),
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
        "# F3-B.3.1 PostgreSQL Parity Verification\n\n"
        f"- Result: **{'PASS' if evidence['passed'] else 'FAIL'}**\n"
        f"- PostgreSQL factory configured: `{factory_set}`\n"
        f"- Batch size: `{evidence['batch_size']}`\n"
        f"- Replay passes: `{evidence['replay_passes']}`\n"
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
