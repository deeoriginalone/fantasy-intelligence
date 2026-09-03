#!/usr/bin/env bash
set -euo pipefail
export F3_TEST_BATCH_SIZE=${F3_TEST_BATCH_SIZE:-1000}
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py \
  tests/test_f3_b4_readiness.py \
  tests/test_f3_c1_publication_gate.py
