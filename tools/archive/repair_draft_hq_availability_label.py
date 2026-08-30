#!/usr/bin/env python3
"""Repair and verify the Draft HQ Monte Carlo availability label.

Safe to run after a partial apply_draft_hq_consistency_fixes.py execution.
Changes only templates/draftboard.html and is idempotent.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "draftboard.html"
PLAN = ROOT / "draft_decision_plan.py"
BACKUP_DIR = ROOT / "backups" / "draft-hq-label-repair"


def main() -> int:
    if not TEMPLATE.exists():
        print("STOPPED: templates/draftboard.html is missing", file=sys.stderr)
        return 1

    original = TEMPLATE.read_text(encoding="utf-8")
    updated = original

    # Match the tile label whether it is plain text, split across whitespace,
    # or split by a <br>, <br/>, or <br /> element.
    patterns = [
        r"NEXT[\s-]*PICK\s*<br\s*/?>\s*AVAILABILITY",
        r"NEXT[\s-]*PICK\s+AVAILABILITY",
        r"Next[\s-]*Pick\s*<br\s*/?>\s*Availability",
        r"Next[\s-]*Pick\s+Availability",
    ]

    changed = False
    for pattern in patterns:
        updated, count = re.subn(
            pattern,
            "MONTE CARLO<br>AVAILABILITY",
            updated,
            count=1,
            flags=re.IGNORECASE,
        )
        if count:
            changed = True
            break

    # Accept an already-correct label in either plain or <br>-split form.
    correct_label = bool(
        re.search(
            r"MONTE\s+CARLO(?:\s*<br\s*/?>\s*|\s+)AVAILABILITY",
            updated,
            flags=re.IGNORECASE,
        )
    )
    if not changed and not correct_label:
        print(
            "STOPPED: the availability tile label was not found. No file was changed.",
            file=sys.stderr,
        )
        return 1

    # Verify that the weighted contribution display from the prior partial run
    # remains installed. Do not fail solely on confidence because that lives in
    # draft_decision_plan.py and may be formatted differently.
    weighted_checks = [
        "candidate.weighted_components.need",
        "candidate.weighted_components.scarcity",
        "candidate.weighted_components.strategy",
        "candidate.weighted_components.league",
    ]
    missing_weighted = [item for item in weighted_checks if item not in updated]
    if missing_weighted:
        print(
            "STOPPED: weighted-column changes are incomplete: "
            + ", ".join(missing_weighted)
            + ". No file was changed.",
            file=sys.stderr,
        )
        return 1

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"draftboard.html.{timestamp}.bak"
    shutil.copy2(TEMPLATE, backup)
    TEMPLATE.write_text(updated, encoding="utf-8")

    final = TEMPLATE.read_text(encoding="utf-8")
    final_label = bool(
        re.search(
            r"MONTE\s+CARLO(?:\s*<br\s*/?>\s*|\s+)AVAILABILITY",
            final,
            flags=re.IGNORECASE,
        )
    )
    if not final_label:
        shutil.copy2(backup, TEMPLATE)
        print("STOPPED: post-write label verification failed; template restored", file=sys.stderr)
        return 1

    confidence_status = "not checked"
    if PLAN.exists():
        plan_text = PLAN.read_text(encoding="utf-8")
        confidence_status = (
            "installed"
            if "confidence_score" in plan_text and "confidence_label" in plan_text
            else "legacy aliases not detected"
        )

    print("PASS: Monte Carlo availability tile label repaired")
    print(f"Backup: {backup.relative_to(ROOT)}")
    print("Weighted contribution columns: verified")
    print(f"Unified confidence aliases: {confidence_status}")
    print("Reload /draftboard; restart Flask only if template caching is enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
