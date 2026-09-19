#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_FILES = [
    REPO_ROOT / "PROJECT_STATUS.md",
    REPO_ROOT / "PROJECT_STATE.md",
    REPO_ROOT / "DEVELOPMENT_ROADMAP.md",
    REPO_ROOT / "docs" / "NEXT_SESSION_HANDOFF.md",
]


def current_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def current_branch():
    return subprocess.check_output(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def update_file(path: Path, head: str, branch: str):
    text = path.read_text(encoding="utf-8")

    pattern = re.compile(
        r"(?im)^(\s*[-*]?\s*HEAD:\s*)([0-9a-f]{7,40})(\s*)$"
    )

    new_text, count = pattern.subn(
        rf"\g<1>{head}\g<3>",
        text,
        count=1,
    )

    if count == 0:
        print(f"[WARN] HEAD line not found: {path}")
        return False

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print(f"[UPDATED] {path}")

    return True


def main():
    head = current_head()
    branch = current_branch()

    print(f"Current HEAD: {head}")
    print(f"Current Branch: {branch}")
    print()

    success = True

    for path in CANONICAL_FILES:
        if not path.exists():
            print(f"[MISSING] {path}")
            success = False
            continue

        if not update_file(path, head, branch):
            success = False

    print()
    print("Done.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
