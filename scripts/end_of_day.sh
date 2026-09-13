#!/usr/bin/env bash

set -euo pipefail

echo
echo "====================================="
echo " Fantasy Intelligence End of Day"
echo "====================================="
echo

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: venv/bin/activate was not found."
    exit 1
fi

mkdir -p docs/database
mkdir -p notebook_bundle
mkdir -p .continuity

echo "[1/10] Verifying required source files..."

for f in \
    PROJECT_STATUS.md \
    PROJECT_STATE.md \
    DEVELOPMENT_ROADMAP.md \
    docs/NEXT_SESSION_HANDOFF.md \
    tools/generate_notebook_bundle.py \
    tools/validate_notebook_bundle.py \
    tools/generate_bundle_change_report.py \
    tools/validate_canonical_sync.py \
    tools/generate_session_recovery_pack.py
do
    if [ ! -f "$f" ]; then
        echo "ERROR: missing required file: $f"
        exit 1
    fi
done

echo "[2/10] Generating notebook bundle..."
python tools/generate_notebook_bundle.py

echo
echo "[3/10] Validating notebook bundle..."
python tools/validate_notebook_bundle.py

echo
echo "[4/10] Creating bundle change report..."
python tools/generate_bundle_change_report.py

echo
echo "[5/10] Validating canonical memory synchronization..."

set +e
python tools/validate_canonical_sync.py
CANONICAL_RESULT=$?
set -e

if [ "$CANONICAL_RESULT" -ne 0 ]; then
    echo
    echo "WARNING: canonical memory files are not synchronized."
    echo "See notebook_bundle/CANONICAL_SYNC_VALIDATION.md"
    echo "The continuity pipeline will continue without guessing."
fi

echo
echo "[6/10] 

echo
echo "[Working Tree Classification]"
python tools/classify_working_tree.py

Generating session recovery pack..."
python tools/generate_session_recovery_pack.py

echo
echo "[7/10] Capturing repository checkpoint..."

{
    echo "# Repository Checkpoint"
    echo
    echo "Generated: $(date)"
    echo
    echo "## Branch"
    git branch --show-current
    echo
    echo "## HEAD"
    git rev-parse HEAD
    echo
    echo "## Recent Commits"
    git log --oneline --decorate -15
    echo
    echo "## Repository Status"
    git status --short --branch
    echo
    echo "## Diff Summary"
    git diff --stat
} > docs/REPOSITORY_CHECKPOINT.md

cp docs/REPOSITORY_CHECKPOINT.md \
    notebook_bundle/REPOSITORY_CHECKPOINT.md

echo
echo "[8/10] Refreshing database continuity docs..."

for f in MIGRATIONS.md PARITY_STATUS.md SCHEMA.md
do
    if [ ! -f "notebook_bundle/$f" ]; then
        echo "ERROR: missing notebook bundle file: $f"
        exit 1
    fi

    cp "notebook_bundle/$f" "docs/database/$f"
done

echo
echo "[9/10] Repacking completed continuity bundle..."
tar -czf notebook_bundle.tar.gz notebook_bundle

echo
echo "[10/10] Verifying final archive..."

tar -tzf notebook_bundle.tar.gz > /dev/null

echo
echo "====================================="
echo " Continuity Summary"
echo "====================================="
echo

echo "Bundle:"
ls notebook_bundle

echo
echo "Archive:"
ls -lh notebook_bundle.tar.gz

echo
echo "Bundle Validation:"
grep -E "Result:|Sensitive patterns absent:" \
    notebook_bundle/BUNDLE_VALIDATION.md || true

echo
echo "Canonical Sync:"
grep -E "Result:|Branch synchronized:|HEAD synchronized:|Next milestone consistent:" \
    notebook_bundle/CANONICAL_SYNC_VALIDATION.md || true

echo
echo "Bundle Changes:"
grep -E "First recorded bundle:|Added files:|Removed files:|Modified files:|Unchanged files:" \
    notebook_bundle/CHANGE_REPORT.md || true

echo
echo "Repository:"
git branch --show-current
git rev-parse --short HEAD

echo
echo "Session recovery file:"
echo "notebook_bundle/SESSION_START.md"

echo
echo "End-of-day continuity capture complete."
echo
