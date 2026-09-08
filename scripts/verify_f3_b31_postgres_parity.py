#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

TEST_FILE = "tests/test_f3_b31_postgres_parity.py"
OUT = Path("audit/f3_b31/postgres_parity")
BLOCKED_OUT = OUT / "verification_blocked.json"
EXPECTED_TESTS = 18


def _pytest_counts(output):
    match = re.search(
        r"(?P<passed>\d+) passed(?:, (?P<failed>\d+) failed)?(?:, (?P<skipped>\d+) skipped)?",
        output,
    )
    if not match:
        return None
    return {
        "passed": int(match.group("passed")),
        "failed": int(match.group("failed") or 0),
        "skipped": int(match.group("skipped") or 0),
    }


def main():
    factory_set = bool(os.environ.get("F3_POSTGRES_STORE_FACTORY"))
    dsn = os.environ.get("F3_POSTGRES_TEST_DATABASE_URL")
    dsn_set = bool(dsn)
    database_name = (urlparse(dsn).path or "").lstrip("/").lower() if dsn else ""
    isolated_database = "test" in database_name or "parity" in database_name
    batch_size = int(os.environ.get("F3_PARITY_BATCH_SIZE", "1000"))
    replay_passes = int(os.environ.get("F3_PARITY_REPLAY_PASSES", "10"))
    if (
        not factory_set
        or not dsn_set
        or not isolated_database
        or batch_size != 1000
        or replay_passes != 10
    ):
        BLOCKED_OUT.parent.mkdir(parents=True, exist_ok=True)
        BLOCKED_OUT.write_text(
            json.dumps(
                {
                    "phase": "F3-B.3.1",
                    "status": "BLOCKED",
                    "postgres_factory_configured": factory_set,
                    "isolated_dsn_configured": dsn_set,
                    "isolated_database_scope": isolated_database,
                    "batch_size": batch_size,
                    "replay_passes": replay_passes,
                    "reason": "Required isolated PostgreSQL configuration was unavailable or not full-gate scoped.",
                    "existing_evidence_preserved": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            "BLOCKED: F3_POSTGRES_STORE_FACTORY and "
            "F3_POSTGRES_TEST_DATABASE_URL must target a test/parity database "
            "with the full 1000-event/10-replay configuration; existing evidence "
            "was preserved.",
            file=sys.stderr,
        )
        return 2

    command = [sys.executable, "-m", "pytest", "-q", TEST_FILE]
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, text=True, capture_output=True, env=os.environ.copy())
    finished = datetime.now(timezone.utc)
    output = result.stdout + result.stderr
    counts = _pytest_counts(output)
    parity_passed = (
        factory_set
        and dsn_set
        and result.returncode == 0
        and counts is not None
        and counts["passed"] == EXPECTED_TESTS
        and counts["failed"] == 0
        and counts["skipped"] == 0
    )
    evidence = {
        "phase": "F3-B.3.1",
        "scope": "InMemoryDraftEventStore and PostgresDraftEventStore contract parity",
        "postgres_factory_configured": factory_set,
        "isolated_dsn_configured": dsn_set,
        "batch_size": batch_size,
        "replay_passes": replay_passes,
        "command": command,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "return_code": result.returncode,
        "passed": parity_passed,
        "pytest_counts": counts,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (OUT / "pytest_output.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    (OUT / "VERIFICATION_RESULTS.md").write_text(
        "# F3-B.3.1 PostgreSQL Parity Verification\n\n"
        f"- Result: **{'PASS' if evidence['passed'] else 'FAIL'}**\n"
        f"- PostgreSQL factory configured: `{factory_set}`\n"
        f"- Isolated DSN configured: `{dsn_set}`\n"
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
    return result.returncode if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
