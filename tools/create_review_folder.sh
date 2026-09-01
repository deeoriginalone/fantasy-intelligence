#!/usr/bin/env bash
set -e

OUT="review_bundle"

rm -rf "$OUT"
mkdir -p "$OUT"

copy_file() {
    if [ -f "$1" ]; then
        mkdir -p "$OUT/$(dirname "$1")"
        cp "$1" "$OUT/$1"
        echo "Copied: $1"
    fi
}

echo "Collecting core files..."

copy_file app.py
copy_file config.py

copy_file draft_state_hardening.py
copy_file draft_operations_hardening.py
copy_file draft_readiness.py
copy_file draft_health_routes.py

copy_file recommendation_explainer.py
copy_file monte_carlo_survival.py
copy_file survival_calibration.py

copy_file templates/draftboard.html

copy_file README.md
copy_file PROJECT_STATUS.md
copy_file PROJECT_STATE.md
copy_file SEASON_READINESS.md

copy_file pytest.ini

echo
echo "Collecting matching tests..."

mkdir -p "$OUT/tests"

find tests -type f 2>/dev/null | grep -E \
'test_(draft|readiness|recommendation|survival)' \
| while read file; do
    mkdir -p "$OUT/$(dirname "$file")"
    cp "$file" "$OUT/$file"
done

echo
echo "Saving git context..."

git log -1 --stat > "$OUT/HEAD_COMMIT.txt"
git status > "$OUT/GIT_STATUS.txt"

echo
echo "Creating zip..."

zip -r review_bundle.zip "$OUT"

echo
echo "Done:"
echo "review_bundle.zip"
