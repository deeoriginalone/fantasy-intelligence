#!/usr/bin/env bash
set -euo pipefail
python -m pytest -q \
  tests/test_draft_event_pipeline.py \
  tests/test_f3_b4_readiness.py \
  tests/test_f3_c1_publication_gate.py
