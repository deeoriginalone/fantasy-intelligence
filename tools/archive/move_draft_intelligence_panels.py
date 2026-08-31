#!/usr/bin/env python3
"""Move Draft HQ intelligence panels above the Player Draft Board.

Run from the fantasy-intelligence project root:
    python move_draft_intelligence_panels.py

The script is idempotent and changes only templates/draftboard.html.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "draftboard.html"
BACKUP_DIR = ROOT / "backups" / "draft-intelligence-layout"

INCLUDES = [
    '{% include "_sleeper_draft_signals.html" %}',
    '{% include "_sleeper_recommendation_overlay.html" %}',
    '{% include "_player_survival_probability.html" %}',
]

# The production template is compressed onto long lines. Match the exact
# visible Player Draft Board opening while tolerating common whitespace forms.
BOARD_MARKERS = [
    '<section class="card"><h2>Player Draft Board</h2>',
    '<section class="card">\n<h2>Player Draft Board</h2>',
    '<h2>Player Draft Board</h2>',
]


def main() -> int:
    if not TEMPLATE.exists():
        print("STOPPED: templates/draftboard.html was not found", file=sys.stderr)
        return 1

    original = TEMPLATE.read_text(encoding="utf-8")

    missing_partials = []
    for include in INCLUDES:
        partial_name = include.split('"')[1]
        if not (ROOT / "templates" / partial_name).exists():
            missing_partials.append(partial_name)
    if missing_partials:
        print(
            "STOPPED: missing intelligence partial(s): "
            + ", ".join(missing_partials),
            file=sys.stderr,
        )
        return 1

    marker = next((item for item in BOARD_MARKERS if item in original), None)
    if marker is None:
        print(
            "STOPPED: Player Draft Board heading anchor was not found. "
            "No file was changed.",
            file=sys.stderr,
        )
        return 1

    # Remove all current copies so re-running cannot create duplicates.
    updated = original
    for include in INCLUDES:
        updated = updated.replace(include, "")

    # Remove whitespace left by the former bottom-of-page includes.
    while "\n\n\n" in updated:
        updated = updated.replace("\n\n\n", "\n\n")

    decision_block = (
        '\n<!-- Draft decision intelligence: keep above the full player board -->\n'
        + "\n".join(INCLUDES)
        + "\n<!-- End draft decision intelligence -->\n"
    )
    updated = updated.replace(marker, decision_block + marker, 1)

    # Validate exact uniqueness and placement before writing.
    for include in INCLUDES:
        if updated.count(include) != 1:
            print(
                f"STOPPED: expected exactly one {include}, "
                f"found {updated.count(include)}. No file was changed.",
                file=sys.stderr,
            )
            return 1

    board_position = updated.find(marker)
    positions = [updated.find(include) for include in INCLUDES]
    if not (
        0 <= positions[0] < positions[1] < positions[2] < board_position
    ):
        print(
            "STOPPED: intelligence panel ordering validation failed. "
            "No file was changed.",
            file=sys.stderr,
        )
        return 1

    # Ensure none of the panels remain after the player-board heading.
    board_tail = updated[board_position:]
    if any(include in board_tail for include in INCLUDES):
        print(
            "STOPPED: an intelligence include still exists below the player board. "
            "No file was changed.",
            file=sys.stderr,
        )
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / (
        "draftboard.html."
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + ".bak"
    )
    shutil.copy2(TEMPLATE, backup)
    TEMPLATE.write_text(updated, encoding="utf-8")

    print("PASS: Draft intelligence panels moved above Player Draft Board")
    print(f"Backup: {backup.relative_to(ROOT)}")
    print("Panel order:")
    print("  1. Live Sleeper Draft Pressure")
    print("  2. Sleeper-Aware Recommendation Overlay")
    print("  3. Next-Pick Player Survival")
    print("  4. Player Draft Board")
    print("Reload /draftboard; an app restart is normally not required for templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
