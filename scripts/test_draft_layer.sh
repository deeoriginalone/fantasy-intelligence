#!/usr/bin/env bash
set -euo pipefail
export F3_TEST_BATCH_SIZE=${F3_TEST_BATCH_SIZE:-25}
python -m pytest -q \
  tests/test_f3_b1_replay_validation.py \
  tests/test_f3_b2_reconciliation.py \
  tests/test_f3_b3_live_reconciliation.py
