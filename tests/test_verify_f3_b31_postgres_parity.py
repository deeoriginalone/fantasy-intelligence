import os
from types import SimpleNamespace
import json

from scripts import verify_f3_b31_postgres_parity as verifier


def test_pytest_counts_distinguish_skips_and_failures():
    assert verifier._pytest_counts("18 passed, 20 subtests passed") == {
        "passed": 18,
        "failed": 0,
        "skipped": 0,
    }
    assert verifier._pytest_counts("9 passed, 9 skipped, 10 subtests passed") == {
        "passed": 9,
        "failed": 0,
        "skipped": 9,
    }


def test_verifier_blocks_without_isolated_configuration(monkeypatch):
    monkeypatch.delenv("F3_POSTGRES_STORE_FACTORY", raising=False)
    monkeypatch.delenv("F3_POSTGRES_TEST_DATABASE_URL", raising=False)

    assert verifier.main() == 2


def test_verifier_accepts_only_configured_no_skip_full_gate(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "F3_POSTGRES_STORE_FACTORY",
        "draft_events.postgres_test_factory:create_test_draft_event_store",
    )
    monkeypatch.setenv(
        "F3_POSTGRES_TEST_DATABASE_URL",
        "postgresql://user@localhost/parity_test",
    )
    monkeypatch.setenv("F3_PARITY_BATCH_SIZE", "1000")
    monkeypatch.setenv("F3_PARITY_REPLAY_PASSES", "10")
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=".................. [100%]\n18 passed, 20 subtests passed in 1s\n",
            stderr="",
        ),
    )
    monkeypatch.setattr(verifier, "OUT", tmp_path / "parity")
    monkeypatch.setattr(verifier, "BLOCKED_OUT", tmp_path / "blocked.json")

    assert verifier.main() == 0
    evidence = json.loads(
        (tmp_path / "parity" / "verification.json").read_text(encoding="utf-8")
    )
    assert evidence["passed"] is True
    assert evidence["pytest_counts"] == {
        "passed": 18,
        "failed": 0,
        "skipped": 0,
    }